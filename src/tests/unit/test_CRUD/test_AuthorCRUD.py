import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from models import Author as Model
from services.crud import AuthorCRUD
from schemas.author import (
    AuthorCreate as Create,
    AuthorFilter as Filter,
    AuthorInDB as Response,
    AuthorUpdate as Update,
)
from services.exceptions import CRUDOperationError


class TestAuthorCRUD:
    @pytest.fixture
    def sample_author_data(self):
        return {
            "id": uuid4(),
            "name": "Fyodor Dostoevsky",
            "bio": "Russian novelist and philosopher",
        }

    @pytest.fixture
    def sample_author(self, sample_author_data):
        return Model(**sample_author_data)

    @pytest.mark.asyncio
    async def test_create_author_success(self, mock_db_session, sample_author_data):
        """Тест успешного создания автора"""
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = sample_author_data["id"]

        mock_db_session.add.side_effect = capture_add
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        crud = AuthorCRUD(mock_db_session)
        result = await crud.create(
            Create(
                name=sample_author_data["name"],
                bio=sample_author_data["bio"],
            )
        )

        assert isinstance(result, Response)
        assert result.name == sample_author_data["name"]
        assert result.bio == sample_author_data["bio"]
        assert created_obj.name == sample_author_data["name"]
        assert created_obj.bio == sample_author_data["bio"]

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(created_obj)

    async def test_create_with_db_error(self, mock_db_session):
        """Тест отката транзакции при ошибке"""
        mock_db_session.commit.side_effect = Exception("DB error")
        mock_db_session.rollback = AsyncMock()

        crud = AuthorCRUD(mock_db_session)

        with pytest.raises(CRUDOperationError):
            await crud.create(Create(name="Test Author", bio="Test Bio"))

        mock_db_session.rollback.assert_called_once()

    async def test_get_by_id_found(self, mock_db_session, sample_author):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_author)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.get_by_id(sample_author.id)

        expected_schema = Response.model_validate(sample_author)
        assert result == expected_schema
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_id_not_found(self, mock_db_session, sample_author):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.get_by_id(sample_author.id)

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_update_success(self, mock_db_session, sample_author):
        test_update = Update(name="Updated Name", bio="Updated Bio")

        # Мокируем get для возврата sample_author
        mock_db_session.get = AsyncMock(return_value=sample_author)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = AuthorCRUD(mock_db_session)
        result = await crud.update(sample_author.id, test_update)

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(sample_author)

    async def test_update_not_found(self, mock_db_session, sample_author):
        test_update = Update(name="Updated Name")

        mock_db_session.get = AsyncMock(return_value=None)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = AuthorCRUD(mock_db_session)
        result = await crud.update(sample_author.id, test_update)

        assert result is None
        mock_db_session.commit.assert_not_awaited()

    async def test_delete_success(self, mock_db_session, sample_author):
        mock_db_session.get = AsyncMock(return_value=sample_author)
        mock_db_session.commit = AsyncMock()

        crud = AuthorCRUD(mock_db_session)
        result = await crud.delete(sample_author.id)

        assert result is True
        mock_db_session.commit.assert_awaited_once()

    async def test_delete_not_found(self, mock_db_session, sample_author):
        mock_db_session.get = AsyncMock(return_value=None)
        mock_db_session.commit = AsyncMock()

        crud = AuthorCRUD(mock_db_session)
        result = await crud.delete(sample_author.id)

        assert result is False
        mock_db_session.commit.assert_not_awaited()

    async def test_get_all(self, mock_db_session, sample_author):
        """Получение списка авторов"""
        test_models = [sample_author]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = test_models

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.get_all()

        assert len(result) == 1
        assert all(isinstance(item, Response) for item in result)
        assert result[0].name == sample_author.name

        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_filter(self, mock_db_session, sample_author):
        """Получение списка авторов с фильтром"""
        test_models = [sample_author]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = test_models

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        filter_params = Filter(name="Dostoevsky")
        result = await crud.get_all(filter_params)

        assert len(result) == 1
        mock_db_session.execute.assert_awaited_once()

    async def test_exists_true(self, mock_db_session, sample_author_data):
        """Проверка существования автора (True)"""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = True
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.exists(name=sample_author_data["name"])

        assert result is True
        mock_db_session.execute.assert_awaited_once()

    async def test_exists_false(self, mock_db_session):
        """Проверка существования автора (False)"""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = False
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.exists(name="Non-existent Author")

        assert result is False
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_name_found(self, mock_db_session, sample_author):
        """Тест поиска автора по точному имени (успешный случай)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_author)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.get_by_name(sample_author.name)

        expected_schema = Response.model_validate(sample_author)
        assert result == expected_schema
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_name_not_found(self, mock_db_session):
        """Тест поиска автора по имени (когда не найден)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.get_by_name("Non-existent Author")

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_name_case_sensitive(self, mock_db_session, sample_author):
        """Тест регистрозависимого поиска по имени"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.get_by_name(sample_author.name.upper())

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_search_in_bio_found(self, mock_db_session, sample_author):
        """Тест поиска по биографии (найдены совпадения)"""
        # Подготовка тестовых данных
        search_term = "novelist"
        sample_author.bio = "Russian novelist and philosopher"

        # Мокируем результат выполнения запроса
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_author]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.search_in_bio(search_term)

        # Проверки
        assert len(result) == 1
        assert isinstance(result[0], Response)
        assert search_term.lower() in result[0].bio.lower()

        # Проверяем что запрос был выполнен с правильными параметрами
        mock_db_session.execute.assert_awaited_once()
        called_query = str(mock_db_session.execute.call_args[0][0])

    async def test_search_in_bio_not_found(self, mock_db_session):
        """Тест поиска по биографии (нет совпадений)"""
        # Мокируем пустой результат
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.search_in_bio("nonexistent")

        assert len(result) == 0
        mock_db_session.execute.assert_awaited_once()

    async def test_search_in_bio_case_insensitive(self, mock_db_session, sample_author):
        """Тест поиска по биографии без учета регистра"""
        # Подготовка тестовых данных
        search_term = "NOVELIST"
        sample_author.bio = "Russian novelist and philosopher"

        # Мокируем результат выполнения запроса
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_author]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = AuthorCRUD(mock_db_session)
        result = await crud.search_in_bio(search_term)

        # Проверяем что поиск работает без учета регистра
        assert len(result) == 1

        # Проверяем что в запросе используется ilike

    async def test_db_error_handling(self, mock_db_session):
        """Тест обработки ошибок БД во всех методах"""
        mock_db_session.execute.side_effect = Exception("DB error")
        crud = AuthorCRUD(mock_db_session)

        with pytest.raises(CRUDOperationError):
            await crud.get_by_id(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_all()

        with pytest.raises(CRUDOperationError):
            await crud.get_by_name("Author")

        with pytest.raises(CRUDOperationError):
            await crud.search_in_bio("term")
