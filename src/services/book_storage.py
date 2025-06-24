import mimetypes

from services.s3_service import S3Client
from typing import Literal, BinaryIO, Optional

from uuid import uuid4
from datetime import timedelta
from redis import Redis

from fastapi import HTTPException


class BookStorage(S3Client):
    def __init__(self, redis: Redis, **s3_kwargs):
        """
        Инициализация сервиса хранения книг.

        :param:redis - экземпляр Redis
        :param:s3_kwargs - параметры для S3Client
        """
        self.redis = redis
        super().__init__(**s3_kwargs)

    async def upload_book_file(
        self,
        book_id: str,
        file_type: Literal["pdf", "cover"],
        file_obj: BinaryIO,
        original_filename: str,
    ) -> str:
        """
        Загрузка файла книги в S3 с автоматическим определением MIME-типа.
        :param: book_id - id книги
        :param: file_type - тип файла (pdf, cover)
        :param: file_obj - объект файла
        :param: original_filename - имя файла
        :return: s3_key - URL файла в S3
        """

        ext = original_filename.split(".")[-1].lower()
        s3_key = f"books/{book_id}/{file_type}.{ext}"
        mime_type = mimetypes.guess_type(original_filename)[0]

        if not await self.upload_file(file_obj, s3_key, mime_type):
            raise HTTPException(500, "Failed to upload book file")

        return s3_key

    async def generate_one_time_url(
        self,
        s3_key: str,
        expires_in: int = 86400,
    ) -> str:
        """
        Генерирование одноразовой ссылки дял скачивания.

        :param:s3_key - ключ файла в S3
        :param:expires_in - время жизни ссылки в секундах
        """
        token = f"dl_{uuid4().hex}"
        await self.redis.setex(token, timedelta(seconds=expires_in), s3_key)
        return f"/download?token={token}"

    async def download_with_token(
        self,
        token: str,
        url_expire: int = 300,
    ) -> str:
        """
        Получение временной S3 ссылки по одноразовому токену.

        :param: token - одноразовый токен
        :param: url_expire - время жизни ссылки в секундах
        :return: URL файла в S3
        """

        lua_script = """
        local token = KEYS[1]
        local s3_key = redis.call('GET', token)
        if s3_key then
            redis.call('DEL', token)
            return s3_key
        end
        return nil
        """

        if s3_key := await self.redis.eval(lua_script, 1, token):
            return await self.generate_presigned_url(s3_key, url_expire)

        raise HTTPException(403, "Invalid or expired token")

    async def get_book_files(
        self,
        book_id: str,
    ) -> list:
        """
        Получение списка файлов книги.

        :param: book_id - id книги
        :return: список файлов книги
        """

        prefix = f"books/{book_id}/"
        async with self._get_client() as client:
            result = await client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )
            return [obj["Key"] for obj in result.get("Contents", [])]
