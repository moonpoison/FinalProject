from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PurchaseCreate(BaseModel):
    item_id: str


class PaymentVerifyRequest(BaseModel):
    payment_id: str
    item_id: str
    amount: int


class PurchaseResponse(BaseModel):
    id: str
    item_id: str  # marketplace item id
    name: str  # item_name
    price: int
    purchased_at: datetime
    creator: str  # item_creator
    status: str
    deadline: Optional[datetime] = None
    my_review: Optional[dict] = None

    class Config:
        from_attributes = True


class PurchaseListResponse(BaseModel):
    active: list[PurchaseResponse]
    pending: list[PurchaseResponse]
    cancelled: list[PurchaseResponse]
