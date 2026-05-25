from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import (
    ConversationResponse, MessageCreate, MessageResponse, StartConversationRequest
)
from app.utils.security import get_current_user

router = APIRouter()


def conversation_to_response(conv: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id,
        participant_ids=[conv.participant1_id, conv.participant2_id],
        participant_names=[conv.participant1_name, conv.participant2_name],
        topic=conv.topic,
        messages=[
            MessageResponse(
                id=msg.id,
                sender_id=msg.sender_id,
                sender_name=msg.sender_name,
                body=msg.body,
                read=msg.read,
                created_at=msg.created_at
            ) for msg in conv.messages
        ],
        updated_at=conv.updated_at
    )


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Conversation)
        .where(
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        )
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    # Load messages for each conversation
    response = []
    for conv in conversations:
        await db.refresh(conv, ["messages"])
        response.append(conversation_to_response(conv))

    return response


@router.post("", response_model=ConversationResponse)
async def create_or_get_conversation(
    request: StartConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Try to find existing conversation by name pattern
    seller_id = f"seller-{request.other_name.lower().replace(' ', '-')}"

    result = await db.execute(
        select(Conversation).where(
            or_(
                and_(
                    Conversation.participant1_id == current_user.id,
                    Conversation.participant2_id == seller_id
                ),
                and_(
                    Conversation.participant1_id == seller_id,
                    Conversation.participant2_id == current_user.id
                )
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.refresh(existing, ["messages"])
        return conversation_to_response(existing)

    # Create new conversation
    conv = Conversation(
        participant1_id=current_user.id,
        participant1_name=current_user.name,
        participant2_id=seller_id,
        participant2_name=request.other_name,
        topic=request.topic
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=conv.id,
        participant_ids=[conv.participant1_id, conv.participant2_id],
        participant_names=[conv.participant1_name, conv.participant2_name],
        topic=conv.topic,
        messages=[],
        updated_at=conv.updated_at
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if conversation exists and user is a participant
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화를 찾을 수 없습니다."
        )

    if current_user.id not in [conv.participant1_id, conv.participant2_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 대화에 참여할 수 없습니다."
        )

    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        sender_name=current_user.name,
        body=message_data.body,
        read=False
    )
    db.add(message)

    # Update conversation timestamp
    from datetime import datetime
    conv.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        body=message.body,
        read=message.read,
        created_at=message.created_at
    )


@router.post("/{conversation_id}/read")
async def mark_messages_read(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get all unread messages in conversation not sent by current user
    result = await db.execute(
        select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_id != current_user.id,
                Message.read == False
            )
        )
    )
    messages = result.scalars().all()

    for msg in messages:
        msg.read = True

    await db.commit()

    return {"message": f"{len(messages)}개의 메시지를 읽음 처리했습니다."}


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get conversations where user is a participant
    conv_result = await db.execute(
        select(Conversation.id).where(
            or_(
                Conversation.participant1_id == current_user.id,
                Conversation.participant2_id == current_user.id
            )
        )
    )
    conv_ids = [row[0] for row in conv_result.fetchall()]

    if not conv_ids:
        return {"count": 0}

    # Count unread messages not sent by current user
    count_result = await db.execute(
        select(func.count(Message.id)).where(
            and_(
                Message.conversation_id.in_(conv_ids),
                Message.sender_id != current_user.id,
                Message.read == False
            )
        )
    )
    count = count_result.scalar() or 0

    return {"count": count}
