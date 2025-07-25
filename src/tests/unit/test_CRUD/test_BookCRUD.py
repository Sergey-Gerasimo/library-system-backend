import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from models import Book as Model
from services.crud import BookCRUD
from schemas import (
    BookCreate as Create,
    BookFilter as Filter,
    BookInDB as Response,
    BookUpdate as Update,
    BookPublishStatus,
)
from services.exceptions import CRUDOperationError


class TestBookCRUD:
    @pytest.fixture
    def sample_book_data(self):
        return {
            "title": "The Great Gatsby",
            "description": "A story of wealth and love",
            "year": 1925,
            "is_published": True,
            "author_id": uuid4(),
            "genre_id": uuid4(),
        }

    @pytest.fixture
    def sample_book(self, sample_book_data):
        # Create a proper SQLAlchemy model instance
        book = Model(
            id=uuid4(),
            title=sample_book_data["title"],
            description=sample_book_data["description"],
            year=sample_book_data["year"],
            is_published=sample_book_data["is_published"],
            author_id=sample_book_data["author_id"],
            genre_id=sample_book_data["genre_id"],
            created_at=datetime.now(timezone.utc),
        )
        # Mock SQLAlchemy instance state
        return book

    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    async def test_create_book_success(self, mock_db_session, sample_book_data):
        """Test successful book creation"""
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = uuid4()
            obj.created_at = datetime.now(timezone.utc)

        mock_db_session.add.side_effect = capture_add

        crud = BookCRUD(mock_db_session)
        result = await crud.create(Create(**sample_book_data))

        assert isinstance(result, Response)
        assert result.title == sample_book_data["title"]
        assert result.description == sample_book_data["description"]
        assert result.is_published == sample_book_data["is_published"]
        assert created_obj.title == sample_book_data["title"]
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_get_by_id_found(self, mock_db_session, sample_book):
        """Test getting book by ID (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_book)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        crud = BookCRUD(mock_db_session)
        result = await crud.get_by_id(sample_book.id)

        assert isinstance(result, Response)
        assert result.id == sample_book.id
        assert result.title == sample_book.title
        mock_db_session.execute.assert_awaited_once()

    async def test_update_book_success(self, mock_db_session, sample_book):
        """Test successful book update"""
        update_data = Update(
            title="Updated Title", description="New description", is_published=False
        )

        mock_db_session.get = AsyncMock(return_value=sample_book)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = BookCRUD(mock_db_session)
        result = await crud.update(sample_book.id, update_data)

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(sample_book)

    async def test_get_by_title_found(self, mock_db_session, sample_book):
        """Test getting book by exact title (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_db_session.execute.return_value = mock_result

        crud = BookCRUD(mock_db_session)
        result = await crud.get_by_title(sample_book.title)

        assert isinstance(result, Response)
        assert result.title == sample_book.title
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_author_found(self, mock_db_session, sample_book):
        """Test getting books by author (found)"""
        author_id = sample_book.author_id

        # Create another book by same author
        another_book = Model(
            id=uuid4(),
            title="Another Book",
            year=2020,
            author_id=author_id,
            is_published=True,
            genre_id=uuid4(),
            created_at=datetime.utcnow(),
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_book, another_book]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = BookCRUD(mock_db_session)
        result = await crud.get_by_author(author_id)

        assert len(result) == 2
        assert all(isinstance(book, Response) for book in result)
        assert all(book.author_id == author_id for book in result)
        mock_db_session.execute.assert_awaited_once()

    async def test_db_error_handling(self, mock_db_session):
        """Test database error handling"""
        mock_db_session.execute.side_effect = Exception("DB error")
        crud = BookCRUD(mock_db_session)

        with pytest.raises(CRUDOperationError):
            await crud.get_by_id(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_by_title("Test")

        with pytest.raises(CRUDOperationError):
            await crud.get_by_author(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_all(Filter())

    async def test_not_found_cases(self, mock_db_session):
        """Test cases when items are not found"""
        mock_db_session.get.return_value = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        crud = BookCRUD(mock_db_session)

        # Test get_by_id not found
        assert await crud.get_by_id(uuid4()) is None

        # Test get_by_title not found
        assert await crud.get_by_title("Unknown") is None

        # Test get_by_author returns empty list
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        assert len(await crud.get_by_author(uuid4())) == 0
