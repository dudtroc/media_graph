import logger_init
import argparse
import uvicorn
import os
import asyncio

from contents_graph.meta2graph_worker import Meta2GraphWorker
from contents_graph.retrieval_graph_worker import RetrievalGraphWorker
from contents_graph.queue_manager import dispatcher
from contents_graph.utils import load_config
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette_context.middleware import ContextMiddleware
from api.router import request_logger, response_logger, GRAPH_ROUTER

app = FastAPI()
def setup_app(server_name, args):
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
    asyncio.create_task(dispatcher())

    root_path = config["NAS_ROOT_PATH"]
    os.makedirs(root_path, exist_ok=True)

    # for idx, device in enumerate(config["contents_graph"]["WOKERS_DEVICE"]):
    #     intern_worker = InternvlWorker(config=config["contents_graph"], root_path=root_path, device=device, worker_id=f"graph_worker-{idx}")
    #     asyncio.create_task(intern_worker.run())

    # for idx, device in enumerate(config["FRAME_SELECTOR"]["WOKERS_DEVICE"]):
    #     selector_worker = FrameSelector(config=config["FRAME_SELECTOR"], root_path=root_path, device=device, worker_id=f"selector_worker-{idx}")
    #     asyncio.create_task(selector_worker.run())
        
    # Meta2Graph 워커 시작
    meta2graph_worker = Meta2GraphWorker(worker_id="meta2graph-worker-0", meta2graph_config=config["META_TO_GRAPH"])
    asyncio.create_task(meta2graph_worker.run())
    
    # RetrievalGraph 워커 시작
    retrieval_graph_worker = RetrievalGraphWorker(worker_id="retrieval-graph-worker-0", retrieval_graph_config=config["RETRIEVAL_GRAPH"])
    asyncio.create_task(retrieval_graph_worker.run())

if __name__ == "__main__":
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