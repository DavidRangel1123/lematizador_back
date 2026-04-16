from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Microservicio IJCF"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str

    # JWT Configuration
    JWT_ALGORITHM: str = "RS256"
    JWT_ISSUER: str
    JWT_AUD: str
    JWT_PUBLIC_KEY_PATH: str = "keys/public_key.pem"

    # Database configuration (opcional, si las necesitas en tu código)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_SERVER: Optional[str] = "db"
    POSTGRES_PORT: Optional[str] = "5432"

    # SQLAlchemy URL (opcional)
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # JWT Secret (opcional, para otros usos)
    JWT_SECRET_KEY: Optional[str] = None

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
