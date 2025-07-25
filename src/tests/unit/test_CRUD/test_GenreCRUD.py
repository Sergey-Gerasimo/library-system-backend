import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from models import Genre
from schemas import (
    GenreCreate as Create,
    GenreInDB as Response,
    GenreUpdate as Update,
    GenreFilter as Filter,
)
from services.crud import GenreCRUD
from services.exceptions import CRUDOperationError


class TestGenreCRUD:
    @pytest.fixture
    def sample_genre_data(self):
        return {"name": "Фантастика", "description": "Жанр о будущем и технологиях"}

    @pytest.fixture
    def sample_genre(self, sample_genre_data):
        return Genre(id=uuid4(), **sample_genre_data)

    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    async def test_create_genre_success(self, mock_db_session, sample_genre_data):
        """Test successful genre creation"""
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = uuid4()

        mock_db_session.add.side_effect = capture_add

        crud = GenreCRUD(mock_db_session)
        result = await crud.create(Create(**sample_genre_data))

        assert isinstance(result, Response)
        assert result.name == sample_genre_data["name"]
        assert result.description == sample_genre_data["description"]
        assert created_obj.name == sample_genre_data["name"]
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_get_by_id_found(self, mock_db_session, sample_genre):
        """Test getting genre by ID (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_genre)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = GenreCRUD(mock_db_session)
        result = await crud.get_by_id(sample_genre.id)

        expected_schema = Response.model_validate(sample_genre)
        assert result == expected_schema
        mock_db_session.execute.assert_awaited_once()

    async def test_update_genre_success(self, mock_db_session, sample_genre):
        """Test successful genre update"""
        update_data = Update(
            name="Научная фантастика",
            description="Жанр о научных концепциях и технологиях будущего",
        )

        mock_db_session.get = AsyncMock(return_value=sample_genre)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = GenreCRUD(mock_db_session)
        result = await crud.update(sample_genre.id, update_data)

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(sample_genre)

    async def test_get_by_name_found(self, mock_db_session, sample_genre):
        """Test getting genre by name (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_genre)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = GenreCRUD(mock_db_session)
        result = await crud.get_by_name(sample_genre.name)

        assert isinstance(result, Response)
        assert result.name == sample_genre.name
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_name_not_found(self, mock_db_session):
        """Test getting genre by name (not found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = GenreCRUD(mock_db_session)
        result = await crud.get_by_name("Несуществующий жанр")

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_search_in_description_not_implemented(self, mock_db_session):
        """Test search_in_description raises NotImplementedError"""
        crud = GenreCRUD(mock_db_session)
        with pytest.raises(NotImplementedError):
            await crud.search_in_description("технологии")

    async def test_get_all_with_filter(self, mock_db_session, sample_genre):
        """Test filtering genres"""
        filter_params = Filter(name="Фантастика", description="технологии")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_genre]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = GenreCRUD(mock_db_session)
        result = await crud.get_all(filter_params)

        assert len(result) == 1
        assert isinstance(result[0], Response)
        assert result[0].name == "Фантастика"
        mock_db_session.execute.assert_awaited_once()
