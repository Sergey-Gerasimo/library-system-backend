from services.auth_service import AuthService
from services.user_service import UserService


def get_auth_service() -> AuthService:
    return AuthService()


def get_user_service() -> UserService:
    return UserService()
