from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: int = 0
    tags: List[str] = []


class TemplateCreate(TemplateBase):
    blocks_data: List[Any] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    blocks_data: Optional[List[Any]] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: int
    downloads: int
    revenue: int
    rating: float
    reviews: int  # reviews_count
    status: str
    blocks_data: List[Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    templates: List[TemplateResponse]
    total: int
