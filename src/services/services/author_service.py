from typing import List, Optional
from uuid import UUID
from loguru import logger

from services.abc import AbstractService
from services.crud import IAuthorCRUD
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

    def __init__(self, crud: IAuthorCRUD):
        super().__init__(crud=crud)
        self._crud = crud
        self._logger = self._logger.bind(domain="authors")

    @handle_service_errors()
    async def get_by_name(self, name: str) -> Optional[Response]:
        """Получить автора по точному совпадению имени.

        :param name: Имя автора для поиска
        :type name: str
        :return: Найденный автор или None
        :rtype: Optional[Response]
        :raises ServiceError: При ошибках доступа к данным
        """
        log_context = {"operation": "get_by_name", "author_name": name}
        self._logger.debug("Searching author by name", **log_context)
        try:
            author = await self._crud.get_by_name(name)
            if author:
                self._logger.debug("Author found", **log_context)
            else:
                self._logger.debug("Author not found", **log_context)
            return author

        except Exception as e:
            self._logger.error(
                "Failed to get author by name",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
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
        log_context = {
            "operation": "search_in_bio",
            "search_term": search_term,
            "term_length": len(search_term),
        }
        self._logger.info("Searching authors by bio", **log_context)

        if len(search_term) < 3:
            self._logger.warning("Search term too short", **log_context, min_length=3)
            raise ServiceValidationError("Слишком короткий поисковый запрос")

        try:
            authors = await self._crud.search_in_bio(search_term)
            self._logger.info(
                "Authors search completed", **log_context, found_count=len(authors)
            )
            return authors
        except Exception as e:
            self._logger.error(
                "Authors search failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
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

        log_context = {
            "operation": "create_with_validation",
            "author_name": author_data.name,
            "bio_length": len(author_data.bio) if author_data.bio else 0,
        }
        self._logger.info("Creating author with validation", **log_context)

        if not author_data.name.strip():
            self._logger.error("Empty author name provided", **log_context)
            raise ServiceValidationError("Имя автора не может быть пустым")

        try:
            existing = await self._crud.get_by_name(author_data.name)
            if existing:
                self._logger.warning(
                    "Author already exists",
                    **log_context,
                    existing_author_id=str(existing.id),
                )
                raise ServiceIntegrityError(f"Автор {author_data.name} уже существует")

            created_author = await self._crud.create(author_data)
            self._logger.success(
                "Author created successfully",
                **log_context,
                author_id=str(created_author.id),
            )
        except Exception as e:
            self._logger.error(
                "Failed to create author",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
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

        log_context = {
            "operation": "update_bio",
            "author_id": str(author_id),
            "new_bio_length": len(new_bio),
        }
        self._logger.info("Updating author bio", **log_context)

        if len(new_bio) < 10:
            self._logger.warning("Bio too short", **log_context, min_length=10)
            raise ServiceValidationError("Биография слишком короткая")

        try:
            author = await self.get(author_id)
            if not author:
                self._logger.error("Author not found for update", **log_context)
                raise ServiceNotFoundError(f"Автор {author_id} не найден")

            log_context["old_bio_length"] = len(author.bio) if author.bio else 0

            updated_author = await self._crud.update(author_id, Update(bio=new_bio))

            self._logger.success(
                "Author bio updated",
                **log_context,
                change_percent=abs(len(new_bio) - log_context["old_bio_length"])
                / max(len(new_bio), 1)
                * 100,
            )
            return updated_author

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
                f"Failed to update bio ({error_type})",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )

            raise ServiceError("Не удалось обновить биографию") from e
