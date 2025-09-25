#!/usr/bin/env python3
"""
SceneGraphAnalyzer 클래스
장면 그래프 JSON을 입력으로 받아 RGCN을 통해 노드 임베딩을 생성하는 모듈
"""

import json
import torch
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from collections import defaultdict

from torch_geometric.data import HeteroData, Data
from torch_geometric.nn import RGCNConv
from sentence_transformers import SentenceTransformer


class SceneGraphAnalyzer:
    """
    장면 그래프를 분석하여 노드 임베딩을 생성하는 클래스
    """
    
    def __init__(self, 
                 model_path: str = "model/embed_triplet_struct_ver1+2/best_model.pt",
                 edge_map_path: str = "config/graph/edge_type_map.json",
                 sbert_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 device: Optional[str] = None):
        """
        SceneGraphAnalyzer 초기화
        
        Args:
            model_path (str): 학습된 RGCN 모델 경로
            edge_map_path (str): 엣지 타입 매핑 파일 경로
            sbert_model (str): Sentence-BERT 모델명
            device (str, optional): 사용할 디바이스. None이면 자동 선택
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sbert_model_name = sbert_model
        
        # 모델 파라미터 (학습 시와 동일하게 설정)
        self.IN_DIM = 384
        self.HIDDEN = 512
        self.OUT_DIM = 384
        self.NUM_BASES = 30
        self.HOP = 1
        self.SELF_WEIGHT = 0.8
        
        # 엣지 타입 매핑 로드
        self.edge_map_path = Path(edge_map_path)
        if not self.edge_map_path.exists():
            raise FileNotFoundError(f"Edge map file not found: {edge_map_path}")
        
        with self.edge_map_path.open() as f:
            self.EDGE2ID: Dict[str, int] = json.load(f)
        
        # Sentence-BERT 모델 초기화
        self.sbert_model = SentenceTransformer(sbert_model, device=self.device).eval()
        
        # RGCN 모델 초기화
        self.rgcn_model = self._load_rgcn_model(model_path)
        
        # 텍스트 캐시 (중복 계산 방지)
        self._text_cache: Dict[str, torch.Tensor] = {}
    
    def _load_rgcn_model(self, model_path: str) -> torch.nn.Module:
        """
        학습된 RGCN 모델을 로드합니다.
        
        Args:
            model_path (str): 모델 파일 경로
            
        Returns:
            torch.nn.Module: 로드된 RGCN 모델
        """
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        num_rel = len(self.EDGE2ID)
        model = RGCN(num_rel, self.IN_DIM, self.HIDDEN, self.OUT_DIM, 
                    self.NUM_BASES, self.HOP, self.SELF_WEIGHT)
        
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.to(self.device).eval()
        
        return model
    
    @torch.no_grad()
    def _embed_text(self, text: str) -> torch.Tensor:
        """
        텍스트를 Sentence-BERT로 임베딩합니다.
        
        Args:
            text (str): 임베딩할 텍스트
            
        Returns:
            torch.Tensor: 임베딩 벡터
        """
        if text not in self._text_cache:
            embedding = self.sbert_model.encode(
                text, 
                normalize_embeddings=True
            )
            self._text_cache[text] = torch.tensor(embedding, dtype=torch.float32)
        
        return self._text_cache[text]
    
    def _preprocess_scene_text(self, meta: Dict) -> str:
        """
        장면 메타데이터를 문장 형태로 전처리합니다.
        
        Args:
            meta (Dict): 장면 메타데이터
            
        Returns:
            str: 전처리된 장면 텍스트
        """
        scene_txt = f"place {meta.get('scene_place', '')} time {meta.get('scene_time', '')} atmosphere {meta.get('scene_atmosphere', '')}".strip()
        return scene_txt or "scene"
    
    def _preprocess_object_text(self, obj: Dict) -> str:
        """
        객체 정보를 문장 형태로 전처리합니다.
        
        Args:
            obj (Dict): 객체 정보
            
        Returns:
            str: 전처리된 객체 텍스트
        """
        return f"A {obj.get('type of', '')} which is a kind of {obj.get('super_type', '')}."
    
    def _preprocess_event_text(self, event: Dict) -> str:
        """
        이벤트 정보를 문장 형태로 전처리합니다.
        
        Args:
            event (Dict): 이벤트 정보
            
        Returns:
            str: 전처리된 이벤트 텍스트
        """
        return event.get('verb', '')
    
    def _preprocess_spatial_text(self, spatial: Dict) -> str:
        """
        공간 관계 정보를 문장 형태로 전처리합니다.
        
        Args:
            spatial (Dict): 공간 관계 정보
            
        Returns:
            str: 전처리된 공간 관계 텍스트
        """
        return spatial.get('predicate', '')
    
    def _extract_id(self, x) -> Optional[int]:
        """
        ID를 추출합니다.
        
        Args:
            x: ID가 포함된 객체
            
        Returns:
            Optional[int]: 추출된 ID
        """
        if isinstance(x, dict):
            for k in ("object_id", "event_id", "spatial_id", "temporal_id"):
                if k in x:
                    return x[k]
        if isinstance(x, int):
            return x
        return None
    
    def _decode_edge_key(self, et_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        엣지 타입 이름을 디코딩합니다.
        
        Args:
            et_name (str): 엣지 타입 이름
            
        Returns:
            Tuple: (source_type, relation, dest_type)
        """
        parts = et_name.split("_")
        if len(parts) < 3:
            return None, None, None
        st = parts[0]
        dt = parts[-1]
        rel = "_".join(parts[1:-1])
        return st, rel, dt
    
    def _safe_add_edge(self, src_id: int, dst_id: int, rel: str, 
                      nid_map: Dict, edge_idx_dict: Dict, edge_typ_dict: Dict,
                      file_name: str = "(unknown)", event_id: Optional[int] = None):
        """
        안전하게 엣지를 추가합니다.
        
        Args:
            src_id (int): 소스 노드 ID
            dst_id (int): 대상 노드 ID
            rel (str): 관계명
            nid_map (Dict): 노드 ID 매핑
            edge_idx_dict (Dict): 엣지 인덱스 딕셔너리
            edge_typ_dict (Dict): 엣지 타입 딕셔너리
            file_name (str): 파일명 (디버깅용)
            event_id (Optional[int]): 이벤트 ID (디버깅용)
        """
        if src_id not in nid_map or dst_id not in nid_map:
            return
        
        st, si = nid_map[src_id]
        dt, di = nid_map[dst_id]
        rel_name = f"{st}_{rel}_{dt}"
        
        if rel_name not in self.EDGE2ID:
            print(f"[skip] unknown rel_name: {rel_name} | file={file_name} | ev_id={event_id}")
            return
        
        eid = self.EDGE2ID[rel_name]
        edge_idx_dict[(st, rel, dt)].append([si, di])
        edge_typ_dict[(st, rel, dt)].append(eid)
    
    def json_to_hetero_data(self, scene_graph_json: Dict, file_name: str = "(unknown)") -> Optional[HeteroData]:
        """
        장면 그래프 JSON을 HeteroData로 변환합니다.
        
        Args:
            scene_graph_json (Dict): 장면 그래프 JSON
            file_name (str): 파일명 (디버깅용)
            
        Returns:
            Optional[HeteroData]: 변환된 이종 그래프 데이터
        """
        if not isinstance(scene_graph_json, dict) or "scene_graph" not in scene_graph_json:
            return None
        
        g = scene_graph_json["scene_graph"]
        data, nid_map = HeteroData(), {}
        
        # 장면 노드 처리
        meta = g.get("meta", {})
        scene_txt = self._preprocess_scene_text(meta)
        data["scene"].x = self._embed_text(scene_txt).unsqueeze(0)
        data["scene"].node_type = torch.full((1,), 0)
        data["scene"].node_ids = [50000]  # scene 노드 ID
        scene_idx = 0
        
        # 객체 노드 처리
        obj_feats = []
        obj_types = []
        obj_ids = []
        for o in g.get("objects", []):
            text = self._preprocess_object_text(o)
            obj_feats.append(self._embed_text(text))
            obj_types.append(o.get("type of", "unknown"))
            obj_ids.append(o["object_id"])
            nid_map[o["object_id"]] = ("object", len(obj_feats) - 1)
        
        data["object"].x = torch.stack(obj_feats) if obj_feats else torch.empty((0, 384))
        data["object"].node_type = torch.full((len(obj_feats),), 1)
        data["object"].label_text = obj_types
        data["object"].node_ids = obj_ids
        
        # 이벤트 노드 처리
        evt_feats = []
        evt_verbs = []
        evt_ids = []
        for ev in g.get("events", []):
            text = self._preprocess_event_text(ev)
            evt_feats.append(self._embed_text(text))
            evt_verbs.append(ev.get("verb", "unknown"))
            evt_ids.append(ev["event_id"])
            nid_map[ev["event_id"]] = ("event", len(evt_feats) - 1)
        
        data["event"].x = torch.stack(evt_feats) if evt_feats else torch.empty((0, 384))
        data["event"].node_type = torch.full((len(evt_feats),), 2)
        data["event"].label_text = evt_verbs
        data["event"].node_ids = evt_ids
        
        # 공간 관계 노드 처리
        spat_feats = []
        spat_preds = []
        for sp in g.get("spatial", []):
            text = self._preprocess_spatial_text(sp)
            spat_feats.append(self._embed_text(text))
            spat_preds.append(sp.get("predicate", "unknown"))
            nid_map[sp["spatial_id"]] = ("spatial", len(spat_feats) - 1)
        
        data["spatial"].x = torch.stack(spat_feats) if spat_feats else torch.empty((0, 384))
        data["spatial"].node_type = torch.full((len(spat_feats),), 3)
        data["spatial"].label_text = spat_preds
        
        # 엣지 생성
        edge_idx_dict, edge_typ_dict = defaultdict(list), defaultdict(list)
        
        # 장면과 다른 노드들 간의 엣지
        for o in g.get("objects", []):
            self._safe_add_edge(scene_idx, o["object_id"], "in_scene", nid_map, edge_idx_dict, edge_typ_dict, file_name)
            self._safe_add_edge(o["object_id"], scene_idx, "to_scene", nid_map, edge_idx_dict, edge_typ_dict, file_name)
        
        for ev in g.get("events", []):
            self._safe_add_edge(scene_idx, ev["event_id"], "in_scene", nid_map, edge_idx_dict, edge_typ_dict, file_name)
            self._safe_add_edge(ev["event_id"], scene_idx, "to_scene", nid_map, edge_idx_dict, edge_typ_dict, file_name)
            
            # 이벤트와 객체 간의 엣지
            subj = self._extract_id(ev.get("subject"))
            obj = self._extract_id(ev.get("object"))
            
            if subj is not None:
                self._safe_add_edge(subj, ev["event_id"], "subject_of_event", nid_map, edge_idx_dict, edge_typ_dict, file_name, ev.get("event_id"))
            
            if obj is not None and nid_map.get(obj, (None,))[0] == "object":
                self._safe_add_edge(ev["event_id"], obj, "object_of_event", nid_map, edge_idx_dict, edge_typ_dict, file_name, ev.get("event_id"))
        
        # 공간 관계 엣지
        for sp in g.get("spatial", []):
            self._safe_add_edge(sp["subject"], sp["spatial_id"], "subject_of_spatial", nid_map, edge_idx_dict, edge_typ_dict, file_name)
            obj_id = sp.get("object", None)
            if isinstance(obj_id, int) and nid_map.get(obj_id, (None,))[0] == "object":
                self._safe_add_edge(sp["spatial_id"], obj_id, "object_of_spatial", nid_map, edge_idx_dict, edge_typ_dict, file_name)
        
        # 시간 관계 엣지
        for tm in g.get("temporal", []):
            self._safe_add_edge(tm["subject"], tm["object"], "before", nid_map, edge_idx_dict, edge_typ_dict, file_name)
        
        # 엣지 데이터 설정
        for key, pairs in edge_idx_dict.items():
            et_name = f"{key[0]}_{key[1]}_{key[2]}"
            eid = self.EDGE2ID[et_name]
            data[key].edge_index = torch.tensor(pairs, dtype=torch.long).t()
            data[key].edge_type = torch.full((len(pairs),), eid, dtype=torch.long)
        
        # 빈 엣지 타입들 초기화
        for et_name, eid in self.EDGE2ID.items():
            st, rel, dt = self._decode_edge_key(et_name)
            if None in (st, rel, dt):
                continue
            key = (st, rel, dt)
            if key not in data.edge_types:
                data[key].edge_index = torch.empty((2, 0), dtype=torch.long)
                data[key].edge_type = torch.full((0,), eid, dtype=torch.long)
        
        return data
    
    def analyze_scene_graph(self, scene_graph_json: Union[Dict, str, Path]) -> Dict[str, torch.Tensor]:
        """
        장면 그래프를 분석하여 노드 임베딩을 생성합니다.
        
        Args:
            scene_graph_json: 장면 그래프 JSON (딕셔너리, 파일 경로, 또는 Path 객체)
            
        Returns:
            Dict[str, torch.Tensor]: 노드 타입별 임베딩 딕셔너리
                - "scene": 장면 임베딩
                - "object": 객체 임베딩들
                - "event": 이벤트 임베딩들
                - "spatial": 공간 관계 임베딩들
                - "node_embeddings": 전체 노드 임베딩 (동종 그래프)
                - "node_types": 노드 타입 정보
                - "node_labels": 노드 라벨 정보
        """
        # JSON 로드
        if isinstance(scene_graph_json, (str, Path)):
            with open(scene_graph_json, 'r', encoding='utf-8') as f:
                scene_graph_json = json.load(f)
        
        # 이종 그래프로 변환
        hetero_data = self.json_to_hetero_data(scene_graph_json)
        if hetero_data is None:
            raise ValueError("Invalid scene graph JSON format")
        
        # 동종 그래프로 변환
        homo_data = hetero_data.to_homogeneous(
            node_attrs=["x", "node_type"],
            add_node_type=True,
            add_edge_type=False
        )
        
        # RGCN을 통한 임베딩 생성
        with torch.no_grad():
            homo_data = homo_data.to(self.device)
            node_embeddings = self.rgcn_model(
                homo_data.x, 
                homo_data.edge_index, 
                homo_data.edge_type
            )
            node_embeddings = F.normalize(node_embeddings, dim=1)
        
        # 노드 정보 추출 (순서대로)
        node_info = self._extract_node_info(hetero_data, homo_data.node_type)
        
        # 결과 구성
        result = {
            "node_embeddings": node_embeddings.cpu().tolist(),  # 리스트 형태로 변환
            "node_info": node_info,  # 각 노드의 상세 정보
            "node_types": homo_data.node_type.cpu().tolist(),  # 리스트 형태로 변환
            "node_labels": self._extract_node_labels(hetero_data)
        }
        
        # 노드 타입별로 임베딩 분리 (기존 호환성 유지)
        node_type_mapping = {0: "scene", 1: "object", 2: "event", 3: "spatial"}
        for node_type, type_name in node_type_mapping.items():
            mask = homo_data.node_type == node_type
            if mask.any():
                result[type_name] = node_embeddings[mask].cpu().tolist()  # 리스트 형태로 변환
            else:
                result[type_name] = []  # 빈 리스트로 초기화
        
        return result
    
    def _extract_node_info(self, hetero_data: HeteroData, node_types: torch.Tensor) -> List[Dict]:
        """
        각 노드의 상세 정보를 추출합니다.
        
        Args:
            hetero_data (HeteroData): 이종 그래프 데이터
            node_types (torch.Tensor): 노드 타입 정보
            
        Returns:
            List[Dict]: 각 노드의 상세 정보 리스트
        """
        node_info = []
        
        # 노드 타입별로 정보 추출
        node_type_mapping = {0: "scene", 1: "object", 2: "event", 3: "spatial"}
        
        # 각 타입별 인덱스 추적
        scene_idx = 0
        obj_idx = 0
        evt_idx = 0
        spat_idx = 0
        
        for i, node_type in enumerate(node_types.tolist()):
            type_name = node_type_mapping[node_type]
            
            if node_type == 0:  # scene
                node_id = hetero_data["scene"].node_ids[scene_idx] if hasattr(hetero_data["scene"], "node_ids") else 50000
                node_info.append({
                    "node_type": "scene",
                    "node_id": node_id,
                    "node_label": "scene",
                    "type_name": "scene"
                })
                scene_idx += 1
            elif node_type == 1:  # object
                if hasattr(hetero_data["object"], "node_ids") and obj_idx < len(hetero_data["object"].node_ids):
                    node_id = hetero_data["object"].node_ids[obj_idx]
                    node_label = hetero_data["object"].label_text[obj_idx] if hasattr(hetero_data["object"], "label_text") else "unknown"
                else:
                    node_id = obj_idx + 1
                    node_label = "unknown"
                
                node_info.append({
                    "node_type": "object", 
                    "node_id": node_id,
                    "node_label": node_label,
                    "type_name": "object"
                })
                obj_idx += 1
            elif node_type == 2:  # event
                if hasattr(hetero_data["event"], "node_ids") and evt_idx < len(hetero_data["event"].node_ids):
                    node_id = hetero_data["event"].node_ids[evt_idx]
                    node_label = hetero_data["event"].label_text[evt_idx] if hasattr(hetero_data["event"], "label_text") else "unknown"
                else:
                    node_id = evt_idx + 101
                    node_label = "unknown"
                
                node_info.append({
                    "node_type": "event",
                    "node_id": node_id,
                    "node_label": node_label,
                    "type_name": "event"
                })
                evt_idx += 1
            else:  # spatial
                node_info.append({
                    "node_type": "spatial",
                    "node_id": spat_idx + 20000,
                    "node_label": "spatial",
                    "type_name": "spatial"
                })
                spat_idx += 1
        
        return node_info
    
    def _extract_node_labels(self, hetero_data: HeteroData) -> List[str]:
        """
        노드 라벨을 추출합니다.
        
        Args:
            hetero_data (HeteroData): 이종 그래프 데이터
            
        Returns:
            List[str]: 노드 라벨 리스트
        """
        labels = []
        
        # 장면 노드
        if hasattr(hetero_data["scene"], "x") and hetero_data["scene"].x.size(0) > 0:
            labels.append("scene")
        
        # 객체 노드
        if hasattr(hetero_data["object"], "label_text"):
            labels.extend(hetero_data["object"].label_text)
        
        # 이벤트 노드
        if hasattr(hetero_data["event"], "label_text"):
            labels.extend(hetero_data["event"].label_text)
        
        # 공간 관계 노드
        if hasattr(hetero_data["spatial"], "label_text"):
            labels.extend(hetero_data["spatial"].label_text)
        
        return labels
    
    def get_node_info(self, scene_graph_json: Union[Dict, str, Path]) -> Dict[str, List[Dict]]:
        """
        장면 그래프의 노드 정보를 반환합니다.
        
        Args:
            scene_graph_json: 장면 그래프 JSON
            
        Returns:
            Dict[str, List[Dict]]: 노드 타입별 정보
        """
        if isinstance(scene_graph_json, (str, Path)):
            with open(scene_graph_json, 'r', encoding='utf-8') as f:
                scene_graph_json = json.load(f)
        
        g = scene_graph_json["scene_graph"]
        
        result = {
            "scene": [{"id": 0, "text": self._preprocess_scene_text(g.get("meta", {}))}],
            "objects": [],
            "events": [],
            "spatial": []
        }
        
        for obj in g.get("objects", []):
            result["objects"].append({
                "id": obj["object_id"],
                "text": self._preprocess_object_text(obj),
                "type": obj.get("type of", ""),
                "super_type": obj.get("super_type", "")
            })
        
        for event in g.get("events", []):
            result["events"].append({
                "id": event["event_id"],
                "text": self._preprocess_event_text(event),
                "verb": event.get("verb", ""),
                "subject": event.get("subject"),
                "object": event.get("object")
            })
        
        for spatial in g.get("spatial", []):
            result["spatial"].append({
                "id": spatial["spatial_id"],
                "text": self._preprocess_spatial_text(spatial),
                "predicate": spatial.get("predicate", ""),
                "subject": spatial.get("subject"),
                "object": spatial.get("object")
            })
        
        return result


