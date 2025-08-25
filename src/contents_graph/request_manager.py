from enum import Enum
from typing import Dict
import uuid
import asyncio
import logger_init

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class TaskStatusCode(int, Enum):
    PENDING = 200
    RUNNING = 201
    COMPLETED = 202
    FAILED = 203
    CANCELLED = 204

task_store: Dict[str, Dict] = {}
task_locks: Dict[str, asyncio.Event] = {}

def create_task(data, task_name): 
    task_id = task_name + "_" + str(uuid.uuid4())  # Fixed: use uuid4 and cast to string
    if task_id in task_store:
        return None
    
    task_store[task_id] = {
        "message": TaskStatus.PENDING,
        "status": TaskStatusCode.PENDING,
        "data": data,
        "result": [],
        "cancelled": False,
        "progress": 0.0,
    }
    task_locks[task_id] = asyncio.Event()
    return task_id

def get_task(task_id):
    return task_store.get(task_id)

def cancel_task(task_id: str):
    if task_id in task_store:
        task_store[task_id]["cancelled"] = True
        set_status(task_id, TaskStatus.CANCELLED)
        return True
    return False

def set_status(task_id, status: TaskStatus, msg: str = None):
    if task_id in task_store:
        task_store[task_id]["message"] = status if msg is None else f"[{status}]: {msg}"
        task_store[task_id]["status"] = TaskStatusCode[status.name]

def set_result(task_id, result):
    logger = logger_init.get_logger()
    if task_id in task_store:
        logger.info(f"Setting result for task {task_id}: {result}")
        task_store[task_id]["result"].append(result)

def set_progress(task_id: str, progress: float):
    if task_id in task_store:
        task_store[task_id]["progress"] = progress * 100.0

def delete_task(task_id: str) -> bool:
    """
    task_store와 task_locks에서 해당 task를 삭제합니다.

    Args:
        task_id (str): 삭제할 작업의 ID

    Returns:
        bool: 삭제 성공 여부
    """
    removed = False
    if task_id in task_store:
        del task_store[task_id]
        removed = True
    if task_id in task_locks:
        del task_locks[task_id]
    return removed