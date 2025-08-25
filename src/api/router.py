import logger_init
import asyncio
import time
from fastapi import Request, APIRouter, HTTPException
from starlette.concurrency import iterate_in_threadpool
from api.schema import AnalyzeRequest, StatusResponse, BaseResponse
from api.schema import MetaToSceneGraphRequest, Meta2GraphStatusResponse
from api.schema import RetrivalGraphRequest, RetrivalGraphStatusResponse
from contents_graph.request_manager import create_task, get_task, cancel_task, TaskStatusCode, delete_task
from contents_graph.queue_manager import task_queue 

base_url='api'
main_router_url = f"/{base_url}"

GUARD_ROUTER = APIRouter (
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
    

@GUARD_ROUTER.post("/v1/meta-to-scenegraph", response_model=BaseResponse)
async def analyze_meta2graph(request: MetaToSceneGraphRequest):
    logger = logger_init.get_logger()
    logger.info(f"Meta-to-SceneGraph Request: {request}")

    task_id = create_task(request.dict(), task_name="META2GRAPH")

    if task_id:
        task = {
            "task_id": task_id,
            "worker_name": "META2GRAPH",
        }

        await task_queue.put(task)
        task_data = get_task(task_id)
        
        return BaseResponse(jobid=task_id, status=task_data['status'], message=task_data['message'])
    else:
        raise HTTPException(status_code=404, detail=f"Failed to create task")
    

@GUARD_ROUTER.get("/v1/meta-to-scenegraph/{jobid}", response_model=Meta2GraphStatusResponse)
async def get_meta2graph_status(jobid: str):
    logger = logger_init.get_logger()
    task = get_task(jobid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task['status'] == TaskStatusCode.COMPLETED:
        if delete_task(jobid): 
            logger.info(f"Task {jobid} completed and deleted.")
        return Meta2GraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"], result=task["result"])
    elif task['status'] == TaskStatusCode.PENDING:
        return Meta2GraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"])
    elif task['status'] == TaskStatusCode.RUNNING:
        return Meta2GraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"], result=task["result"])
    elif task['status'] in [TaskStatusCode.FAILED, TaskStatusCode.CANCELLED]:
        if delete_task(jobid):
            logger.info(f"Task {jobid} finished and deleted.")
        return Meta2GraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"])
    else:
        raise HTTPException(status_code=404, detail="Unknown task status")


@GUARD_ROUTER.delete("/v1/meta-to-scenegraph/{jobid}", response_model=Meta2GraphStatusResponse)
async def cancel_meta2graph_task_endpoint(jobid: str):
    logger = logger_init.get_logger()
    
    task = get_task(jobid)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] in [TaskStatusCode.COMPLETED, TaskStatusCode.CANCELLED, TaskStatusCode.FAILED]:
        return Meta2GraphStatusResponse(status=task["status"], message="Task already finished or cancelled or failed.")
    
    # Cancel 처리
    cancelled = cancel_task(jobid)
    if cancelled:
        logger.info(f"Task {jobid} cancelled by user.")
        return Meta2GraphStatusResponse(status=TaskStatusCode.CANCELLED, message="Cancellation requested.")
    else:
        raise HTTPException(status_code=400, detail="Unable to cancel task.")
    



@GUARD_ROUTER.post("/v1/retrieve-scenegraph", response_model=BaseResponse)
async def retrieve_scenegraph(request: RetrivalGraphRequest):
    logger = logger_init.get_logger()
    logger.info(f"Retrieve-Scenegraph Request: {request}")

    task_id = create_task(request.dict(), task_name="RETRIEVE_SCENEGRAPH")

    if task_id:
        task = {
            "task_id": task_id,
            "worker_name": "RETRIEVE_SCENEGRAPH",
        }

        await task_queue.put(task)
        task_data = get_task(task_id)
        
        return BaseResponse(jobid=task_id, status=task_data['status'], message=task_data['message'])
    else:
        raise HTTPException(status_code=404, detail=f"Failed to create task")
    

@GUARD_ROUTER.get("/v1/retrieve-scenegraph/{jobid}", response_model=RetrivalGraphStatusResponse)
async def get_retrieve_scenegraph_status(jobid: str):
    logger = logger_init.get_logger()
    task = get_task(jobid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task['status'] == TaskStatusCode.COMPLETED:
        if delete_task(jobid): 
            logger.info(f"Task {jobid} completed and deleted.")
        return RetrivalGraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"], result=task["result"])
    elif task['status'] == TaskStatusCode.PENDING:
        return RetrivalGraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"])
    elif task['status'] == TaskStatusCode.RUNNING:
        return RetrivalGraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"], result=task["result"])
    elif task['status'] in [TaskStatusCode.FAILED, TaskStatusCode.CANCELLED]:
        if delete_task(jobid):
            logger.info(f"Task {jobid} finished and deleted.")
        return RetrivalGraphStatusResponse(status=task['status'], message=task["message"], progress=task["progress"])
    else:
        raise HTTPException(status_code=404, detail="Unknown task status")


@GUARD_ROUTER.delete("/v1/retrieve-scenegraph/{jobid}", response_model=RetrivalGraphStatusResponse)
async def cancel_retrieve_scenegraph_task_endpoint(jobid: str):
    logger = logger_init.get_logger()
    
    task = get_task(jobid)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] in [TaskStatusCode.COMPLETED, TaskStatusCode.CANCELLED, TaskStatusCode.FAILED]:
        return RetrivalGraphStatusResponse(status=task["status"], message="Task already finished or cancelled or failed.")
    
    # Cancel 처리
    cancelled = cancel_task(jobid)
    if cancelled:
        logger.info(f"Task {jobid} cancelled by user.")
        return RetrivalGraphStatusResponse(status=TaskStatusCode.CANCELLED, message="Cancellation requested.")
    else:
        raise HTTPException(status_code=400, detail="Unable to cancel task.")