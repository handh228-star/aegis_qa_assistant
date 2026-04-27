from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import project, document, testcase
    Base.metadata.create_all(bind=engine)
    # 기존 DB에 신규 컬럼 추가 (SQLite 개발용 마이그레이션)
    from sqlalchemy import text
    with engine.connect() as conn:
        for col, definition in [
            ("review_status", "VARCHAR DEFAULT 'pending'"),
            ("review_note", "TEXT"),
            ("change_type", "VARCHAR DEFAULT 'unknown'"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE testcases ADD COLUMN {col} {definition}"))
                conn.commit()
            except Exception:
                pass

        # 기존 행의 NULL 값 기본값으로 채우기
        conn.execute(text("UPDATE testcases SET review_status = 'pending' WHERE review_status IS NULL"))
        conn.execute(text("UPDATE testcases SET change_type = 'unknown' WHERE change_type IS NULL"))
        conn.commit()
