#!/usr/bin/env python3
"""
QueryToTriplesConverter 클래스
사용자의 질문을 입력받아 triples 형태로 변환하고 검색까지 수행하는 클래스
"""

import os
import ast
import yaml
import torch
import heapq
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple, Any
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer

load_dotenv()

# 검색 관련 상수
DATASET = "drama_media_data"  # "dummy" or "media_data" or "drama_media_data"
JSON_ROOT = Path(f"/media_data/output/{DATASET}/scene_graph_class/gpt-4o")
Z_CACHE = Path(f"/media_data//cache/cached_graphs_{DATASET}_embed_fixed_z_ver1+2")
BERT_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TOP_K = 5


class RetrievalGraphConverter:
    """
    사용자의 질문을 입력받아 triples 형태로 변환하고 검색까지 수행하는 클래스
    """
    
    def __init__(self, 
                 instruction_path: str = "config/instruction/NL2query.txt",
                 api_key: Optional[str] = None,
                 model: str = "gpt-4o-mini",
                 temperature: float = 0.0,
                 max_tokens: int = 256):
        """
        QueryToTriplesConverter 초기화
        
        Args:
            base_config_path (str): 기본 설정 파일 경로
            api_key (str, optional): OpenAI API 키. None이면 환경변수에서 로드
            model (str): 사용할 OpenAI 모델명
            temperature (float): 생성 온도 (0.0 = 결정적)
            max_tokens (int): 최대 토큰 수
        """
        self.instruction_path = instruction_path
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # API 키 설정
        if api_key is None:
            api_key = os.getenv("OPEN_AI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API 키가 필요합니다. 환경변수 OPEN_AI_API_KEY를 설정하거나 api_key 파라미터를 전달하세요.")
        
        # OpenAI 클라이언트 초기화
        self.client = OpenAI(api_key=api_key)
        
        # 설정 파일 로드 및 instruction 템플릿 로드
        self.qa_template = self._load_qa_template()
        
        # SBERT 모델 초기화
        self.sbert = SentenceTransformer(BERT_NAME, device=DEVICE).eval()
    
    def _load_qa_template(self) -> str:
        """
        QA to triple instruction 템플릿을 로드합니다.
        
        Returns:
            str: QA 템플릿 내용
        """
        try:
            
            # QA to triple instruction 경로 가져오기
            qa_template_path = self.instruction_path
            
            # instruction 템플릿 로드
            qa_template = Path(qa_template_path).read_text()
            
            return qa_template
            
        except FileNotFoundError as e:
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {e}")
        except KeyError as e:
            raise KeyError(f"설정 파일에 필요한 키가 없습니다: {e}")
        except Exception as e:
            raise Exception(f"설정 파일 로드 중 오류 발생: {e}")
    
    @torch.no_grad()
    def _vec(self, txt: str) -> torch.Tensor:
        """
        텍스트를 벡터로 변환합니다.
        
        Args:
            txt (str): 변환할 텍스트
            
        Returns:
            torch.Tensor: 변환된 벡터
        """
        return torch.tensor(
            self.sbert.encode(txt, max_length=32, normalize_embeddings=True),
            dtype=torch.float32
        )
    
    def _token_to_sentence(self, tok: str | None) -> str:
        """
        토큰을 문장으로 변환합니다.
        
        Args:
            tok (str | None): 변환할 토큰
            
        Returns:
            str: 변환된 문장
        """
        if not tok:
            return ""
        sup, typ = tok.split(":", 1) if ":" in tok else (tok, tok)
        return f"A {typ} which is a kind of {sup}."
    
    def _embed_query(self, tokens: List[str]) -> Tuple[torch.Tensor|None, ...]:
        """
        쿼리 토큰을 임베딩합니다.
        
        Args:
            tokens (List[str]): 임베딩할 토큰 리스트
            
        Returns:
            Tuple[torch.Tensor|None, ...]: 임베딩된 벡터들
        """
        s_tok, v_tok, o_tok = (tokens + [None, None])[:3]
        q_s = self._vec(self._token_to_sentence(s_tok)) if s_tok else None
        q_v = self._vec(v_tok) if v_tok else None
        q_o = (
            self._vec(self._token_to_sentence(o_tok))
            if o_tok not in (None, "", "none", "None") else None
        )
        return q_s, q_v, q_o
    
    def _extract_list(self, txt: str) -> List:
        """
        텍스트에서 리스트 형태를 추출합니다.
        
        Args:
            txt (str): 추출할 텍스트
            
        Returns:
            List: 추출된 리스트
        """
        start, end = txt.find("["), txt.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            return ast.literal_eval(txt[start : end + 1])
        except Exception:
            return []
    
    def _triples_in_scene(self, js) -> List[Tuple[int, int, Optional[int], str]]:
        """
        장면 그래프에서 triples를 추출합니다.
        
        Args:
            js: 장면 그래프 JSON 객체
            
        Returns:
            List[Tuple[int, int, Optional[int], str]]: 추출된 triples
        """
        out, g = [], js["scene_graph"]
        for ev in g.get("events", []):
            s, o = ev.get("subject"), ev.get("object")
            if s is None:
                continue
            # object가 정수 ID가 아닐 경우 None 처리
            o = o if isinstance(o, int) else None
            out.append((s, ev["event_id"], o, ev.get("verb", "")))
        return out
    
    def _search_topk_multi(self, queries_emb: List[Tuple], tau: float, k: int = TOP_K):
        """
        여러 쿼리에 대해 top-k 검색을 수행합니다.
        
        Args:
            queries_emb (List[Tuple]): 임베딩된 쿼리들
            tau (float): 유사도 임계값
            k (int): 반환할 최대 결과 수
            
        Returns:
            List: 검색 결과
        """
        heap = []
        total_q = len(queries_emb)

        print(f"data length: {len(list(Z_CACHE.rglob('*.pt')))}")

        for pt_fp in tqdm(list(Z_CACHE.rglob("*.pt")), desc="search"):
            blob = torch.load(pt_fp, map_location="cpu")
            z = F.normalize(blob["z"], dim=1)
            id2idx = {nid: i for i, nid in enumerate(blob["orig_id"])}

            rel_path = Path(blob["path"])
            js_fp = JSON_ROOT / rel_path
            if not js_fp.exists(): 
                continue
            scene_triples = self._triples_in_scene(json.load(js_fp.open()))
            if not scene_triples: 
                continue

            matched = []
            used = set()

            for q_idx, (q_s, q_v, q_o) in enumerate(queries_emb):
                best = None
                for sid, eid, oid, _ in scene_triples:
                    # triple의 각 요소가 list인 경우 스킵
                    if any(isinstance(x, list) for x in (sid, eid, oid)):
                        continue
                    if sid not in id2idx or eid not in id2idx: 
                        continue
                    # 객체 필수 여부 판단
                    need_obj = q_o is not None
                    if need_obj and oid is None:              
                        continue

                    v_s = z[id2idx[sid]]
                    v_v = z[id2idx[eid]]
                    v_o = z[id2idx[oid]] if (oid is not None and oid in id2idx) else None

                    # 객체 유효성 점검
                    if need_obj and v_o is None: 
                        continue

                    s_sim = float(torch.dot(q_s, v_s)) if q_s is not None else None
                    v_sim = float(torch.dot(q_v, v_v)) if q_v is not None else None
                    o_sim = (
                        float(torch.dot(q_o, v_o))
                        if (q_o is not None and v_o is not None) else None
                    )

                    # 임계치 검사
                    if (q_s is not None and s_sim < tau) or \
                       (q_v is not None and v_sim < tau) or \
                       (q_o is not None and o_sim < tau):
                        continue

                    sims = [x for x in (s_sim, v_sim, o_sim) if x is not None]
                    sim = sum(sims) / len(sims)

                    if best is None or sim > best[0]:
                        best = (sim, s_sim, v_sim, o_sim, (sid, eid, oid))
                if best:
                    matched.append((q_idx,) + best)
                    used.add(best[-1])

            if not matched: 
                continue
            match_cnt = len(matched)
            avg_sim = sum(m[1] for m in matched) / match_cnt
            heapq.heappush(heap, (match_cnt, avg_sim, matched, rel_path.parts[0], rel_path, total_q))
            if len(heap) > k: 
                heapq.heappop(heap)

        return sorted(heap, key=lambda x: (-x[0], -x[1]))
    
    def __call__(self, question: str, tau: float = 0.30, top_k: int = TOP_K) -> dict:
        """
        사용자의 질문을 입력받아 triples로 변환하고 검색까지 수행합니다.
        
        Args:
            question (str): 사용자의 질문
            tau (float): 유사도 임계값
            top_k (int): 반환할 최대 결과 수
            
        Returns:
            dict: 변환된 triples와 검색 결과를 포함한 딕셔너리
        """
        try:
            # 1. 질문을 triples로 변환
            print(f"🚀 질문을 triples로 변환 중...")
            print(f"질문: {question}")
            
            # instruction 템플릿에 질문 삽입
            prompt = self.qa_template.replace("$CONTENT", question)
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            # 응답 내용 추출
            content = response.choices[0].message.content
            print(f"LLM 응답:\n{content}")
            
            # triples 추출
            triples = self._extract_list(content)
            
            # triples 형태 정규화 (단일 triple인 경우 리스트로 감싸기)
            if triples and not isinstance(triples[0], list):
                triples = [triples]
            
            print(f"✅ 변환 완료: {len(triples)}개 triple 생성")
            
            if not triples:
                print("❌ triples가 생성되지 않아 검색을 건너뜁니다.")
                return {
                    "question": question,
                    "triples": [],
                    "search_results": [],
                    "success": False
                }
            
            # 2. triples 임베딩
            print(f"🚀 triples 임베딩 중...")
            queries_emb = [self._embed_query(t) for t in triples]
            
            # 3. 검색 수행
            print(f"🚀 검색 수행 중... (tau={tau}, top_k={top_k})")

            search_results = self._search_topk_multi(queries_emb, tau, top_k)
            
            print(f"✅ 검색 완료: {len(search_results)}개 결과")
            
            # 4. 결과 반환
            return {
                "question": question,
                "triples": triples,
                "search_results": search_results,
                "success": True,
                "tau": tau,
                "top_k": top_k
            }
            
        except Exception as e:
            print(f"❌ 처리 중 오류 발생: {e}")
            return {
                "question": question,
                "triples": [],
                "search_results": [],
                "success": False,
                "error": str(e)
            }
    
    def convert_question(self, question: str) -> List[List[str]]:
        """
        질문을 triples로만 변환합니다 (검색 없음).
        
        Args:
            question (str): 사용자의 질문
            
        Returns:
            List[List[str]]: 변환된 triples 리스트
        """
        try:
            # instruction 템플릿에 질문 삽입
            prompt = self.qa_template.replace("$CONTENT", question)
            
            # OpenAI API 호출
            print(f"🚀 질문을 triples로 변환 중...")
            print(f"질문: {question}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            # 응답 내용 추출
            content = response.choices[0].message.content
            print(f"LLM 응답:\n{content}")
            
            # triples 추출
            triples = self._extract_list(content)
            
            # triples 형태 정규화 (단일 triple인 경우 리스트로 감싸기)
            if triples and not isinstance(triples[0], list):
                triples = [triples]
            
            print(f"✅ 변환 완료: {len(triples)}개 triple 생성")
            return triples
            
        except Exception as e:
            print(f"❌ 질문 변환 중 오류 발생: {e}")
            return []
    
    def get_template_info(self) -> dict:
        """
        현재 로드된 템플릿 정보를 반환합니다.
        
        Returns:
            dict: 템플릿 정보
        """
        return {
            "instruction_path": self.instruction_path,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "template_length": len(self.qa_template)
        }
    
    def update_model(self, model: str):
        """
        사용할 모델을 변경합니다.
        
        Args:
            model (str): 새로운 모델명
        """
        self.model = model
        print(f"모델이 {model}로 변경되었습니다.")
    
    def update_parameters(self, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        """
        생성 파라미터를 업데이트합니다.
        
        Args:
            temperature (float, optional): 새로운 온도 값
            max_tokens (int, optional): 새로운 최대 토큰 수
        """
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        print(f"파라미터가 업데이트되었습니다: temperature={self.temperature}, max_tokens={self.max_tokens}")
    



# 사용 예시
if __name__ == "__main__":
    # 클래스 초기화
    converter = RetrievalGraphConverter(
        base_config_path="config/base_params.yaml",
        model="gpt-4o-mini"
    )
    
    # 예시 질문
    example_question = "남녀가 키스하는 장면을 찾아줘."
    
    # 1. triples만 변환 (검색 없음)
    print("=== triples만 변환 ===")
    triples = converter.convert_question(example_question)
    
    if triples:
        print(f"\n변환된 triples:")
        for i, triple in enumerate(triples):
            print(f"  {i+1}: {triple}")
    else:
        print("❌ 변환 실패")
    
    # 2. triples 변환 + 검색 수행
    print("\n=== triples 변환 + 검색 수행 ===")
    result = converter(example_question, tau=0.30, top_k=5)
    
    if result["success"]:
        print(f"\n질문: {result['question']}")
        print(f"triples: {result['triples']}")
        print(f"검색 결과 수: {len(result['search_results'])}")
        
        if result['search_results']:
            print("\n검색 결과:")
            for i, (cnt, avg_sim, matched, drama, rel, total_q) in enumerate(result['search_results'][:3], 1):
                print(f"  {i}. Scene = {drama}/{rel.name}")
                print(f"      matched {cnt}/{total_q} triples | avg_sim = {avg_sim:.3f}")
    else:
        print(f"❌ 처리 실패: {result.get('error', 'Unknown error')}")
    
    # 템플릿 정보 출력
    template_info = converter.get_template_info()
    print(f"\n템플릿 정보: {template_info}")
