#!/usr/bin/env python3
"""
저장된 장면그래프와 임베딩 데이터 확인 스크립트
"""

import requests
import json
import os
from typing import Dict, List, Any

class SceneGraphDataChecker:
    """저장된 장면그래프 데이터 확인 클래스"""
    
    def __init__(self, api_base_url: str = None):
        self.api_base_url = api_base_url or os.getenv("API_URL", "http://localhost:8000")
        self.session = requests.Session()
    
    def check_connection(self) -> bool:
        """API 서버 연결 확인"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            if response.status_code == 200:
                print("✅ API 서버 연결 성공")
                return True
            else:
                print(f"❌ API 서버 연결 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API 서버 연결 오류: {e}")
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
    
    def get_scenes(self, video_id: int) -> List[Dict[str, Any]]:
        """특정 비디오의 장면 목록 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/videos/{video_id}/scenes")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 장면 목록 조회 실패: {e}")
            return []
    
    def get_scene_graph(self, scene_id: int) -> Dict[str, Any]:
        """특정 장면의 그래프 정보 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/scenes/{scene_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 장면 그래프 조회 실패: {e}")
            return {}
    
    def get_objects(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 객체 노드 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/scenes/{scene_id}/objects")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 객체 노드 조회 실패: {e}")
            return []
    
    def get_events(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 이벤트 노드 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/scenes/{scene_id}/events")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 이벤트 노드 조회 실패: {e}")
            return []
    
    def get_spatial_relations(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 공간관계 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/scenes/{scene_id}/spatial")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 공간관계 조회 실패: {e}")
            return []
    
    def get_temporal_relations(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 시간관계 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/scenes/{scene_id}/temporal")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 시간관계 조회 실패: {e}")
            return []
    
    def get_embeddings(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 임베딩 정보 조회"""
        try:
            response = self.session.get(f"{self.api_base_url}/scenes/{scene_id}/embeddings")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 임베딩 정보 조회 실패: {e}")
            return []
    
    def check_all_data(self):
        """모든 저장된 데이터 확인"""
        print("🔍 저장된 장면그래프 데이터 확인")
        print("=" * 60)
        
        # 1. API 연결 확인
        if not self.check_connection():
            return
        
        # 2. 비디오 목록 조회
        print("\n📺 저장된 비디오 목록:")
        videos = self.get_videos()
        for video in videos:
            print(f"  - {video['drama_name']} {video['episode_number']} (ID: {video['id']}, Unique ID: {video['video_unique_id']})")
        
        if not videos:
            print("  저장된 비디오가 없습니다.")
            return
        
        # 3. 각 비디오의 장면들 확인
        for video in videos:
            print(f"\n🎭 비디오 '{video['drama_name']} {video['episode_number']}'의 장면들:")
            scenes = self.get_scenes(video['id'])
            
            if not scenes:
                print("  저장된 장면이 없습니다.")
                continue
            
            for scene in scenes:
                print(f"\n  📍 장면 ID: {scene['id']}")
                print(f"     - 장면 번호: {scene.get('scene_number', 'N/A')}")
                print(f"     - 프레임: {scene.get('start_frame', 'N/A')}-{scene.get('end_frame', 'N/A')}")
                print(f"     - 장소: {scene.get('scene_place', 'N/A')}")
                print(f"     - 시간: {scene.get('scene_time', 'N/A')}")
                print(f"     - 분위기: {scene.get('scene_atmosphere', 'N/A')}")
                
                # 4. 객체 노드 조회
                objects = self.get_objects(scene['id'])
                print(f"\n     👥 객체 노드 ({len(objects)}개):")
                for obj in objects:
                    print(f"       - {obj.get('label', 'N/A')} (ID: {obj.get('object_id', 'N/A')}, 타입: {obj.get('type_of', 'N/A')})")
                
                # 5. 이벤트 노드 조회
                events = self.get_events(scene['id'])
                print(f"\n     🎬 이벤트 노드 ({len(events)}개):")
                for event in events:
                    print(f"       - {event.get('verb', 'N/A')} (ID: {event.get('event_id', 'N/A')}, 주체: {event.get('subject_id', 'N/A')})")
                
                # 6. 공간관계 조회
                spatial = self.get_spatial_relations(scene['id'])
                print(f"\n     📍 공간관계 ({len(spatial)}개):")
                for rel in spatial:
                    print(f"       - {rel.get('predicate', 'N/A')} (ID: {rel.get('spatial_id', 'N/A')}, 주체: {rel.get('subject_id', 'N/A')} → 대상: {rel.get('object_id', 'N/A')})")
                
                # 7. 시간관계 조회
                temporal = self.get_temporal_relations(scene['id'])
                print(f"\n     ⏰ 시간관계 ({len(temporal)}개):")
                for rel in temporal:
                    print(f"       - {rel.get('predicate', 'N/A')} (ID: {rel.get('temporal_id', 'N/A')}, 주체: {rel.get('subject_id', 'N/A')} → 대상: {rel.get('object_id', 'N/A')})")
                
                # 8. 임베딩 정보 조회
                embeddings = self.get_embeddings(scene['id'])
                print(f"\n     🔗 임베딩 정보 ({len(embeddings)}개):")
                for emb in embeddings:
                    embedding_vector = emb.get('embedding', [])
                    vector_length = len(embedding_vector) if isinstance(embedding_vector, list) else 0
                    print(f"       - 노드 ID: {emb.get('node_id', 'N/A')}, 타입: {emb.get('node_type', 'N/A')}, 벡터 차원: {vector_length}")
                    if vector_length > 0:
                        print(f"         벡터 샘플: [{embedding_vector[0]:.4f}, {embedding_vector[1]:.4f}, {embedding_vector[2]:.4f}, ...]")
        
        print("\n" + "=" * 60)
        print("✅ 데이터 확인 완료!")

def main():
    """메인 실행 함수"""
    checker = SceneGraphDataChecker()
    checker.check_all_data()

if __name__ == "__main__":
    main()
