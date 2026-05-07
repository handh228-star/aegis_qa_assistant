from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # 단계별 모델 분리
    GEMINI_MODEL_EXTRACT: str = "gemini-2.5-flash"   # PDF 기능 추출
    GEMINI_MODEL_TC: str = "gemini-2.5-pro"           # TC 생성
    GEMINI_MODEL_VISION: str = "gemini-2.5-flash"     # 크롤러 화면 분석

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/aegis_qa.db"

    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    REPORT_DIR: Path = BASE_DIR / "reports"
    VECTOR_DB_DIR: Path = BASE_DIR / "vectordb"
    MANUAL_DIR: Path = BASE_DIR / "manual_xperp"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-2"

    # XpERP 웹 크롤러 설정 (.env에서 오버라이드)
    XPERP_BASE_URL: str = ""
    XPERP_USER_ID: str = ""
    XPERP_PASSWORD: str = ""

    class Config:
        env_file = BASE_DIR / ".env"


settings = Settings()
