from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.chat import ChatCardResponse, ChatMessageResponse, ChatThreadResponse, CreateChatMessageRequest
from app.services.chats import (
    assert_chat_member,
    create_message,
    get_chat_by_id,
    list_user_chats,
    serialize_chat,
    serialize_message,
)


router = APIRouter()


@router.get("/chats", response_model=list[ChatCardResponse])
async def api_list_chats(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ChatCardResponse]:
    chats = await list_user_chats(session, user=current_user)
    return [serialize_chat(chat) for chat in chats]


@router.get("/chats/{chat_id}", response_model=ChatThreadResponse)
async def api_get_chat(
    chat_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ChatThreadResponse:
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    assert_chat_member(chat, current_user)
    messages = sorted(chat.messages, key=lambda item: item.created_at)
    return ChatThreadResponse(
        chat=serialize_chat(chat),
        messages=[serialize_message(message) for message in messages],
    )


@router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def api_post_chat_message(
    chat_id: int,
    payload: CreateChatMessageRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    message = await create_message(session, chat=chat, author=current_user, body=payload.body)
    return serialize_message(message)
