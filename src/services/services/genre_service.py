from uuid import UUID
from typing import List, Optional
from loguru import logger

from services.abc import AbstractService
from services.crud import IGenreCRUD
from services.exceptions import (
    ServiceError,
    ServiceNotFoundError,
    ServiceValidationError,
    ServiceIntegrityError,
    handle_service_errors,
)
from models import Genre as Model
from schemas import (
    GenreCreate as Create,
    GenreInDB as Responce,
    GenreUpdate as Update,
    GenreFilter as Filter,
)


class GenreService(AbstractService["Model", "Create", "Update", "Filter", "Responce"]):
    """Сервис для работы с жанрами.

    Наследует базовый функционал от AbstractService и реализует
    специфичную для жанров бизнес-логику.

    :ivar _crud: CRUD слой для работы с жанрами
    :vartype _crud: IGenreCRUD

    Пример использования:
        .. code-block:: python

            genre_service = GenreService(genre_crud)
            new_genre = await genre_service.create(
                GenreCreate(name="Фантастика", description="Жанр о будущем")
            )
    """

    def __init__(self, crud: IGenreCRUD):
        """Инициализация сервиса.

        :param crud: CRUD слой для работы с жанрами
        :type crud: IGenreCRUD
        """
        super().__init__(crud=crud)
        self._crud = crud
        self._logger = self._logger.bind(domain="genres")

    @handle_service_errors()
    async def get_by_name(self, name: str) -> Optional[Responce]:
        """Получить жанр по точному названию.

        :param name: Название жанра
        :type name: str
        :return: Найденный жанр или None
        :rtype: Optional[Responce]
        :raises ServiceError: При ошибках доступа к данным
        """

        self._logger.debug("Getting genre by name", name=name)
        try:

            genre = await self._crud.get_by_name(name)
            if genre:
                self._logger.debug("Genre found", name=name)
            else:
                self._logger.debug("Genre not found", name=name)
            return genre

        except Exception as e:
            self._logger.error("Failed to get genre by name", name=name, error=str(e))
            raise ServiceError(f"Ошибка при поиске жанра: {str(e)}") from e

    @handle_service_errors()
    async def search_in_description(self, search_term: str) -> List[Responce]:
        """Поиск жанров по ключевым словам в описании.

        :param search_term: Строка для поиска
        :type search_term: str
        :return: Список найденных жанров
        :rtype: List[Responce]
        :raises ServiceValidationError: Если поисковый запрос слишком короткий
        :raises ServiceError: При ошибках поиска
        """
        self._logger.info("Searching genres by description", search_term=search_term)

        if len(search_term) < 3:
            self._logger.warning(
                "Search term too short", search_term=search_term, min_length=3
            )
            raise ServiceValidationError(
                "Поисковый запрос должен содержать минимум 3 символа"
            )

        try:

            genres = await self._crud.search_in_description(search_term)
            self._logger.info(
                "Genres search completed",
                search_term=search_term,
                found_count=len(genres),
            )
            return genres

        except Exception as e:
            self._logger.error(
                "Genres search failed", search_term=search_term, error=str(e)
            )
            raise ServiceError(f"Ошибка при поиске жанров: {str(e)}") from e

    @handle_service_errors(max_retries=3)
    async def create_with_validation(self, genre_data: Create) -> Responce:
        """Создать жанр с дополнительной валидацией.

        :param genre_data: Данные для создания жанра
        :type genre_data: Create
        :return: Созданный жанр
        :rtype: Responce
        :raises ServiceValidationError: При невалидных данных
        :raises ServiceIntegrityError: Если жанр уже существует
        :raises ServiceError: При ошибках создания
        """
        self._logger.info(
            "Creating genre with validation",
            genre_name=genre_data.name,
            description_length=(
                len(genre_data.description) if genre_data.description else 0
            ),
        )
        if not genre_data.name.strip():
            self._logger.error(
                "Empty genre name provided", genre_data=genre_data.model_dump()
            )
            raise ServiceValidationError("Название жанра не может быть пустым")

        try:
            existing = await self._crud.get_by_name(genre_data.name)
            if existing:
                self._logger.warning("Genre already exists", genre_name=genre_data.name)
                raise ServiceIntegrityError(f"Жанр '{genre_data.name}' уже существует")

            created_genre = await self._crud.create(genre_data)
            self._logger.success(
                "Genre created successfully",
                genre_id=str(created_genre.id),
                genre_name=created_genre.name,
            )
            return created_genre

        except Exception as e:
            self._logger.error(
                "Failed to create genre", genre_name=genre_data.name, error=str(e)
            )

            raise ServiceError(f"Не удалось создать жанр: {str(e)}") from e

    @handle_service_errors()
    async def update_description(
        self, genre_id: UUID, new_description: str
    ) -> Responce:
        """Обновить описание жанра.

        :param genre_id: ID жанра
        :type genre_id: UUID
        :param new_description: Новое описание
        :type new_description: str
        :return: Обновленный жанр
        :rtype: Responce
        :raises ServiceNotFoundError: Если жанр не найден
        :raises ServiceValidationError: При слишком коротком описании
        :raises ServiceError: При ошибках обновления
        """
        self._logger.info(
            "Updating genre description",
            genre_id=str(genre_id),
            description_length=len(new_description),
        )

        if len(new_description) < 10:
            self._logger.warning(
                "Description too short",
                genre_id=str(genre_id),
                min_length=10,
                actual_length=len(new_description),
            )

            raise ServiceValidationError(
                "Описание должно содержать минимум 10 символов"
            )

        genre = await self.get(genre_id)

        if not genre:
            self._logger.error("Genre not found for update", genre_id=str(genre_id))

            raise ServiceNotFoundError(f"Жанр с ID {genre_id} не найден")

        try:
            updated_genre = await self._crud.update(
                genre_id, Update(description=new_description)
            )
            self._logger.success(
                "Genre description updated",
                genre_id=str(genre_id),
                new_description_length=len(new_description),
            )
            return updated_genre

        except Exception as e:
            self._logger.error(
                "Failed to update genre description",
                genre_id=str(genre_id),
                error=str(e),
            )
            raise ServiceError(f"Не удалось обновить описание: {str(e)}") from e
