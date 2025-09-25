#!/usr/bin/env python3
"""
장면그래프 데이터베이스 통합 클라이언트
모든 DB API 접근 기능을 통합한 클래스
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 기존 클라이언트 모듈들 import
from src.db.util.check_stored_data import SceneGraphDataChecker
from src.db.util.delete_video_data import VideoDataDeleter
from src.db.util.scene_graph_api_uploader import SceneGraphAPIUploader

# 환경 변수 로드
load_dotenv()

class SceneGraphDBClient:
    """
    장면그래프 데이터베이스 통합 클라이언트
    
    이 클래스는 다음 기능들을 통합합니다:
    - 비디오 데이터 삭제 (VideoDataDeleter)
    - 저장된 데이터 확인 (SceneGraphDataChecker)  
    - 장면그래프 데이터 업로드 (SceneGraphAPIUploader)
    - 기본적인 DB API 접근 기능
    """
    
    def __init__(self, db_api_base_url: str = None):
        """
        초기화
        
        Args:
            db_api_base_url: API 서버 URL (기본값: 환경변수 API_URL 또는 http://localhost:8000)
        """
        self.db_api_base_url = db_api_base_url or os.getenv("API_URL", "http://localhost:8000")
        self.session = requests.Session()
        
        # 하위 클라이언트들 초기화
        self.deleter = VideoDataDeleter(self.db_api_base_url)
        self.checker = SceneGraphDataChecker(self.db_api_base_url)
        self.uploader = SceneGraphAPIUploader(self.db_api_base_url)
        
        print(f"🌐 SceneGraphClient 초기화 완료 - API URL: {self.db_api_base_url}")
    
    # ==================== 기본 연결 및 상태 확인 ====================
    
    def health_check(self) -> bool:
        """API 서버 헬스 체크"""
        return self.checker.check_connection()
    
    def get_server_info(self) -> Dict[str, Any]:
        """서버 기본 정보 조회"""
        try:
            response = self.session.get(f"{self.db_api_base_url}/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 서버 정보 조회 실패: {e}")
            return {}
    
    # ==================== 비디오 관리 ====================
    
    def get_videos(self) -> List[Dict[str, Any]]:
        """저장된 비디오 목록 조회"""
        return self.checker.get_videos()
    
    def get_video_info(self, video_unique_id: int) -> Optional[Dict[str, Any]]:
        """특정 비디오의 상세 정보 조회"""
        return self.deleter.get_video_info(video_unique_id)
    
    def create_video(self, drama_name: str, episode_number: str, video_unique_id: int = None) -> Optional[Dict[str, Any]]:
        """비디오 생성"""
        try:
            if video_unique_id is None:
                video_unique_id = self._generate_video_id(drama_name, episode_number)
            
            video_data = {
                "video_unique_id": video_unique_id,
                "drama_name": drama_name,
                "episode_number": episode_number
            }
            
            response = self.session.post(f"{self.db_api_base_url}/videos", json=video_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 비디오 생성 실패: {e}")
            return None
    
    def delete_video(self, video_unique_id: int, confirm: bool = False) -> bool:
        """비디오 및 연결된 모든 데이터 삭제"""
        return self.deleter.delete_video(video_unique_id, confirm)
    
    def list_videos(self) -> None:
        """비디오 목록 표시"""
        self.deleter.list_videos()
    
    # ==================== 장면 관리 ====================
    
    def get_scenes(self, video_id: int) -> List[Dict[str, Any]]:
        """특정 비디오의 장면 목록 조회"""
        return self.checker.get_scenes(video_id)
    
    def get_scene_graph(self, scene_id: int) -> Dict[str, Any]:
        """특정 장면의 완전한 그래프 정보 조회"""
        return self.checker.get_scene_graph(scene_id)
    
    def get_scene_objects(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 객체 노드 조회"""
        return self.checker.get_objects(scene_id)
    
    def get_scene_events(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 이벤트 노드 조회"""
        return self.checker.get_events(scene_id)
    
    def get_scene_spatial_relations(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 공간관계 조회"""
        return self.checker.get_spatial_relations(scene_id)
    
    def get_scene_temporal_relations(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 시간관계 조회"""
        return self.checker.get_temporal_relations(scene_id)
    
    def get_scene_embeddings(self, scene_id: int) -> List[Dict[str, Any]]:
        """특정 장면의 임베딩 정보 조회"""
        return self.checker.get_embeddings(scene_id)
    
    # ==================== 장면그래프 업로드 ====================
    
    def upload_scene_graph_with_pt(self, scene_data: Dict[str, Any], embedding_info: Dict[str, Any], 
                                 video_unique_id: int, drama_name: str, episode_number: str,
                                 start_frame: int, end_frame: int) -> bool:
        """
        장면그래프 데이터와 임베딩 정보를 직접 입력받아 업로드
        
        Args:
            scene_data: 장면그래프 JSON 데이터
            embedding_info: 임베딩 정보 {'node_info': [...], 'node_embeddings': [...]}
            video_unique_id: 비디오 고유 ID
            drama_name: 드라마명
            episode_number: 에피소드 번호
            start_frame: 시작 프레임
            end_frame: 종료 프레임
        
        Returns:
            bool: 업로드 성공 여부
        """
        try:
            print("🚀 장면그래프 데이터 직접 업로드 시작")
            print("=" * 50)
            
            # 1. API 서버 헬스 체크
            if not self.health_check():
                print("❌ API 서버에 연결할 수 없습니다.")
                return False
            
            # 2. 비디오 생성/조회
            video_result = self.create_video(drama_name, episode_number, video_unique_id)
            if not video_result:
                print("❌ 비디오 생성 실패")
                return False
            
            video_id = video_result.get('video_id')
            actual_video_unique_id = video_result.get('video_unique_id')
            print(f"✅ 비디오 준비 완료: {drama_name} {episode_number} (ID: {video_id})")
            
            # 3. 장면 메타데이터 생성 (임베딩 제외)
            scene_meta = scene_data.get('scene_graph', {}).get('meta', {})
            scene_payload = {
                "scene_number": f"{start_frame}-{end_frame}",
                "scene_place": scene_meta.get('scene_place'),
                "scene_time": scene_meta.get('scene_time'),
                "scene_atmosphere": scene_meta.get('scene_atmosphere'),
                "start_frame": start_frame,
                "end_frame": end_frame
            }
            
            # 장면 생성 API 호출 (임베딩 없이)
            scene_request = {
                "video_unique_id": actual_video_unique_id,
                "scene_data": scene_payload,
                "pt_data": None  # 임베딩은 나중에 처리
            }
            
            response = self.session.post(f"{self.db_api_base_url}/scenes", json=scene_request)
            response.raise_for_status()
            scene_result = response.json()
            scene_id = scene_result.get('scene_id')
            
            if not scene_id:
                print("❌ 장면 생성 실패")
                return False
            
            print(f"✅ 장면 생성 완료: {scene_id}")
            
            # 4. 노드 데이터 저장 (objects, events, spatial, temporal)
            self._create_nodes_from_data(scene_id, scene_data.get('scene_graph', {}), actual_video_unique_id)
            
            # 5. 임베딩 데이터 저장
            self._create_embeddings_from_info(scene_id, embedding_info, actual_video_unique_id)
            
            print("\n" + "=" * 50)
            print("✅ 장면그래프 데이터 업로드 완료!")
            print(f"📺 비디오: {drama_name} {episode_number}")
            print(f"🎭 장면: 프레임 {start_frame}-{end_frame}")
            print(f"🆔 비디오 ID: {video_id}, 장면 ID: {scene_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ 업로드 실패: {e}")
            return False
    
    # ==================== 내부 헬퍼 메서드 ====================
    
    def _create_nodes_from_data(self, scene_id: int, scene_graph: Dict[str, Any], video_unique_id: int) -> None:
        """장면그래프 데이터에서 노드들을 생성"""
        print(f"🔗 노드 데이터 저장 시작: Scene ID {scene_id}")
        
        try:
            # 1. 객체 노드 저장
            objects = scene_graph.get('objects', [])
            if objects:
                self._create_objects_from_data(scene_id, objects, video_unique_id)
            
            # 2. 이벤트 노드 저장
            events = scene_graph.get('events', [])
            if events:
                self._create_events_from_data(scene_id, events, video_unique_id)
            
            # 3. 공간 관계 저장
            spatial = scene_graph.get('spatial', [])
            if spatial:
                self._create_spatial_from_data(scene_id, spatial, video_unique_id)
            
            # 4. 시간 관계 저장
            temporal = scene_graph.get('temporal', [])
            if temporal:
                self._create_temporal_from_data(scene_id, temporal, video_unique_id)
            
            print(f"✅ 모든 노드 데이터 저장 완료")
            
        except Exception as e:
            print(f"❌ 노드 데이터 저장 실패: {e}")
            raise
    
    def _create_objects_from_data(self, scene_id: int, objects: List[Dict[str, Any]], video_unique_id: int) -> None:
        """객체 노드 데이터 저장"""
        print(f"👥 객체 노드 저장: {len(objects)}개")
        
        for obj in objects:
            try:
                original_object_id = obj.get('object_id')
                new_object_id = f"{video_unique_id}_{scene_id}_object_{original_object_id}"
                
                object_data = {
                    "scene_id": scene_id,
                    "object_id": new_object_id,
                    "super_type": obj.get('super_type', 'unknown'),
                    "type_of": obj.get('type of', 'unknown'),
                    "label": obj.get('label', 'unknown'),
                    "attributes": obj.get('attributes', {})
                }
                
                response = self.session.post(f"{self.db_api_base_url}/objects", json=object_data)
                response.raise_for_status()
                print(f"  ✅ 객체 저장: {obj.get('label')} (ID: {new_object_id})")
                
            except Exception as e:
                print(f"  ❌ 객체 저장 실패: {obj.get('label')} - {e}")
    
    def _create_events_from_data(self, scene_id: int, events: List[Dict[str, Any]], video_unique_id: int) -> None:
        """이벤트 노드 데이터 저장"""
        print(f"🎬 이벤트 노드 저장: {len(events)}개")
        
        for i, event in enumerate(events):
            try:
                original_event_id = event.get('event_id', f"EVT_{i}")
                new_event_id = f"{video_unique_id}_{scene_id}_event_{original_event_id}"
                
                # subject_id와 object_id를 새로운 객체 ID로 매핑
                subject_id = str(event.get('subject', ''))
                object_id = str(event.get('object', '')) if event.get('object') else None
                
                # 객체 ID 매핑 (간단한 매핑 로직)
                if subject_id.isdigit():
                    subject_id = f"{video_unique_id}_{scene_id}_object_{subject_id}"
                if object_id and object_id.isdigit():
                    object_id = f"{video_unique_id}_{scene_id}_object_{object_id}"
                
                event_data = {
                    "scene_id": scene_id,
                    "event_id": new_event_id,
                    "subject_id": subject_id,
                    "verb": event.get('verb', 'unknown_action'),
                    "object_id": object_id,
                    "attributes": {"attribute": event.get('attribute', '')}
                }
                
                response = self.session.post(f"{self.db_api_base_url}/events", json=event_data)
                response.raise_for_status()
                print(f"  ✅ 이벤트 저장: {event.get('verb')} (ID: {new_event_id})")
                
            except Exception as e:
                print(f"  ❌ 이벤트 저장 실패: {event.get('verb')} - {e}")
    
    def _create_spatial_from_data(self, scene_id: int, spatial: List[Dict[str, Any]], video_unique_id: int) -> None:
        """공간 관계 데이터 저장"""
        print(f"📍 공간 관계 저장: {len(spatial)}개")
        
        for i, rel in enumerate(spatial):
            try:
                original_spatial_id = rel.get('spatial_id', f"SPAT_{i}")
                new_spatial_id = f"{video_unique_id}_{scene_id}_spatial_{original_spatial_id}"
                
                # subject_id와 object_id를 새로운 객체 ID로 매핑
                subject_id = str(rel.get('subject', ''))
                object_id = str(rel.get('object', ''))
                
                if subject_id.isdigit():
                    subject_id = f"{video_unique_id}_{scene_id}_object_{subject_id}"
                if object_id.isdigit():
                    object_id = f"{video_unique_id}_{scene_id}_object_{object_id}"
                
                spatial_data = {
                    "scene_id": scene_id,
                    "spatial_id": new_spatial_id,
                    "subject_id": subject_id,
                    "predicate": rel.get('predicate', 'unknown_relation'),
                    "object_id": object_id
                }
                
                response = self.session.post(f"{self.db_api_base_url}/spatial", json=spatial_data)
                response.raise_for_status()
                print(f"  ✅ 공간 관계 저장: {rel.get('predicate')} (ID: {new_spatial_id})")
                
            except Exception as e:
                print(f"  ❌ 공간 관계 저장 실패: {rel.get('predicate')} - {e}")
    
    def _create_temporal_from_data(self, scene_id: int, temporal: List[Dict[str, Any]], video_unique_id: int) -> None:
        """시간 관계 데이터 저장"""
        print(f"⏰ 시간 관계 저장: {len(temporal)}개")
        
        for i, rel in enumerate(temporal):
            try:
                original_temporal_id = rel.get('temporal_id', f"TEMP_{i}")
                new_temporal_id = f"{video_unique_id}_{scene_id}_temporal_{original_temporal_id}"
                
                # subject_id와 object_id를 새로운 이벤트 ID로 매핑
                subject_id = str(rel.get('subject', ''))
                object_id = str(rel.get('object', ''))
                
                if subject_id.isdigit():
                    subject_id = f"{video_unique_id}_{scene_id}_event_{subject_id}"
                if object_id.isdigit():
                    object_id = f"{video_unique_id}_{scene_id}_event_{object_id}"
                
                temporal_data = {
                    "scene_id": scene_id,
                    "temporal_id": new_temporal_id,
                    "subject_id": subject_id,
                    "predicate": rel.get('predicate', 'unknown_relation'),
                    "object_id": object_id
                }
                
                response = self.session.post(f"{self.db_api_base_url}/temporal", json=temporal_data)
                response.raise_for_status()
                print(f"  ✅ 시간 관계 저장: {rel.get('predicate')} (ID: {new_temporal_id})")
                
            except Exception as e:
                print(f"  ❌ 시간 관계 저장 실패: {rel.get('predicate')} - {e}")
    
    def _create_embeddings_from_info(self, scene_id: int, embedding_info: Dict[str, Any], video_unique_id: int) -> None:
        """임베딩 정보에서 임베딩 데이터 저장"""
        print(f"🔗 임베딩 데이터 저장 시작")
        
        try:
            node_info = embedding_info.get('node_info', [])
            node_embeddings = embedding_info.get('node_embeddings', [])
            
            if len(node_info) != len(node_embeddings):
                print(f"❌ 노드 정보와 임베딩 개수가 일치하지 않음: {len(node_info)} vs {len(node_embeddings)}")
                return
            
            # scene 노드는 제외하고 처리
            for i, node in enumerate(node_info):
                node_type = node.get('node_type')
                if node_type == 'scene':
                    continue
                
                original_node_id = node.get('node_id')
                node_label = node.get('node_label', 'unknown')
                
                # 실제 node_id 생성: {video_unique_id}_{scene_id}_{node_type}_{orig_id}
                actual_node_id = f"{video_unique_id}_{scene_id}_{node_type}_{original_node_id}"
                
                # 임베딩 벡터 가져오기
                embedding_vector = node_embeddings[i]
                
                # 임베딩 데이터 저장
                embedding_data = {
                    "node_id": actual_node_id,
                    "node_type": node_type,
                    "embedding": embedding_vector
                }
                
                # 임베딩 저장 API 호출 (직접 데이터베이스에 저장)
                response = self.session.post(f"{self.db_api_base_url}/embeddings", json=embedding_data)
                response.raise_for_status()
                
                print(f"  ✅ 임베딩 저장: {node_label} ({node_type}) - {actual_node_id}")
            
            print(f"✅ 임베딩 데이터 저장 완료: {len([n for n in node_info if n.get('node_type') != 'scene'])}개")
            
        except Exception as e:
            print(f"❌ 임베딩 데이터 저장 실패: {e}")
            raise

    # ==================== 검색 기능 ====================
    
    def vector_search(self, query_embedding: List[float], node_type: str = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        벡터 기반 유사도 검색
        
        Args:
            query_embedding: 검색할 벡터 (384차원)
            node_type: 노드 타입 필터 (object, event, spatial, temporal)
            top_k: 반환할 결과 수
        
        Returns:
            List[Dict]: 검색 결과
        """
        try:
            search_data = {
                "query_embedding": query_embedding,
                "node_type": node_type,
                "top_k": top_k
            }
            
            response = self.session.post(f"{self.db_api_base_url}/search/vector", json=search_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            return []
    
    def hybrid_search(self, query_text: str, query_embedding: List[float], node_type: str = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (텍스트 + 벡터)
        
        Args:
            query_text: 검색할 텍스트
            query_embedding: 검색할 벡터 (384차원)
            node_type: 노드 타입 필터
            top_k: 반환할 결과 수
        
        Returns:
            List[Dict]: 검색 결과
        """
        try:
            search_data = {
                "query_text": query_text,
                "query_embedding": query_embedding,
                "node_type": node_type,
                "top_k": top_k
            }
            
            response = self.session.post(f"{self.db_api_base_url}/search/hybrid", json=search_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 하이브리드 검색 실패: {e}")
            return []
    
    # ==================== 데이터 확인 및 관리 ====================
    
    def check_all_data(self) -> None:
        """모든 저장된 데이터 확인"""
        self.checker.check_all_data()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """데이터베이스 요약 정보 조회"""
        try:
            videos = self.get_videos()
            total_scenes = 0
            total_objects = 0
            total_events = 0
            total_embeddings = 0
            
            for video in videos:
                scenes = self.get_scenes(video['id'])
                total_scenes += len(scenes)
                
                for scene in scenes:
                    objects = self.get_scene_objects(scene['id'])
                    events = self.get_scene_events(scene['id'])
                    embeddings = self.get_scene_embeddings(scene['id'])
                    
                    total_objects += len(objects)
                    total_events += len(events)
                    total_embeddings += len(embeddings)
            
            return {
                "total_videos": len(videos),
                "total_scenes": total_scenes,
                "total_objects": total_objects,
                "total_events": total_events,
                "total_embeddings": total_embeddings,
                "videos": videos
            }
        except Exception as e:
            print(f"❌ 데이터 요약 조회 실패: {e}")
            return {}
    
    # ==================== 유틸리티 함수 ====================
    
    def _generate_video_id(self, drama_name: str, episode_number: str) -> int:
        """비디오 고유 ID 생성"""
        # 간단한 해시 기반 ID 생성
        import hashlib
        content = f"{drama_name}_{episode_number}"
        hash_obj = hashlib.md5(content.encode())
        return int(hash_obj.hexdigest()[:8], 16)
    
    def export_scene_data(self, scene_id: int, output_file: str = None) -> bool:
        """
        장면 데이터를 JSON 파일로 내보내기
        
        Args:
            scene_id: 장면 ID
            output_file: 출력 파일 경로 (기본값: scene_{scene_id}.json)
        
        Returns:
            bool: 내보내기 성공 여부
        """
        try:
            scene_data = self.get_scene_graph(scene_id)
            if not scene_data:
                print(f"❌ 장면 {scene_id} 데이터를 찾을 수 없습니다.")
                return False
            
            if output_file is None:
                output_file = f"scene_{scene_id}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(scene_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 장면 데이터 내보내기 완료: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 장면 데이터 내보내기 실패: {e}")
            return False
    
    def import_scene_data(self, json_file_path: str) -> bool:
        """
        JSON 파일에서 장면 데이터 가져오기
        
        Args:
            json_file_path: JSON 파일 경로
        
        Returns:
            bool: 가져오기 성공 여부
        """
        return self.upload_scene_graph(json_file_path)
    
    # ==================== 대화형 모드 ====================
    
    def interactive_mode(self) -> None:
        """대화형 모드 실행"""
        print("🎭 장면그래프 데이터베이스 클라이언트")
        print("=" * 50)
        
        while True:
            print("\n사용 가능한 명령어:")
            print("1. 데이터 확인 (check)")
            print("2. 비디오 목록 (list)")
            print("3. 비디오 삭제 (delete)")
            print("4. 장면그래프 업로드 (upload)")
            print("5. 벡터 검색 (search)")
            print("6. 데이터 요약 (summary)")
            print("7. 종료 (quit)")
            
            choice = input("\n명령어를 선택하세요: ").strip().lower()
            
            if choice == 'check':
                self.check_all_data()
            elif choice == 'list':
                self.list_videos()
            elif choice == 'delete':
                self._interactive_delete()
            elif choice == 'upload':
                self._interactive_upload_new()
            elif choice == 'search':
                self._interactive_search()
            elif choice == 'summary':
                self._show_summary()
            elif choice in ['quit', 'exit', 'q']:
                print("👋 프로그램을 종료합니다.")
                break
            else:
                print("❌ 잘못된 명령어입니다.")
    
    def _interactive_delete(self) -> None:
        """대화형 삭제 모드"""
        self.list_videos()
        try:
            video_id = int(input("삭제할 비디오의 고유 ID를 입력하세요: "))
            confirm = input("정말로 삭제하시겠습니까? (yes/no): ").strip().lower() == 'yes'
            self.delete_video(video_id, confirm)
        except ValueError:
            print("❌ 올바른 숫자를 입력해주세요.")
    
    def _interactive_upload_new(self) -> None:
        """대화형 업로드 모드 (새로운 인터페이스)"""
        print("📝 새로운 업로드 인터페이스")
        print("이 기능은 직접 데이터를 입력받아 업로드합니다.")
        print("현재는 파일 기반 업로드만 지원합니다.")
        
        json_file = input("JSON 파일 경로를 입력하세요: ").strip()
        
        if os.path.exists(json_file):
            # 기존 파일 기반 업로드 (임시)
            print("⚠️  파일 기반 업로드는 현재 지원되지 않습니다.")
            print("💡 직접 데이터를 입력하여 업로드하세요.")
        else:
            print("❌ 파일을 찾을 수 없습니다.")
    
    def _interactive_search(self) -> None:
        """대화형 검색 모드"""
        print("벡터 검색을 위해서는 384차원 벡터가 필요합니다.")
        print("현재는 간단한 텍스트 검색만 지원합니다.")
        # TODO: 실제 벡터 검색 구현
    
    def _show_summary(self) -> None:
        """데이터 요약 표시"""
        summary = self.get_data_summary()
        if summary:
            print("\n📊 데이터베이스 요약:")
            print(f"  - 비디오: {summary['total_videos']}개")
            print(f"  - 장면: {summary['total_scenes']}개")
            print(f"  - 객체: {summary['total_objects']}개")
            print(f"  - 이벤트: {summary['total_events']}개")
            print(f"  - 임베딩: {summary['total_embeddings']}개")


def main():
    """메인 실행 함수"""
    import sys
    
    client = SceneGraphClient()
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "check":
            client.check_all_data()
        elif command == "list":
            client.list_videos()
        elif command == "summary":
            client._show_summary()
        elif command == "interactive":
            client.interactive_mode()
        else:
            print("사용법:")
            print("  python scene_graph_client.py check        # 데이터 확인")
            print("  python scene_graph_client.py list         # 비디오 목록")
            print("  python scene_graph_client.py summary      # 데이터 요약")
            print("  python scene_graph_client.py interactive  # 대화형 모드")
    else:
        # 기본적으로 대화형 모드 실행
        client.interactive_mode()


if __name__ == "__main__":
    main()
