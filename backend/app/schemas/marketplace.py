from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class MarketplaceItemBase(BaseModel):
    title: str
    description: str
    category: str
    price: int = 0
    tags: List[str] = []


class MarketplaceItemCreate(MarketplaceItemBase):
    blocks_data: List[Any] = []
    block_colors: List[str] = []
    features: List[str] = []  # AI 생성 주요 기능
    usage_steps: List[str] = []  # AI 생성 사용 방법


class MarketplaceItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    blocks_data: Optional[List[Any]] = None


class MarketplaceItemResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    price: int
    rating: float
    reviews: int  # alias for reviews_count
    downloads: int
    creator: str  # alias for creator_name
    creator_avatar: Optional[str] = None
    tags: List[str]
    block_colors: List[str]
    blocks_data: Optional[List[Any]] = None  # 블록 데이터
    features: Optional[List[str]] = None  # AI 생성 주요 기능
    usage_steps: Optional[List[str]] = None  # AI 생성 사용 방법
    featured: bool
    verified: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MarketplaceListResponse(BaseModel):
    items: List[MarketplaceItemResponse]
    total: int


class ReviewCreate(BaseModel):
    rating: int  # 1-5
    text: str


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    rating: int
    text: str
    created_at: datetime

    class Config:
        from_attributes = True
