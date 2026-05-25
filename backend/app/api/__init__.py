from fastapi import APIRouter
from app.api import auth, chat, marketplace, purchases, users, ai, workspaces, videos, execution, knowledge, validation

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["인증"])
api_router.include_router(chat.router, prefix="/conversations", tags=["채팅"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["마켓플레이스"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["구매"])
api_router.include_router(users.router, prefix="/users", tags=["사용자"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["워크스페이스"])
api_router.include_router(videos.router, prefix="/videos", tags=["영상 처리"])
api_router.include_router(execution.router, prefix="/execution", tags=["실행"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["지식베이스"])
api_router.include_router(validation.router, tags=["검증"])
