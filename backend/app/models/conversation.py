from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    participant1_id = Column(String, ForeignKey("users.id"), nullable=False)
    participant1_name = Column(String, nullable=False)
    participant2_id = Column(String, ForeignKey("users.id"), nullable=False)
    participant2_name = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
