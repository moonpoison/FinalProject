from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str
    role: str = "buyer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    avatar: Optional[str] = None
    joined_at: datetime
    notif_email: bool = True
    notif_sale: bool = True
    notif_review: bool = False

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    error: Optional[str] = None


class SignupResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    error: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None
    notif_email: Optional[bool] = None
    notif_sale: Optional[bool] = None
    notif_review: Optional[bool] = None
