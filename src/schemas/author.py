from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID


class AuthorBase(BaseModel):
    """Базовая схема автора"""

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Полное имя автора",
        examples=["Лев Толстой"],
    )
    bio: Optional[str] = Field(
        None,
        max_length=2000,
        description="Биография автора",
        examples=["Русский писатель, классик мировой литературы"],
    )


class AuthorCreate(AuthorBase):
    """Схема для создания автора"""

    @field_validator("name")
    def name_must_contain_space(cls, v):
        if " " not in v:
            raise ValueError("Имя автора должно содержать пробел (Фамилия Имя)")
        return v.title()  # Автоматически форматируем имя с заглавных букв


class AuthorUpdate(BaseModel):
    """Схема для обновления автора (все поля опциональны)"""

    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Полное имя автора",
        examples=["Фёдор Достоевский"],
    )
    bio: Optional[str] = Field(
        None,
        max_length=2000,
        description="Биография автора",
        examples=["Великий русский писатель и мыслитель"],
    )

    @field_validator("name", mode="before")
    def validate_name_if_present(cls, v):
        if v is None:
            return v
        if " " not in v:
            raise ValueError("Имя автора должно содержать пробел (Фамилия Имя)")
        return v.title()


class AuthorInDB(AuthorBase):
    """Схема для возврата автора из БД"""

    id: UUID

    class Config:
        from_attributes = True  # Ранее называлось orm_mode=True в Pydantic v1


class AuthorFilter(BaseModel):
    """Простая модель фильтрации авторов"""

    name: Optional[str] = None
    bio_contains: Optional[str] = None
    has_books: Optional[bool] = None
