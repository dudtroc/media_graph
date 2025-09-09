from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

'''
Base Request Schema
'''  


class AnalyzeRequest(BaseModel):
    videoPath: str
    shotList: List[Dict[str, float]]

class AnalyzeResult(BaseModel):
    startTime: float
    endTime: float
    label: List[str]
    description: str

class BaseResponse(BaseModel):
    jobid: str
    status: int
    message: str

class StatusResponse(BaseModel):
    status: int
    message: str
    progress: Optional[float] = None
    result: Optional[List[AnalyzeResult]] = None

class Meta2GraphStatusResponse(BaseModel):
    """Meta2Graph 전용 상태 응답 스키마"""
    status: int
    message: str
    progress: Optional[float] = None
    result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None  # 메타데이터 결과를 위한 유연한 타입

class MetaToSceneGraphRequest(BaseModel):
    """meta-to-scenegraph 요청을 위한 스키마"""
    metadata: Dict[str, Any]

class RetrivalGraphStatusResponse(BaseModel):
    """RetrivalGraph 전용 상태 응답 스키마"""
    status: int
    message: str
    progress: Optional[float] = None
    result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None  # 메타데이터 결과를 위한 유연한 타입

class RetrivalGraphRequest(BaseModel):
    """RetrivalGraph 요청을 위한 스키마"""
    query: str
    tau: float = 0.3
    top_k: int = 5