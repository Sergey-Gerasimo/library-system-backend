from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator
import datetime

from uuid import UUID

from models import BookHistoryAction, FileType


class BookCreate(BaseModel):
    title: str
    description: Optional[str] = None
    author_id: UUID
    genre_id: UUID
    year: int
    is_published: bool = False


class BookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    author_id: Optional[UUID] = None
    genre_id: Optional[UUID] = None
    year: Optional[int] = None
    is_published: Optional[bool] = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v > current_year + 5:
                raise ValueError(
                    f"Year cannot be more than 5 years in the future (current year: {current_year})"
                )
            if v < 1000:
                raise ValueError("Year must be after 1000")
        return v


class BookResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    author_id: UUID
    genre_id: Optional[UUID]
    year: int
    is_published: bool
    created_at: datetime.datetime
    author_name: Optional[str]
    genre_name: Optional[str]

    class Config:
        from_attributes = True


class BookFileResponse(BaseModel):
    id: UUID
    file_type: FileType
    original_name: str
    size_bytes: int
    mime_type: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class BookWithFilesResponse(BookResponse):
    files: List[BookFileResponse] = []


class BookHistoryEntry(BaseModel):
    id: UUID
    action: BookHistoryAction
    changed_at: datetime.datetime
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    user_id: int
    username: str

    class Config:
        from_attributes = True
