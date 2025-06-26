import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db_session():
    """Фикстура для мока асинхронной сессии SQLAlchemy."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def author_service(mock_db_session):
    """Фикстура для сервиса авторов с мок-сессией."""
    from services.author_service import AuthorService

    return AuthorService(mock_db_session)


@pytest.fixture
def sample_author_data():
    """Фикстура с тестовыми данными автора."""
    return {"name": "Test Author", "bio": "Test Bio"}


@pytest.fixture
def sample_author():
    """Фикстура с моком объекта автора."""
    from models import Author
    from uuid import uuid4

    return Author(id=uuid4(), name="Test Author", bio="Test Bio")
