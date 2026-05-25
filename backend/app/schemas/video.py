from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class VideoUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str


class VideoStatusResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    status: str
    progress: int
    error_message: Optional[str] = None
    duration: Optional[int] = None
    frame_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoAnalysisResult(BaseModel):
    task_name: str
    summary: str
    confidence: float
    transcript: Optional[str] = None
    detected_actions: List[dict]
    groups: List[dict]


class VideoDetailResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    status: str
    progress: int
    error_message: Optional[str] = None
    duration: Optional[int] = None
    frame_count: int = 0
    transcript: Optional[str] = None
    analysis_result: Optional[dict] = None
    generated_blocks: Optional[List[Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    videos: List[VideoStatusResponse]
    total: int
