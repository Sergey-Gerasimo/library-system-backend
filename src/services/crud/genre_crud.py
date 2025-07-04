from typing import Protocol, Union
from sqlalchemy import select, delete, update, and_

from services.abc import AbstractCRUD, ICRUD

from models import Genre as Model
from schemas import (
    GenreCreate as Create,
    GenreInDB as Responce,
    GenreUpdate as Update,
    GenreFilter as Filter,
)


class IGenreCRUD(
    ICRUD["Responce", "Create", "Update", "Filter"],
    Protocol,
):
    """Протокол для типизации CRUD операций с жанрами.

    Наследует базовый интерфейс ICRUD.
    Определяет стандартный контракт для работы с жанрами.

    Типы:
        Responce: GenreInDB - схема ответа с данными жанра
        Create: GenreCreate - схема создания жанра
        Update: GenreUpdate - схема обновления жанра
        Filter: GenreFilter - схема фильтрации жанров
    """

    async def get_by_name(self, name: str) -> Union[Responce, None]: ...
    async def search_in_description(
        self, search_term: str
    ) -> Union[Responce, None]: ...


class GenreCRUD(AbstractCRUD["Model", "Create", "Update", "Filter", "Responce"]):
    """Реализация CRUD операций для работы с жанрами.

    Наследует все базовые CRUD операции от AbstractCRUD.
    Все методы защищены декоратором @handle_db_errors для обработки ошибок БД.

    Типы:
        Model: Genre - SQLAlchemy модель жанра
        Create: GenreCreate - схема создания жанра
        Update: GenreUpdate - схема обновления жанра
        Filter: GenreFilter - схема фильтрации жанров
        Responce: GenreInDB - схема ответа с данными жанра

    Пример использования:
        # Инициализация
        genre_crud = GenreCRUD(db_session)

        # Создание жанра
        new_genre = await genre_crud.create(GenreCreate(
            name="Фантастика",
            description="Жанр о будущем и технологиях"
        ))

        # Получение жанра
        genre = await genre_crud.get_by_id(genre_id)
    """

    @property
    def model(self) -> type[Model]:
        """Возвращает класс SQLAlchemy модели Genre.

        :return: Класс модели жанра
        :rtype: type[Genre]
        """
        return Model

    @property
    def response_schema(self) -> type[Responce]:
        """Возвращает Pydantic схему GenreInDB для валидации ответов.

        :return: Класс схемы ответа
        :rtype: type[GenreInDB]
        """
        return Responce

    async def get_by_name(self, name: str) -> Union[Responce, None]:
        """Возвращает Жанр по имени.

        :return: Жанр если найден, None если не найден
        :rtype: type[GenreInDB
        """

        result = await self.db.execute(select(Model).where(Model.name == name))
        genre = result.scalar_one_or_none()

        return self.response_schema.model_validate(genre) if genre else None

    async def search_in_description(self, search_term: str) -> Union[Responce, None]:
        """
        Возвращает Жанр по поисковому запросу в описании.

        :return: Жанр если найден, None если не найден
        :rtype: type[GenreInDB]
        """
        raise NotImplementedError()