class RGCN(torch.nn.Module):
    """
    RGCN 모델 클래스
    """
    
    def __init__(self, num_rel: int, in_dim: int, hidden_dim: int, out_dim: int, 
                 num_bases: int, hop: int, self_weight: float):
        super().__init__()
        self.self_loop_id = num_rel
        self.self_weight = self_weight
        
        self.convs = torch.nn.ModuleList([
            RGCNConv(in_dim if i == 0 else hidden_dim,
                     out_dim if i == hop - 1 else hidden_dim,
                     num_rel + 1, num_bases=num_bases)
            for i in range(hop)
        ])
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_type: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x (torch.Tensor): 노드 특성
            edge_index (torch.Tensor): 엣지 인덱스
            edge_type (torch.Tensor): 엣지 타입
            
        Returns:
            torch.Tensor: 노드 임베딩
        """
        N = x.size(0)
        loop_idx = torch.arange(N, device=x.device)
        self_loops = torch.stack([loop_idx, loop_idx])
        loop_types = torch.full((N,), self.self_loop_id, dtype=torch.long, device=x.device)
        
        edge_index = torch.cat([edge_index, self_loops], dim=1)
        edge_type = torch.cat([edge_type, loop_types])
        
        out = x
        for i, conv in enumerate(self.convs):
            h = conv(out, edge_index, edge_type)
            out = self.self_weight * out + (1 - self.self_weight) * (F.relu(h) if i < len(self.convs) - 1 else h)
        
        return out
