from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RUTA_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Configuración de la API: variables de entorno y, en desarrollo, backend/.env."""

    model_config = SettingsConfigDict(
        env_file=RUTA_ENV,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_uri_intervenciones: str | None = None
    mongodb_db: str = "kmr"
    jwt_secret: str | None = None
    jwt_expira_minutos: int = 120
    frontend_url: str = "http://localhost:5173"
    brevo_api_key: str | None = None
    correo_remitente: str | None = None
    km_max_por_dia: int = 500


@lru_cache
def obtener_settings() -> Settings:
    return Settings()
