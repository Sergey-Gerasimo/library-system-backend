import pytest
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status, UploadFile
from io import BytesIO
import asyncio
from models import Book, Author, Genre, BookFile
from schemas import BookCreate, BookUpdate

from services import BookService

from models import FileType


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.upload_book_file = AsyncMock(return_value="s3_key")
    storage.generate_presigned_url = AsyncMock(
        return_value="http://example.com/cover.jpg"
    )
    storage.generate_one_time_url = AsyncMock(
        return_value="http://example.com/download.pdf"
    )
    storage.delete_file = AsyncMock()
    storage.get_book_files = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def book_service(mock_db_session, mock_storage):
    service = BookService(mock_db_session, mock_storage)

    # Мокируем внутренние методы
    service._get_author = AsyncMock(return_value=MagicMock(spec=Author))
    service._get_genre = AsyncMock(return_value=MagicMock(spec=Genre))
    service._record_history = AsyncMock()
    service._upload_book_file = AsyncMock(return_value=MagicMock(spec=BookFile))
    return service


@pytest.fixture
def valid_book_data():
    return BookCreate(
        title="Test Book",
        description="Test Description",
        author_id=uuid4(),
        genre_id=uuid4(),
        year=2023,
        is_published=True,
    )


@pytest.fixture
def mock_upload_files():
    cover = MagicMock(spec=UploadFile)
    cover.filename = "cover.jpg"
    cover.content_type = "image/jpeg"
    cover.file = BytesIO(b"cover data")

    pdf = MagicMock(spec=UploadFile)
    pdf.filename = "book.pdf"
    pdf.content_type = "application/pdf"
    pdf.file = BytesIO(b"pdf data")

    return cover, pdf


class TestBookService:
    @pytest.mark.asyncio
    async def test_create_book_success(
        self,
        book_service,
        mock_db_session,
        mock_storage,
        valid_book_data,
        mock_upload_files,
    ):
        cover_file, pdf_file = mock_upload_files

        # Создаем реальный объект Book вместо MagicMock
        test_book = Book(
            id=uuid4(),
            title=valid_book_data.title,
            description=valid_book_data.description,
            author_id=valid_book_data.author_id,
            genre_id=valid_book_data.genre_id,
            year=valid_book_data.year,
            is_published=valid_book_data.is_published,
        )

        # Мокируем создание книги
        with patch("models.Book", return_value=test_book):
            result = await book_service.create_book(
                cover_file, pdf_file, valid_book_data, user_id=uuid4()
            )

        # Проверяем что вернулся объект Book с правильными данными
        assert isinstance(result, Book)
        assert result.title == valid_book_data.title
        assert result.description == valid_book_data.description
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_book_rollback_on_error(
        self,
        book_service,
        mock_db_session,
        mock_storage,
        valid_book_data,
        mock_upload_files,
    ):
        cover_file, pdf_file = mock_upload_files

        with patch.object(book_service, "_upload_book_file") as mock_upload_file:
            mock_upload_file.side_effect = Exception("S3 error")
            # Убедимся что исключение действительно возникает
            with pytest.raises(HTTPException) as exc_info:
                await book_service.create_book(
                    cover_file, pdf_file, valid_book_data, user_id=uuid4()
                )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create book" in str(exc_info.value.detail)
        assert mock_upload_file.call_count == 2
        mock_db_session.rollback.assert_awaited_once()
        mock_storage.get_book_files.assert_called_once()
        mock_db_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_book_success(self, book_service, mock_db_session, mock_storage):
        book_id = uuid4()
        test_book = Book(
            id=book_id,
            title="Test Book",
            author_id=uuid4(),
            genre_id=uuid4(),
            year=2023,
        )

        # Настройка моков для execute
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = test_book
        mock_db_session.execute.return_value = mock_result

        result = await book_service.get_book(book_id)

        assert isinstance(result, Book)
        assert result.id == book_id
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_book_success(self, book_service, mock_db_session):
        book_id = uuid4()
        test_book = Book(
            id=book_id,
            title="Original Title",
            author_id=uuid4(),
            genre_id=uuid4(),
            year=2023,
        )

        # Мокируем get_book
        book_service.get_book = AsyncMock(return_value=test_book)

        # Мокируем execute для файлов
        mock_file_result = MagicMock()
        mock_file_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_file_result

        update_data = BookUpdate(title="Updated Title")
        result = await book_service.update_book(book_id, update_data, user_id=uuid4())

        assert isinstance(result, Book)
        assert (
            result.title == "Original Title"
        )  # Проверяем что вернулся исходный объект
        mock_db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_book_success(
        self, book_service, mock_db_session, mock_storage
    ):
        book_id = uuid4()
        test_book = Book(
            id=book_id,
            title="Test Book",
            author_id=uuid4(),
            genre_id=uuid4(),
            year=2023,
        )

        # Мокируем get_book
        book_service.get_book = AsyncMock(return_value=test_book)

        # Мокируем файлы книги
        test_file = BookFile(
            id=uuid4(),
            book_id=book_id,
            storage_key="s3_key",
            file_type=FileType.COVER,
            original_name="cover.jpg",
        )
        mock_file_result = MagicMock()
        mock_file_result.scalars.return_value.all.return_value = [test_file]
        mock_db_session.execute.return_value = mock_file_result

        result = await book_service.delete_book(book_id, user_id=uuid4())

        assert isinstance(result, Book)
        assert result.id == book_id
        mock_storage.delete_file.assert_called_once_with("s3_key")
        mock_db_session.commit.assert_awaited_once()
