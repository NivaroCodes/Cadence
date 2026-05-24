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


settings = Settings()
