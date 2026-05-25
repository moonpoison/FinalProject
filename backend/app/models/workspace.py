from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Workspace(Base):
    """사용자의 자동화 워크스페이스 (시트)"""
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False, default="새 작업")
    description = Column(String(500), nullable=True)
    blocks_data = Column(JSON, default=list)  # 블록 데이터 배열
    order_index = Column(Integer, default=0)  # 탭 순서
    is_active = Column(Boolean, default=True)  # 활성 탭 여부
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="workspaces")
