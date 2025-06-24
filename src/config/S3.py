from envparse import Env
from typing import Optional

env = Env()


class S3Settings:
    AWS_ACCESS_KEY_ID: str = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = env.str("AWS_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME: str = env.str("S3_BUCKET_NAME")
    S3_ENDPOINT_URL: str = env.str("S3_ENDPOINT_URL")
    S3_REGION_NAME: str = env.str("S3_REGION_NAME")


s3_settings = S3Settings()
