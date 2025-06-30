from typing import List, Optional
from uuid import UUID
from services.abc import AbstractService
from services.exceptions import (
    ServiceError,
    ServiceNotFoundError,
    ServiceValidationError,
    ServiceIntegrityError,
    handle_service_errors,
)
from models import Author as Model
from schemas import (
    AuthorCreate as Create,
    AuthorInDB as Response,
    AuthorUpdate as Update,
    AuthorFilter as Filter,
)


class AuthorService(AbstractService[Model, Create, Update, Filter, Response]):
    """Сервис для работы с авторами.

    Реализует бизнес-логику поверх базовых CRUD операций, включая:
    - Поиск авторов по различным критериям
    - Специальные методы создания и обновления с валидацией
    - Поиск по содержимому биографии

    :inherits: AbstractService[Model, Create, Update, Filter, Response]
    """

    @handle_service_errors()
    async def get_by_name(self, name: str) -> Optional[Response]:
        """Получить автора по точному совпадению имени.

        :param name: Имя автора для поиска
        :type name: str
        :return: Найденный автор или None
        :rtype: Optional[Response]
        :raises ServiceError: При ошибках доступа к данным
        """
        try:
            return await self.crud.get_by_name(name)

        except Exception as e:
            raise ServiceError("Не удалось найти автора") from e

    @handle_service_errors()
    async def search_in_bio(self, search_term: str) -> List[Response]:
        """Поиск авторов по ключевым словам в биографии.

        :param search_term: Строка для поиска
        :type search_term: str
        :return: Список найденных авторов
        :rtype: List[Response]
        :raises ServiceValidationError: Если поисковый запрос слишком короткий
        :raises ServiceError: При ошибках поиска
        """

        if len(search_term) < 3:
            raise ServiceValidationError("Слишком короткий поисковый запрос")

        try:
            return await self.crud.search_in_bio(search_term)
        except Exception as e:
            raise ServiceError("Ошибка при поиске авторов") from e

    @handle_service_errors(max_retries=3)
    async def create_with_validation(self, author_data: Create) -> Response:
        """Создать автора с дополнительной валидацией.

        :param author_data: Данные для создания автора
        :type author_data: Create
        :return: Созданный автор
        :rtype: Response
        :raises ServiceValidationError: При пустом имени
        :raises ServiceIntegrityError: Если автор уже существует
        :raises ServiceError: При ошибках создания
        """

        if not author_data.name.strip():
            raise ServiceValidationError("Имя автора не может быть пустым")

        existing = await self.crud.get_by_name(author_data.name)
        if existing:
            raise ServiceIntegrityError(f"Автор {author_data.name} уже существует")

        try:
            return await self.crud.create(author_data)
        except Exception as e:
            raise ServiceError("Не удалось создать автора") from e

    @handle_service_errors()
    async def update_bio(self, author_id: UUID, new_bio: str) -> Response:
        """Обновить биографию автора с проверками.

        :param author_id: Идентификатор автора
        :type author_id: UUID
        :param new_bio: Новая биография
        :type new_bio: str
        :return: Обновленный автор
        :rtype: Response
        :raises ServiceNotFoundError: Если автор не найден
        :raises ServiceValidationError: При слишком короткой биографии
        :raises ServiceError: При ошибках обновления
        """

        if len(new_bio) < 10:
            raise ServiceValidationError("Биография слишком короткая")

        author = await self.get(author_id)
        if not author:
            raise ServiceNotFoundError(f"Автор {author_id} не найден")

        try:
            return await self.crud.update(author_id, Update(bio=new_bio))
        except Exception as e:
            raise ServiceError("Не удалось обновить биографию") from e
