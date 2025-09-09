#!/usr/bin/env python3
"""
JSON 데이터를 보내는 테스트 클라이언트
큐 시스템이 제대로 동작하는지 확인
"""

import httpx
import time
import json
import os


def wait_for_task_completion(base_url, jobid, max_wait_time=300, check_interval=2):
    """
    작업이 완료될 때까지 주기적으로 GET API로 상태를 체크합니다.
    
    Args:
        base_url (str): 서버 기본 URL
        jobid (str): 작업 ID
        max_wait_time (int): 최대 대기 시간 (초)
        check_interval (int): 상태 확인 간격 (초)
    
    Returns:
        dict: 작업 결과 또는 None (실패 시)
    """
    print(f"⏳ 작업 {jobid} 상태 주기적 체크 시작...")
    print(f"📊 체크 간격: {check_interval}초, 최대 대기: {max_wait_time}초")
    
    start_time = time.time()
    consecutive_errors = 0
    max_consecutive_errors = 5
    last_status = None
    
    while True:
        # 최대 대기 시간 체크
        elapsed_time = time.time() - start_time
        if elapsed_time > max_wait_time:
            print(f"❌ 최대 대기 시간({max_wait_time}초) 초과")
            return None
        
        try:
            print(f"🔄 GET /api/v1/meta-to-scenegraph/{jobid} - 상태 확인 중...")
            
            # GET API로 작업 상태 확인
            response = httpx.get(
                f"{base_url}/api/v1/meta-to-scenegraph/{jobid}",
                timeout=15
            )
            
            consecutive_errors = 0  # 성공 시 에러 카운터 리셋
            
            if response.status_code == 200:
                result = response.json()
                current_status = result.get('status')
                progress = result.get('progress', 0)
                
                # 상태 변화 감지 및 출력
                if current_status != last_status:
                    print(f"🔄 상태 변화 감지: {last_status} → {current_status}")
                    last_status = current_status
                
                print(f"📊 현재 상태: {current_status}, 진행률: {progress}%")
                
                # 작업 완료 체크
                if current_status == 202:  # TaskStatusCode.COMPLETED
                    print(f"✅ 작업 완료! 결과 수신 중...")
                    print(f"📋 최종 결과: {result.get('result', [])}")
                    return result
                    
                elif current_status == 203:  # TaskStatusCode.FAILED
                    print(f"❌ 작업 실패: {result.get('message', 'Unknown error')}")
                    return None
                    
                elif current_status == 204:  # TaskStatusCode.CANCELLED
                    print(f"❌ 작업 취소됨: {result.get('message', 'Task cancelled')}")
                    return None
                    
                elif current_status == 200:  # TaskStatusCode.PENDING
                    print(f"⏳ 작업 대기 중... (PENDING)")
                    time.sleep(check_interval)
                    
                elif current_status == 201:  # TaskStatusCode.RUNNING
                    print(f"⚡ 작업 실행 중... (RUNNING) - {progress}% 완료")
                    time.sleep(check_interval)
                    
                else:
                    print(f"❓ 알 수 없는 상태: {current_status}")
                    time.sleep(check_interval)
                    
            elif response.status_code == 404:
                print(f"⚠️ 작업 {jobid}을 찾을 수 없습니다. 잠시 후 다시 시도합니다.")
                time.sleep(check_interval * 2)
                
            else:
                print(f"❌ 상태 확인 실패: {response.status_code} - {response.text}")
                time.sleep(check_interval)
                
        except httpx.TimeoutException:
            consecutive_errors += 1
            print(f"⏰ GET 요청 타임아웃 (연속 {consecutive_errors}/{max_consecutive_errors})")
            
            if consecutive_errors >= max_consecutive_errors:
                print("❌ 연속 타임아웃 에러가 너무 많습니다. 작업을 중단합니다.")
                return None
                
            time.sleep(check_interval * 2)
            
        except httpx.ConnectError:
            consecutive_errors += 1
            print(f"🔌 GET 요청 연결 오류 (연속 {consecutive_errors}/{max_consecutive_errors})")
            
            if consecutive_errors >= max_consecutive_errors:
                print("❌ 연속 연결 에러가 너무 많습니다. 작업을 중단합니다.")
                return None
                
            time.sleep(check_interval * 2)
            
        except Exception as e:
            consecutive_errors += 1
            print(f"❌ GET 요청 중 예상치 못한 오류: {e} (연속 {consecutive_errors}/{max_consecutive_errors})")
            
            if consecutive_errors >= max_consecutive_errors:
                print("❌ 연속 에러가 너무 많습니다. 작업을 중단합니다.")
                return None
                
            time.sleep(check_interval)


