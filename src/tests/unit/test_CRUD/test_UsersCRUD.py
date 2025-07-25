import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from models import User as Model
from schemas import (
    UserCreate as Create,
    UserInDB as Response,
    UserUpdate as Update,
    UserFilter as Filter,
    UserRole,
)
from services.crud import UserCRUD
from services.exceptions import CRUDOperationError


class TestUserCRUD:
    @pytest.fixture
    def sample_user_data(self):
        return {
            "username": "johndoe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "hashed_password": "hashed_password",
            "roles": [UserRole.EDITOR],
            "is_active": True,
        }

    @pytest.fixture
    def sample_user(self, sample_user_data):
        return Model(id=uuid4(), **sample_user_data)

    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    async def test_create_user_success(self, mock_db_session, sample_user_data):
        """Test successful user creation"""
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = uuid4()

        mock_db_session.add.side_effect = capture_add

        crud = UserCRUD(mock_db_session)
        result = await crud.create(Create(**sample_user_data))

        assert isinstance(result, Response)
        assert result.username == sample_user_data["username"]
        assert result.email == sample_user_data["email"]
        assert result.roles == sample_user_data["roles"]
        assert created_obj.hashed_password == sample_user_data["hashed_password"]
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_get_by_id_found(self, mock_db_session, sample_user):
        """Test getting user by ID (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = UserCRUD(mock_db_session)
        result = await crud.get_by_id(sample_user.id)

        expected_schema = Response.model_validate(sample_user)
        assert result == expected_schema
        mock_db_session.execute.assert_awaited_once()

    async def test_update_user_success(self, mock_db_session, sample_user):
        """Test successful user update"""
        update_data = Update(
            full_name="John Updated", roles=[UserRole.ADMIN], is_active=False
        )

        mock_db_session.get = AsyncMock(return_value=sample_user)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = UserCRUD(mock_db_session)
        result = await crud.update(sample_user.id, update_data)

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(sample_user)

    async def test_get_by_username_found(self, mock_db_session, sample_user):
        """Test getting user by username (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = UserCRUD(mock_db_session)
        result = await crud.get_by_username(sample_user.username)

        assert isinstance(result, Response)
        assert result.username == sample_user.username
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_email_found(self, mock_db_session, sample_user):
        """Test getting user by email (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = UserCRUD(mock_db_session)
        result = await crud.get_by_email(sample_user.email)

        assert isinstance(result, Response)
        assert result.email == sample_user.email
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_username_not_found(self, mock_db_session):
        """Test getting user by username (not found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = UserCRUD(mock_db_session)
        result = await crud.get_by_username("nonexistent")

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_email_not_found(self, mock_db_session):
        """Test getting user by email (not found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = UserCRUD(mock_db_session)
        result = await crud.get_by_email("nonexistent@example.com")

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_filter(self, mock_db_session, sample_user):
        """Test filtering users"""
        filter_params = Filter(
            username="johndoe",
            email="john@example.com",
            is_active=True,
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_user]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = UserCRUD(mock_db_session)
        result = await crud.get_all(filter_params)

        assert len(result) == 1
        assert isinstance(result[0], Response)
        assert result[0].username == "johndoe"
        mock_db_session.execute.assert_awaited_once()

    async def test_db_error_handling(self, mock_db_session):
        """Test database error handling"""
        mock_db_session.execute.side_effect = Exception("DB error")
        crud = UserCRUD(mock_db_session)

        with pytest.raises(CRUDOperationError):
            await crud.get_by_id(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_by_username("testuser")

        with pytest.raises(CRUDOperationError):
            await crud.get_by_email("test@example.com")

        with pytest.raises(CRUDOperationError):
            await crud.get_all(Filter())
