import logger_init
import asyncio
import time
from fastapi import Request, APIRouter, HTTPException
from starlette.concurrency import iterate_in_threadpool
from .schema import AnalyzeRequest, StatusResponse, BaseResponse
from .schema import MetaToSceneGraphRequest, Meta2GraphStatusResponse
from .schema import RetrivalGraphRequest, RetrivalGraphStatusResponse
from contents_graph.task_manager import task_manager, TaskStatus, TaskStatusCode 

base_url='api'
main_router_url = f"/{base_url}"

GRAPH_ROUTER = APIRouter (
    prefix=main_router_url
)

### Print request, response log ###
async def request_logger(request: Request, call_next):
    # from server_main import LOGGER
    logger = logger_init.get_logger()
    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    return response

async def response_logger(request: Request, call_next):
    # from server_main import LOGGER
    logger = logger_init.get_logger()
    response = await call_next(request)
    
    res_body = [chunk async for chunk in response.body_iterator]
    response.body_iterator = iterate_in_threadpool(iter(res_body))
    logger.info(f"Response: {response.status_code}")
    
    return response
    

@GRAPH_ROUTER.post("/v1/meta-to-scenegraph", response_model=BaseResponse)
async def analyze_meta2graph(request: MetaToSceneGraphRequest):
    logger = logger_init.get_logger()
    logger.info(f"Meta-to-SceneGraph Request: {request}")

    # FastAPI 앱에서 설정 가져오기
    from fastapi import Request
    from starlette_context import context
    
    # 설정을 context에서 가져오기
    config = context.get("config")
    if not config:
        # fallback으로 직접 로드
        from contents_graph.utils import load_config
        config = load_config("/workspace/config/media-graph_config.json")
    
    # Meta2Graph 태스크를 Celery에 제출
    task_id = task_manager.submit_meta2graph_task(
        metadata=request.metadata,
        video_info=request.video_info,
        meta2graph_config=config["META_TO_GRAPH"],
        graph_anlayzer_config=config["SCENE_GRAPH_ANALYZER"],
        db_config=config["SCENE_GRAPH_DB"]
    )

    if task_id:
        task_data = task_manager.get_task(task_id)
        return BaseResponse(
            jobid=task_id, 
            status=task_data['status_code'], 
            message=task_data['status']
        )
    else:
        raise HTTPException(status_code=404, detail=f"Failed to create task")
    

@GRAPH_ROUTER.get("/v1/meta-to-scenegraph/{jobid}", response_model=Meta2GraphStatusResponse)
async def get_meta2graph_status(jobid: str):
    logger = logger_init.get_logger()
    task = task_manager.get_task(jobid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task['status'] == TaskStatus.SUCCESS:
        logger.info(f"Task {jobid} completed successfully.")
        return Meta2GraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"], 
            result=task["result"]
        )
    elif task['status'] == TaskStatus.PENDING:
        return Meta2GraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"]
        )
    elif task['status'] == TaskStatus.PROGRESS:
        return Meta2GraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"], 
            result=task["result"]
        )
    elif task['status'] in [TaskStatus.FAILURE, TaskStatus.REVOKED]:
        logger.info(f"Task {jobid} finished with status: {task['status']}")
        return Meta2GraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"]
        )
    else:
        raise HTTPException(status_code=404, detail="Unknown task status")


@GRAPH_ROUTER.delete("/v1/meta-to-scenegraph/{jobid}", response_model=Meta2GraphStatusResponse)
async def cancel_meta2graph_task_endpoint(jobid: str):
    logger = logger_init.get_logger()
    
    task = task_manager.get_task(jobid)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] in [TaskStatus.SUCCESS, TaskStatus.REVOKED, TaskStatus.FAILURE]:
        return Meta2GraphStatusResponse(
            status=task["status_code"], 
            message="Task already finished or cancelled or failed."
        )
    
    # Cancel 처리
    cancelled = task_manager.cancel_task(jobid)
    if cancelled:
        logger.info(f"Task {jobid} cancelled by user.")
        return Meta2GraphStatusResponse(
            status=TaskStatusCode.REVOKED, 
            message="Cancellation requested."
        )
    else:
        raise HTTPException(status_code=400, detail="Unable to cancel task.")
    



@GRAPH_ROUTER.post("/v1/retrieve-scenegraph", response_model=BaseResponse)
async def retrieve_scenegraph(request: RetrivalGraphRequest):
    logger = logger_init.get_logger()
    logger.info(f"Retrieve-Scenegraph Request: {request}")

    # FastAPI 앱에서 설정 가져오기
    from fastapi import Request
    from starlette_context import context
    
    # 설정을 context에서 가져오기
    config = context.get("config")
    if not config:
        # fallback으로 직접 로드
        from contents_graph.utils import load_config
        config = load_config("/workspace/config/media-graph_config.json")
    
    # RetrievalGraph 태스크를 Celery에 제출
    task_id = task_manager.submit_retrieval_graph_task(
        query=request.query,
        tau=request.tau,
        top_k=request.top_k,
        config=config["RETRIEVAL_GRAPH"]
    )

    if task_id:
        task_data = task_manager.get_task(task_id)
        return BaseResponse(
            jobid=task_id, 
            status=task_data['status_code'], 
            message=task_data['status']
        )
    else:
        raise HTTPException(status_code=404, detail=f"Failed to create task")
    

@GRAPH_ROUTER.get("/v1/retrieve-scenegraph/{jobid}", response_model=RetrivalGraphStatusResponse)
async def get_retrieve_scenegraph_status(jobid: str):
    logger = logger_init.get_logger()
    task = task_manager.get_task(jobid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task['status'] == TaskStatus.SUCCESS:
        logger.info(f"Task {jobid} completed successfully.")
        return RetrivalGraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"], 
            result=task["result"]
        )
    elif task['status'] == TaskStatus.PENDING:
        return RetrivalGraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"]
        )
    elif task['status'] == TaskStatus.PROGRESS:
        return RetrivalGraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"], 
            result=task["result"]
        )
    elif task['status'] in [TaskStatus.FAILURE, TaskStatus.REVOKED]:
        logger.info(f"Task {jobid} finished with status: {task['status']}")
        return RetrivalGraphStatusResponse(
            status=task['status_code'], 
            message=task["status"], 
            progress=task["progress"]
        )
    else:
        raise HTTPException(status_code=404, detail="Unknown task status")


@GRAPH_ROUTER.delete("/v1/retrieve-scenegraph/{jobid}", response_model=RetrivalGraphStatusResponse)
async def cancel_retrieve_scenegraph_task_endpoint(jobid: str):
    logger = logger_init.get_logger()
    
    task = task_manager.get_task(jobid)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] in [TaskStatus.SUCCESS, TaskStatus.REVOKED, TaskStatus.FAILURE]:
        return RetrivalGraphStatusResponse(
            status=task["status_code"], 
            message="Task already finished or cancelled or failed."
        )
    
    # Cancel 처리
    cancelled = task_manager.cancel_task(jobid)
    if cancelled:
        logger.info(f"Task {jobid} cancelled by user.")
        return RetrivalGraphStatusResponse(
            status=TaskStatusCode.REVOKED, 
            message="Cancellation requested."
        )
    else:
        raise HTTPException(status_code=400, detail="Unable to cancel task.")