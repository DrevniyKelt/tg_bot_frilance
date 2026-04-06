from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ForumPost, ForumTopic, User, utcnow


async def list_forum_topics(session: AsyncSession) -> list[ForumTopic]:
    return (
        await session.scalars(
            select(ForumTopic)
            .options(
                selectinload(ForumTopic.author),
                selectinload(ForumTopic.posts).selectinload(ForumPost.author),
            )
            .order_by(ForumTopic.updated_at.desc())
        )
    ).all()


async def get_forum_topic_by_id(session: AsyncSession, topic_id: int) -> ForumTopic | None:
    return await session.scalar(
        select(ForumTopic)
        .options(
            selectinload(ForumTopic.author),
            selectinload(ForumTopic.posts).selectinload(ForumPost.author),
        )
        .where(ForumTopic.id == topic_id)
    )


async def create_forum_topic(
    session: AsyncSession,
    *,
    author: User,
    title: str,
    body: str,
) -> ForumTopic:
    cleaned_title = title.strip()
    cleaned_body = body.strip()
    if len(cleaned_title) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Topic title is too short.")
    if len(cleaned_body) < 12:
      raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Topic body is too short.")

    topic = ForumTopic(author_id=author.id, title=cleaned_title, body=cleaned_body)
    session.add(topic)
    await session.commit()
    return await get_forum_topic_by_id(session, topic.id)


async def create_forum_post(
    session: AsyncSession,
    *,
    topic: ForumTopic,
    author: User,
    body: str,
) -> ForumPost:
    cleaned_body = body.strip()
    if len(cleaned_body) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reply is too short.")

    post = ForumPost(topic_id=topic.id, author_id=author.id, body=cleaned_body)
    topic.updated_at = utcnow()
    session.add(post)
    await session.commit()
    return await get_forum_post_by_id(session, post.id)


async def get_forum_post_by_id(session: AsyncSession, post_id: int) -> ForumPost | None:
    return await session.scalar(
        select(ForumPost)
        .options(
            selectinload(ForumPost.author),
            selectinload(ForumPost.topic).selectinload(ForumTopic.author),
        )
        .where(ForumPost.id == post_id)
    )


def serialize_forum_topic(topic: ForumTopic) -> dict:
    last_reply_at = topic.posts[-1].created_at.isoformat() if topic.posts else None
    return {
        "id": topic.id,
        "title": topic.title,
        "body": topic.body,
        "author_id": topic.author_id,
        "author_name": topic.author.display_name,
        "posts_count": len(topic.posts),
        "created_at": topic.created_at.isoformat(),
        "updated_at": topic.updated_at.isoformat(),
        "last_reply_at": last_reply_at,
    }


def serialize_forum_post(post: ForumPost) -> dict:
    return {
        "id": post.id,
        "topic_id": post.topic_id,
        "author_id": post.author_id,
        "author_name": post.author.display_name,
        "body": post.body,
        "created_at": post.created_at.isoformat(),
    }