def test_meta2graph_json(json_file_path=None):
    """사용자 정의 JSON 데이터 테스트"""
    base_url = "http://localhost:10105"
    
    print("\n🔧 Custom JSON Test")
    print("=" * 30)
    
    # JSON 파일 경로 설정 (명령줄 인수 또는 기본값)
    if json_file_path is None:
        json_file_path = "custom_test_data.json"
    
    try:
        # JSON 파일 읽기
        print(f"📁 JSON 파일 읽기: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            custom_data = json.load(f)
        print("✅ JSON 파일을 성공적으로 읽었습니다.")
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        print("기본 테스트 데이터를 사용합니다.")
        custom_data = {
            "metadata": {
                "Main Characters": [
                    {"name": "Test Character", "description": "Test description"}
                ],
                "Action": ["Test action"],
                "Scene Info": {"Place": "Test place"},
                "Scene Number": "TEST-001"
            }
        }

    # metadata 필드로 감싸기
    request_data = {"metadata": custom_data}
    
    print(f"📤 Sending request data:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    try:
        print("🔄 1단계: 작업 요청 (POST)")
        # 1. 작업 요청 - 작업 ID 받기 (빠른 응답을 위해 짧은 타임아웃)
        
        # requests 세션 생성 및 설정 조정
        session = httpx.Client()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'close'  # Keep-Alive 문제 해결
        })
        
        response = session.post(
            f"{base_url}/api/v1/meta-to-scenegraph", 
            json=request_data,
            timeout=10,  # POST 요청은 빠르게 응답받아야 함
            headers={'Connection': 'close'}  # 추가 헤더 설정
        )
        
        if response.status_code == 200:
            result = response.json()
            jobid = result.get('jobid')
            print(f"✅ 작업 요청 성공!")
            print(f"📋 작업 ID: {jobid}")
            print(f"📊 초기 상태: {result.get('status')}")
            print(f"💬 메시지: {result.get('message')}")
            
            if jobid:
                print("🔄 2단계: 작업 상태 주기적 체크 (GET)")
                print("💡 서버가 작업을 큐에 넣었습니다. 이제 상태를 주기적으로 체크합니다.")
                # 2. 작업 완료까지 주기적으로 상태 체크
                final_result = wait_for_task_completion(base_url, jobid)
                if final_result:
                    print("🎉 전체 테스트 완료!")
                    return True
                else:
                    print("❌ 작업 처리 실패")
                    return False
            else:
                print("❌ 작업 ID를 받지 못함")
                return False
            
        else:
            print(f"❌ 작업 요청 실패: {response.status_code} - {response.text}")
            return False
            
    except httpx.TimeoutException:
        print("⏰ POST 요청 타임아웃 (10초)")
        print("💡 서버가 응답하지 않습니다. 서버 상태를 확인해주세요.")
        return False
        
    except httpx.ConnectError:
        print("🔌 연결 오류")
        print("💡 서버가 실행 중인지 확인해주세요.")
        return False
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    print("🚀 Starting JSON Tests...")
    print("Make sure the server is running on http://localhost:10105")
    print("=" * 50)
    
    # 사용자 정의 JSON 테스트 (명령줄 인수로 파일 경로 지정 가능)
    json_file_path = "data/test/Kingdom_EP01_visual_3135-7977_(00_02_11-00_05_33)_meta_info.json"
    test_meta2graph_json(json_file_path)
    
    print("\n✨ All tests completed!")
