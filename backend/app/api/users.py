from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.template import Template, TemplateStatus
from app.models.purchase import Purchase, PurchaseStatus
from app.schemas.auth import UserResponse, UserUpdate
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse, TemplateListResponse
from app.utils.security import get_current_user, verify_password, get_password_hash


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        avatar=current_user.avatar,
        joined_at=current_user.joined_at,
        notif_email=current_user.notif_email if current_user.notif_email is not None else True,
        notif_sale=current_user.notif_sale if current_user.notif_sale is not None else True,
        notif_review=current_user.notif_review if current_user.notif_review is not None else False
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_data = user_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "role":
            from app.models.user import UserRole
            setattr(current_user, field, UserRole(value))
        else:
            setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        avatar=current_user.avatar,
        joined_at=current_user.joined_at,
        notif_email=current_user.notif_email if current_user.notif_email is not None else True,
        notif_sale=current_user.notif_sale if current_user.notif_sale is not None else True,
        notif_review=current_user.notif_review if current_user.notif_review is not None else False
    )


@router.get("/me/templates", response_model=TemplateListResponse)
async def get_my_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Template)
        .where(Template.owner_id == current_user.id)
        .order_by(Template.created_at.desc())
    )
    templates = result.scalars().all()

    return TemplateListResponse(
        templates=[
            TemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                category=t.category,
                price=t.price,
                downloads=t.downloads,
                revenue=t.revenue,
                rating=t.rating,
                reviews=t.reviews_count,
                status=t.status.value,
                blocks_data=t.blocks_data or [],
                tags=t.tags or [],
                created_at=t.created_at,
                updated_at=t.updated_at
            ) for t in templates
        ],
        total=len(templates)
    )


@router.post("/me/templates", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    template = Template(
        owner_id=current_user.id,
        name=template_data.name,
        description=template_data.description,
        category=template_data.category,
        price=template_data.price,
        tags=template_data.tags,
        blocks_data=template_data.blocks_data,
        status=TemplateStatus.DRAFT
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        price=template.price,
        downloads=template.downloads,
        revenue=template.revenue,
        rating=template.rating,
        reviews=template.reviews_count,
        status=template.status.value,
        blocks_data=template.blocks_data or [],
        tags=template.tags or [],
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/me/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.owner_id == current_user.id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="템플릿을 찾을 수 없습니다."
        )

    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status":
            setattr(template, field, TemplateStatus(value))
        else:
            setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        price=template.price,
        downloads=template.downloads,
        revenue=template.revenue,
        rating=template.rating,
        reviews=template.reviews_count,
        status=template.status.value,
        blocks_data=template.blocks_data or [],
        tags=template.tags or [],
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/me/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Template).where(
            Template.id == template_id,
            Template.owner_id == current_user.id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="템플릿을 찾을 수 없습니다."
        )

    await db.delete(template)
    await db.commit()

    return {"message": "템플릿이 삭제되었습니다."}


@router.get("/me/stats")
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get templates stats
    template_result = await db.execute(
        select(
            func.count(Template.id),
            func.sum(Template.downloads),
            func.sum(Template.revenue),
            func.avg(Template.rating)
        ).where(Template.owner_id == current_user.id)
    )
    template_stats = template_result.first()

    # Get active purchases count
    purchase_result = await db.execute(
        select(func.count(Purchase.id)).where(
            Purchase.buyer_id == current_user.id,
            Purchase.status == PurchaseStatus.ACTIVE
        )
    )
    active_purchases = purchase_result.scalar() or 0

    return {
        "templates_count": template_stats[0] or 0,
        "total_downloads": template_stats[1] or 0,
        "total_revenue": template_stats[2] or 0,
        "avg_rating": round(template_stats[3] or 0, 1),
        "active_purchases": active_purchases
    }


@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다."
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "비밀번호가 변경되었습니다."}


@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Delete all related data
    from app.models.workspace import Workspace
    from app.models.video import Video
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.review import Review

    # Delete workspaces
    await db.execute(
        select(Workspace).where(Workspace.owner_id == current_user.id)
    )

    # Delete videos and their files
    video_result = await db.execute(
        select(Video).where(Video.owner_id == current_user.id)
    )
    videos = video_result.scalars().all()
    import os
    import shutil
    for video in videos:
        if video.file_path and os.path.exists(video.file_path):
            os.remove(video.file_path)
        if video.audio_path and os.path.exists(video.audio_path):
            os.remove(video.audio_path)
        if video.frames_dir and os.path.exists(video.frames_dir):
            shutil.rmtree(video.frames_dir)
        await db.delete(video)

    # Delete templates
    template_result = await db.execute(
        select(Template).where(Template.owner_id == current_user.id)
    )
    for t in template_result.scalars().all():
        await db.delete(t)

    # Delete reviews
    review_result = await db.execute(
        select(Review).where(Review.user_id == current_user.id)
    )
    for r in review_result.scalars().all():
        await db.delete(r)

    # Delete purchases
    purchase_result = await db.execute(
        select(Purchase).where(Purchase.buyer_id == current_user.id)
    )
    for p in purchase_result.scalars().all():
        await db.delete(p)

    # Delete workspaces
    workspace_result = await db.execute(
        select(Workspace).where(Workspace.owner_id == current_user.id)
    )
    for w in workspace_result.scalars().all():
        await db.delete(w)

    # Delete user
    await db.delete(current_user)
    await db.commit()

    return {"message": "계정이 삭제되었습니다."}
