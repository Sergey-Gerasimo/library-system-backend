from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

from enum import Enum


# Enum для статусов публикации (если нужно)
class BookPublishStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BookBase(BaseModel):
    """Базовая схема книги"""

    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    year: int = Field(..., ge=0)
    is_published: bool = False


class BookCreate(BookBase):
    """Схема для создания книги"""

    author_id: UUID = None
    genre_id: UUID = None


class BookUpdate(BaseModel):
    """Схема для обновления книги"""

    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    author_id: Optional[UUID] = None
    genre_id: Optional[UUID] = None
    year: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None


class BookInDB(BookBase):
    """Схема для ответа с данными книги"""

    id: UUID
    author_id: Optional[UUID] = None
    genre_id: Optional[UUID] = None
    created_at: datetime

    # Конфигурация для работы с ORM
    model_config = ConfigDict(from_attributes=True)


class BookFilter(BaseModel):
    """Схема для фильтрации книг"""

    title: Optional[str] = None
    author_id: Optional[UUID] = None
    genre_id: Optional[UUID] = None
    year_from: Optional[int] = Field(None, ge=0)
    year_to: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Война",
                "author_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "year_from": 1900,
                "is_published": True,
            }
        }
