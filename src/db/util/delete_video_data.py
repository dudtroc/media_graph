#!/usr/bin/env python3
"""
비디오 및 연결된 장면 데이터 삭제 클라이언트
특정 비디오의 모든 데이터를 삭제하는 기능을 제공합니다.
"""

import requests
import os
import json
from typing import Dict, List, Any, Optional

class VideoDataDeleter:
    """비디오 데이터 삭제 클래스"""
    
    def __init__(self, api_base_url: str = None):
        self.api_base_url = api_base_url or os.getenv("API_URL", "http://localhost:8000")
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """API 서버 헬스 체크"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            if response.status_code == 200:
                print("✅ API 서버 연결 성공")
                return True
            else:
                print(f"❌ API 서버 응답 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API 서버 연결 실패: {e}")
            return False
    
    def get_videos(self) -> List[Dict[str, Any]]:
        """저장된 비디오 목록 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/videos")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 비디오 목록 조회 실패: {e}")
            return []
    
    def get_video_info(self, video_unique_id: int) -> Optional[Dict[str, Any]]:
        """특정 비디오의 상세 정보 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/videos/{video_unique_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ 비디오를 찾을 수 없습니다: {video_unique_id}")
                return None
            else:
                print(f"❌ 비디오 정보 조회 실패: {e}")
                return None
        except Exception as e:
            print(f"❌ 비디오 정보 조회 오류: {e}")
            return None
    
    def delete_video(self, video_unique_id: int, confirm: bool = False) -> bool:
        """비디오 및 연결된 모든 장면 데이터 삭제"""
        print(f"🗑️ 비디오 삭제 요청: {video_unique_id}")
        
        # 1. 비디오 정보 확인
        video_info = self.get_video_info(video_unique_id)
        if not video_info:
            return False
        
        print(f"\n📺 삭제할 비디오 정보:")
        print(f"   - 드라마: {video_info['drama_name']} {video_info['episode_number']}")
        print(f"   - 고유 ID: {video_info['video_unique_id']}")
        print(f"   - 장면 수: {video_info['scene_count']}개")
        
        if video_info['scenes']:
            print(f"\n🎭 연결된 장면들:")
            for i, scene in enumerate(video_info['scenes'], 1):
                print(f"   {i}. 장면 ID: {scene['scene_id']} - {scene['scene_number']}")
                print(f"      프레임: {scene['start_frame']}-{scene['end_frame']}")
                print(f"      장소: {scene['scene_place']}")
        
        # 2. 확인 요청
        if not confirm:
            print(f"\n⚠️ 경고: 이 작업은 되돌릴 수 없습니다!")
            print(f"   - 비디오 '{video_info['drama_name']} {video_info['episode_number']}'")
            print(f"   - 연결된 {video_info['scene_count']}개 장면")
            print(f"   - 모든 객체, 이벤트, 관계, 임베딩 데이터")
            
            user_input = input(f"\n정말로 삭제하시겠습니까? (yes/no): ").strip().lower()
            if user_input not in ['yes', 'y']:
                print("❌ 삭제가 취소되었습니다.")
                return False
        
        # 3. 삭제 실행
        try:
            print(f"\n🔄 삭제 중...")
            response = self.session.delete(f"{self.api_base_url}/videos/{video_unique_id}")
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ 삭제 완료!")
            print(f"   - 비디오 ID: {result['video_unique_id']}")
            print(f"   - 삭제된 장면: {result['deleted_scenes']}개")
            print(f"   - 삭제된 데이터:")
            for data_type, count in result['deleted_data'].items():
                print(f"     * {data_type}: {count}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ 비디오를 찾을 수 없습니다: {video_unique_id}")
            else:
                print(f"❌ 삭제 실패: {e}")
                print(f"응답 내용: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ 삭제 오류: {e}")
            return False
    
    def list_videos(self) -> None:
        """비디오 목록 표시"""
        print("📺 저장된 비디오 목록:")
        print("=" * 60)
        
        videos = self.get_videos()
        if not videos:
            print("저장된 비디오가 없습니다.")
            return
        
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video['drama_name']} {video['episode_number']}")
            print(f"   - 고유 ID: {video['video_unique_id']}")
            print(f"   - DB ID: {video['id']}")
            print(f"   - 생성일: {video['created_at']}")
            print()
    
    def interactive_delete(self) -> None:
        """대화형 삭제 모드"""
        print("🗑️ 비디오 삭제 도구")
        print("=" * 60)
        
        # 1. API 연결 확인
        if not self.health_check():
            return
        
        # 2. 비디오 목록 표시
        self.list_videos()
        
        # 3. 삭제할 비디오 선택
        try:
            video_unique_id = int(input("삭제할 비디오의 고유 ID를 입력하세요: "))
        except ValueError:
            print("❌ 올바른 숫자를 입력해주세요.")
            return
        
        # 4. 삭제 실행
        success = self.delete_video(video_unique_id)
        
        if success:
            print(f"\n🎉 비디오 {video_unique_id} 삭제가 성공적으로 완료되었습니다!")
        else:
            print(f"\n💥 비디오 {video_unique_id} 삭제에 실패했습니다.")

def main():
    """메인 실행 함수"""
    import sys
    
    deleter = VideoDataDeleter()
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            # 비디오 목록만 표시
            deleter.list_videos()
        elif sys.argv[1].isdigit():
            # 특정 비디오 삭제
            video_unique_id = int(sys.argv[1])
            confirm = len(sys.argv) > 2 and sys.argv[2] == "--yes"
            
            if not deleter.health_check():
                return
            
            success = deleter.delete_video(video_unique_id, confirm)
            if success:
                print(f"\n🎉 비디오 {video_unique_id} 삭제 완료!")
            else:
                print(f"\n💥 비디오 {video_unique_id} 삭제 실패!")
        else:
            print("사용법:")
            print("  python delete_video_data.py                    # 대화형 모드")
            print("  python delete_video_data.py list              # 비디오 목록 표시")
            print("  python delete_video_data.py <video_id>        # 특정 비디오 삭제")
            print("  python delete_video_data.py <video_id> --yes  # 확인 없이 삭제")
    else:
        # 대화형 모드
        deleter.interactive_delete()

if __name__ == "__main__":
    main()
