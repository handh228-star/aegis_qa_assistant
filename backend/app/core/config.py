from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/aegis_qa.db"

    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    REPORT_DIR: Path = BASE_DIR / "reports"
    VECTOR_DB_DIR: Path = BASE_DIR / "vectordb"
    MANUAL_DIR: Path = BASE_DIR / "manual_xperp"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-2"

    class Config:
        env_file = BASE_DIR / ".env"


settings = Settings()
