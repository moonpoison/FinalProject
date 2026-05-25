from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, LoginResponse, SignupResponse
)
from app.utils.security import (
    verify_password, get_password_hash, create_access_token, get_current_user
)
from app.config import settings

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email.lower())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다."
        )

    # Create new user
    user = User(
        email=user_data.email.lower(),
        hashed_password=get_password_hash(user_data.password),
        name=user_data.name,
        role=UserRole(user_data.role) if user_data.role in ["buyer", "seller"] else UserRole.BUYER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return SignupResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            avatar=user.avatar,
            joined_at=user.joined_at
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            avatar=user.avatar,
            joined_at=user.joined_at
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        avatar=current_user.avatar,
        joined_at=current_user.joined_at
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # JWT는 서버에 저장하지 않으므로 클라이언트에서 토큰을 삭제하면 됨
    return {"message": "로그아웃 되었습니다."}


@router.post("/agent-token")
async def generate_agent_token(current_user: User = Depends(get_current_user)):
    """에이전트용 장기 토큰 발급 (30일)"""
    agent_token = create_access_token(
        data={"sub": current_user.id, "type": "agent"},
        expires_delta=timedelta(days=30)
    )
    return {
        "token": agent_token,
        "expires_in_days": 30,
        "message": "이 토큰을 에이전트 실행 시 --token 옵션에 사용하세요.",
    }
