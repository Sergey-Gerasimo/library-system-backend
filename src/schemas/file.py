from pydantic import BaseModel
from fastapi import UploadFile
from typing import Dict, Optional


class File(BaseModel):
    filename: str
    content_type: Optional[str] = None
    headers: Dict[str, str] = {}
    content: bytes
    size: int

    @classmethod
    async def from_uploadfile(cls, upload_file: UploadFile):
        content = await upload_file.read()
        await upload_file.seek(0)

        return cls(
            filename=upload_file.filename.encode("ascii", errors="ignore").decode(
                "ascii"
            ),
            content_type=upload_file.content_type.encode(
                "ascii", errors="ignore"
            ).decode("ascii"),
            headers=dict(upload_file.headers),
            content=content,
            size=upload_file.size,
        )
