import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Python 경로에 src 디렉토리 추가
sys.path.insert(0, '/workspace/src')
sys.path.insert(0, '/workspace')

load_dotenv()

# Celery 앱 설정
celery_app = Celery(
    'media-graph',
    broker=os.getenv('CELERY_BROKER_URL', 'amqp://admin:admin123@localhost:5672//'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['src.contents_graph.tasks']
)

# Celery 설정
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,  # 25분
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    result_expires=3600,  # 1시간
)

# 큐 설정
celery_app.conf.task_routes = {
    'src.contents_graph.tasks.process_meta2graph': {'queue': 'meta2graph_queue'},
    'src.contents_graph.tasks.process_retrieval_graph': {'queue': 'retrieval_graph_queue'},
}

# 로거 초기화
try:
    import logger_init
    logger = logger_init.get_logger()
except ImportError:
    # fallback 로거
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    celery_app.start()
