#!/usr/bin/env python3
"""
RetrievalGraphWorker 테스트 스크립트
"""

import asyncio
import time
from dotenv import load_dotenv
from contents_graph.retrieval_graph_worker import RetrievalGraphWorker
from contents_graph.queue_manager import retrieve_scenegraph_queue
from contents_graph.request_manager import create_task, get_task, TaskStatus

load_dotenv()

async def test_retrieval_graph_worker():
    # 설정
    retrieval_graph_config = {
        "api_key_name": "OPEN_AI_API_KEY",
        "base_config_path": "config/base_params.yaml",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 256
    }
    
    # 워커 생성
    worker = RetrievalGraphWorker(
        worker_id="retrieval-graph-worker-test",
        retrieval_graph_config=retrieval_graph_config
    )
    
    # 테스트 질문
    test_query = "남녀가 키스하는 장면을 찾아줘."
    
    # 태스크 생성
    task_data = {
        "query": test_query,
        "tau": 0.30,
        "top_k": 5
    }
    
    task_id = create_task("RETRIEVE_SCENEGRAPH", task_data)
    print(f"테스트 태스크 생성: {task_id}")
    
    # 워커에 태스크 전달
    await retrieve_scenegraph_queue.put({
        "task_id": task_id,
        "worker_name": "RETRIEVE_SCENEGRAPH"
    })
    
    # 워커 실행 (별도 태스크로)
    worker_task = asyncio.create_task(worker.handle_task({
        "task_id": task_id,
        "worker_name": "RETRIEVE_SCENEGRAPH"
    }))
    
    # 결과 대기
    max_wait = 60  # 최대 60초 대기
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        task = get_task(task_id)
        if task and task.get("status") in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            break
        await asyncio.sleep(1)
    
    # 워커 태스크 취소
    worker_task.cancel()
    
    # 결과 확인
    task = get_task(task_id)
    if task:
        print(f"태스크 상태: {task.get('status')}")
        if task.get("result"):
            print(f"결과: {task['result']}")
        if task.get("error"):
            print(f"오류: {task['error']}")
    else:
        print("태스크를 찾을 수 없습니다.")

if __name__ == "__main__":
    asyncio.run(test_retrieval_graph_worker())
