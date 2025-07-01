from typing import BinaryIO, Union, Optional, List, Any, Dict
from uuid import UUID
import magic

from services.crud import IStorageRUD, IBookFilesCRUD
from schemas import (
    BookFileInDB as Responce,
    BookFileCreate as Create,
    BookFileUpdate as Update,
    BookFileFilter as Filter,
    File,
    FileType,
)


# TODO: реализовать методы StorageService


class StorageService:
    def __init__(self, storage_crud: IStorageRUD, book_files_crud: IBookFilesCRUD):
        self._storage_crud = storage_crud
        self._book_files_crud = book_files_crud

    def __get_mime_type(self, file_bytes: bytes) -> str:
        """Определить MIME-тип файла по его содержимому.

        :param file_bytes: Байтовое содержимое файла
        :type file_bytes: bytes
        :return: MIME-тип файла
        :rtype: str
        """
        mime = magic.Magic(mime=True)
        return mime.from_buffer(file_bytes)

    async def upload_file(
        self, book_id: UUID, s3_key, file: File, file_type: FileType
    ) -> bool:
        if file.content_type is None:
            file.content_type = self.__get_mime_type(file_bytes=file.content)

        if not await self._storage_crud.upload_file(
            file_key=s3_key,
            file_data=file.content,
            content_type=file.content_type,
            metadata=file.headers,
        ):
            raise

        await self._book_files_crud.create(
            Create(
                book_id=book_id,
                storage_key=s3_key,
                file_type=file_type,
                original_name=file.filename,
                size_bytes=file.size,
                mime_type=file.content_type,
            )
        )

        return s3_key

    async def download_file(self, file_key: str) -> "File":
        file = await self._storage_crud.download_file(file_key=file_key)
        return file

    async def get_book_files(self, book_id: UUID) -> List["Responce"]:
        books = await self._book_files_crud.get_by_book(book_id=book_id)
        return books

    async def delete_file(self, file_id: UUID) -> bool:
        return await self._book_files_crud.delete(id=file_id)

    async def get_file_metadata(self, file_key: str) -> Dict[str, Any]:
        meta = await self._storage_crud.get_file_metadata(file_key=file_key)
        return meta

    async def update_file_metadata(
        self,
        file_key: str,
        metadata: Dict[str, Any],
        content_type: Optional[str] = None,
    ) -> bool:

        return await self._storage_crud.update_file_metadata(
            file_key=file_key, metadata=metadata, content_type=content_type
        )

    async def generate_download_link(
        self,
        file_key: str,
        expires_in: int = 3600,
        download_filename: Optional[str] = None,
    ) -> str:
        link = await self._storage_crud.generate_presigned_url(
            file_key=file_key,
            expires_in=expires_in,
            download_filename=download_filename,
        )
        return link

    async def file_exists(self, file_key: str) -> bool:
        raise NotImplementedError()

    async def find_file_by_storage_key(self, storage_key: str) -> Optional["Responce"]:
        raise NotImplementedError()

    async def list_files(self, prefix: Optional[str] = None) -> List[str]:
        raise NotImplementedError()

    async def update_file_record(
        self, file_id: UUID, update_data: "Update"
    ) -> Optional["Responce"]:
        raise NotImplementedError()

    async def get_file_by_id(self, file_id: UUID) -> Optional["Responce"]:
        raise NotImplementedError()

    async def create_file_record(self, create_data: "Create") -> "Responce":
        raise NotImplementedError()

    async def exists_file_record(self, **kwargs: Any) -> bool:
        raise NotImplementedError()

    async def get_all_file_records(
        self,
        filter: Optional["Filter"] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> List["Responce"]:
        raise NotImplementedError()
