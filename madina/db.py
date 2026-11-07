from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from madina.config import settings

Base = declarative_base()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    username = Column(String(128), nullable=True)
    language = Column(String(16), default="uz")
    voice_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationMemory(Base):
    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, nullable=False, index=True)
    context = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_user(db, telegram_user_id: int, first_name: str | None = None, last_name: str | None = None, username: str | None = None) -> UserProfile:
    user = db.query(UserProfile).filter_by(telegram_user_id=telegram_user_id).first()
    if user is None:
        user = UserProfile(
            telegram_user_id=telegram_user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username
        user.updated_at = datetime.utcnow()
        db.commit()
    return user


def save_message(db, telegram_user_id: int, role: str, content: str) -> None:
    message = ChatMessage(telegram_user_id=telegram_user_id, role=role, content=content)
    db.add(message)
    db.commit()


def get_recent_history(db, telegram_user_id: int, limit: int = 12) -> list[dict[str, str]]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.telegram_user_id == telegram_user_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def clear_history(db, telegram_user_id: int) -> None:
    db.query(ChatMessage).filter(ChatMessage.telegram_user_id == telegram_user_id).delete()
    db.commit()


def get_user(db, telegram_user_id: int) -> UserProfile | None:
    return db.query(UserProfile).filter_by(telegram_user_id=telegram_user_id).first()


def update_user_language(db, telegram_user_id: int, language: str) -> UserProfile:
    user = get_user(db, telegram_user_id)
    if user is None:
        user = UserProfile(telegram_user_id=telegram_user_id, language=language)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.language = language
        db.commit()
    return user


def set_voice_mode(db, telegram_user_id: int, enabled: bool) -> UserProfile:
    user = get_user(db, telegram_user_id)
    if user is None:
        user = UserProfile(telegram_user_id=telegram_user_id, voice_enabled=enabled)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.voice_enabled = enabled
        db.commit()
    return user
