from typing import BinaryIO, Union, Optional, List, Any, Dict
from uuid import UUID
import magic
from loguru import logger

from services.crud import IStorageRUD, IBookFilesCRUD
from services.exceptions import handle_service_errors, handle_storage_service_errors
from schemas import (
    BookFileInDB as Responce,
    BookFileCreate as Create,
    BookFileUpdate as Update,
    BookFileFilter as Filter,
    File,
    FileType,
)


class StorageService:
    def __init__(self, storage_crud: IStorageRUD, book_files_crud: IBookFilesCRUD):
        self._storage_crud = storage_crud
        self._book_files_crud = book_files_crud
        self._logger = logger.bind(service="StorageService", domain="storage")

    def __get_mime_type(self, file_bytes: bytes) -> str:
        """Определить MIME-тип файла по его содержимому.

        :param file_bytes: Байтовое содержимое файла
        :type file_bytes: bytes
        :return: MIME-тип файла
        :rtype: str
        """
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(file_bytes)
            self._logger.debug(
                "MIME type determined",
                mime_type=mime_type,
                bytes_length=len(file_bytes),
            )

            return mime_type

        except Exception as e:
            self._logger.error(
                "Failed to determine MIME type",
                error=str(e),
                bytes_length=len(file_bytes),
            )
            raise

    @handle_service_errors()
    @handle_storage_service_errors()
    async def upload_file(
        self, book_id: UUID, s3_key, file: File, file_type: FileType
    ) -> bool:
        self._logger.info(
            "Uploading file",
            book_id=str(book_id),
            s3_key=s3_key,
            file_type=file_type.value,
            filename=file.filename,
            size_bytes=file.size,
        )

        if file.content_type is None:
            file.content_type = self.__get_mime_type(file_bytes=file.content)
            self._logger.debug("Detected content type", content_type=file.content_type)

        if not await self._storage_crud.upload_file(
            file_key=s3_key,
            file_data=file.content,
            content_type=file.content_type,
            metadata=file.headers,
        ):
            self._logger.error(
                "File upload failed", book_id=str(book_id), s3_key=s3_key
            )
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

        self._logger.success(
            "File uploaded successfully",
            book_id=str(book_id),
            s3_key=s3_key,
            file_type=file_type.value,
        )

        return s3_key

    @handle_service_errors()
    @handle_storage_service_errors()
    async def download_file(self, file_key: str) -> "File":
        self._logger.info("Downloading file", file_key=file_key)

        try:
            file = await self._storage_crud.download_file(file_key=file_key)
            self._logger.debug(
                "File downloaded",
                file_key=file_key,
                size_bytes=len(file.content) if file.content else 0,
            )
            return file

        except Exception as e:
            self._logger.error("File download failed", file_key=file_key, error=str(e))
            raise

    @handle_service_errors()
    @handle_storage_service_errors()
    async def get_book_files(self, book_id: UUID) -> List["Responce"]:
        self._logger.debug("Getting book files", book_id=str(book_id))
        books = await self._book_files_crud.get_by_book(book_id=book_id)
        self._logger.info(
            "Retrieved book files", book_id=str(book_id), file_count=len(books)
        )
        return books

    @handle_service_errors()
    @handle_storage_service_errors()
    async def delete_file(self, file_id: UUID) -> bool:
        self._logger.warning("Deleting file", file_id=str(file_id))

        result = await self._book_files_crud.delete(id=file_id)

        if result:
            self._logger.info("File deleted successfully", file_id=str(file_id))
        else:
            self._logger.error("File deletion failed", file_id=str(file_id))

        return result

    @handle_service_errors()
    @handle_storage_service_errors()
    async def get_file_metadata(self, file_key: str) -> Dict[str, Any]:
        self._logger.debug("Getting file metadata", file_key=file_key)

        meta = await self._storage_crud.get_file_metadata(file_key=file_key)

        self._logger.debug(
            "Retrieved file metadata",
            file_key=file_key,
            metadata_keys=list(meta.keys()) if meta else None,
        )
        return meta

    @handle_service_errors()
    @handle_storage_service_errors()
    async def update_file_metadata(
        self,
        file_key: str,
        metadata: Dict[str, Any],
        content_type: Optional[str] = None,
    ) -> bool:
        self._logger.info(
            "Updating file metadata",
            file_key=file_key,
            metadata_keys=list(metadata.keys()),
            content_type=content_type,
        )

        result = await self._storage_crud.update_file_metadata(
            file_key=file_key, metadata=metadata, content_type=content_type
        )

        if result:
            self._logger.debug("File metadata updated successfully", file_key=file_key)
        else:
            self._logger.error("File metadata update failed", file_key=file_key)

        return result

    @handle_service_errors()
    @handle_storage_service_errors()
    async def generate_download_link(
        self,
        file_key: str,
        expires_in: int = 3600,
        download_filename: Optional[str] = None,
    ) -> str:
        self._logger.info(
            "Generating download link",
            file_key=file_key,
            expires_in=expires_in,
            download_filename=download_filename,
        )

        link = await self._storage_crud.generate_presigned_url(
            file_key=file_key,
            expires_in=expires_in,
            download_filename=download_filename,
        )

        self._logger.debug(
            "Download link generated",
            file_key=file_key,
            link=(
                link[:50] + "..." if link else None
            ),  # Логируем часть ссылки для безопасности
        )
        return link

    @handle_service_errors()
    @handle_storage_service_errors()
    async def file_exists(self, file_key: str) -> bool:
        self._logger.debug("Checking file existence", file_key=file_key)

        exists = await self._book_files_crud.exists(storage_key=file_key)

        self._logger.debug(
            "File existence check result", file_key=file_key, exists=exists
        )

        return exists
