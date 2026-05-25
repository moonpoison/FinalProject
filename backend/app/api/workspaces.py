from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse,
    WorkspaceListResponse, WorkspaceBulkUpdate
)
from app.utils.security import get_current_user

router = APIRouter()


def workspace_to_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        blocks_data=workspace.blocks_data or [],
        order_index=workspace.order_index,
        is_active=workspace.is_active,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at
    )


@router.get("", response_model=WorkspaceListResponse)
async def get_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """사용자의 모든 워크스페이스 조회"""
    result = await db.execute(
        select(Workspace)
        .where(Workspace.owner_id == current_user.id)
        .order_by(Workspace.order_index)
    )
    workspaces = result.scalars().all()

    return WorkspaceListResponse(
        workspaces=[workspace_to_response(w) for w in workspaces],
        total=len(workspaces)
    )


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """새 워크스페이스 생성"""
    # 현재 최대 order_index 조회
    max_order_result = await db.execute(
        select(func.max(Workspace.order_index))
        .where(Workspace.owner_id == current_user.id)
    )
    max_order = max_order_result.scalar() or -1

    workspace = Workspace(
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        blocks_data=data.blocks_data,
        order_index=max_order + 1,
        is_active=True
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    return workspace_to_response(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """특정 워크스페이스 조회"""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워크스페이스를 찾을 수 없습니다."
        )

    return workspace_to_response(workspace)


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """워크스페이스 수정"""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워크스페이스를 찾을 수 없습니다."
        )

    # 필드 업데이트
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)

    await db.commit()
    await db.refresh(workspace)

    return workspace_to_response(workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """워크스페이스 삭제"""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워크스페이스를 찾을 수 없습니다."
        )

    await db.delete(workspace)
    await db.commit()

    return {"message": "워크스페이스가 삭제되었습니다."}


@router.post("/{workspace_id}/blocks", response_model=WorkspaceResponse)
async def save_blocks(
    workspace_id: str,
    blocks: List[dict],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """워크스페이스 블록 저장"""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워크스페이스를 찾을 수 없습니다."
        )

    workspace.blocks_data = blocks
    await db.commit()
    await db.refresh(workspace)

    return workspace_to_response(workspace)


@router.post("/bulk-update")
async def bulk_update_workspaces(
    data: WorkspaceBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """여러 워크스페이스 일괄 업데이트 (순서 변경 등)"""
    for update in data.updates:
        workspace_id = update.get("id")
        if not workspace_id:
            continue

        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.owner_id == current_user.id
            )
        )
        workspace = result.scalar_one_or_none()

        if workspace:
            if "order_index" in update:
                workspace.order_index = update["order_index"]
            if "name" in update:
                workspace.name = update["name"]
            if "is_active" in update:
                workspace.is_active = update["is_active"]

    await db.commit()

    return {"message": f"{len(data.updates)}개 워크스페이스가 업데이트되었습니다."}


@router.post("/from-purchase", response_model=WorkspaceResponse)
async def create_from_purchase(
    item_id: str,
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """구매한 아이템에서 워크스페이스 생성"""
    from app.models.purchase import Purchase, PurchaseStatus
    from app.models.marketplace_item import MarketplaceItem

    # 구매 확인
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
            detail="구매 확정된 아이템만 워크스페이스에 추가할 수 있습니다."
        )

    # 아이템 정보 조회
    item_result = await db.execute(
        select(MarketplaceItem).where(MarketplaceItem.id == item_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아이템을 찾을 수 없습니다."
        )

    # 최대 order_index
    max_order_result = await db.execute(
        select(func.max(Workspace.order_index))
        .where(Workspace.owner_id == current_user.id)
    )
    max_order = max_order_result.scalar() or -1

    # 워크스페이스 생성
    workspace = Workspace(
        owner_id=current_user.id,
        name=name,
        description=f"마켓플레이스에서 가져온 자동화: {item.title}",
        blocks_data=item.blocks_data or [],
        order_index=max_order + 1,
        is_active=True
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    return workspace_to_response(workspace)
