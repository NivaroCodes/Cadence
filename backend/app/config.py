from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    GEMINI_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    GMAIL_CREDENTIALS_PATH: str
    GMAIL_TOKEN_PATH: str = "token.pickle"
    TELEGRAM_BOT_TOKEN: str

    APP_ENV: str = "dev"
    DEBUG: bool = False

    JWT_SECRET_KEY: str = "super_secret_fallback_dev_key_32_characters_long"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    PASSWORD_MIN_LENGTH: int = 8

    GOOGLE_CLIENT_ID: str = "dummy_google_client_id_for_dev_only"
    GOOGLE_CLIENT_SECRET: str = "dummy_google_client_secret_for_dev_only"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/oauth/google/callback"
    ENCRYPTION_KEY: str = "fallback_dev_key_32_chars_long"


settings = Settings()
