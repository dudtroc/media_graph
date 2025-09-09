import logger_init
import argparse
import uvicorn
import os
import asyncio

from contents_graph.utils import load_config
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette_context.middleware import ContextMiddleware
from api.router import request_logger, response_logger, GRAPH_ROUTER

app = FastAPI()
def setup_app(server_name, args):
    # logger 초기화
    logger = logger_init.get_logger()
    
    app.middleware('http')(request_logger)
    app.middleware('http')(response_logger)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ContextMiddleware)
    logger.info(f'Start {server_name}')
    
    app.state.config = load_config(args.config_file)
    if server_name == "media_graph":
        app.include_router(GRAPH_ROUTER) 
    else:
        logger.error(f'Not supported type: {server_name}')
        return None
    
    return app

@app.on_event("startup")
async def startup_event():
    config = app.state.config  # 여기서 사용 가능
    logger = logger_init.get_logger()
    
    # NAS 루트 경로 생성
    root_path = config["NAS_ROOT_PATH"]
    os.makedirs(root_path, exist_ok=True)
    
    # 설정을 app.state에 저장 (context는 request cycle에서만 사용 가능)
    app.state.config = config
    
    # Celery 연결 테스트
    try:
        from contents_graph.task_manager import task_manager
        # Redis 연결 테스트
        task_manager.redis_client.ping()
        logger.info("Redis connection successful")
        
        # Celery 브로커 연결 테스트
        from contents_graph.celery_app import celery_app
        celery_app.control.inspect().stats()
        logger.info("Celery broker connection successful")
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis or Celery broker: {e}")
        raise
    
    logger.info("Media Graph API server started with Celery backend")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_lev", type=str, default="INFO", help="NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL")
    parser.add_argument("--log_file", type=str, default="/workspace/log/media-graph.log")
    parser.add_argument("--config_file", type=str, default="/workspace/config/media-graph_config.json")
    parser.add_argument("--ip", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=str, default="10102")
    args = parser.parse_args()

    SERVER_NAME = "media_graph"
    logger_it = logger_init.initialize_logger(SERVER_NAME, args.log_lev, args.log_file)
    logger_init.seg_logger(logger_it)
    logger = logger_init.get_logger()

    logger.info(f'SERVER INFO')
    logger.info(f'- Adress: {args.ip}:{args.port}')
    logger.info(f'- Log: {args.log_file}')
    logger.info(f'- Config: {args.config_file}')

    app = setup_app(SERVER_NAME, args)
    if app is None:
        logger.error('')
        exit(1)

    uvicorn.run(app, host=args.ip, port=int(args.port))

if __name__ == "__main__":
    main()