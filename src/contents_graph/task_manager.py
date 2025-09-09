import os
import redis
import json
import uuid
import time
from enum import Enum
from typing import Dict, Optional
import logger_init
from .celery_app import celery_app
from .tasks import process_meta2graph, process_retrieval_graph

# logger 초기화
try:
    logger = logger_init.get_logger()
    if logger is None:
        # fallback logger
        import logging
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
except:
    # fallback logger
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"

class TaskStatusCode(int, Enum):
    PENDING = 200
    PROGRESS = 201
    SUCCESS = 202
    FAILURE = 203
    REVOKED = 204

class TaskManager:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True
        )
        self.task_prefix = "media_graph_task:"
    
    def create_task(self, data: dict, task_name: str) -> str:
        """새로운 태스크를 생성하고 Celery에 제출"""
        task_id = f"{task_name}_{str(uuid.uuid4())}"
        
        # Redis에 태스크 정보 저장
        task_info = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "status_code": TaskStatusCode.PENDING,
            "data": data,
            "result": None,
            "progress": 0.0,
            "created_at": time.time(),
            "celery_task_id": None
        }
        
        self.redis_client.setex(
            f"{self.task_prefix}{task_id}",
            3600,  # 1시간 TTL
            json.dumps(task_info)
        )
        
        logger.info(f"Created task: {task_id}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """태스크 정보를 Redis에서 가져오기"""
        task_data = self.redis_client.get(f"{self.task_prefix}{task_id}")
        if not task_data:
            return None
        
        task_info = json.loads(task_data)
        
        # Celery 태스크가 있다면 상태 업데이트
        if task_info.get("celery_task_id"):
            self._update_task_from_celery(task_info)
        
        return task_info
    
    def _update_task_from_celery(self, task_info: dict):
        """Celery 태스크 상태를 확인하고 업데이트"""
        celery_task_id = task_info["celery_task_id"]
        celery_result = celery_app.AsyncResult(celery_task_id)
        
        if celery_result.state == 'PENDING':
            task_info["status"] = TaskStatus.PENDING
            task_info["status_code"] = TaskStatusCode.PENDING
        elif celery_result.state == 'PROGRESS':
            task_info["status"] = TaskStatus.PROGRESS
            task_info["status_code"] = TaskStatusCode.PROGRESS
            if celery_result.info:
                task_info["progress"] = celery_result.info.get("progress", 0.0)
        elif celery_result.state == 'SUCCESS':
            task_info["status"] = TaskStatus.SUCCESS
            task_info["status_code"] = TaskStatusCode.SUCCESS
            task_info["result"] = celery_result.result
            task_info["progress"] = 100.0
        elif celery_result.state == 'FAILURE':
            task_info["status"] = TaskStatus.FAILURE
            task_info["status_code"] = TaskStatusCode.FAILURE
            task_info["result"] = {"error": str(celery_result.info)}
        elif celery_result.state == 'REVOKED':
            task_info["status"] = TaskStatus.REVOKED
            task_info["status_code"] = TaskStatusCode.REVOKED
        
        # Redis에 업데이트된 정보 저장
        self.redis_client.setex(
            f"{self.task_prefix}{task_info['task_id']}",
            3600,
            json.dumps(task_info)
        )
    
    def submit_meta2graph_task(self, metadata: dict, config: dict) -> str:
        """Meta2Graph 태스크를 Celery에 제출"""
        task_id = self.create_task({"metadata": metadata}, "meta2graph")
        
        # Celery 태스크 제출
        celery_task = process_meta2graph.delay(metadata, config)
        
        # Redis에 Celery 태스크 ID 저장
        task_info = self.get_task(task_id)
        task_info["celery_task_id"] = celery_task.id
        self.redis_client.setex(
            f"{self.task_prefix}{task_id}",
            3600,
            json.dumps(task_info)
        )
        
        logger.info(f"Submitted meta2graph task {task_id} to Celery: {celery_task.id}")
        return task_id
    
    def submit_retrieval_graph_task(self, query: str, tau: float, top_k: int, config: dict) -> str:
        """RetrievalGraph 태스크를 Celery에 제출"""
        task_id = self.create_task({
            "query": query,
            "tau": tau,
            "top_k": top_k
        }, "retrieval_graph")
        
        # Celery 태스크 제출
        celery_task = process_retrieval_graph.delay(query, tau, top_k, config)
        
        # Redis에 Celery 태스크 ID 저장
        task_info = self.get_task(task_id)
        task_info["celery_task_id"] = celery_task.id
        self.redis_client.setex(
            f"{self.task_prefix}{task_id}",
            3600,
            json.dumps(task_info)
        )
        
        logger.info(f"Submitted retrieval_graph task {task_id} to Celery: {celery_task.id}")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """태스크 취소"""
        task_info = self.get_task(task_id)
        if not task_info:
            return False
        
        if task_info.get("celery_task_id"):
            # Celery 태스크 취소
            celery_app.control.revoke(task_info["celery_task_id"], terminate=True)
        
        # Redis에서 태스크 상태 업데이트
        task_info["status"] = TaskStatus.REVOKED
        task_info["status_code"] = TaskStatusCode.REVOKED
        self.redis_client.setex(
            f"{self.task_prefix}{task_id}",
            3600,
            json.dumps(task_info)
        )
        
        logger.info(f"Cancelled task: {task_id}")
        return True

# 전역 TaskManager 인스턴스
task_manager = TaskManager()
