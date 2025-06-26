from typing import Optional, Dict, Any
import mimetypes

from sqlalchemy.future import select
from sqlalchemy import update, delete
import asyncio

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from models import (
    Book,
    Author,
    Genre,
    BookFile,
    BookHistory,
    BookHistoryAction,
    FileType,
)
from services.book_storage import BookStorage

from schemas import (
    BookCreate,
    BookHistoryAction,
    BookUpdate,
)

from typing import Tuple


class BookService:
    """Сервис для управления книгами и связанными файлами в системе.

    Обеспечивает создание, чтение, обновление и удаление книг с сохранением
    файлов в S3 хранилище и поддержанием истории изменений.
    """

    def __init__(self, db: AsyncSession, storage: BookStorage):
        """Инициализирует сервис книг.

        :param db: Асинхронная сессия базы данных SQLAlchemy
        :type db: AsyncSession
        :param storage: Сервис для работы с файловым хранилищем S3
        :type storage: BookStorage
        """
        self.db = db
        self.storage = storage

    async def _get_author(self, author_id: UUID) -> Author:
        """Получает автора по ID.

        :param author_id: UUID автора
        :type author_id: UUID
        :return: Объект автора
        :rtype: Author
        :raises HTTPException: 404 если автор не найден
        """
        result = await self.db.execute(select(Author).where(Author.id == author_id))
        author = result.scalars().first()
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        return author

    async def _get_genre(self, genre_id: UUID) -> Genre:
        """Получает жанр по ID.

        :param genre_id: UUID жанра
        :type genre_id: UUID
        :return: Объект жанра
        :rtype: Genre
        :raises HTTPException: 404 если жанр не найден
        """
        result = await self.db.execute(select(Genre).where(Genre.id == genre_id))
        genre = result.scalars().first()
        if not genre:
            raise HTTPException(status_code=404, detail="Genre not found")
        return genre

    async def _record_history(
        self,
        book_id: UUID,
        user_id: UUID,
        action: BookHistoryAction,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ):
        """Записывает изменение книги в историю.

        :param book_id: ID изменяемой книги
        :type book_id: int
        :param user_id: ID пользователя, совершившего изменение
        :type user_id: int
        :param action: Тип действия (создание/изменение/удаление)
        :type action: BookHistoryAction
        :param old_values: Старые значения полей, defaults to None
        :type old_values: Optional[Dict[str, Any]]
        :param new_values: Новые значения полей, defaults to None
        :type new_values: Optional[Dict[str, Any]]
        """
        history_entry = BookHistory(
            book_id=book_id,
            user_id=user_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
        )
        self.db.add(history_entry)
        await self.db.flush()

    async def _upload_book_file(
        self,
        book_id: UUID,
        file_type: FileType,
        file: UploadFile,
        original_name: str,
    ) -> BookFile:
        """Загружает файл книги в хранилище и создает запись в БД.

        :param book_id: ID книги
        :type book_id: UUID
        :param file_type: Тип файла (обложка/PDF)
        :type file_type: FileType
        :param file: Объект загружаемого файла
        :type file: UploadFile
        :param original_name: Оригинальное имя файла
        :type original_name: str
        :return: Созданная запись о файле
        :rtype: BookFile
        """

        s3_key = await self.storage.upload_book_file(
            str(book_id), file_type.value, file.file, original_name
        )

        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        db_file = BookFile(
            book_id=book_id,
            storage_key=s3_key,
            file_type=file_type,
            original_name=original_name,
            size_bytes=file_size,
            mime_type=mimetypes.guess_type(original_name)[0]
            or "application/octet-stream",
        )

        self.db.add(db_file)
        await self.db.flush()
        return db_file

    async def _validate_files(
        self, cover_file: UploadFile, pdf_file: UploadFile
    ) -> Tuple[UploadFile, UploadFile]:
        """Проверяет корректность типов файлов книги.

        :param cover_file: Файл обложки
        :type cover_file: UploadFile
        :param pdf_file: PDF файл книги
        :type pdf_file: UploadFile
        :return: Кортеж проверенных файлов (обложка, PDF)
        :rtype: Tuple[UploadFile, UploadFile]
        :raises HTTPException: 415 если тип файла не соответствует ожидаемому
        """

        cover_mime = cover_file.content_type

        if not cover_mime or not cover_mime.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Cover must be an image file",
            )

        if pdf_file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Book file must be PDF",
            )

        return cover_file, pdf_file

    async def _cleanup_files(self, book_id: UUID):
        """Удаляет файлы книги из хранилища при откате транзакции.

        :param book_id: ID книги
        :type book_id: UUID
        """
        try:
            files = await self.storage.get_book_files(str(book_id))
            for file_key in files:
                await self.storage.delete_file(file_key)
        except Exception as e:
            print(f"Failed to cleanup files for book {book_id}: {str(e)}")

    async def _handle_file_update(
        self, book_id: UUID, file_type: FileType, file: UploadFile
    ):
        """Обновляет файл книги (удаляет старый, загружает новый).

        :param book_id: ID книги
        :type book_id: UUID
        :param file_type: Тип файла
        :type file_type: FileType
        :param file: Новый файл
        :type file: UploadFile
        """

        result = await self.db.execute(
            select(BookFile)
            .where(BookFile.book_id == book_id)
            .where(BookFile.file_type == file_type)
        )
        old_file = result.scalars().first()

        if old_file:
            await self.storage.delete_file(old_file.storage_key)
            await self.db.execute(delete(BookFile).where(BookFile.id == old_file.id))

        await self._upload_book_file(book_id, file_type, file, file.filename)

    async def create_book(
        self,
        cover_file: UploadFile,
        pdf_file: UploadFile,
        book_data: BookCreate,
        user_id: UUID,
    ) -> Book:
        """Создает новую книгу с файлами.

        :param cover_file: Файл обложки книги
        :type cover_file: UploadFile
        :param pdf_file: PDF файл книги
        :type pdf_file: UploadFile
        :param book_data: Данные для создания книги
        :type book_data: BookCreate
        :param user_id: ID пользователя, создающего книгу
        :type user_id: UUID
        :return: Созданная книга
        :rtype: Book
        :raises HTTPException: 400 при ошибках валидации, 500 при ошибках создания
        """

        async with self.db.begin():
            try:
                cover_file, pdf_file = await self._validate_files(cover_file, pdf_file)

                await self._get_author(book_data.author_id)
                await self._get_genre(book_data.genre_id)

                db_book = Book(
                    **book_data.model_dump(exclude={"cover_file", "pdf_file"})
                )

                cover_task = self._upload_book_file(
                    db_book.id, FileType.COVER, cover_file, cover_file.filename
                )

                pdf_task = self._upload_book_file(
                    db_book.id, FileType.PDF, pdf_file, pdf_file.filename
                )
                self.db.add(db_book)
                await self.db.flush()

                await asyncio.gather(cover_task, pdf_task)

                await self._record_history(
                    book_id=db_book.id,
                    user_id=user_id,
                    action=BookHistoryAction.CREATE,
                    new_values=book_data.model_dump(),
                )

                await self.db.commit()
                return db_book

            except Exception as e:
                await self.db.rollback()

                if "db_book" in locals():
                    await self._cleanup_files(db_book.id)

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create book: {str(e)}",
                )

    async def get_book(self, book_id: UUID) -> Book:
        """Получает книгу со всеми связанными данными.

        :param book_id: ID книги
        :type book_id: UUID
        :return: Объект книги с файлами, автором и жанром
        :rtype: Book
        :raises HTTPException: 404 если книга не найдена
        """
        query = (
            select(Book)
            .where(Book.id == book_id)
            .options(
                selectinload(Book.files),
                joinedload(Book.author),
                joinedload(Book.genre),
            )
        )

        result = await self.db.execute(query)
        book = result.unique().scalar_one_or_none()

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )

        for file in book.files:
            if file.file_type == FileType.COVER:
                file.cover_url = await self.storage.generate_presigned_url(
                    file.storage_key, expires_in=3600 * 24 * 7  # a week
                )
            elif file.file_type == FileType.PDF:
                file.download_url = await self.storage.generate_one_time_url(
                    file.storage_key
                )

        return book

    async def delete_book(self, book_id: UUID, user_id: UUID) -> Book:
        """Удаляет книгу и все связанные с ней данные.

        :param book_id: ID удаляемой книги
        :type book_id: UUID
        :param user_id: ID пользователя, выполняющего удаление
        :type user_id: UUID
        :return: Удаленная книга
        :rtype: Book
        :raises HTTPException: 404 если книга не найдена, 500 при ошибках удаления
        """
        db_book = await self.get_book(book_id=book_id)

        try:
            await self._record_history(
                book_id=db_book.id,
                user_id=user_id,
                action=BookHistoryAction.DELETE,
                old_values={
                    "title": db_book.title,
                    "description": db_book.description,
                    "author_id": db_book.author_id,
                    "genre_id": db_book.genre_id,
                    "year": db_book.year,
                    "is_published": db_book.is_published,
                },
            )

            result = await self.db.execute(
                select(BookFile).where(BookFile.book_id == book_id)
            )
            files = result.scalars().all()

            for file in files:
                await self.storage.delete_file(file.storage_key)
                await self.db.delete(file)

            await self.db.delete(db_book)
            await self.db.commit()

            return db_book

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to delete book: {str(e)}"
            )

    async def update_book(
        self,
        book_id: UUID,
        book_data: BookUpdate,
        user_id: UUID,
        cover_file: Optional[UploadFile] = None,
        pdf_file: Optional[UploadFile] = None,
    ) -> Book:
        """Обновляет данные книги и/или файлы.

        :param book_id: ID обновляемой книги
        :type book_id: UUID
        :param book_data: Новые данные книги
        :type book_data: BookUpdate
        :param user_id: ID пользователя, выполняющего обновление
        :type user_id: UUID
        :return: Обновленный объект книги
        :rtype: Book
        :raises HTTPException: 500 при ошибках обновления, 404 если книга не найдена
        """
        db_book = await self.get_book(book_id=book_id)

        old_values = {
            "title": db_book.title,
            "description": db_book.description,
            "author_id": db_book.author_id,
            "genre_id": db_book.genre_id,
            "year": db_book.year,
            "is_published": db_book.is_published,
        }

        try:
            if book_data.author_id:
                await self._get_author(book_data.author_id)

            if book_data.genre_id:
                await self._get_genre(book_data.genre_id)

            update_data = book_data.model_dump(
                exclude_unset=True, exclude={"cover_file", "pdf_file"}
            )
            await self.db.execute(
                update(Book).where(Book.id == book_id).values(**update_data)
            )

            if cover_file:
                await self._handle_file_update(db_book.id, FileType.COVER, cover_file)

            if pdf_file:
                await self._handle_file_update(db_book.id, FileType.PDF, pdf_file)

            await self._record_history(
                book_id=db_book.id,
                user_id=user_id,
                action=BookHistoryAction.UPDATE,
                old_values=old_values,
                new_values=update_data,
            )

            await self.db.commit()
            await self.db.refresh(db_book)
            return db_book

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to update book: {str(e)}"
            )
