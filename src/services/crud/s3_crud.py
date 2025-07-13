from contextlib import asynccontextmanager
import aiobotocore
from aiobotocore.client import AioBaseClient
from typing import Optional, Union, BinaryIO, AsyncIterator, Any, Protocol
import aiobotocore.client
import aiobotocore.session
from schemas import File

from services.exceptions import handle_storage_errors


class IStorageRUD(Protocol):
    """Протокол для типизации хранилищ файлов с CRUD операциями.

    Определяет стандартный интерфейс для работы с файловыми хранилищами.
    Может использоваться для создания альтернативных реализаций (например, для локального
    хранилища или других облачных провайдеров).
    """

    async def download_file(self, file_key: str, **kwargs) -> File:
        """Скачивает файл из хранилища."""
        ...

    async def get_file_metadata(self, file_key: str, **kwargs) -> dict:
        """Получает метаданные файла."""
        ...

    async def delete_file(self, file_key: str) -> bool:
        """Удаляет файл из хранилища."""
        ...

    async def list_files(self, prefix: Optional[str] = None) -> list:
        """Возвращает список файлов."""
        ...

    async def generate_presigned_url(
        self,
        file_key: str,
        expires_in: int = 3600,
        download_filename: Optional[str] = None,
    ) -> str:
        """Генерирует временную ссылку для доступа к файлу."""
        ...

    async def upload_file(
        self,
        file_key: str,
        file_data: Union[bytes, BinaryIO, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs: Any,
    ) -> bool:
        """Загружает файл в хранилище."""
        ...

    async def update_file_metadata(
        self,
        file_key: str,
        metadata: dict,
        content_type: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Обновляет метаданные файла."""
        ...


# NOTE: Возможно надо сделать рефаторинг(Перейти от параметров к структурам)


class S3CRUD:
    """Асинхронный клиент для работы с Amazon S3 (Simple Storage Service).

    Предоставляет полный набор CRUD операций для управления файлами в S3-совместимом хранилище:
    - Загрузка и скачивание файлов
    - Управление метаданными
    - Генерация временных ссылок
    - Удаление и перечисление файлов

    Класс реализует протокол IStorageRUD и поддерживает работу как с Amazon S3, так и с S3-совместимыми
    хранилищами (например, MinIO, Yandex Object Storage и др.).

    Особенности:
        - Асинхронная работа на основе aiobotocore
        - Поддержка как бинарных данных, так и файловых потоков
        - Гибкое управление метаданными и Content-Type
        - Генерация presigned URL для временного доступа
        - Полная типизация методов
        - Контекстные менеджеры для управления подключениями
        - Единая обработка ошибок через декоратор @handle_s3_errors

    Обрабатываемые ошибки:
        - S3NotFoundError: файл или бакет не найдены
        - S3AccessDeniedError: недостаточно прав для операции
        - S3InvalidStateError: недопустимое состояние объекта
        - S3ConnectionError: проблемы с подключением к хранилищу
        - S3OperationError: прочие ошибки операций с S3

    Пример использования:
        s3 = S3CRUD(
            aws_access_key_id="YOUR_ACCESS_KEY",
            aws_secret_access_key="YOUR_SECRET_KEY",
            region_name="us-east-1",
            bucket_name="my-bucket",
            endpoint_url="https://s3.amazonaws.com"  # опционально для S3-совместимых хранилищ
        )

        # Загрузка файла
        await s3.upload_file(
            file_key="documents/report.pdf",
            file_data=b"PDF content...",
            content_type="application/pdf",
            metadata={"author": "john.doe"}
        )

        # Скачивание файла
        data = await s3.download_file("documents/report.pdf")

        # Генерация временной ссылки
        url = await s3.generate_presigned_url(
            "documents/report.pdf",
            expires_in=3600,
            download_filename="annual_report.pdf"
        )
    """

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
    ):
        """Инициализирует клиент для работы с S3 хранилищем.

        :param aws_access_key_id: AWS Access Key ID
        :type aws_access_key_id: str
        :param aws_secret_access_key: AWS Secret Access Key
        :type aws_secret_access_key: str
        :param region_name: Название региона S3 (например, "us-east-1")
        :type region_name: str
        :param bucket_name: Имя S3 бакета
        :type bucket_name: str
        :param endpoint_url: Кастомный endpoint URL для S3-совместимых хранилищ, defaults to None
        :type endpoint_url: Optional[str]
        """

        self._bucket_name = bucket_name
        self._config = {
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "region_name": region_name,
            "endpoint_url": endpoint_url,
        }

        self.session = aiobotocore.session.get_session()

    @property
    def bucket_name(self) -> str:
        """Возвращает имя S3 бакета.

        :return: Имя бакета
        :rtype: str
        """

        return self._bucket_name

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[AioBaseClient]:
        """Контекстный менеджер для получения клиента S3.

        Создает и управляет жизненным циклом асинхронного клиента S3.
        Автоматически закрывает соединение при выходе из контекста.
        Ошибки обрабатываются декоратором @handle_s3_errors.

        :yield: Асинхронный клиент S3
        :rtype: AsyncIterator[AioBaseClient]
        """

        async with self.session.create_client("s3", **self._config) as client:
            yield client

    @handle_storage_errors()
    async def upload_file(
        self,
        file_key: str,
        file_data: Union[bytes, BinaryIO, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Загружает файл в S3 хранилище.

        Поддерживает загрузку как бинарных данных (bytes), так и файловых объектов.
        Позволяет указать Content-Type и пользовательские метаданные.

        :param file_key: Ключ файла в S3 (путь + имя файла)
        :type file_key: str
        :param file_data: Данные для загрузки (bytes или файловый объект)
        :type file_data: Union[bytes, BinaryIO, BinaryIO]
        :param content_type: MIME-тип содержимого, defaults to None
        :type content_type: Optional[str]
        :param metadata: Пользовательские метаданные, defaults to None
        :type metadata: Optional[dict]
        :return: True при успешной загрузке
        :rtype: bool
        :raises S3NotFoundError: Если бакет не существует
        :raises S3AccessDeniedError: При отсутствии прав на запись
        :raises S3InvalidStateError: При проблемах с состоянием объекта
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках загрузки
        """
        async with self._get_client() as client:
            put_params = {
                "Bucket": self._bucket_name,
                "Key": file_key,
                "Body": file_data,
            }

            if content_type:
                put_params["ContentType"] = content_type

            if metadata:
                put_params["Metadata"] = metadata

            await client.put_object(**put_params)

            return True

    @handle_storage_errors()
    async def download_file(
        self,
        file_key: str,
    ) -> File:
        """Скачивает файл из S3 хранилища.

        Возвращает содержимое файла в виде байтов. Для больших файлов
        рекомендуется использовать потоковую загрузку.

        :param file_key: Ключ файла в S3
        :type file_key: str
        :return: файл
        :rtype: File
        :raises S3NotFoundError: Если файл не найден в бакете
        :raises S3AccessDeniedError: При отсутствии прав на чтение
        :raises S3InvalidStateError: Если объект в Glacier и требует восстановления
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках скачивания
        """
        async with self._get_client() as client:
            try:
                response = await client.get_object(
                    Bucket=self._bucket_name, Key=file_key
                )

                content_type = response.get("ContentType")
                content_length = response.get("ContentLength", 0)
                metadata = response.get("Metadata", {})

                async with response["Body"] as stream:
                    data = await stream.read()

                    return File(
                        filename=file_key.split("/")[-1],
                        content_type=content_type,
                        headers={
                            **metadata,
                            "Content-Length": str(content_length),
                            "Content-Type": content_type,
                        },
                        content=data,
                        size=content_length,
                    )

            except client.exceptions.NoSuchKey:
                raise FileNotFoundError(
                    f"File {file_key} not found in bucket {self.bucket_name}"
                )

    @handle_storage_errors()
    async def get_file_metadata(self, file_key: str) -> dict:
        """Получает метаданные файла из S3.

        Возвращает словарь с основной информацией о файле:
        - content_type: MIME-тип содержимого
        - metadata: Пользовательские метаданные
        - last_modified: Время последнего изменения (datetime)
        - size: Размер файла в байтах

        :param file_key: Ключ файла в S3
        :type file_key: str
        :return: Словарь с метаданными
        :rtype: dict
        :raises S3NotFoundError: Если файл не найден
        :raises S3AccessDeniedError: При отсутствии прав на чтение метаданных
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках получения метаданных
        """

        async with self._get_client() as client:
            try:
                response = await client.head_object(
                    Bucket=self._bucket_name, Key=file_key
                )
                return {
                    "content_type": response.get("ContentType"),
                    "metadata": response.get("Metadata", {}),
                    "last_modified": response.get("LastModified"),
                    "size": response.get("ContentLength"),
                }
            except client.exceptions.NoSuchKey:
                raise FileNotFoundError(
                    f"File {file_key} not found in bucket {self.bucket_name}"
                )

    @handle_storage_errors()
    async def update_file_metadata(
        self, file_key: str, metadata: dict, content_type: Optional[str] = None
    ) -> bool:
        """Обновляет метаданные файла в S3.

        Важно: В S3 метаданные нельзя обновить отдельно от объекта.
        Этот метод создает копию объекта с новыми метаданными.

        :param file_key: Ключ файла в S3
        :type file_key: str
        :param metadata: Новые пользовательские метаданные
        :type metadata: dict
        :param content_type: Новый MIME-тип, defaults to None
        :type content_type: Optional[str]
        :return: True при успешном обновлении
        :rtype: bool
        :raises S3NotFoundError: Если файл не найден
        :raises S3AccessDeniedError: При отсутствии прав на обновление
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках обновления
        """

        async with self._get_client() as client:
            copy_params = {
                "Bucket": self._bucket_name,
                "Key": file_key,
                "CopySource": f"{self.bucket_name}/{file_key}",
                "Metadata": metadata,
                "MetadataDirective": "REPLACE",
            }

            if content_type:
                copy_params["ContentType"] = content_type

            await client.copy_object(**copy_params)
            return True

    @handle_storage_errors()
    async def delete_file(self, file_key: str) -> bool:
        """Удаляет файл из S3 хранилища.

        :param file_key: Ключ удаляемого файла
        :type file_key: str
        :return: True при успешном удалении
        :rtype: bool
        :raises S3NotFoundError: Если файл не найден
        :raises S3AccessDeniedError: При отсутствии прав на удаление
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках удаления
        """

        async with self._get_client() as client:
            await client.delete_object(Bucket=self._bucket_name, Key=file_key)
            return True

    @handle_storage_errors()
    async def list_files(self, prefix: Optional[str] = None) -> list:
        """Возвращает список файлов в бакете.

        Поддерживает фильтрацию по префиксу (виртуальные папки).

        :param prefix: Префикс для фильтрации (например, "documents/"), defaults to None
        :type prefix: Optional[str]
        :return: Список ключей файлов
        :rtype: list
        :raises S3NotFoundError: Если бакет не существует
        :raises S3AccessDeniedError: При отсутствии прав на чтение списка
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках запроса
        """

        async with self._get_client() as client:
            list_params = {"Bucket": self._bucket_name}
            if prefix:
                list_params["Prefix"] = prefix

            response = await client.list_objects_v2(**list_params)
            return [obj["Key"] for obj in response.get("Contents", [])]

    @handle_storage_errors()
    async def generate_presigned_url(
        self,
        file_key: str,
        expires_in: int = 3600,
        download_filename: Optional[str] = None,
    ) -> str:
        """Генерирует presigned URL для временного доступа к файлу.

        Presigned URL позволяет предоставлять доступ к объектам S3 без необходимости
        настраивать права доступа для каждого пользователя.

        :param file_key: Ключ файла в S3
        :type file_key: str
        :param expires_in: Время жизни ссылки в секундах, defaults to 3600 (1 час)
        :type expires_in: int
        :param download_filename: Имя файла для скачивания, defaults to None
        :type download_filename: Optional[str]
        :return: Сгенерированная URL-ссылка
        :rtype: str
        :raises S3NotFoundError: Если файл не найден
        :raises S3AccessDeniedError: При отсутствии прав на генерацию ссылки
        :raises S3ConnectionError: При проблемах с подключением
        :raises S3OperationError: При прочих ошибках генерации
        """

        async with self._get_client() as client:
            params = {"Bucket": self._bucket_name, "Key": file_key}
            if download_filename:
                params["ResponseContentDisposition"] = (
                    f"attachment; filename={download_filename}"
                )

            return await client.generate_presigned_url(
                "get_object", Params=params, ExpiresIn=expires_in
            )
