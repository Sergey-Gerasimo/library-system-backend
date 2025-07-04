from schemas import Token
from fastapi import HTTPException, status
import httpx
from config.keycloak import openid_config, keycloak_settings
from loguru import logger
from datetime import datetime


class AuthService:
    """Сервис аутентификации и авторизации.

    Реализует логику работы с OAuth2/OpenID Connect через Keycloak,
    предоставляя основные методы для аутентификации пользователей
    и управления токенами.

    Типы:
        Token: Pydantic схема для работы с токенами доступа

    Зависимости:
        httpx: Для HTTP-запросов к Keycloak
        fastapi.HTTPException: Для обработки ошибок API
        config.keycloak: Конфигурация подключения к Keycloak

    Пример использования:
        token = await AuthService.direct_login(username="user", password="pass")
        user_info = await AuthService.verify_access_token(token.access_token)
    """

    def __init__(self):
        self._logger = logger.bind(service="AuthService", domain="authtorization")

    async def _get_response(
        self, client: httpx.AsyncClient, username: str, password: str
    ) -> httpx.request:
        """Внутренний метод для получения токена по учетным данным.

        :param client: Асинхронный HTTP клиент
        :type client: httpx.AsyncClient
        :param username: Логин пользователя
        :type username: str
        :param password: Пароль пользователя
        :type password: str
        :return: Ответ от сервера авторизации
        :rtype: httpx.request
        """
        log_context = {
            "operation": "token_request",
            "client_id": keycloak_settings.CLIENT_ID,
            "grant_type": "password",
            "username": username[:3] + "***",  # Частичное логирование имени
        }

        self._logger.debug("Requesting token from Keycloak", **log_context)

        try:
            response = await client.post(
                openid_config["token_endpoint"],
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "client_id": keycloak_settings.CLIENT_ID,
                    "client_secret": keycloak_settings.CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            self._logger.debug(
                "Received response from Keycloak",
                **log_context,
                status_code=response.status_code,
                response_time=response.elapsed.total_seconds()
            )
            return response

        except Exception as e:
            self._logger.error(
                "Keycloak request failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def direct_login(self, username: str, password: str) -> Token:
        """Аутентификация пользователя по логину и паролю.

        Использует OAuth2 Resource Owner Password Credentials flow.

        :param username: Логин пользователя
        :type username: str
        :param password: Пароль пользователя
        :type password: str
        :return: Токены доступа
        :rtype: Token
        :raises HTTPException: 400 при ошибке запроса
        :raises HTTPException: При ошибке аутентификации (статус от Keycloak)
        """
        log_context = {
            "operation": "direct_login",
            "username": username[:3] + "***",
            "client_id": keycloak_settings.CLIENT_ID,
        }

        self._logger.info("Starting direct login", **log_context)

        try:
            async with httpx.AsyncClient() as client:
                response = AuthService._get_response(client, username, password)

                if response.status_code != 200:
                    error_detail = response.json().get(
                        "error_description", "Invalid credentials"
                    )
                    self._logger.warning(
                        "Login failed",
                        **log_context,
                        status_code=response.status_code,
                        error_detail=error_detail
                    )
                    raise HTTPException(
                        status_code=response.status_code, detail="Invalid credentials"
                    )

                token_data = response.json()
                self._logger.success(
                    "Login successful",
                    **log_context,
                    token_expires_in=token_data["expires_in"]
                )

                return Token(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    expires_in=token_data["expires_in"],
                )

        except HTTPException:
            raise
        except Exception as e:
            self._logger.error(
                "Unexpected login error",
                **log_context,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(status_code=400, detail="Authentication failed")

    async def login_via_authtorization_code(self, code: str) -> Token:
        """Аутентификация через код авторизации.

        Использует OAuth2 Authorization Code flow.

        :param code: Код авторизации
        :type code: str
        :return: Токены доступа
        :rtype: Token
        :raises HTTPException: При ошибке аутентификации
        """
        log_context = {
            "operation": "auth_code_login",
            "client_id": keycloak_settings.CLIENT_ID,
            "code": code[:6] + "***",  # Частичное логирование кода
        }

        self._logger.info("Starting authorization code login", **log_context)

        try:
            async with httpx.AsyncClient() as client:
                token_data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": keycloak_settings.CLIENT_ID,
                    "client_secret": keycloak_settings.CLIENT_SECRET,
                    "redirect_uri": keycloak_settings.REDIRECT_URL,
                }

                response = await client.post(
                    openid_config["token_endpoint"],
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_detail = response.json().get("error", "Unknown error")
                    self._logger.warning(
                        "Authorization code login failed",
                        **log_context,
                        status_code=response.status_code,
                        error=error_detail
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to obtain tokens",
                    )

                tokens = response.json()
                self._logger.success(
                    "Authorization code login successful",
                    **log_context,
                    expires_in=tokens["expires_in"]
                )

                return Token(
                    access_token=tokens["access_token"],
                    token_type="bearer",
                    expires_in=tokens["expires_in"],
                    refresh_token=tokens.get("refresh_token"),
                )

        except Exception as e:
            self._logger.error(
                "Authorization code login error",
                **log_context,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def refresh_token(self, refresh_token: str) -> Token:
        """Обновление токена доступа.

        :param refresh_token: Refresh token
        :type refresh_token: str
        :return: Новые токены доступа
        :rtype: Token
        :raises HTTPException: 401 при невалидном токене
        """
        log_context = {
            "operation": "refresh_token",
            "client_id": keycloak_settings.CLIENT_ID,
            "token_fragment": refresh_token[:6]
            + "***",  # Безопасное логирование токена
        }

        self._logger.info("Refreshing token", **log_context)

        try:
            async with httpx.AsyncClient() as client:
                token_data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": keycloak_settings.CLIENT_ID,
                    "client_secret": keycloak_settings.CLIENT_SECRET,
                }

                response = await client.post(
                    openid_config["token_endpoint"],
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    self._logger.warning(
                        "Token refresh failed",
                        **log_context,
                        status_code=response.status_code
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid refresh token",
                    )

                tokens = response.json()

                self._logger.success(
                    "Token refreshed", **log_context, expires_in=tokens["expires_in"]
                )
                return Token(
                    access_token=tokens["access_token"],
                    token_type="bearer",
                    expires_in=tokens["expires_in"],
                    refresh_token=tokens.get("refresh_token"),
                )

        except HTTPException:
            raise
        except Exception as e:
            self._logger.error(
                "Token refresh error",
                **log_context,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def verify_access_token(self, token: str) -> dict:
        """Валидация токена доступа.

        :param token: Токен доступа
        :type token: str
        :return: Информация о токене
        :rtype: dict
        :raises HTTPException: 401 при невалидном токене
        """

        log_context = {
            "operation": "verify_token",
            "client_id": keycloak_settings.CLIENT_ID,
            "token_fragment": token[:6] + "***",
        }

        self._logger.debug("Verifying access token", **log_context)

        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "token": token,
                    "client_id": keycloak_settings.CLIENT_ID,
                    "client_secret": keycloak_settings.CLIENT_SECRET,
                }
                response = await client.post(
                    openid_config["introspection_endpoint"],
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                result = response.json()

                if not result.get("active", False):
                    logger.warning(
                        "Invalid token detected",
                        **log_context,
                        reason=result.get("error", "Unknown")
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired token",
                    )

                self._logger.debug(
                    "Token verified successfully",
                    **log_context,
                    token_scope=result.get("scope"),
                    expires_in=result.get("exp", 0) - int(datetime.now())
                )

                return result

        except HTTPException:
            raise
        except Exception as e:
            self._logger.error(
                "Token verification failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def logout(self, token: str):
        """Завершение сессии пользователя.

        :param token: Refresh token
        :type token: str
        """
        log_context = {
            "operation": "logout",
            "client_id": keycloak_settings.CLIENT_ID,
            "token_fragment": token[:6] + "***",
        }

        self._logger.info("Logging out user", **log_context)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    openid_config["logout_endpoint"],
                    data={
                        "client_id": keycloak_settings.CLIENT_ID,
                        "client_secret": keycloak_settings.CLIENT_SECRET,
                        "refresh_token": token,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 204:
                    self._logger.warning(
                        "Logout may have failed",
                        **log_context,
                        status_code=response.status_code
                    )
                else:
                    self._logger.success("User logged out", **log_context)

        except Exception as e:
            self._logger.error(
                "Logout error", **log_context, error=str(e), error_type=type(e).__name__
            )
            raise
