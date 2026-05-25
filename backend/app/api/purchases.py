from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import httpx

from app.database import get_db
from app.models.user import User
from app.models.marketplace_item import MarketplaceItem
from app.models.purchase import Purchase, PurchaseStatus
from app.models.review import Review
from app.schemas.purchase import PurchaseCreate, PurchaseResponse, PurchaseListResponse, PaymentVerifyRequest
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter()


def purchase_to_response(purchase: Purchase, review: Review = None) -> PurchaseResponse:
    my_review = None
    if review:
        my_review = {"rating": review.rating, "text": review.text}

    return PurchaseResponse(
        id=purchase.id,
        item_id=purchase.item_id,
        name=purchase.item_name,
        price=purchase.price,
        purchased_at=purchase.purchased_at,
        creator=purchase.item_creator,
        status=purchase.status.value,
        deadline=purchase.deadline,
        my_review=my_review
    )


@router.get("", response_model=PurchaseListResponse)
async def get_purchases(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Purchase)
        .where(Purchase.buyer_id == current_user.id)
        .order_by(Purchase.purchased_at.desc())
    )
    purchases = result.scalars().all()

    active = []
    pending = []
    cancelled = []

    for purchase in purchases:
        # Get review for this purchase if exists
        review_result = await db.execute(
            select(Review).where(
                Review.user_id == current_user.id,
                Review.purchase_id == purchase.id
            )
        )
        review = review_result.scalar_one_or_none()

        response = purchase_to_response(purchase, review)

        if purchase.status == PurchaseStatus.ACTIVE:
            active.append(response)
        elif purchase.status == PurchaseStatus.PENDING:
            pending.append(response)
        else:
            cancelled.append(response)

    return PurchaseListResponse(
        active=active,
        pending=pending,
        cancelled=cancelled
    )


@router.post("", response_model=PurchaseResponse)
async def create_purchase(
    purchase_data: PurchaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get item
    item_result = await db.execute(
        select(MarketplaceItem).where(MarketplaceItem.id == purchase_data.item_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이템을 찾을 수 없습니다."
        )

    # Check if already purchased
    existing_result = await db.execute(
        select(Purchase).where(
            Purchase.item_id == purchase_data.item_id,
            Purchase.buyer_id == current_user.id,
            Purchase.status != PurchaseStatus.CANCELLED
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 구매한 아이템입니다."
        )

    # For free items, auto-confirm
    initial_status = PurchaseStatus.ACTIVE if item.price == 0 else PurchaseStatus.PENDING

    # Create purchase
    purchase = Purchase(
        buyer_id=current_user.id,
        item_id=item.id,
        item_name=item.title,
        item_creator=item.creator_name,
        price=item.price,
        status=initial_status
    )
    db.add(purchase)

    # Increment download count
    item.downloads += 1

    await db.commit()
    await db.refresh(purchase)

    return purchase_to_response(purchase)


@router.post("/{purchase_id}/confirm", response_model=PurchaseResponse)
async def confirm_purchase(
    purchase_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Purchase).where(Purchase.id == purchase_id)
    )
    purchase = result.scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="구매 내역을 찾을 수 없습니다."
        )

    if purchase.buyer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 구매를 확정할 권한이 없습니다."
        )

    if purchase.status != PurchaseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="대기 중인 구매만 확정할 수 있습니다."
        )

    purchase.status = PurchaseStatus.ACTIVE
    purchase.confirmed_at = datetime.utcnow()
    purchase.deadline = None

    await db.commit()
    await db.refresh(purchase)

    return purchase_to_response(purchase)


@router.post("/{purchase_id}/cancel", response_model=PurchaseResponse)
async def cancel_purchase(
    purchase_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Purchase).where(Purchase.id == purchase_id)
    )
    purchase = result.scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="구매 내역을 찾을 수 없습니다."
        )

    if purchase.buyer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 구매를 취소할 권한이 없습니다."
        )

    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 취소된 구매입니다."
        )

    purchase.status = PurchaseStatus.CANCELLED
    purchase.cancelled_at = datetime.utcnow()
    purchase.deadline = None

    await db.commit()
    await db.refresh(purchase)

    return purchase_to_response(purchase)


@router.post("/verify-payment", response_model=PurchaseResponse)
async def verify_payment(
    payment_data: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """PortOne 결제를 검증하고 구매를 처리합니다."""

    # Get item
    item_result = await db.execute(
        select(MarketplaceItem).where(MarketplaceItem.id == payment_data.item_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이템을 찾을 수 없습니다."
        )

    # Check if already purchased
    existing_result = await db.execute(
        select(Purchase).where(
            Purchase.item_id == payment_data.item_id,
            Purchase.buyer_id == current_user.id,
            Purchase.status != PurchaseStatus.CANCELLED
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 구매한 아이템입니다."
        )

    # PortOne API로 결제 검증
    if settings.PORTONE_API_SECRET:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.portone.io/payments/{payment_data.payment_id}",
                    headers={"Authorization": f"PortOne {settings.PORTONE_API_SECRET}"}
                )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="결제 정보를 확인할 수 없습니다."
                    )

                payment_info = response.json()

                # 금액 검증
                if payment_info.get("amount", {}).get("total") != payment_data.amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="결제 금액이 일치하지 않습니다."
                    )

                # 결제 상태 확인
                if payment_info.get("status") != "PAID":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="결제가 완료되지 않았습니다."
                    )

        except httpx.HTTPError as e:
            print(f"[Payment] PortOne API 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="결제 검증 중 오류가 발생했습니다."
            )

    # Create purchase (결제 완료 상태로)
    purchase = Purchase(
        buyer_id=current_user.id,
        item_id=item.id,
        item_name=item.title,
        item_creator=item.creator_name,
        price=item.price,
        status=PurchaseStatus.ACTIVE,
        payment_id=payment_data.payment_id
    )
    db.add(purchase)

    # Increment download count
    item.downloads += 1

    await db.commit()
    await db.refresh(purchase)

    return purchase_to_response(purchase)
