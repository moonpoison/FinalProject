from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MessageBase(BaseModel):
    body: str


class MessageCreate(MessageBase):
    pass


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    body: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    other_id: str
    other_name: str
    topic: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    participant_ids: List[str]
    participant_names: List[str]
    topic: Optional[str] = None
    messages: List[MessageResponse]
    updated_at: datetime

    class Config:
        from_attributes = True


class StartConversationRequest(BaseModel):
    other_name: str
    topic: str
