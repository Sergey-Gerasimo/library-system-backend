from envparse import Env

env = Env()


class KeycloakSettings:
    """Настройки Keycloak OAuth2"""

    CLIENT_ID: str = env.str("CLIENT_ID")
    CLIENT_SECRET: str = env.str("CLIENT_SECRET")
    REDIRECT_URL: str = env.str("HOST") + "/auth/callback"
    SCOPE: str = env.str("SCOPE", default="openid profile email")


keycloak_settings = KeycloakSettings()

openid_config = {
    "issuer": "https://sso.guap.ru:8443/realms/master",
    "token_endpoint": "https://sso.guap.ru:8443/realms/master/protocol/openid-connect/token",
    "jwks_uri": "https://sso.guap.ru:8443/realms/master/protocol/openid-connect/certs",
    "userinfo_endpoint": "https://sso.guap.ru:8443/realms/master/protocol/openid-connect/userinfo",
    "introspection_endpoint": "https://sso.guap.ru:8443/realms/master/protocol/openid-connect/token/introspect",
    "authorization_endpoint": "https://sso.guap.ru:8443/realms/master/protocol/openid-connect/auth",
    "logout_endpoint": "https://sso.guap.ru:8443/realms/master/protocol/openid-connect/logout",
}

client_config = {
    "client_id": keycloak_settings.CLIENT_ID,
    "client_secret": keycloak_settings.CLIENT_SECRET,
    "scope": keycloak_settings.SCOPE,
}
