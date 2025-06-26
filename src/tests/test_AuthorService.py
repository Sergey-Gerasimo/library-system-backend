import pytest
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Author
from schemas import AuthorCreate, AuthorUpdate
from services.author_service import AuthorService


class TestCreateAuthor:
    async def test_create_author_success(self, author_service, mock_db_session):
        author_data = AuthorCreate(name="Test Author", bio="Test Bio")
        test_uuid = uuid4()

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh = AsyncMock()

        real_author = Author(name=author_data.name, bio=author_data.bio)
        real_author.id = test_uuid

        async def mock_refresh(author):
            author.id = test_uuid

        mock_db_session.refresh.side_effect = mock_refresh

        result = await author_service.create_author(author_data)

        assert isinstance(result, Author)
        assert result.name == "Test Author"
        assert result.bio == "Test Bio"
        assert result.id == test_uuid

        mock_db_session.add.assert_called_once()
        added_author = mock_db_session.add.call_args[0][0]
        assert added_author.name == "Test Author"
        assert added_author.bio == "Test Bio"

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(added_author)

    async def test_create_author_conflict(self, author_service, mock_db_session):
        author_data = AuthorCreate(name="Test Author", bio="Test Bio")
        mock_db_session.commit.side_effect = IntegrityError("mock", "mock", "mock")

        with pytest.raises(HTTPException) as exc_info:
            await author_service.create_author(author_data)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        mock_db_session.rollback.assert_awaited_once()


class TestGetAuthorById:
    async def test_get_author_found(self, author_service, mock_db_session):
        author_id = uuid4()
        mock_author = Author(id=author_id, name="Test Author", bio="Test Bio")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_author
        mock_db_session.execute.return_value = mock_result

        result = await author_service.get_author_by_id(author_id)

        assert result == mock_author
        mock_db_session.execute.assert_awaited_once()
        mock_result.scalar_one_or_none.assert_called_once()

    async def test_get_author_not_found(self, author_service, mock_db_session):
        author_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await author_service.get_author_by_id(author_id)

        assert exc_info.value.status_code == 404
        mock_db_session.execute.assert_awaited_once()

    async def test_get_author_database_error(self, author_service, mock_db_session):
        author_id = uuid4()
        mock_db_session.execute.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            await author_service.get_author_by_id(author_id)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetAllAuthors:
    async def test_get_all_authors_success(self, author_service, mock_db_session):
        mock_authors = [
            Author(id=uuid4(), name="Author 1", bio="Bio 1"),
            Author(id=uuid4(), name="Author 2", bio="Bio 2"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_authors
        mock_db_session.execute.return_value = mock_result

        result = await author_service.get_all_authors()

        assert result == mock_authors
        mock_db_session.execute.assert_awaited_once()


class TestUpdateAuthor:
    async def test_update_author_success(self, author_service, mock_db_session):
        author_id = uuid4()
        update_data = AuthorUpdate(name="Updated Author", bio="Updated Bio")
        existing_author = Author(id=author_id, name="Old Author", bio="Old Bio")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_author
        mock_db_session.execute.return_value = mock_result

        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.side_effect = [mock_result, mock_check_result]

        result = await author_service.update_author(author_id, update_data)

        assert result.name == "Updated Author"
        assert result.bio == "Updated Bio"
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(existing_author)

    async def test_update_author_not_found(self, author_service, mock_db_session):
        author_id = uuid4()
        update_data = AuthorUpdate(name="Updated Author")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await author_service.update_author(author_id, update_data)

        assert exc_info.value.status_code == 404

    async def test_update_author_name_conflict(self, author_service, mock_db_session):
        author_id = uuid4()
        update_data = AuthorUpdate(name="Existing Author")
        existing_author = Author(id=author_id, name="Old Author", bio="Old Bio")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_author
        mock_db_session.execute.return_value = mock_result

        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = Author()
        mock_db_session.execute.side_effect = [mock_result, mock_check_result]

        with pytest.raises(HTTPException) as exc_info:
            await author_service.update_author(author_id, update_data)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        mock_db_session.rollback.assert_awaited_once()

    async def test_update_author_no_changes(self, author_service, mock_db_session):
        author_id = uuid4()
        update_data = AuthorUpdate()  # Пустые данные
        existing_author = Author(
            id=author_id, name="Existing Author", bio="Existing Bio"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_author
        mock_db_session.execute.return_value = mock_result

        result = await author_service.update_author(author_id, update_data)

        assert result == existing_author
        mock_db_session.commit.assert_not_awaited()
        mock_db_session.refresh.assert_not_awaited()


class TestDeleteAuthor:
    async def test_delete_author_success(self, author_service, mock_db_session):
        author_id = uuid4()
        mock_author = Author(id=author_id, name="Test Author", bio="Test Bio")

        with patch.object(
            author_service, "get_author_by_id", AsyncMock(return_value=mock_author)
        ):
            result = await author_service.delete_author(author_id)

        assert result == mock_author
        mock_db_session.execute.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_delete_author_with_books(self, author_service, mock_db_session):
        author_id = uuid4()
        mock_author = Author(id=author_id, name="Test Author", bio="Test Bio")

        with patch.object(
            author_service, "get_author_by_id", AsyncMock(return_value=mock_author)
        ):
            mock_db_session.commit.side_effect = IntegrityError("mock", "mock", "mock")

            with pytest.raises(HTTPException) as exc_info:
                await author_service.delete_author(author_id)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            mock_db_session.rollback.assert_awaited_once()
