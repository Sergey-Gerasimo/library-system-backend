import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from models import BookHistory as Model
from schemas import (
    BookHistoryCreate as Create,
    BookHistoryInDB as Response,
    BookHistoryUpdate as Update,
    BookHistoryFilter as Filter,
    BookHistoryAction,
)
from services.crud import BookHistoryCRUD
from services.exceptions import CRUDOperationError


class TestBookHistoryCRUD:
    @pytest.fixture
    def sample_history_data(self):
        return {
            "book_id": uuid4(),
            "user_id": uuid4(),
            "action": BookHistoryAction.UPDATE,
            "old_values": {"title": "Old Title"},
            "new_values": {"title": "New Title"},
        }

    @pytest.fixture
    def sample_history(self, sample_history_data):
        return Model(id=uuid4(), changed_at=datetime.utcnow(), **sample_history_data)

    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    async def test_create_history_success(self, mock_db_session, sample_history_data):
        """Test successful history entry creation"""
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = uuid4()
            obj.changed_at = datetime.utcnow()

        mock_db_session.add.side_effect = capture_add

        crud = BookHistoryCRUD(mock_db_session)
        result = await crud.create(Create(**sample_history_data))

        assert isinstance(result, Response)
        assert result.book_id == sample_history_data["book_id"]
        assert result.action == BookHistoryAction.UPDATE
        assert result.old_values == {"title": "Old Title"}
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_get_by_id_found(self, mock_db_session, sample_history):
        """Test getting history entry by ID (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_history)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = BookHistoryCRUD(mock_db_session)
        result = await crud.get_by_id(sample_history.id)

        assert isinstance(result, Response)
        assert result.id == sample_history.id
        assert result.changed_at == sample_history.changed_at
        mock_db_session.execute.assert_awaited_once()

    async def test_update_history_success(self, mock_db_session, sample_history):
        """Test successful history entry update"""
        update_data = Update(
            action=BookHistoryAction.DELETE,
            old_values={"title": "Deleted Title"},
            new_values=None,
        )

        mock_db_session.get = AsyncMock(return_value=sample_history)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = BookHistoryCRUD(mock_db_session)
        result = await crud.update(sample_history.id, update_data)

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(sample_history)

        assert isinstance(result, Response)
        mock_db_session.commit.assert_awaited_once()

    async def test_get_by_book_found(self, mock_db_session, sample_history):
        """Test getting history by book ID (found)"""
        book_id = sample_history.book_id

        another_history = Model(
            id=uuid4(),
            book_id=book_id,
            user_id=uuid4(),
            action=BookHistoryAction.CREATE,
            old_values=None,
            new_values={"title": "New Book"},
            changed_at=datetime.utcnow(),
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_history, another_history]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = BookHistoryCRUD(mock_db_session)
        result = await crud.get_by_book(book_id)

        assert len(result) == 2
        assert all(isinstance(h, Response) for h in result)
        assert all(h.book_id == book_id for h in result)
        assert {h.action for h in result} == {
            BookHistoryAction.UPDATE,
            BookHistoryAction.CREATE,
        }
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_user_found(self, mock_db_session, sample_history):
        """Test getting history by user ID (found)"""
        user_id = sample_history.user_id

        # Create another history entry by same user
        another_history = Model(
            id=uuid4(),
            book_id=uuid4(),
            user_id=user_id,
            action=BookHistoryAction.DELETE,
            old_values={"title": "Deleted Book"},
            new_values=None,
            changed_at=datetime.utcnow(),
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_history, another_history]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = BookHistoryCRUD(mock_db_session)
        result = await crud.get_by_user(user_id)

        assert len(result) == 2
        assert all(isinstance(h, Response) for h in result)
        assert all(h.user_id == user_id for h in result)
        mock_db_session.execute.assert_awaited_once()

    async def test_create_with_minimal_data(self, mock_db_session):
        """Test creation with minimal required data"""

        def capture_add(obj):
            obj.id = uuid4()
            obj.changed_at = datetime.utcnow()

        mock_db_session.add.side_effect = capture_add

        minimal_data = {
            "book_id": uuid4(),
            "user_id": uuid4(),
            "action": BookHistoryAction.CREATE,
        }

        crud = BookHistoryCRUD(mock_db_session)
        result = await crud.create(Create(**minimal_data))

        assert isinstance(result, Response)
        assert result.old_values is None
        assert result.new_values is None

    async def test_db_error_handling(self, mock_db_session):
        """Test database error handling"""
        mock_db_session.execute.side_effect = Exception("DB error")
        crud = BookHistoryCRUD(mock_db_session)

        with pytest.raises(CRUDOperationError):
            await crud.get_by_id(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_by_book(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_by_user(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_all(Filter())
