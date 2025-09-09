#!/usr/bin/env python3
"""
MetaToGraphConverter 클래스
meta_data를 입력받아 API를 이용해서 장면 그래프로 변환하는 클래스
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from contents_graph.api.openai_client import OpenAIAssistantClient

load_dotenv()

class MetaToGraphConverter:
    """
    meta_data를 입력받아 API를 이용해서 장면 그래프로 변환하는 클래스
    """
    
    def __init__(self, 
                 instruction_path: str = "config/instruction/meta2graph_ver2_kor.txt",
                 api_key: Optional[str] = None,
                 model: str = "gpt-4o",
                 assistant_name: str = "meta2graph"):
        """
        MetaToGraphConverter 초기화
        
        Args:
            instruction_path (str): instruction 파일 경로
            api_key (str, optional): OpenAI API 키. None이면 환경변수에서 로드
            model (str): 사용할 모델명
            assistant_name (str): assistant 이름
        """
        self.instruction_path = instruction_path
        self.model = model
        self.assistant_name = assistant_name
        
        # API 키 설정
        if api_key is None:
            api_key = os.getenv("OPEN_AI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API 키가 필요합니다. 환경변수 OPEN_AI_API_KEY를 설정하거나 api_key 파라미터를 전달하세요.")
        
        # instruction 로드
        self.instruction = self._load_instruction()
        
        # OpenAI 클라이언트 초기화
        self.assistant_client = OpenAIAssistantClient(
            api_key=api_key,
            assistant_name=self.assistant_name,
            instruction_path=self.instruction_path,
            model=self.model,
        )
    
    def _load_instruction(self) -> str:
        """
        instruction 파일을 로드합니다.
        
        Returns:
            str: instruction 내용
        """
        try:
            with open(self.instruction_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Instruction 파일을 찾을 수 없습니다: {self.instruction_path}")
        except Exception as e:
            raise Exception(f"Instruction 파일 로드 중 오류 발생: {e}")
    
    def _clean_and_parse_scene_graph(self, raw: str) -> Any:
        """
        API 응답을 정리하고 JSON으로 파싱합니다.
        
        Args:
            raw (str): API 응답 문자열
            
        Returns:
            Any: 파싱된 JSON 객체 또는 None
        """
        if not isinstance(raw, str):
            return None

        s = raw.strip()
        # 코드펜스 제거
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE)

        # 1차 파싱
        try:
            obj = json.loads(s)
            # 응답이 또다른 문자열 JSON을 감싼 경우
            if isinstance(obj, str):
                try:
                    return json.loads(obj)
                except json.JSONDecodeError:
                    return obj
            return obj
        except json.JSONDecodeError:
            pass

        # 바깥 JSON 블록만 추출해서 재시도
        m = re.search(r'(\{.*\}|\[.*\])', s, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
        return None
    
    def _extract_message_content(self, outer: dict) -> str:
        """
        OpenAIAssistantClient의 응답 구조에서 content를 추출합니다.
        
        Args:
            outer (dict): API 응답 객체
            
        Returns:
            str: 추출된 content 문자열
        """
        content = (
            outer.get("response", {})
                 .get("body", {})
                 .get("choices", [{}])[0]
                 .get("message", {})
                 .get("content", "")
        )
        if isinstance(content, str):
            return content
        # content가 list[dict] (예: [{"type":"text","text":"..."}]) 형태일 수도 있음
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict):
                    if "text" in part and isinstance(part["text"], str):
                        texts.append(part["text"])
                    elif "content" in part and isinstance(part["content"], str):
                        texts.append(part["content"])
            return "\n".join(texts).strip()
        # 기타 타입은 문자열 변환
        return str(content)
    
    def __call__(self, meta_data: Dict[str, Any], scene_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        meta_data를 입력받아 API를 이용해서 장면 그래프로 변환합니다.
        
        Args:
            meta_data (Dict[str, Any]): 변환할 메타 데이터
            scene_number (str, optional): 장면 번호. None이면 meta_data에서 추출
            
        Returns:
            Optional[Dict[str, Any]]: 변환된 장면 그래프 또는 None (실패 시)
        """
        print(f"[MetaToGraphConverter] __call__ 메서드 호출됨 - meta_data: {type(meta_data)}")
        print(f"[MetaToGraphConverter] scene_number: {scene_number}")
        
        try:
            # scene_number 추출
            if scene_number is None:
                scene_number = meta_data.get("Scene Number")
                if not scene_number:
                    raise ValueError("meta_data에 'Scene Number'가 없거나 scene_number 파라미터를 전달해야 합니다.")
            
            # instruction 생성
            scene_instruction = (
                self.instruction.replace("$SCENE_NUMBER", scene_number)
                + "\n\ninput meta: \n"
                + json.dumps(meta_data, ensure_ascii=False, indent=2)
            )
            
            # API 호출
            print(f"🚀 장면 {scene_number} 변환 중...")
            result = self.assistant_client(scene_instruction)
            
            # 응답 처리
            if isinstance(result, dict):
                # batch 응답 형태인 경우
                content = self._extract_message_content(result)
            else:
                # 개별 응답 형태인 경우
                content = str(result)
            
            # JSON 파싱
            scene_graph = self._clean_and_parse_scene_graph(content)
            if not scene_graph:
                print(f"❌ 장면 {scene_number} 변환 실패: JSON 파싱 오류")
                return None
            
            # Scene Number 추가
            if isinstance(scene_graph, dict):
                scene_graph["Scene Number"] = scene_number
            
            print(f"✅ 장면 {scene_number} 변환 완료")
            return scene_graph
            
        except Exception as e:
            print(f"❌ 장면 {scene_number} 변환 중 오류 발생: {e}")
            return None
    
    def batch_call(self, meta_data_list: list[Dict[str, Any]]) -> list[Optional[Dict[str, Any]]]:
        """
        여러 meta_data를 배치로 처리합니다.
        
        Args:
            meta_data_list (list[Dict[str, Any]]): 변환할 메타 데이터 리스트
            
        Returns:
            list[Optional[Dict[str, Any]]]: 변환된 장면 그래프 리스트 (실패한 항목은 None)
        """
        if not meta_data_list:
            return []
        
        results = []
        prompts = []
        
        # 프롬프트 생성
        for meta_data in meta_data_list:
            scene_number = meta_data.get("Scene Number")
            if not scene_number:
                print(f"⚠️ Scene Number 누락된 메타 데이터 건너뜀")
                results.append(None)
                prompts.append("")
                continue
                
            scene_instruction = (
                self.instruction.replace("$SCENE_NUMBER", scene_number)
                + "\n\ninput meta: \n"
                + json.dumps(meta_data, ensure_ascii=False, indent=2)
            )
            prompts.append(scene_instruction)
        
        # 배치 API 호출
        print(f"🚀 배치 변환 시작 (총 {len(meta_data_list)}개)")
        try:
            raw_response = self.assistant_client.run_batch_job(prompts)
            
            # 응답 처리
            lines = raw_response.strip().splitlines()
            if len(lines) != len(meta_data_list):
                print(f"⚠️ 응답 개수({len(lines)})와 요청 개수({len(meta_data_list)}) 불일치")
            
            for idx, line in enumerate(lines):
                try:
                    if idx >= len(meta_data_list):
                        break
                        
                    outer = json.loads(line)
                    content = self._extract_message_content(outer)
                    if not content:
                        results.append(None)
                        continue

                    scene_graph = self._clean_and_parse_scene_graph(content)
                    if not scene_graph:
                        results.append(None)
                        continue

                    # Scene Number 추가
                    scene_number = meta_data_list[idx].get("Scene Number")
                    if isinstance(scene_graph, dict) and scene_number:
                        scene_graph["Scene Number"] = scene_number
                    
                    results.append(scene_graph)
                    
                except Exception as e:
                    print(f"❌ 응답 {idx} 처리 오류: {e}")
                    results.append(None)
            
            # 결과 개수 맞추기
            while len(results) < len(meta_data_list):
                results.append(None)
                
        except Exception as e:
            print(f"❌ 배치 처리 중 오류 발생: {e}")
            results = [None] * len(meta_data_list)
        
        print(f"🎉 배치 변환 완료 (성공: {len([r for r in results if r is not None])}/{len(meta_data_list)})")
        return results
    
    def save_scene_graph(self, scene_graph: Dict[str, Any], output_path: str) -> bool:
        """
        장면 그래프를 파일로 저장합니다.
        
        Args:
            scene_graph (Dict[str, Any]): 저장할 장면 그래프
            output_path (str): 저장할 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 디렉토리 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 저장
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                json.dump(scene_graph, f, indent=4, ensure_ascii=False)
            
            print(f"✅ 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 저장 실패 ({output_path}): {e}")
            return False


