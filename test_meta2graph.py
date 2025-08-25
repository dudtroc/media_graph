#!/usr/bin/env python3
"""
Meta-to-SceneGraph API 테스트 클라이언트
기존 safety-check API와 동일한 구조로 테스트
"""

import requests
import time
import json
import os

def test_meta2graph_api():
    """Meta-to-SceneGraph API 테스트"""
    base_url = "http://localhost:10102"
    
    print("🧪 Meta-to-SceneGraph API Test")
    print("=" * 40)
    
    # 테스트할 데이터
    test_data = {
        "videoPath": "/test/video.mp4",
        "shotList": [
            {"startTime": 0.0, "endTime": 5.0},
            {"startTime": 5.0, "endTime": 10.0},
            {"startTime": 10.0, "endTime": 15.0}
        ],
        "metadata": {
            "title": "Test Video",
            "duration": 15.0,
            "format": "mp4"
        },
        "options": {
            "graph_type": "scene",
            "detail_level": "high",
            "include_audio": True
        }
    }
    
    print("📤 Sending Meta-to-SceneGraph request:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    
    try:
        # API 요청
        response = requests.post(
            f"{base_url}/api/v1/meta-to-scenegraph",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result}")
            
            # 작업 ID 추출
            jobid = result.get("jobid")
            if jobid:
                print(f"📋 Job ID: {jobid}")
                
                # 작업 상태 모니터링
                monitor_job_status(base_url, jobid)
            else:
                print("❌ No job ID received")
                
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: 서버가 실행 중인지 확인하세요")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def test_meta2graph_from_file(json_file_path="data/test/Kingdom_EP01_visual_3135-7977_(00_02_11-00_05_33)_meta_info.json"):
    """JSON 파일에서 데이터를 읽어와서 Meta-to-SceneGraph API 테스트"""
    base_url = "http://localhost:10102"
    
    print(f"\n📁 Meta-to-SceneGraph API Test from File")
    print("=" * 50)
    
    # JSON 파일 읽기
    if not os.path.exists(json_file_path):
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_file_path}")
        return False
    
    try:
        print(f"📁 JSON 파일 읽기: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        print("✅ JSON 파일을 성공적으로 읽었습니다.")
        
        # 필수 필드 확인 및 변환
        if "videoPath" not in test_data or "shotList" not in test_data:
            print("⚠️ 필수 필드가 없습니다. 기본 구조로 변환합니다.")
            test_data = {
                "videoPath": test_data.get("videoPath", "/test/video.mp4"),
                "shotList": test_data.get("shotList", []),
                "metadata": test_data,
                "options": {}
            }
        
        print("📤 Sending Meta-to-SceneGraph request:")
        print(json.dumps(test_data, indent=2, ensure_ascii=False))
        
        # API 요청
        response = requests.post(
            f"{base_url}/api/v1/meta-to-scenegraph",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result}")
            
            # 작업 ID 추출
            jobid = result.get("jobid")
            if jobid:
                print(f"📋 Job ID: {jobid}")
                
                # 작업 상태 모니터링
                monitor_job_status(base_url, jobid)
            else:
                print("❌ No job ID received")
                
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파일 파싱 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def monitor_job_status(base_url, jobid):
    """작업 상태 모니터링"""
    print(f"\n📊 Monitoring job status: {jobid}")
    print("=" * 40)
    
    max_wait = 60  # 최대 대기 시간 (초)
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # 작업 상태 조회
            response = requests.get(f"{base_url}/api/safety-check/{jobid}", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                
                # 상태 출력
                status_code = status_data.get("status", "unknown")
                message = status_data.get("message", "No message")
                progress = status_data.get("progress", 0)
                
                print(f"📈 Status: {status_code} | Progress: {progress:.1f}% | Message: {message}")
                
                # 완료, 실패, 취소 상태 확인
                if status_code in [202, 203, 204]:  # COMPLETED, FAILED, CANCELLED
                    if status_code == 202:  # COMPLETED
                        result = status_data.get("result", [])
                        print(f"🎉 Job completed! Result: {json.dumps(result, indent=2)}")
                    elif status_code == 203:  # FAILED
                        print(f"💥 Job failed: {message}")
                    elif status_code == 204:  # CANCELLED
                        print(f"⏹️ Job cancelled: {message}")
                    return True
                
                # 진행 중이면 잠시 대기
                if status_code == 201:  # RUNNING
                    time.sleep(2)
                else:
                    time.sleep(2)
                    
            else:
                print(f"⚠️ Failed to get status: {response.status_code}")
                time.sleep(2)
                
        except Exception as e:
            print(f"⚠️ Error monitoring status: {e}")
            time.sleep(2)
    
    print(f"⏰ Timeout after {max_wait} seconds")
    return False

def main():
    """메인 테스트 실행"""
    print("🚀 Starting Meta-to-SceneGraph API Tests...")
    print("Make sure the server is running on http://localhost:10102")
    print("=" * 60)
    
    try:
        # 1. 기본 API 테스트
        test_meta2graph_api()
        
        # 2. JSON 파일에서 데이터를 읽어와서 테스트
        test_meta2graph_from_file()
        
        print("\n🎉 All Meta-to-SceneGraph tests completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
