# 🚀 SUAI-library-system

**Система библиотеки. Доступ к системе осуществляется через sso.guap**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![OAuth](https://img.shields.io/badge/OAuth_2.0-✓-yellow)](https://oauth.net/2/)
[![License](https://img.shields.io/badge/License-MIT-red)](https://opensource.org/licenses/MIT)

## Документация

### Примеры использования

#### Прямая аутентификация по логину/паролю

```bash
curl -X POST \
  '{$HOST}/api/v1/auth/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=user@guap.ru&password=secret123&grant_type=password'
```

**ответ**

```json
{
  "access_token": "string",
  "token_type": "string",
  "expires_in": 0,
  "refresh_token": "string",
  "scope": "string"
}
```

#### Обновление токена

```bash
curl -X POST \
  '{$HOST}/api/v1/auth/refresh-token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'refresh_token=eyJhbGciOi...'
```

**ответ**

```json
{
  "access_token": "string",
  "token_type": "string",
  "expires_in": 0,
  "refresh_token": "string",
  "scope": "string"
}
```

#### Получение информации о текущем пользователе

```bash
curl -X GET \
  '{$HOST}/api/v1/users/me' \
  -H 'Authorization: Bearer eyJhbGciOi...'
```

**Ответ**

```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "full_name": "string",
  "roles": []
}
```

#### Выход из системы

```bash
curl -X GET \
  '{$HOST}/api/v1/auth/logout' \
  -H 'Authorization: Bearer eyJhbGciOi...'
  ```

### basic configuration

```.env
# ===== Core Settings =====
APP_HOST=0.0.0.0
APP_PORT=8000
APP_RELOAD=True
ENVIRONMENT=local  # local/staging/prod

# ===== PostgreSQL =====
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=app_user
POSTGRES_PASSWORD=strong_password_123!
POSTGRES_DB=app_db


# ===== Redis =====
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password_456!
REDIS_DB=0
REDIS_SSL=False
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}

# ===== S3 Storage =====
# Локальный MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001

AWS_ACCESS_KEY_ID=${MINIO_ACCESS_KEY}
AWS_SECRET_ACCESS_KEY=${MINIO_SECRET_KEY}
S3_BUCKET_NAME=app-storage
S3_REGION_NAME=us-east-1

S3_ENDPOINT_URL=http://minio:9000

# ===== SSO Auth =====
CLIENT_ID=""
CLIENT_SECRET=""
DOMAIN=""

```
