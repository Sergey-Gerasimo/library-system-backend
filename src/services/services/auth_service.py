from schemas import Token
from fastapi import HTTPException, status
import httpx
from config.keycloak import openid_config, keycloak_settings


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

    @staticmethod
    async def _get_response(
        client: httpx.AsyncClient, username: str, password: str
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
        return await client.post(
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

    @staticmethod
    async def direct_login(username: str, password: str) -> Token:
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
        try:
            async with httpx.AsyncClient() as client:
                response = AuthService._get_response(client, username, password)

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code, detail="Invalid credentials"
                    )

                token_data = response.json()

                return Token(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    expires_in=token_data["expires_in"],
                )

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def login_via_authtorization_code(code: str) -> Token:
        """Аутентификация через код авторизации.

        Использует OAuth2 Authorization Code flow.

        :param code: Код авторизации
        :type code: str
        :return: Токены доступа
        :rtype: Token
        :raises HTTPException: При ошибке аутентификации
        """
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
                raise HTTPException(
                    status_code=response.status_code, detail="Failed to obtain tokens"
                )

            tokens = response.json()
            return Token(
                access_token=tokens["access_token"],
                token_type="bearer",
                expires_in=tokens["expires_in"],
                refresh_token=tokens.get("refresh_token"),
            )

    @staticmethod
    async def refresh_token(refresh_token: str) -> Token:
        """Обновление токена доступа.

        :param refresh_token: Refresh token
        :type refresh_token: str
        :return: Новые токены доступа
        :rtype: Token
        :raises HTTPException: 401 при невалидном токене
        """
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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            tokens = response.json()
            return Token(
                access_token=tokens["access_token"],
                token_type="bearer",
                expires_in=tokens["expires_in"],
                refresh_token=tokens.get("refresh_token"),
            )

    @staticmethod
    async def verify_access_token(token: str) -> dict:
        """Валидация токена доступа.

        :param token: Токен доступа
        :type token: str
        :return: Информация о токене
        :rtype: dict
        :raises HTTPException: 401 при невалидном токене
        """
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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )
            return result

    @staticmethod
    async def logout(token: str):
        """Завершение сессии пользователя.

        :param token: Refresh token
        :type token: str
        """
        async with httpx.AsyncClient() as client:
            await client.post(
                openid_config["logout_endpoint"],
                data={
                    "client_id": keycloak_settings.CLIENT_ID,
                    "client_secret": keycloak_settings.CLIENT_SECRET,
                    "refresh_token": token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
