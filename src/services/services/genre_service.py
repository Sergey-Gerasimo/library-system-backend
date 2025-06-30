from uuid import UUID
from typing import List, Optional

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
        self._crud = crud

    @handle_service_errors()
    async def get_by_name(self, name: str) -> Optional[Responce]:
        """Получить жанр по точному названию.

        :param name: Название жанра
        :type name: str
        :return: Найденный жанр или None
        :rtype: Optional[Responce]
        :raises ServiceError: При ошибках доступа к данным
        """
        try:
            return await self._crud.get_by_name(name)
        except Exception as e:
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
        if len(search_term) < 3:
            raise ServiceValidationError(
                "Поисковый запрос должен содержать минимум 3 символа"
            )

        try:
            return await self._crud.search_in_description(search_term)
        except Exception as e:
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
        if not genre_data.name.strip():
            raise ServiceValidationError("Название жанра не может быть пустым")

        existing = await self._crud.get_by_name(genre_data.name)
        if existing:
            raise ServiceIntegrityError(f"Жанр '{genre_data.name}' уже существует")

        try:
            return await self._crud.create(genre_data)
        except Exception as e:
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
        if len(new_description) < 10:
            raise ServiceValidationError(
                "Описание должно содержать минимум 10 символов"
            )

        genre = await self.get(genre_id)
        if not genre:
            raise ServiceNotFoundError(f"Жанр с ID {genre_id} не найден")

        try:
            return await self._crud.update(
                genre_id, Update(description=new_description)
            )
        except Exception as e:
            raise ServiceError(f"Не удалось обновить описание: {str(e)}") from e
