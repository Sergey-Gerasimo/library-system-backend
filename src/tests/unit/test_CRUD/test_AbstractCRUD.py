import pytest
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    column_property,
    DeclarativeBase,
)
from typing import Annotated, Optional, List

from services.abc import AbstractCRUD
from services.exceptions import CRUDOperationError


class Base(DeclarativeBase):
    pass


uuid = Annotated[UUID, mapped_column(default=uuid4, primary_key=True)]
# делаем постоянный uuid для тестов


# SQLAlchemy модель
class _TestModel(Base):
    __tablename__ = "test_model"

    id: Mapped[uuid]
    name: Mapped[str]


class _TestCreateSchema(BaseModel):
    name: str


class _TestUpdateSchema(BaseModel):
    name: Optional[str] = None


class _TestFilterSchema(BaseModel):
    name: Optional[str] = None


class _TestResponseSchema(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class _TestCRUD(
    AbstractCRUD[
        _TestModel,
        _TestCreateSchema,
        _TestUpdateSchema,
        _TestFilterSchema,
        _TestResponseSchema,
    ]
):
    @property
    def model(self):
        return _TestModel

    @property
    def response_schema(self):
        return _TestResponseSchema


class TestAbstractCRUD:
    """Тесты для AbstractCRUD"""

    async def test_create_success(self, mock_db_session, test_uuid):
        """Тест успешного создания записи"""
        test_data = _TestCreateSchema(name="Test User")

        # Захватываем созданный объект для проверки
        created_obj = None

        def capture_add(obj):
            nonlocal created_obj
            created_obj = obj
            obj.id = test_uuid  # Имитируем генерацию ID как в реальной БД

        # Мокируем поведение
        mock_db_session.add.side_effect = capture_add
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        crud = _TestCRUD(mock_db_session)
        result = await crud.create(test_data)

        # Проверки
        assert isinstance(result, _TestResponseSchema)
        assert result.name == "Test User"
        assert isinstance(result.id, UUID)

        # Проверяем что объект создан с правильными данными
        assert created_obj.name == "Test User"
        assert created_obj.id == result.id  # ID должен совпадать

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(created_obj)

    async def test_create_with_db_error(self):
        """Тест отката транзакции при ошибке"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit.side_effect = Exception("DB error")
        mock_db.rollback = AsyncMock()

        crud = _TestCRUD(mock_db)

        with pytest.raises(CRUDOperationError):
            await crud.create(_TestCreateSchema(name="Test User"))

        mock_db.rollback.assert_called_once()

    async def test_get_by_id_found(self, mock_db_session, test_uuid):
        """Успешный поиск записи по ID"""

        test_model = _TestModel(id=test_uuid, name="Test User")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=test_model)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        expected_dict = {"id": test_uuid, "name": "Test User"}
        expected_response = _TestResponseSchema(**expected_dict)

        crud = _TestCRUD(mock_db_session)
        result = await crud.get_by_id(test_uuid)

        assert result == expected_response
        assert isinstance(result.id, UUID)

        mock_db_session.execute.assert_called_once()
        called_query = mock_db_session.execute.call_args[0][0]

    async def test_get_by_id_not_found(self, mock_db_session, test_uuid):
        """Поиск несуществующей записи"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = _TestCRUD(mock_db_session)
        result = await crud.get_by_id(uuid4())

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_update_success(self, mock_db_session, test_uuid):
        """Успешное обновление записи"""
        test_model = _TestModel(id=test_uuid, name="Test User")
        test_update = _TestUpdateSchema(name="blablabla")

        mock_db_session.get = AsyncMock(return_value=test_model)
        mock_db_session.execute = AsyncMock(return_value=None)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = _TestCRUD(mock_db_session)
        result = await crud.update(test_model.id, test_update)

        mock_db_session.execute.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()

    async def test_update_not_found(self, mock_db_session, test_uuid):
        """Обновление несуществующей записи"""
        test_model = _TestModel(id=test_uuid, name="Test User")
        test_update = _TestUpdateSchema(name="blablabla")

        mock_db_session.get = AsyncMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=None)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = _TestCRUD(mock_db_session)
        result = await crud.update(test_model.id, test_update)
        assert result is None

        mock_db_session.execute.assert_not_awaited()
        mock_db_session.commit.assert_not_awaited()
        mock_db_session.refresh.assert_not_awaited()

    async def test_delete_success(self, mock_db_session, test_uuid):
        """Успешное удаление записи"""
        test_model = _TestModel(id=test_uuid, name="Test User")

        mock_db_session.get = AsyncMock(return_value=test_model)
        mock_db_session.execute = AsyncMock(return_value=None)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = _TestCRUD(mock_db_session)
        result = await crud.delete(test_model.id)
        assert result is not None

        mock_db_session.execute.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()

    async def test_delete_not_found(self, mock_db_session, test_uuid):
        """Удаление несуществующей записи"""
        test_model = _TestModel(id=test_uuid, name="Test User")

        mock_db_session.get = AsyncMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=None)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        crud = _TestCRUD(mock_db_session)
        result = await crud.delete(test_model.id)
        assert result == False

        mock_db_session.execute.assert_not_awaited()
        mock_db_session.commit.assert_not_awaited()

    async def test_get_all(self, mock_db_session):
        """Получение списка без фильтров"""
        test_models = [_TestModel(id=uuid4(), name=f"User {i}") for i in range(3)]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = test_models

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = _TestCRUD(mock_db_session)
        result = await crud.get_all()

        assert len(result) == 3
        assert all(isinstance(item, _TestResponseSchema) for item in result)

        mock_db_session.execute.assert_awaited_once()
        mock_result.scalars.assert_called_once()
        mock_scalars.all.assert_called_once()

        called_query = mock_db_session.execute.call_args[0][0]
        assert "SELECT" in str(called_query)

    async def test_exists_true(self, mock_db_session):
        """Проверка существования записи (True)"""

        # Мокируем цепочку вызовов SQLAlchemy
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = True
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = _TestCRUD(mock_db_session)
        result = await crud.exists(name="test@example.com")

        assert result is True
        mock_db_session.execute.assert_awaited_once()

        # Проверяем сформированный запрос
        called_query = mock_db_session.execute.call_args[0][0]
        assert "EXISTS" in str(called_query)

    async def test_exists_false(self, mock_db_session):
        """Проверка существования записи (False)"""
        # Мокируем цепочку вызовов SQLAlchemy
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = False
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        crud = _TestCRUD(mock_db_session)
        result = await crud.exists(name="test@example.com")

        assert result is False
        mock_db_session.execute.assert_awaited_once()

        # Проверяем сформированный запрос
        called_query = mock_db_session.execute.call_args[0][0]
        assert "EXISTS" in str(called_query)

    async def test_init_with_invalid_db_session(self):
        """Инициализация с неверным типом сессии должна вызывать TypeError"""
        # 1. Пробуем передать синхронную сессию вместо асинхронной
        with pytest.raises(TypeError) as exc_info:
            invalid_session = MagicMock()  # Просто мок, не AsyncSession
            _TestCRUD(invalid_session)

        # 2. Проверяем сообщение об ошибке
        assert "db_session must be AsyncSession" in str(exc_info.value)

        # 3. Проверяем другие невалидные типы
        with pytest.raises(TypeError):
            _TestCRUD(None)

        with pytest.raises(TypeError):
            _TestCRUD("not_a_session")

        with pytest.raises(TypeError):
            _TestCRUD(123)

    def test_abstract_properties_not_implemented(self):
        """Проверка, что нельзя создать экземпляр без реализации обязательных свойств"""

        # 1. Создаем тестовый класс без реализации абстрактных свойств
        class InvalidCRUD(AbstractCRUD):
            pass

        # 2. Проверяем, что при создании экземпляра выбрасывается TypeError
        with pytest.raises(TypeError) as exc_info:
            InvalidCRUD(AsyncMock(spec=AsyncSession))

        # 3. Проверяем, что в сообщении об ошибке указаны все нереализованные свойства
        error_message = str(exc_info.value)
        assert "Can't instantiate abstract class" in error_message
        assert "model" in error_message
        assert "response_schema" in error_message

        # 4. Проверяем частичную реализацию (если реализовано только одно свойство)
        class PartiallyImplementedCRUD(AbstractCRUD):
            @property
            def model(self):
                return _TestModel

        with pytest.raises(TypeError) as exc_info:
            PartiallyImplementedCRUD(AsyncMock(spec=AsyncSession))

        assert "response_schema" in str(exc_info.value)
        assert "model" not in str(exc_info.value)  # model уже реализован
