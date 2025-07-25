import pytest
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from typing import Optional, List
from services.abc import AbstractService
from services.exceptions import (
    ServiceError,
    CRUDIntegrityError,
    ServiceNotFoundError,
    ServiceValidationError,
    ServiceIntegrityError,
)


class TestModel:
    def __init__(self, id: UUID, name: str):
        self.id = id
        self.name = name


class TestCreateSchema(BaseModel):
    name: str


class TestUpdateSchema(BaseModel):
    name: str


class TestFilterSchema(BaseModel):
    name: str


class TestResponseSchema(BaseModel):
    id: UUID
    name: str


# Тестовый сервис, реализующий AbstractService
class TestService(
    AbstractService[
        TestModel,
        TestCreateSchema,
        TestUpdateSchema,
        TestFilterSchema,
        TestResponseSchema,
    ]
):
    pass


@pytest.fixture
def mock_crud():
    return AsyncMock()


@pytest.fixture
def test_service(mock_crud):
    return TestService(crud=mock_crud)


@pytest.fixture
def sample_record():
    record_id = uuid4()
    return TestModel(id=record_id, name="Test Record")


@pytest.fixture
def sample_response(sample_record):
    return TestResponseSchema(id=sample_record.id, name=sample_record.name)


async def test_create_success(test_service, mock_crud, sample_response):
    create_data = TestCreateSchema(name="New Record")
    mock_crud.create.return_value = sample_response

    result = await test_service.create(create_data)

    assert result == sample_response
    mock_crud.create.assert_awaited_once_with(create_data)


async def test_create_integrity_error(test_service, mock_crud):
    create_data = TestCreateSchema(name="New Record")
    mock_crud.create.side_effect = CRUDIntegrityError("Duplicate entry")

    with pytest.raises(ServiceIntegrityError):
        await test_service.create(create_data)


async def test_get_success(test_service, mock_crud, sample_response):
    record_id = sample_response.id
    mock_crud.get_by_id.return_value = sample_response

    result = await test_service.get(record_id)

    assert result == sample_response
    mock_crud.get_by_id.assert_awaited_once_with(record_id)


async def test_get_not_found(test_service, mock_crud):
    record_id = uuid4()
    mock_crud.get_by_id.return_value = None

    with pytest.raises(ServiceNotFoundError):
        await test_service.get(record_id)


async def test_update_success(test_service, mock_crud, sample_response):
    record_id = sample_response.id
    update_data = TestUpdateSchema(name="Updated Name")
    updated_response = TestResponseSchema(id=record_id, name="Updated Name")
    mock_crud.update.return_value = updated_response

    result = await test_service.update(record_id, update_data)

    assert result == updated_response
    mock_crud.update.assert_awaited_once_with(record_id, update_data)


async def test_update_not_found(test_service, mock_crud):
    record_id = uuid4()
    update_data = TestUpdateSchema(name="Updated Name")
    mock_crud.update.return_value = None

    with pytest.raises(ServiceNotFoundError):
        await test_service.update(record_id, update_data)


async def test_delete_success(test_service, mock_crud):
    record_id = uuid4()
    mock_crud.delete.return_value = True

    result = await test_service.delete(record_id)

    assert result is True
    mock_crud.delete.assert_awaited_once_with(record_id)


@pytest.mark.asyncio
async def test_delete_not_found(test_service, mock_crud):
    record_id = uuid4()
    mock_crud.delete.return_value = False

    with pytest.raises(ServiceNotFoundError):
        await test_service.delete(record_id)


async def test_exists_true(test_service, mock_crud):
    mock_crud.exists.return_value = True

    result = await test_service.exists(name="Test")

    assert result is True
    mock_crud.exists.assert_awaited_once_with(name="Test")


async def test_get_all_success(test_service, mock_crud, sample_response):
    filter_data = TestFilterSchema(name="Test")
    mock_crud.get_all.return_value = [sample_response]

    results = await test_service.get_all(filter=filter_data, limit=10, offset=0)

    assert len(results) == 1
    assert results[0] == sample_response
    mock_crud.get_all.assert_awaited_once_with(
        filter=filter_data, limit=10, offset=0, order_by=None
    )


async def test_get_all_validation_error(test_service):
    with pytest.raises(ServiceValidationError):
        await test_service.get_all(limit=1001)

    with pytest.raises(ServiceValidationError):
        await test_service.get_all(offset=-1)
