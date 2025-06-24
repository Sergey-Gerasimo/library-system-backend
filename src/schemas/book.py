from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator
import datetime

from models import BookHistoryAction, FileType


class BookCreate(BaseModel):
    title: str
    description: Optional[str] = None
    author_id: int
    genre_id: int
    year: int
    is_published: bool = False

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        current_year = datetime.datetime.now().year
        if v > current_year + 5:  # Allow books up to 5 years in the future
            raise ValueError(
                f"Year cannot be more than 5 years in the future (current year: {current_year})"
            )
        if v < 1000:  # Assuming no books before 1000 AD
            raise ValueError("Year must be after 1000")
        return v


class BookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    author_id: Optional[int] = None
    genre_id: Optional[int] = None
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
    id: int
    title: str
    description: Optional[str]
    author_id: int
    genre_id: Optional[int]
    year: int
    is_published: bool
    created_at: datetime.datetime
    author_name: Optional[str]
    genre_name: Optional[str]

    class Config:
        from_attributes = True


class BookFileResponse(BaseModel):
    id: int
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
    id: int
    action: BookHistoryAction
    changed_at: datetime.datetime
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    user_id: int
    username: str

    class Config:
        from_attributes = True
