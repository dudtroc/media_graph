import logger_init
import queue
import asyncio
# from asyncio import Queue

# 모델별 요청 큐
selector_queue = asyncio.Queue()
meta2graph_queue = asyncio.Queue()
retrieve_scenegraph_queue = asyncio.Queue()

# 간단한 테스트용 큐
simple_test_queue = asyncio.Queue()

# Dispatcher 큐
task_queue = asyncio.Queue()    

# 라우팅 테이블
ROUTING = {
    "FRAME_SELECTOR": selector_queue,
    "SIMPLE_TEST": simple_test_queue,
    "META2GRAPH": meta2graph_queue,
    "RETRIEVE_SCENEGRAPH": retrieve_scenegraph_queue
}

async def dispatcher():
    logger = logger_init.get_logger()
    while True:
        task = await task_queue.get()
        print(f"task: {task}")
        worker = task["worker_name"]
        if worker in ROUTING:
            await ROUTING[worker].put(task)
        else:
            logger.warning(f"[!] Unknown ROUTING: {worker}")


async def bridge_sync_to_async(sync_q: queue.Queue, async_q: asyncio.Queue):
    loop = asyncio.get_event_loop()
    while True:
        try:
            frame = await loop.run_in_executor(None, sync_q.get, True, 0.1)
            await async_q.put(frame)
            if frame[0] is None and frame[1] is None:
                break
        except queue.Empty:
            await asyncio.sleep(0.01)