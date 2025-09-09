#!/usr/bin/env python3
"""
Celery 기반 Media Graph API 테스트 스크립트
"""
import requests
import time
import json

BASE_URL = "http://localhost:10103/api"

def test_meta2graph():
    """Meta-to-SceneGraph API 테스트"""
    print("=== Testing Meta-to-SceneGraph API ===")
    
    # 테스트 데이터
    test_data = {
        "metadata": {
            "title": "Test Video",
            "description": "A test video for scene graph generation",
            "duration": 120,
            "genre": "action"
        }
    }
    
    # 작업 제출
    response = requests.post(f"{BASE_URL}/v1/meta-to-scenegraph", json=test_data)
    print(f"Submit response: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        job_id = result["jobid"]
        print(f"Job ID: {job_id}")
        
        # 작업 상태 폴링
        while True:
            status_response = requests.get(f"{BASE_URL}/v1/meta-to-scenegraph/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status: {status_data['status']}, Progress: {status_data.get('progress', 0)}%")
                
                if status_data['status'] in [202, 203, 204]:  # SUCCESS, FAILURE, REVOKED
                    if status_data.get('result'):
                        print(f"Result: {json.dumps(status_data['result'], indent=2)}")
                    break
                    
                time.sleep(2)
            else:
                print(f"Error checking status: {status_response.status_code}")
                break
    else:
        print(f"Error submitting job: {response.text}")

def test_retrieval_graph():
    """Retrieval Graph API 테스트"""
    print("\n=== Testing Retrieval Graph API ===")
    
    # 테스트 데이터
    test_data = {
        "query": "Find action scenes with cars",
        "tau": 0.3,
        "top_k": 5
    }
    
    # 작업 제출
    response = requests.post(f"{BASE_URL}/v1/retrieve-scenegraph", json=test_data)
    print(f"Submit response: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        job_id = result["jobid"]
        print(f"Job ID: {job_id}")
        
        # 작업 상태 폴링
        while True:
            status_response = requests.get(f"{BASE_URL}/v1/retrieve-scenegraph/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status: {status_data['status']}, Progress: {status_data.get('progress', 0)}%")
                
                if status_data['status'] in [202, 203, 204]:  # SUCCESS, FAILURE, REVOKED
                    if status_data.get('result'):
                        print(f"Result: {json.dumps(status_data['result'], indent=2)}")
                    break
                    
                time.sleep(2)
            else:
                print(f"Error checking status: {status_response.status_code}")
                break
    else:
        print(f"Error submitting job: {response.text}")

def test_health_check():
    """API 서버 상태 확인"""
    print("=== Testing API Health ===")
    
    try:
        # 간단한 GET 요청으로 서버 상태 확인
        response = requests.get(f"{BASE_URL}/v1/meta-to-scenegraph/nonexistent", timeout=5)
        if response.status_code == 404:
            print("✓ API server is running")
            return True
        else:
            print(f"✗ Unexpected response: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ API server is not accessible: {e}")
        return False

if __name__ == "__main__":
    print("Media Graph API Test Script")
    print("=" * 50)
    
    # API 서버 상태 확인
    if not test_health_check():
        print("\nPlease make sure the API server is running:")
        print("  ./docker_launch.sh -r")
        exit(1)
    
    # API 테스트 실행
    test_meta2graph()
    test_retrieval_graph()
    
    print("\n=== Test completed ===")
