import asyncio
from contextlib import asynccontextmanager

from typing import Optional, BinaryIO, AsyncGenerator

from aiobotocore.session import get_session
from botocore.exceptions import ClientError, BotoCoreError

from config.S3 import s3_settings
from logging import Logger


class S3Client:
    def __init__(
        self,
        access_key: str = s3_settings.AWS_ACCESS_KEY_ID,
        secret_key: str = s3_settings.AWS_SECRET_ACCESS_KEY,
        endpoint_url: str = s3_settings.S3_ENDPOINT_URL,
        bucket_name: str = s3_settings.S3_BUCKET_NAME,
        region_name: str = s3_settings.S3_REGION_NAME,
        logger: Optional[Logger] = None,
    ):
        """
        Инциализация для S3Client
        :param bucket_name: Название бакета
        :param access_key: AWS Access Key ID
        :param secret_key: AWS Secret Access Key
        :param endpoint_url: URL эндпоинта S3
        :param region_name: Название региона
        :param logger: Логгер
        """

        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
            "region_name": region_name,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

        self.logger = logger

    @asynccontextmanager
    async def get_client(self):
        """
        Контекстный менеджер для получения S3 клиента.

        Пример использования:
        async with s3_client.get_client() as client:
            await client.list_objects(Bucket=bucket_name)
        """
        try:
            async with self.session.create_client("s3", **self.config) as client:
                yield client

        except BotoCoreError as e:
            if self.logger is not None:
                self.logger.error(f"S3 connection error: {str(e)}")
            raise

    async def upload_file(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Загрузка файла в S3.

        :param: file_obj - объект с файлом
        :param: s3_key - ключ для файла в S3
        :param: content_type - тип контента
        :param: metadata - метаданные для файла
        :reutrn: True если загрузка успешна
        """
        extra_args = {}

        if content_type is not None:
            extra_args["ContentType"] = content_type
        if metadata is not None:
            extra_args["Metadata"] = metadata

        try:
            async with self.get_client() as client:

                await client.put_object(
                    Body=file_obj, Bucket=self.bucket_name, Key=s3_key
                )
                return True

        except ClientError as e:
            if self.logger is not None:
                self.logger.error(f"Failed to upload file {s3_key}: {str(e)}")

            return False

    async def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Скачивание файла из S3.

        :param s3_key: Ключ (путь) в S3
        :return: Содержимое файла или None при ошибке
        """
        try:
            async with self.get_client() as client:
                response = await client.get_object(Bucket=self.bucket_name, Key=s3_key)
                async with response["Body"] as stream:
                    return await stream.read()

        except ClientError as e:
            if self.logger is not None:
                self.logger.error(f"Failed to download file {s3_key}: {str(e)}")

            return None

    async def delete_file(self, s3_key: str) -> bool:
        """
        Удаление файла из S3.

        :param: s3_key: Ключ (путь) в S3
        :return: True если удаление успешно
        """
        try:
            async with self.get_client() as client:
                await client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                return True

        except ClientError as e:
            if self.logger is not None:
                self.logger.error(f"Failed to delete file {s3_key}: {str(e)}")

            return False

    async def file_exist(self, s3_key: str) -> bool:
        """
        Проверка существования файла в S3.
        :param: s3_key: Ключ (путь) в S3
        :return: True если файл существует
        """

        try:
            async with self.get_client() as client:
                await client.head_object(Bucket=self.bucket_name, Key=s3_key)
                return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False

            if self.logger is not None:
                self.logger.error(f"Error checking file {s3_key}: {str(e)}")

            return False

    async def generate_presigned_url(
        self, s3_key: str, expires_in: int = 3600
    ) -> Optional[str]:
        """
        Генерирование предварительно подписанного URL для доступа к файлу в S3.
        :param: s3_key: Ключ (путь) в S3
        :param: expires_in: Время жизни URL в секундах
        :return: URL для доступа к файлу
        """
        try:
            async with self.get_client() as client:
                return await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expires_in,
                )

        except ClientError as e:
            if self.logger is not None:
                self.logger.error(
                    f"Failed to generate presigned URL for {s3_key}: {str(e)}"
                )
            return None
