from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    author_id: int
    author_name: str
    body: str
    created_at: str


class ChatCardResponse(BaseModel):
    id: int
    order_id: int
    order_slug: str
    order_title: str
    client_id: int
    client_name: str
    executor_id: int
    executor_name: str
    last_message: str | None
    updated_at: str


class ChatThreadResponse(BaseModel):
    chat: ChatCardResponse
    messages: list[ChatMessageResponse]


class CreateChatMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
