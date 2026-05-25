from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.database import Base


class TemplateStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    SUSPENDED = "suspended"


class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    price = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    revenue = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    status = Column(SQLEnum(TemplateStatus), default=TemplateStatus.DRAFT)
    blocks_data = Column(JSON, default=list)  # 블록 데이터
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="templates")
