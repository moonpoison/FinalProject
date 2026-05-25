from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from app.database import Base


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.BUYER)
    avatar = Column(String, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Notification settings
    notif_email = Column(Boolean, default=True)
    notif_sale = Column(Boolean, default=True)
    notif_review = Column(Boolean, default=False)

    # Relationships
    marketplace_items = relationship("MarketplaceItem", back_populates="creator_user")
    purchases = relationship("Purchase", back_populates="buyer")
    reviews = relationship("Review", back_populates="user")
    templates = relationship("Template", back_populates="owner")
    workspaces = relationship("Workspace", back_populates="owner")
    videos = relationship("Video", back_populates="owner")
