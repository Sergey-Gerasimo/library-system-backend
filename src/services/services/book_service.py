from typing import override, Optional, List
from uuid import UUID
import magic

from services.crud import IBookCRUD, IBookFilesCRUD, IStorageRUD
from schemas import (
    BookCreate as Create,
    BookFilter as Filter,
    BookInDB as Responce,
    BookUpdate as Update,
    BookFileCreate,
    FileType,
    File,
)

# BUG: Строки в метаданных дожны быть в формате ASCII. Вылетает ошибки если не так
# TODO: Добавить проверку на ASCII
# TODO: Добвить ошибки


class BookService:
    """Сервис для работы с книгами и связанными файлами.

    Обеспечивает:
    - Создание книг с прикрепленными PDF и обложками
    - Управление файлами в S3 хранилище
    - Базовые CRUD операции для книг
    - Связь между книгами и их файлами

    :ivar _book_crud: CRUD слой для работы с книгами
    :vartype _book_crud: IBookCRUD
    :ivar _book_files_crud: CRUD слой для работы с файлами книг
    :vartype _book_files_crud: IBookFilesCRUD
    :ivar _s3: Клиент для работы с S3 хранилищем
    :vartype _s3: IStorageRUD
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

    def __get_mime_type(self, file_bytes: bytes) -> str:
        """Определить MIME-тип файла по его содержимому.

        :param file_bytes: Байтовое содержимое файла
        :type file_bytes: bytes
        :return: MIME-тип файла
        :rtype: str
        """
        mime = magic.Magic(mime=True)
        return mime.from_buffer(file_bytes)

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
        :raises Exception: При ошибке загрузки в S3
        """

        content_type = self.__get_mime_type(file.content)

        if not await self._s3.upload_file(
            file_key=s3_key,
            file_data=file.content,
            content_type=content_type,
            metadata=file.headers,
        ):
            raise Exception("Failed to upload file to S3")

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

        return s3_key

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

    @override
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
        :raises ValueError: Если не переданы обязательные параметры
        """

        if book is None:
            if None in (title, year, author_id, genre_id):
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

        s3_pdf_key = self._create_s3_key(bookInDB.id, file_name=pdf.filename)
        s3_cover_key = self._create_s3_key(bookInDB.id, file_name=cover.filename)

        await self._upload_file(
            book_id=bookInDB.id,
            s3_key=s3_pdf_key,
            file=pdf,
            file_type=FileType.PDF,
        )

        await self._upload_file(
            book_id=bookInDB.id,
            s3_key=s3_cover_key,
            file=cover,
            file_type=FileType.COVER,
        )

        return bookInDB

    async def get(self, id: UUID) -> Responce:
        """Получить книгу по ID.

        :param id: ID книги
        :type id: UUID
        :return: Найденная книга
        :rtype: Responce
        """
        book = await self._book_crud.get_by_id(id=id)
        return book

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
        """
        books = await self._book_crud.get_all(
            filter=filter, limit=limit, offset=offset, order_by=order_by
        )

        return books

    async def get_by_author(self, author_id: UUID) -> List[Responce]:
        """Получить книги по ID автора.

        :param author_id: ID автора
        :type author_id: UUID
        :return: Список книг автора
        :rtype: List[Responce]
        """
        books = await self._book_crud.get_by_author(author_id=author_id)
        return books

    async def get_by_title(self, title: str) -> Responce:
        """Получить книгу по точному названию.

        :param title: Название книги
        :type title: str
        :return: Найденная книга
        :rtype: Responce
        """
        books = await self._book_crud.get_by_title(title=title)
        return books

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
        """

        if book is None:
            book = Update(
                title=title,
                year=year,
                author_id=author_id,
                genre_id=genre_id,
                is_published=is_published,
                description=description,
            )

        await self._book_crud.update(id=id, update_data=book)

        if pdf is not None:
            s3_pdf_key = self._create_s3_key(id, file_name=pdf.filename)
            await self._upload_file(
                book_id=id,
                s3_key=s3_pdf_key,
                file=pdf,
                file_type=FileType.PDF,
            )

        if cover is not None:
            s3_cover_key = self._create_s3_key(id, file_name=cover.filename)

            await self._upload_file(
                book_id=id,
                s3_key=s3_cover_key,
                file=cover,
                file_type=FileType.COVER,
            )

    async def exists(self, **kwargs) -> bool:
        """Проверить существование книги по параметрам.

        :param kwargs: Параметры для поиска
        :return: Флаг существования
        :rtype: bool
        """
        return await self._crud.exists(**kwargs)

    async def delete(self, id: UUID):
        """Удалить книгу и все связанные файлы.

        :param id: ID книги
        :type id: UUID
        :raises Exception: Если книга не найдена
        """
        book = await self._book_crud.get_by_id(id)
        if book is None:
            raise

        files = await self._book_files_crud.get_by_book(book.id)
        for file in files:
            await self._s3.delete_file(file.storage_key)
            await self._book_files_crud.delete(file.id)

        await self._book_crud.delete(book.id)
