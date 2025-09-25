import os
import sys
import time
from celery import current_task
from dotenv import load_dotenv

# Python 경로에 src 디렉토리 추가
sys.path.insert(0, '/workspace/src')
sys.path.insert(0, '/workspace')

load_dotenv()

from .celery_app import celery_app
from .core.meta_to_graph_converter import MetaToGraphConverter
from .core.retrieval_graph_converter import RetrievalGraphConverter
from .core.scene_graph_analyzer import SceneGraphAnalyzer
from src.db.scene_graph_client import SceneGraphDBClient

# 로거 초기화
try:
    import logger_init
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

@celery_app.task(bind=True, name='src.contents_graph.tasks.process_meta2graph')
def process_meta2graph(self, metadata, video_info, meta2graph_config, graph_anlayzer_config, db_config):
    """
    Meta-to-SceneGraph 작업을 처리하는 Celery 태스크
    """
    task_id = self.request.id
    print(f"[Celery Task] process_meta2graph 시작 - task_id: {task_id}")
    print(f"[Celery Task] metadata 타입: {type(metadata)}")
    print(f"[Celery Task] meta2graph_config: {meta2graph_config}")
    logger.info(f"[Celery] Processing meta2graph task: {task_id}")
    
    try:
        # 환경변수 확인
        api_key_name = meta2graph_config.get("api_key_name")
        if not api_key_name:
            raise ValueError("api_key_name이 meta2graph_config에 설정되지 않았습니다.")
        
        api_key = os.getenv(api_key_name)
        if not api_key:
            raise ValueError(f"환경변수 '{api_key_name}'이 설정되지 않았습니다.")
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 0.0, 'status': 'Initializing...'})
        
        # MetaToGraphConverter 초기화
        meta2graph_config["api_key"] = api_key
        print(f"[Celery Task] MetaToGraphConverter 초기화 시작")
        converter = MetaToGraphConverter(
            instruction_path=meta2graph_config["instruction_path"],
            api_key=meta2graph_config["api_key"],
            model=meta2graph_config["model"],
            assistant_name=meta2graph_config["assistant_name"]
        )
        print(f"[Celery Task] MetaToGraphConverter 초기화 완료")
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 25.0, 'status': 'Processing metadata...'})
        
        # 메타데이터 처리
        print(f"[Celery Task] converter(metadata) 호출 시작")
        scene_graph = converter(metadata)
        print(f"[Celery Task] converter(metadata) 호출 완료 - 결과: {type(scene_graph)}")
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 50.0, 'status': 'Processing metadata...'})

        analyzer = SceneGraphAnalyzer(
            model_path=graph_anlayzer_config["model_path"],
            edge_map_path=graph_anlayzer_config["edge_map_path"],
            sbert_model=graph_anlayzer_config["sbert_model"]
        )
        
        embedding_result = analyzer.analyze_scene_graph(scene_graph)
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 75.0, 'status': 'Finalizing...'})
        
        scene_graph_client = SceneGraphDBClient(
            db_api_base_url = db_config.get("db_api_base_url")
            )
        
        scene_graph_client.upload_scene_graph_with_pt(
            scene_data=scene_graph,
            embedding_info=embedding_result,
            video_unique_id=video_info.get("video_unique_id"),
            drama_name=video_info.get("drama_name"),
            episode_number=video_info.get("episode_number"),
            start_frame=video_info.get("start_frame"),
            end_frame=video_info.get("end_frame")
        )
        
        # 결과 반환
        result = {
            "scene_graph": scene_graph,
            # "embedding_result": embedding_result,
            "processed_at": time.time(),
            "task_id": task_id,
            "worker_id": f"celery-worker-{os.getpid()}"
        }
        
        logger.info(f"[Celery] Completed meta2graph task: {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"[Celery] Error in meta2graph task {task_id}: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0.0}
        )
        raise

@celery_app.task(bind=True, name='src.contents_graph.tasks.process_retrieval_graph')
def process_retrieval_graph(self, query, tau, top_k, retrieval_graph_config):
    """
    Retrieval-Graph 작업을 처리하는 Celery 태스크
    """
    task_id = self.request.id
    logger.info(f"[Celery] Processing retrieval_graph task: {task_id}")
    
    try:
        # 환경변수 확인
        api_key_name = retrieval_graph_config.get("api_key_name")
        if not api_key_name:
            raise ValueError("api_key_name이 retrieval_graph_config에 설정되지 않았습니다.")
        
        api_key = os.getenv(api_key_name)
        if not api_key:
            raise ValueError(f"환경변수 '{api_key_name}'이 설정되지 않았습니다.")
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 0.0, 'status': 'Initializing...'})
        
        # RetrievalGraphConverter 초기화
        retrieval_graph_config["api_key"] = api_key
        converter = RetrievalGraphConverter(
            instruction_path=retrieval_graph_config["instruction_path"],
            api_key=api_key,
            model=retrieval_graph_config["model"],
            temperature=retrieval_graph_config.get("temperature", 0.0),
            max_tokens=retrieval_graph_config.get("max_tokens", 256)
        )
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 25.0, 'status': 'Processing query...'})
        
        # 쿼리 처리
        result = converter(query, tau, top_k)
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'progress': 75.0, 'status': 'Finalizing...'})
        
        # 결과 반환
        final_result = {
            "result": result,
            "processed_at": time.time(),
            "task_id": task_id,
            "worker_id": f"celery-worker-{os.getpid()}"
        }
        
        logger.info(f"[Celery] Completed retrieval_graph task: {task_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"[Celery] Error in retrieval_graph task {task_id}: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0.0}
        )
        raise
