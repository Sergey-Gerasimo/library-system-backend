from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class GenreBase(BaseModel):
    """Базовая схема для жанра"""

    name: str
    description: Optional[str] = None


class GenreCreate(GenreBase):
    """Схема для создания жанра"""

    pass


class GenreUpdate(BaseModel):
    """Схема для обновления жанра (все поля опциональны)"""

    name: Optional[str] = None
    description: Optional[str] = None


class GenreInDB(GenreBase):
    """Схема для возврата жанра из БД"""

    id: UUID

    class Config:
        from_attributes = True  # Ранее known as orm_mode


class GenreFilter(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None


class GenreWithBooks(GenreInDB):
    """Схема жанра с книгами"""

    books: list["BookInDB"] = []
    best_books: list["BookInDB"] = []


class BookInDB(BaseModel):
    """Упрощенная схема книги для вложенности"""

    id: UUID
    title: str
    is_published: bool

    class Config:
        from_attributes = True
