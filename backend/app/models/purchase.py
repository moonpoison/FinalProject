from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
import uuid

from app.database import Base


class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_id = Column(String, ForeignKey("marketplace_items.id"), nullable=False)
    item_name = Column(String, nullable=False)
    item_creator = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(SQLEnum(PurchaseStatus), default=PurchaseStatus.PENDING)
    payment_id = Column(String, nullable=True)  # PortOne 결제 ID
    deadline = Column(DateTime, nullable=True)  # 구매 확정 기한 (3일)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Relationships
    buyer = relationship("User", back_populates="purchases")
    item = relationship("MarketplaceItem", back_populates="purchases")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.deadline:
            self.deadline = datetime.utcnow() + timedelta(days=3)
