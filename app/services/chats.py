from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Chat, ChatMessage, Order, User, utcnow
from app.schemas.chat import ChatCardResponse, ChatMessageResponse


async def ensure_chat_for_order_pair(
    session: AsyncSession,
    *,
    order: Order,
    client: User,
    executor: User,
) -> Chat:
    existing = await session.scalar(
        select(Chat)
        .options(
            selectinload(Chat.order),
            selectinload(Chat.client),
            selectinload(Chat.executor),
            selectinload(Chat.messages).selectinload(ChatMessage.author),
        )
        .where(
            Chat.order_id == order.id,
            Chat.client_id == client.id,
            Chat.executor_id == executor.id,
        )
    )
    if existing is not None:
        return existing

    chat = Chat(order_id=order.id, client_id=client.id, executor_id=executor.id)
    session.add(chat)
    await session.flush()
    return await get_chat_by_id(session, chat.id)


async def list_user_chats(session: AsyncSession, *, user: User) -> list[Chat]:
    return (
        await session.scalars(
            select(Chat)
            .options(
                selectinload(Chat.order),
                selectinload(Chat.client),
                selectinload(Chat.executor),
                selectinload(Chat.messages).selectinload(ChatMessage.author),
            )
            .where(or_(Chat.client_id == user.id, Chat.executor_id == user.id))
            .order_by(Chat.updated_at.desc())
        )
    ).all()


async def get_chat_by_id(session: AsyncSession, chat_id: int) -> Chat | None:
    return await session.scalar(
        select(Chat)
        .options(
            selectinload(Chat.order),
            selectinload(Chat.client),
            selectinload(Chat.executor),
            selectinload(Chat.messages).selectinload(ChatMessage.author),
        )
        .where(Chat.id == chat_id)
    )


async def create_message(
    session: AsyncSession,
    *,
    chat: Chat,
    author: User,
    body: str,
) -> ChatMessage:
    _assert_chat_member(chat, author)
    message = ChatMessage(chat_id=chat.id, author_id=author.id, body=body.strip())
    chat.updated_at = utcnow()
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return await get_message_by_id(session, message.id)


async def get_message_by_id(session: AsyncSession, message_id: int) -> ChatMessage | None:
    return await session.scalar(
        select(ChatMessage)
        .options(
            selectinload(ChatMessage.author),
            selectinload(ChatMessage.chat).selectinload(Chat.order),
            selectinload(ChatMessage.chat).selectinload(Chat.client),
            selectinload(ChatMessage.chat).selectinload(Chat.executor),
        )
        .where(ChatMessage.id == message_id)
    )


def serialize_chat(chat: Chat) -> ChatCardResponse:
    last_message = chat.messages[-1].body if chat.messages else None
    return ChatCardResponse(
        id=chat.id,
        order_id=chat.order_id,
        order_slug=chat.order.slug,
        order_title=chat.order.title,
        client_id=chat.client_id,
        client_name=chat.client.display_name,
        executor_id=chat.executor_id,
        executor_name=chat.executor.display_name,
        last_message=last_message,
        updated_at=chat.updated_at.isoformat(),
    )


def serialize_message(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        chat_id=message.chat_id,
        author_id=message.author_id,
        author_name=message.author.display_name,
        body=message.body,
        created_at=message.created_at.isoformat(),
    )


def assert_chat_member(chat: Chat, user: User) -> None:
    _assert_chat_member(chat, user)


def _assert_chat_member(chat: Chat, user: User) -> None:
    if user.id not in {chat.client_id, chat.executor_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat is available only to order participants.")
