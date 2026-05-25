from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.marketplace_item import MarketplaceItem
from app.models.review import Review
from app.schemas.marketplace import (
    MarketplaceItemCreate, MarketplaceItemUpdate, MarketplaceItemResponse,
    MarketplaceListResponse, ReviewCreate, ReviewResponse
)
from app.utils.security import get_current_user, get_current_user_optional

router = APIRouter()


def item_to_response(item: MarketplaceItem, include_blocks: bool = False) -> MarketplaceItemResponse:
    return MarketplaceItemResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        category=item.category,
        price=item.price,
        rating=item.rating,
        reviews=item.reviews_count,
        downloads=item.downloads,
        creator=item.creator_name,
        creator_avatar=item.creator_avatar,
        tags=item.tags or [],
        block_colors=item.block_colors or [],
        blocks_data=item.blocks_data if include_blocks else None,
        features=item.features if include_blocks else None,
        usage_steps=item.usage_steps if include_blocks else None,
        featured=item.featured,
        verified=item.verified,
        status=item.status,
        created_at=item.created_at
    )


@router.get("/items", response_model=MarketplaceListResponse)
async def get_items(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query("인기순"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(MarketplaceItem).where(MarketplaceItem.status == "active")

    # Category filter
    if category and category != "전체":
        query = query.where(MarketplaceItem.category == category)

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                MarketplaceItem.title.ilike(search_pattern),
                MarketplaceItem.description.ilike(search_pattern)
            )
        )

    # Sort
    if sort == "인기순":
        query = query.order_by(MarketplaceItem.downloads.desc())
    elif sort == "최신순":
        query = query.order_by(MarketplaceItem.created_at.desc())
    elif sort == "평점순":
        query = query.order_by(MarketplaceItem.rating.desc())
    elif sort == "무료":
        query = query.where(MarketplaceItem.price == 0).order_by(MarketplaceItem.downloads.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return MarketplaceListResponse(
        items=[item_to_response(item) for item in items],
        total=total
    )


@router.get("/items/{item_id}", response_model=MarketplaceItemResponse)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MarketplaceItem).where(MarketplaceItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이템을 찾을 수 없습니다."
        )

    # 상세 조회 시 블록 데이터 포함
    return item_to_response(item, include_blocks=True)


@router.post("/items", response_model=MarketplaceItemResponse)
async def create_item(
    item_data: MarketplaceItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = MarketplaceItem(
        title=item_data.title,
        description=item_data.description,
        category=item_data.category,
        price=item_data.price,
        creator_id=current_user.id,
        creator_name=current_user.name,
        creator_avatar=current_user.name[0] if current_user.name else "U",
        tags=item_data.tags,
        block_colors=item_data.block_colors,
        blocks_data=item_data.blocks_data,
        features=item_data.features,
        usage_steps=item_data.usage_steps,
        status="active"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item_to_response(item)


@router.put("/items/{item_id}", response_model=MarketplaceItemResponse)
async def update_item(
    item_id: str,
    item_data: MarketplaceItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MarketplaceItem).where(MarketplaceItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이템을 찾을 수 없습니다."
        )

    if item.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 아이템을 수정할 권한이 없습니다."
        )

    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    return item_to_response(item)


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MarketplaceItem).where(MarketplaceItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이템을 찾을 수 없습니다."
        )

    if item.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 아이템을 삭제할 권한이 없습니다."
        )

    await db.delete(item)
    await db.commit()

    return {"message": "아이템이 삭제되었습니다."}


@router.get("/items/{item_id}/reviews", response_model=List[ReviewResponse])
async def get_item_reviews(
    item_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Review).where(Review.item_id == item_id).order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()

    # Get user names
    response = []
    for review in reviews:
        user_result = await db.execute(select(User).where(User.id == review.user_id))
        user = user_result.scalar_one_or_none()
        response.append(ReviewResponse(
            id=review.id,
            user_id=review.user_id,
            user_name=user.name if user else "Unknown",
            rating=review.rating,
            text=review.text,
            created_at=review.created_at
        ))

    return response


@router.post("/items/{item_id}/reviews", response_model=ReviewResponse)
async def create_review(
    item_id: str,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.models.purchase import Purchase, PurchaseStatus

    # Check if user has purchased this item
    purchase_result = await db.execute(
        select(Purchase).where(
            Purchase.item_id == item_id,
            Purchase.buyer_id == current_user.id,
            Purchase.status == PurchaseStatus.ACTIVE
        )
    )
    purchase = purchase_result.scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="구매 확정된 아이템만 리뷰를 작성할 수 있습니다."
        )

    # Check if review already exists
    existing_result = await db.execute(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.item_id == item_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 리뷰를 작성했습니다."
        )

    # Create review
    review = Review(
        user_id=current_user.id,
        item_id=item_id,
        purchase_id=purchase.id,
        rating=review_data.rating,
        text=review_data.text
    )
    db.add(review)

    # Update item rating
    item_result = await db.execute(select(MarketplaceItem).where(MarketplaceItem.id == item_id))
    item = item_result.scalar_one_or_none()
    if item:
        # Calculate new average rating
        total_reviews = item.reviews_count + 1
        new_rating = ((item.rating * item.reviews_count) + review_data.rating) / total_reviews
        item.rating = round(new_rating, 1)
        item.reviews_count = total_reviews

    await db.commit()
    await db.refresh(review)

    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        user_name=current_user.name,
        rating=review.rating,
        text=review.text,
        created_at=review.created_at
    )
