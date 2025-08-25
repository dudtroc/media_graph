import asyncio
import time
import logger_init
import concurrent.futures
from contents_graph.queue_manager import retrieve_scenegraph_queue
from contents_graph.request_manager import set_status, set_result, get_task, set_progress, TaskStatus, TaskStatusCode
from contents_graph.core.retrieval_graph_converter import RetrievalGraphConverter
import os
from dotenv import load_dotenv
load_dotenv()

class RetrievalGraphWorker:
    """
    Retrieval-Graph 작업을 처리하는 워커 클래스
    사용자 질문을 triples로 변환하고 검색을 수행하는 워커
    """
    
    def __init__(self, 
                 worker_id: str = "retrieval-graph-worker-0",
                 retrieval_graph_config: dict = None):
        self.logger = logger_init.get_logger()
        self.worker_id = worker_id
        self.logger.info(f"[{self.worker_id}] RetrievalGraph worker initialized and ready.")

        # 환경변수 존재 여부 확인
        api_key_name = retrieval_graph_config.get("api_key_name")
        if not api_key_name:
            raise ValueError("api_key_name이 retrieval_graph_config에 설정되지 않았습니다.")
        
        api_key = os.getenv(api_key_name)
        if not api_key:
            raise ValueError(f"환경변수 '{api_key_name}'이 설정되지 않았습니다. .env 파일을 확인하거나 환경변수를 설정하세요.")
        
        retrieval_graph_config["api_key"] = api_key
        self.retrieval_graph_converter = RetrievalGraphConverter(
            instruction_path=retrieval_graph_config["instruction_path"],
            api_key=api_key,
            model=retrieval_graph_config["model"],
            temperature=retrieval_graph_config.get("temperature", 0.0),
            max_tokens=retrieval_graph_config.get("max_tokens", 256)
        )
        
        # ThreadPoolExecutor 초기화
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    async def run(self):
        while True:
            task = await retrieve_scenegraph_queue.get()
            await self.handle_task(task)

    async def handle_task(self, task: dict):
        task_id = task["task_id"]
        self.logger.info(f"[{self.worker_id}] Processing task: {task_id}")
        
        task = get_task(task_id)
        if not task or task["cancelled"]:
            self.logger.warning(f"[{self.worker_id}] Task {task_id} not found or cancelled")
            set_status(task_id, TaskStatus.CANCELLED)
            return

        try:
            task_data = task["data"]
            
            set_progress(task_id, 0.0)
            set_status(task_id, TaskStatus.RUNNING)

            query = task_data["query"]
            tau = task_data.get("tau", 0.30)
            top_k = task_data.get("top_k", 5)
            
            print(f"query: {query}")
            print(f"tau: {tau}")
            print(f"top_k: {top_k}")

            # ThreadPoolExecutor를 사용하여 별도 쓰레드에서 실행
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self.retrieval_graph_converter, 
                query, tau, top_k
            )
            print(f"result: {result}")
            
            # 결과를 딕셔너리 형태로 저장 (스키마 검증을 위해)
            final_result = {
                "result": result,
                "processed_at": time.time(),
                "worker_id": self.worker_id
            }
            
            set_result(task_id, final_result)
            task = get_task(task_id)

            progress = 100.0
            set_progress(task_id, progress)
            
            self.logger.info(f"[{self.worker_id}] task {task_id}, progress: {progress:.2f}")

            if progress >= 1.0:
                set_status(task_id, TaskStatus.COMPLETED)
                self.logger.info(f"[{self.worker_id}] Finished task {task_id}, progress: {progress:.2f}")

            
        except Exception as e:
            self.logger.error(f"[{self.worker_id}] Error: {e}")
            set_status(task_id, TaskStatus.FAILED, str(e))
    
    def __del__(self):
        # ThreadPoolExecutor 정리
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
