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
# FastAPI
APP_HOST=0.0.0.0
APP_PORT=8000
APP_RELOAD=True
MAIN_API_BASE_URL=""

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password_123
REDIS_SSL=False

#Connecting to sso.guap
CLIENT_ID=""
CLIENT_SECRET=""
DOMEN=""

```
