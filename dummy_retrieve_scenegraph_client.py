#!/usr/bin/env python3
"""
Retrieve-Scenegraph API를 테스트하는 클라이언트
사용자 질문을 입력받아 triples로 변환하고 검색을 수행하는 API 테스트
"""

import httpx
import time
import json
import os


def format_search_results(search_results):
    """
    search_results를 깔끔하게 포맷팅하여 출력합니다.
    
    Args:
        search_results (list): 검색 결과 리스트
    """
    if not search_results:
        print("📊 검색 결과가 없습니다.")
        return
    
    print(f"\n🔍 검색 결과 ({len(search_results)}개):")
    print("=" * 80)
    
    for i, result in enumerate(search_results, 1):
        print(f"\n📌 결과 #{i}")
        print("-" * 40)
        
        # 실제 데이터 구조에 맞게 수정
        # result[0]: 순위 (1)
        # result[1]: 전체 유사도 점수
        # result[2]: 세부 점수 리스트 [[0, 전체, 텍스트, 시각, 그래프, [ID들]]]
        # result[3]: 작품명
        # result[4]: 파일 경로
        # result[5]: 추가 정보
        
        rank = result[0]
        similarity_score = result[1]
        print(f"🏆 순위: {rank}")
        print(f"📊 전체 유사도 점수: {similarity_score:.4f}")
        
        # 세부 점수 정보
        detailed_scores = result[2]
        if detailed_scores and len(detailed_scores) > 0:
            score_detail = detailed_scores[0]  # 첫 번째 세부 점수
            if len(score_detail) >= 5:
                print(f"📈 세부 점수:")
                print(f"   - 전체 유사도: {score_detail[1]:.4f}")
                print(f"   - 텍스트 유사도: {score_detail[2]:.4f}")
                print(f"   - 시각적 유사도: {score_detail[3]:.4f}")
                print(f"   - 그래프 유사도: {score_detail[4]:.4f}")
                
                # ID 정보가 있다면 출력
                if len(score_detail) > 5 and score_detail[5]:
                    print(f"   - 관련 ID: {score_detail[5]}")
        
        # 메타데이터
        if len(result) >= 5:
            print(f"📺 작품명: {result[3]}")
            print(f"📁 파일 경로: {result[4]}")
        
        # 추가 정보
        if len(result) >= 6:
            print(f"🔢 추가 정보: {result[5]}")


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
            print(f"🔄 GET /api/v1/retrieve-scenegraph/{jobid} - 상태 확인 중...")
            
            # GET API로 작업 상태 확인
            response = httpx.get(
                f"{base_url}/api/v1/retrieve-scenegraph/{jobid}",
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
                    
                    # 결과를 깔끔하게 포맷팅하여 출력
                    result_data = result.get('result', [])
                    if result_data and len(result_data) > 0:
                        first_result = result_data[0]["result"]
                        if 'search_results' in first_result:
                            print(f"\n📋 질문: {first_result.get('question', 'N/A')}")
                            print(f"🔗 추출된 트리플: {first_result.get('triples', [])}")
                            
                            # search_results를 깔끔하게 포맷팅
                            search_results = first_result.get('search_results', [])
                            print(f"🔍 검색된 결과 수: {len(search_results)}개")
                            format_search_results(search_results)
                        else:
                            print(f"📋 최종 결과: {result_data}")
                    else:
                        print(f"📋 최종 결과: {result_data}")
                    
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


def test_retrieve_scenegraph_question(question="남녀가 키스하는 장면을 찾아줘.", tau=0.30, top_k=5):
    """직접 질문을 입력하여 retrieve-scenegraph API 테스트"""
    base_url = "http://localhost:10102"
    
    print(f"\n🔧 Retrieve-Scenegraph API Test - Direct Question")
    print("=" * 50)
    print(f"📝 질문: {question}")
    print(f"🔍 유사도 임계값 (tau): {tau}")
    print(f"📊 최대 결과 수 (top_k): {top_k}")
    
    request_data = {
        "query": question,
        "tau": tau,
        "top_k": top_k
    }
    
    print(f"📤 Sending request data:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    try:
        print("🔄 1단계: 작업 요청 (POST)")
        
        session = httpx.Client()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'close'
        })
        
        response = session.post(
            f"{base_url}/api/v1/retrieve-scenegraph", 
            json=request_data,
            timeout=10,
            headers={'Connection': 'close'}
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
        return False
        
    except httpx.ConnectError:
        print("🔌 연결 오류")
        return False
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    print("🚀 Starting Retrieve-Scenegraph API Tests...")
    print("Make sure the server is running on http://localhost:10102")
    print("=" * 60)
    
    # 1. 기본 질문으로 테스트
    print("\n" + "="*50)
    print("📝 Test 1: 기본 질문 테스트")
    print("="*50)
    test_retrieve_scenegraph_question("남녀가 키스하는 장면을 찾아줘.", 0.30, 5)
    
    print("\n✨ All tests completed!")
