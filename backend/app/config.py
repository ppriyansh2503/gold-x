from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://goldx:goldx_dev@localhost:5432/goldx"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://goldx:goldx_dev@localhost:5432/goldx"
    MCX_BHAVCOPY_URL: str = "https://www.mcxindia.com/backpage.aspx/GetDatewiseBhavCopy"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings() -> Settings:
    return Settings()
