from typing import Optional, Protocol, List
from sqlalchemy import select, delete, update, and_
from uuid import UUID
from abc import abstractmethod

from services.abc import AbstractCRUD, ICRUD
from services.exceptions import handle_db_errors
from models import BookFile
from schemas import (
    BookFileCreate as Create,
    BookFileInDB as Response,
    BookFileUpdate as Update,
    BookFileFilter as Filter,
)


class IBookFilesCRUD(
    ICRUD["Response", "Create", "Update", "Filter"],
    Protocol,
):
    """Протокол для типизации CRUD операций с файлами книг.

    Расширяет базовый интерфейс ICRUD специфичными методами для работы
    с файлами книг. Определяет контракт для всех реализаций сервиса файлов.

    Методы:
        get_by_storage_key: Получение файла по ключу хранилища
        get_by_book: Получение всех файлов книги

    Типы:
        Response: BookFileInDB - схема ответа с данными файла
        Create: BookFileCreate - схема создания записи файла
        Update: BookFileUpdate - схема обновления записи файла
        Filter: BookFileFilter - схема фильтрации файлов
    """

    async def get_by_storage_key(self, storage_key: str) -> Optional["Response"]:
        """Получает информацию о файле по его уникальному ключу в хранилище.

        :param storage_key: Уникальный идентификатор файла в хранилище
        :type storage_key: str
        :return: Данные файла или None если не найден
        :rtype: Optional[BookFileInDB]
        """
        ...

    async def get_by_book(self, book_id: UUID) -> List["Response"]:
        """Получает все файлы, связанные с указанной книгой.

        :param book_id: Идентификатор книги
        :type book_id: UUID
        :return: Список файлов книги
        :rtype: List[BookFileInDB]
        """
        ...


class BookFilesCRUD(AbstractCRUD[BookFile, Create, Update, Filter, Response]):
    """Реализация CRUD операций для работы с файлами книг.

    Наследует базовые CRUD операции от AbstractCRUD и добавляет
    специализированные методы для работы с файлами:
    - Поиск по ключу хранилища
    - Получение всех файлов книги

    Все методы защищены декоратором @handle_db_errors для обработки ошибок БД.

    Типы:
        BookFile: SQLAlchemy модель файла книги
        Create: BookFileCreate - схема создания файла
        Update: BookFileUpdate - схема обновления файла
        Filter: BookFileFilter - схема фильтрации файлов
        Response: BookFileInDB - схема ответа с данными файла

    Пример использования:
        # Инициализация
        files_crud = BookFilesCRUD(db_session)

        # Создание записи о файле
        new_file = await files_crud.create(BookFileCreate(
            book_id=uuid.UUID("..."),
            file_type="epub",
            storage_key="books/123/epub",
            original_name="book.epub",
            size=1024
        ))

        # Получение файла по ключу
        file = await files_crud.get_by_storage_key("books/123/epub")

        # Получение всех файлов книги
        book_files = await files_crud.get_by_book(book_id)
    """

    @property
    def model(self) -> type[BookFile]:
        """Возвращает класс SQLAlchemy модели BookFile.

        Используется в базовых CRUD операциях для взаимодействия с БД.

        :return: Класс модели файла книги
        :rtype: type[BookFile]
        """
        return BookFile

    @property
    def response_schema(self) -> type[Response]:
        """Возвращает Pydantic схему BookFileInDB для валидации ответов.

        Используется для преобразования объектов БД в Pydantic модели.

        :return: Класс схемы ответа
        :rtype: type[BookFileInDB]
        """
        return Response

    @handle_db_errors()
    async def get_by_storage_key(self, storage_key: str) -> Optional[Response]:
        """Находит файл по его уникальному ключу в хранилище.

        Ключ хранилища должен быть уникальным идентификатором файла
        во внешнем файловом хранилище (S3, локальное хранилище и т.д.).

        :param storage_key: Уникальный ключ файла в хранилище
        :type storage_key: str
        :return: Данные файла или None если не найден
        :rtype: Optional[BookFileInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.storage_key == storage_key)
        )
        file = result.scalar_one_or_none()
        return self.response_schema.model_validate(file) if file else None

    @handle_db_errors()
    async def get_by_book(self, book_id: UUID) -> list[Response]:
        """Получает все файлы, связанные с указанной книгой.

        Возвращает список всех файлов разных типов (PDF, EPUB и т.д.),
        которые принадлежат указанной книге.

        :param book_id: Идентификатор книги
        :type book_id: UUID
        :return: Список файлов книги
        :rtype: list[BookFileInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """

        result = await self.db.execute(
            select(self.model).where(self.model.book_id == book_id)
        )
        return [self.response_schema.model_validate(f) for f in result.scalars().all()]
