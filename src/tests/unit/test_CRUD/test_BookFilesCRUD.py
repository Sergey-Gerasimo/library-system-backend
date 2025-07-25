import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from models import BookFile
from schemas import (
    BookFileCreate as Create,
    BookFileInDB as Response,
    BookFileUpdate as Update,
    BookFileFilter as Filter,
    FileType,
)
from services.crud import BookFilesCRUD
from services.exceptions import CRUDOperationError


class TestBookFilesCRUD:
    @pytest.fixture
    def sample_file_data(self):
        return {
            "book_id": uuid4(),
            "storage_key": "books/123/epub",
            "file_type": FileType.PDF,
            "original_name": "book.pdf",
            "size_bytes": 1024,
            "mime_type": "application/pdf",
        }

    @pytest.fixture
    def sample_file(self, sample_file_data):
        file = BookFile(
            id=uuid4(), created_at=datetime.now(timezone.utc), **sample_file_data
        )
        return file

    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    async def test_create_file_success(self, mock_db_session, sample_file_data):
        """Test successful file creation"""
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = uuid4()
            obj.created_at = datetime.now(timezone.utc)

        mock_db_session.add.side_effect = capture_add

        crud = BookFilesCRUD(mock_db_session)
        result = await crud.create(Create(**sample_file_data))

        assert isinstance(result, Response)
        assert result.storage_key == sample_file_data["storage_key"]
        assert result.file_type == FileType.PDF
        assert created_obj.storage_key == sample_file_data["storage_key"]
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_get_by_id_found(self, mock_db_session, sample_file):
        """Test getting file by ID (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_file)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = BookFilesCRUD(mock_db_session)
        result = await crud.get_by_id(sample_file.id)

        expected_schema = Response.model_validate(sample_file)
        assert result == expected_schema
        mock_db_session.execute.assert_awaited_once()

    async def test_update_file_success(self, mock_db_session, sample_file):
        """Test successful file update"""
        update_data = Update(
            original_name="updated.pdf", size_bytes=2048, mime_type="application/x-pdf"
        )

        # Мокируем get для возврата sample_author
        mock_db_session.get = AsyncMock(return_value=sample_file)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = BookFilesCRUD(mock_db_session)
        result = await crud.update(sample_file.id, update_data)

        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(sample_file)

    async def test_get_by_storage_key_found(self, mock_db_session, sample_file):
        """Test getting file by storage key (found)"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_file
        mock_db_session.execute.return_value = mock_result

        crud = BookFilesCRUD(mock_db_session)
        result = await crud.get_by_storage_key(sample_file.storage_key)

        assert isinstance(result, Response)
        assert result.storage_key == sample_file.storage_key
        mock_db_session.execute.assert_awaited_once()

    async def test_get_by_book_found(self, mock_db_session, sample_file):
        """Test getting files by book ID (found)"""
        book_id = sample_file.book_id

        another_file = BookFile(
            id=uuid4(),
            book_id=book_id,
            storage_key="books/123/cover",
            file_type=FileType.COVER,
            original_name="cover.jpg",
            size_bytes=512,
            mime_type="image/jpeg",
            created_at=datetime.utcnow(),
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_file, another_file]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = BookFilesCRUD(mock_db_session)
        result = await crud.get_by_book(book_id)

        assert len(result) == 2
        assert all(isinstance(f, Response) for f in result)
        assert all(f.book_id == book_id for f in result)
        assert {f.file_type for f in result} == {FileType.PDF, FileType.COVER}
        mock_db_session.execute.assert_awaited_once()

    async def test_get_all_with_filter(self, mock_db_session, sample_file):
        """Test filtering files"""
        filter_params = Filter(
            book_id=sample_file.book_id,
            file_type=FileType.PDF,
            mime_type="application/pdf",
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_file]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        crud = BookFilesCRUD(mock_db_session)
        result = await crud.get_all(filter_params)

        assert len(result) == 1
        assert isinstance(result[0], Response)
        assert result[0].file_type == FileType.PDF
        mock_db_session.execute.assert_awaited_once()

    async def test_db_error_handling(self, mock_db_session):
        """Test database error handling"""
        mock_db_session.execute.side_effect = Exception("DB error")
        crud = BookFilesCRUD(mock_db_session)

        with pytest.raises(CRUDOperationError):
            await crud.get_by_id(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_by_storage_key("test")

        with pytest.raises(CRUDOperationError):
            await crud.get_by_book(uuid4())

        with pytest.raises(CRUDOperationError):
            await crud.get_all(Filter())
