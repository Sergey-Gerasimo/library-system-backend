from typing import override, Optional, List
from uuid import UUID
import magic
import asyncio
from loguru import logger

from services.crud import IBookCRUD, IBookFilesCRUD, IStorageRUD
from services.exceptions import (
    handle_service_errors,
    handle_storage_service_errors,
    ServiceError,
    ServiceIntegrityError,
    ServiceNotFoundError,
    ServiceOperationError,
    ServiceTemporaryError,
    ServiceValidationError,
)

from utils import translit_dict

from schemas import (
    BookCreate as Create,
    BookFilter as Filter,
    BookInDB as Responce,
    BookUpdate as Update,
    BookFileCreate,
    FileType,
    File,
)


class BookService:
    """Сервис для работы с книгами и связанными файлами.

    Обеспечивает:
    - Создание книг с прикрепленными PDF и обложками
    - Управление файлами в S3 хранилище
    - Базовые CRUD операции для книг
    - Связь между книгами и их файлами
    - Валидацию MIME-типов загружаемых файлов
    - Обработку и трансформацию ошибок хранилища и БД

    :ivar _book_crud: CRUD слой для работы с книгами
    :vartype _book_crud: IBookCRUD
    :ivar _book_files_crud: CRUD слой для работы с файлами книг
    :vartype _book_files_crud: IBookFilesCRUD
    :ivar _s3: Клиент для работы с S3 хранилищем
    :vartype _s3: IStorageRUD

    :raises ServiceValidationError: При невалидных данных или файлах
    :raises ServiceNotFoundError: При отсутствии запрашиваемых данных
    :raises ServiceOperationError: При ошибках операций с хранилищем
    :raises ServiceTemporaryError: При временных проблемах с хранилищем
    """

    def __init__(
        self,
        book_crud: IBookCRUD,
        book_files_crud: IBookFilesCRUD,
        s3: IStorageRUD,
    ):
        """Инициализация сервиса.

        :param book_crud: CRUD слой для книг
        :type book_crud: IBookCRUD
        :param book_files_crud: CRUD слой для файлов книг
        :type book_files_crud: IBookFilesCRUD
        :param s3: Клиент S3 хранилища
        :type s3: IStorageRUD
        """
        self._book_crud = book_crud
        self._book_files_crud = book_files_crud
        self._s3 = s3
        self._logger = logger.bind(service="BookService", domain="books")

    def __get_mime_type(self, file_bytes: bytes) -> str:
        """Определить MIME-тип файла по его содержимому.

        :param file_bytes: Байтовое содержимое файла
        :type file_bytes: bytes
        :return: MIME-тип файла
        :rtype: str
        :raises ServiceValidationError: Если не удалось определить MIME-тип
        """
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(file_bytes)
            self._logger.debug(
                "MIME type determined",
                content_length=len(file_bytes),
                detected_type=mime_type,
            )

            return mime_type

        except Exception as e:
            self._logger.error(
                "Failed to detect MIME type",
                error=str(e),
                content_length=len(file_bytes),
            )
            raise ServiceValidationError(f"Invalid file content: {str(e)}") from e

    async def _upload_file(
        self, book_id: UUID, s3_key, file: File, file_type: FileType
    ) -> str:
        """Загрузить файл в S3 и создать запись в БД.

        :param book_id: ID книги
        :type book_id: UUID
        :param s3_key: Ключ файла в S3
        :type s3_key: str
        :param file: Файл для загрузки
        :type file: File
        :param file_type: Тип файла
        :type file_type: FileType
        :return: Ключ загруженного файла в S3
        :rtype: str
        :raises ServiceValidationError: При невалидных метаданных или типе файла
        :raises ServiceOperationError: При ошибке загрузки в S3
        """

        log_context = {
            "book_id": str(book_id),
            "s3_key": s3_key,
            "file_type": file_type.value,
            "file_name": file.filename,
            "file_size": file.size,
        }

        self._logger.info("Starting file upload", **log_context)
        try:

            content_type = self.__get_mime_type(file.content)
            log_context["content_type"] = content_type

            for key, value in file.headers.items():
                if not all(ord(char) < 128 for char in f"{key}{value}"):
                    self._logger.warning(
                        "Non-ASCII metadata detected", **log_context, metadata_key=key
                    )
                    raise ServiceValidationError(
                        "Metadata keys and values must be ASCII only"
                    )

            upload_result = await self._s3.upload_file(
                file_key=s3_key,
                file_data=file.content,
                content_type=content_type,
                metadata=translit_dict(file.headers),
            )

            if not upload_result:
                self._logger.error("S3 upload failed", **log_context)
                raise ServiceOperationError("Failed to upload file to S3")

            await self._book_files_crud.create(
                BookFileCreate(
                    book_id=book_id,
                    storage_key=s3_key,
                    file_type=file_type,
                    original_name=file.filename,
                    size_bytes=file.size,
                    mime_type=content_type,
                )
            )

            self._logger.success("File uploaded successfully", **log_context)
            return s3_key
        except ServiceValidationError:
            raise
        except Exception as e:
            self._logger.error(
                "File upload failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceOperationError(f"File upload failed: {str(e)}") from e

    def _create_s3_key(self, book_id: UUID, file_name) -> str:
        """Сгенерировать ключ для хранения файла в S3.

        :param book_id: ID книги
        :type book_id: UUID
        :param file_name: Имя файла
        :type file_name: str
        :return: Ключ для хранения в S3
        :rtype: str
        """
        return f"{book_id}/{file_name}"

    async def create(
        self,
        pdf: File,
        cover: File,
        book: Optional[Create] = None,
        *,
        title: Optional[str] = None,
        year: Optional[int] = None,
        author_id: Optional[UUID] = None,
        genre_id: Optional[UUID] = None,
        is_published: bool = False,
        description: Optional[str] = None,
    ) -> Responce:
        """Создать новую книгу с файлами.

        :param pdf: PDF файл книги
        :type pdf: File
        :param cover: Файл обложки
        :type cover: File
        :param book: Данные для создания книги, defaults to None
        :type book: Optional[Create]
        :keyword title: Название книги, если не передана схема Create
        :type title: Optional[str]
        :keyword year: Год издания, если не передана схема Create
        :type year: Optional[int]
        :keyword author_id: ID автора, если не передана схема Create
        :type author_id: Optional[UUID]
        :keyword genre_id: ID жанра, если не передана схема Create
        :type genre_id: Optional[UUID]
        :keyword is_published: Флаг публикации, defaults to False
        :type is_published: bool
        :keyword description: Описание книги, defaults to None
        :type description: Optional[str]
        :return: Созданная книга
        :rtype: Responce
        :raises ServiceValidationError: Если не переданы обязательные параметры
        :raises ServiceIntegrityError: При нарушении целостности данных
        :raises ServiceOperationError: При ошибках загрузки файлов
        """

        creation_context = {
            "pdf_file": pdf.filename,
            "pdf_size": pdf.size,
            "cover_file": cover.filename,
            "cover_size": cover.size,
            "title": title,
            "year": year,
            "author_id": author_id,
            "genre_id": genre_id,
            "is_published": is_published,
            "description": description,
        }

        self._logger.info("Starting book creation", **creation_context)

        try:
            if book is None:
                if None in (title, year, author_id, genre_id):
                    self._logger.error("Missing required fields", **creation_context)
                    raise ValueError("Missing required book fields")

                book = Create(
                    title=title,
                    year=year,
                    author_id=author_id,
                    genre_id=genre_id,
                    is_published=is_published,
                    description=description,
                )

            bookInDB = await self._book_crud.create(book)
            creation_context["book_id"] = str(bookInDB.id)

            self._logger.debug("Book record created", **creation_context)

            try:
                s3_pdf_key = self._create_s3_key(bookInDB.id, file_name=pdf.filename)
                s3_cover_key = self._create_s3_key(
                    bookInDB.id, file_name=cover.filename
                )

                upload_tasks = [
                    self._upload_file(
                        book_id=bookInDB.id,
                        s3_key=s3_pdf_key,
                        file=pdf,
                        file_type=FileType.PDF,
                    ),
                    self._upload_file(
                        book_id=bookInDB.id,
                        s3_key=s3_cover_key,
                        file=cover,
                        file_type=FileType.COVER,
                    ),
                ]

                await asyncio.gather(*upload_tasks)
                self._logger.success("Book created successfully", **creation_context)
                return bookInDB

            except Exception as upload_error:
                self._logger.error(
                    "Rolling back book creation due to file upload failure",
                    **creation_context,
                    error=str(upload_error),
                )
                await self._book_crud.delete(bookInDB.id)
                raise

        except Exception as e:
            error_type = (
                "validation" if isinstance(e, ServiceValidationError) else "operation"
            )
            self._logger.error(
                f"Book creation failed ({error_type})",
                **creation_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            if isinstance(e, ServiceValidationError):
                raise
            raise ServiceOperationError(f"Book creation failed: {str(e)}") from e

    @handle_service_errors()
    @handle_storage_service_errors()
    async def get(self, id: UUID) -> Responce:
        """Получить книгу по ID.

        :param id: ID книги
        :type id: UUID
        :return: Найденная книга
        :rtype: Responce
        :raises ServiceNotFoundError: Если книга не найдена
        :raises ServiceOperationError: При ошибках доступа к данным
        """

        try:
            book = await self._book_crud.get_by_id(id=id)
            if not book:
                raise ServiceNotFoundError(f"Book with id {id} not found")
            return book
        except Exception as e:
            if isinstance(e, ServiceNotFoundError):
                raise
            raise ServiceOperationError(f"Failed to get book: {str(e)}") from e

    @handle_service_errors()
    @handle_storage_service_errors()
    async def get_all(
        self,
        filter: Filter,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
    ) -> List[Responce]:
        """Получить список книг с фильтрацией и пагинацией.

        :param filter: Параметры фильтрации
        :type filter: Filter
        :param limit: Лимит записей, defaults to 100
        :type limit: int
        :param offset: Смещение, defaults to 0
        :type offset: int
        :param order_by: Поле сортировки, defaults to None
        :type order_by: str | None
        :return: Список книг
        :rtype: List[Responce]
        :raises ServiceValidationError: При невалидных параметрах запроса
        :raises ServiceOperationError: При ошибках доступа к данным
        """
        try:
            if limit < 1 or offset < 0:
                raise ServiceValidationError("Invalid pagination parameters")

            books = await self._book_crud.get_all(
                filter=filter, limit=limit, offset=offset, order_by=order_by
            )
            return books
        except Exception as e:
            if isinstance(e, ServiceValidationError):
                raise
            raise ServiceOperationError(f"Failed to get books: {str(e)}") from e

    @handle_service_errors()
    @handle_storage_service_errors()
    async def get_by_author(self, author_id: UUID) -> List[Responce]:
        """Получить книги по ID автора.

        :param author_id: ID автора
        :type author_id: UUID
        :return: Список книг автора
        :rtype: List[Responce]
        :raises ServiceNotFoundError: Если автор не найден
        :raises ServiceOperationError: При ошибках доступа к данным
        """
        try:
            books = await self._book_crud.get_by_author(author_id=author_id)
            if not books:
                raise ServiceNotFoundError(f"No books found for author {author_id}")
            return books
        except Exception as e:
            if isinstance(e, ServiceNotFoundError):
                raise
            raise ServiceOperationError(
                f"Failed to get author's books: {str(e)}"
            ) from e

    @handle_service_errors()
    @handle_storage_service_errors()
    async def get_by_title(self, title: str) -> Responce:
        """Получить книгу по точному названию.

        :param title: Название книги
        :type title: str
        :return: Найденная книга
        :rtype: Responce
        :raises ServiceNotFoundError: Если книга не найдена
        :raises ServiceValidationError: При пустом названии
        :raises ServiceOperationError: При ошибках доступа к данным
        """
        try:
            if not title:
                raise ServiceValidationError("Title cannot be empty")

            book = await self._book_crud.get_by_title(title=title)
            if not book:
                raise ServiceNotFoundError(f"Book '{title}' not found")
            return book
        except Exception as e:
            if isinstance(e, (ServiceNotFoundError, ServiceValidationError)):
                raise
            raise ServiceOperationError(f"Failed to get book by title: {str(e)}") from e

    @handle_service_errors()
    @handle_storage_service_errors()
    async def update(
        self,
        id: UUID,
        pdf: Optional[File],
        cover: Optional[File],
        book: Optional[Update] = None,
        *,
        title: Optional[str] = None,
        year: Optional[int] = None,
        author_id: Optional[UUID] = None,
        genre_id: Optional[UUID] = None,
        is_published: bool = False,
        description: Optional[str] = None,
    ) -> Responce:
        """Обновить данные книги и/или файлы.

        :param id: ID книги
        :type id: UUID
        :param pdf: Новый PDF файл, если требуется обновление
        :type pdf: Optional[File]
        :param cover: Новая обложка, если требуется обновление
        :type cover: Optional[File]
        :param book: Данные для обновления, defaults to None
        :type book: Optional[Update]
        :keyword title: Новое название, если не передана схема Update
        :type title: Optional[str]
        :keyword year: Новый год издания
        :type year: Optional[int]
        :keyword author_id: Новый ID автора
        :type author_id: Optional[UUID]
        :keyword genre_id: Новый ID жанра
        :type genre_id: Optional[UUID]
        :keyword is_published: Новый статус публикации
        :type is_published: bool
        :keyword description: Новое описание
        :type description: Optional[str]
        :return: Обновленная книга
        :rtype: Responce
        :raises ServiceNotFoundError: Если книга не найдена
        :raises ServiceValidationError: При невалидных данных
        :raises ServiceOperationError: При ошибках обновления
        """
        update_context = {
            "book_id": str(id),
            "update_fields": {
                "title": title,
                "year": year,
                "author_id": author_id,
                "genre_id": genre_id,
                "is_published": is_published,
                "description": description,
            },
            "files_updated": {"pdf": pdf is not None, "cover": cover is not None},
        }

        self._logger.info("Starting book update", **update_context)

        try:
            existing_book = await self.get(id)
            update_context["current_state"] = {
                "title": existing_book.title,
                "author_id": str(existing_book.author_id),
                "status": "published" if existing_book.is_published else "unpublished",
            }

            if book is None:
                book = Update(
                    title=title,
                    year=year,
                    author_id=author_id,
                    genre_id=genre_id,
                    is_published=is_published,
                    description=description,
                )

            updated_book = await self._book_crud.update(id=id, update_data=book)
            update_context["new_state"] = {
                "title": updated_book.title,
                "author_id": str(updated_book.author_id),
                "status": "published" if updated_book.is_published else "unpublished",
            }

            # Обновляем файлы, если они предоставлены
            upload_tasks = []
            if pdf is not None:
                s3_pdf_key = self._create_s3_key(id, file_name=pdf.filename)
                upload_tasks.append(
                    self._upload_file(
                        book_id=id,
                        s3_key=s3_pdf_key,
                        file=pdf,
                        file_type=FileType.PDF,
                    )
                )

            if cover is not None:
                s3_cover_key = self._create_s3_key(id, file_name=cover.filename)
                upload_tasks.append(
                    self._upload_file(
                        book_id=id,
                        s3_key=s3_cover_key,
                        file=cover,
                        file_type=FileType.COVER,
                    )
                )

            if upload_tasks:
                await asyncio.gather(*upload_tasks)
                self._logger.debug("Files updated successfully", **update_context)

            self._logger.success("Book updated successfully", **update_context)
            return updated_book

        except Exception as e:
            error_type = (
                "not_found"
                if isinstance(e, ServiceNotFoundError)
                else (
                    "validation"
                    if isinstance(e, ServiceValidationError)
                    else "operation"
                )
            )

            self._logger.error(
                f"Book update failed ({error_type})",
                **update_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    @handle_service_errors()
    @handle_storage_service_errors()
    async def exists(self, **kwargs) -> bool:
        """Проверить существование книги по параметрам.

        :param kwargs: Параметры для поиска
        :return: Флаг существования
        :rtype: bool
        :raises ServiceValidationError: При невалидных параметрах поиска
        :raises ServiceOperationError: При ошибках проверки
        """
        try:
            if not kwargs:
                raise ServiceValidationError("At least one search parameter required")
            return await self._book_crud.exists(**kwargs)
        except Exception as e:
            if isinstance(e, ServiceValidationError):
                raise
            raise ServiceOperationError(f"Existence check failed: {str(e)}") from e

    @handle_service_errors()
    @handle_storage_service_errors()
    async def delete(self, id: UUID):
        """Удалить книгу и все связанные файлы.

        :param id: ID книги
        :type id: UUID
        :raises ServiceNotFoundError: Если книга не найдена
        :raises ServiceOperationError: При ошибках удаления
        """
        delete_context = {"book_id": str(id)}
        self._logger.warning("Starting book deletion", **delete_context)

        try:
            book = await self.get(id)
            delete_context.update(
                {"title": book.title, "author_id": str(book.author_id)}
            )

            if not book:
                raise ServiceNotFoundError(f"Book with id {id} not found")

            files = await self._book_files_crud.get_by_book(book.id)
            delete_context["file_count"] = len(files)

            self._logger.debug("Deleting associated files", **delete_context)

            delete_tasks = [self._s3.delete_file(file.storage_key) for file in files]
            delete_tasks.extend(self._book_files_crud.delete(file.id) for file in files)

            await asyncio.gather(*delete_tasks)
            await self._book_crud.delete(book.id)

            self._logger.warning("Book deleted successfully", **delete_context)

        except Exception as e:
            error_type = (
                "not_found" if isinstance(e, ServiceNotFoundError) else "operation"
            )
            self._logger.error(
                f"Book deletion failed ({error_type})",
                **delete_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
