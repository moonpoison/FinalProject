from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class BlockFieldValue(BaseModel):
    """블록 필드 값"""
    name: str
    value: Any


class WorkspaceBlockData(BaseModel):
    """워크스페이스 내 블록 데이터"""
    id: str
    type: str
    category: str
    label: str
    icon: str
    color: str
    instance_id: str
    field_values: dict = {}
    group_id: Optional[str] = None
    group_label: Optional[str] = None
    group_color: Optional[str] = None


class WorkspaceCreate(BaseModel):
    """워크스페이스 생성"""
    name: str = "새 작업"
    description: Optional[str] = None
    blocks_data: List[dict] = []


class WorkspaceUpdate(BaseModel):
    """워크스페이스 수정"""
    name: Optional[str] = None
    description: Optional[str] = None
    blocks_data: Optional[List[dict]] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class WorkspaceResponse(BaseModel):
    """워크스페이스 응답"""
    id: str
    name: str
    description: Optional[str]
    blocks_data: List[dict]
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceListResponse(BaseModel):
    """워크스페이스 목록 응답"""
    workspaces: List[WorkspaceResponse]
    total: int


class WorkspaceBulkUpdate(BaseModel):
    """여러 워크스페이스 일괄 업데이트 (순서 변경 등)"""
    updates: List[dict]  # [{id: str, order_index: int}, ...]
