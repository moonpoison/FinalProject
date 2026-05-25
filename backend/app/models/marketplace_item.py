from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class MarketplaceItem(Base):
    __tablename__ = "marketplace_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # 웹 자동화, 데이터 수집, SNS 자동화, 업무 자동화, 쇼핑몰
    price = Column(Integer, default=0)  # 0 = 무료
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    creator_name = Column(String, nullable=False)
    creator_avatar = Column(String, nullable=True)
    tags = Column(JSON, default=list)  # ["네이버", "쇼핑", "최저가"]
    block_colors = Column(JSON, default=list)  # ["#22c55e", "#3b82f6", ...]
    blocks_data = Column(JSON, default=list)  # 실제 블록 데이터
    features = Column(JSON, default=list)  # AI 생성 주요 기능 목록
    usage_steps = Column(JSON, default=list)  # AI 생성 사용 방법
    featured = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    status = Column(String(20), default="active")  # active, draft, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator_user = relationship("User", back_populates="marketplace_items")
    purchases = relationship("Purchase", back_populates="item")
    reviews = relationship("Review", back_populates="item")
