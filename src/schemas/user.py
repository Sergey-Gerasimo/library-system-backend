from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    roles: list[str] = list()
