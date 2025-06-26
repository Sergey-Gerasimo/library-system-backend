import pytest
from services import BookStorage
from unittest.mock import AsyncMock, MagicMock, patch

from uuid import uuid4


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.setex = AsyncMock()
    redis.eval = AsyncMock()
    return redis


@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    client.upload_fileobj = AsyncMock()
    client.generate_presigned_url = AsyncMock()
    client.list_objects_v2 = AsyncMock()
    client.delete_object = AsyncMock()
    client.get_object = AsyncMock()
    return client


@pytest.fixture
def book_storage(mock_redis, mock_s3_client):
    with patch("services.s3_service.S3Client.get_client") as mock_get_client:
        mock_get_client.return_value.__aenter__.return_value = mock_s3_client
        storage = BookStorage(mock_redis)
        storage._get_client = mock_get_client
        return storage


class TestUploadBookFile:
    async def test_upload_book_success(self, book_storage, mock_s3_client, mock_redis):
        book_id = uuid4()
        file_type = "pdf"
        file_object = b"blablabla"
        file_nmae = "some_pdf_file"

        res = await book_storage.upload_book_file(
            book_id=book_id,
            file_type=file_type,
            file_obj=file_object,
            original_filename=file_nmae,
        )

        assert res == f"books/{book_id}/pdf.pdf"
