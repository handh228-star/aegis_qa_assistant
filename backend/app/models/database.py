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
    from app.models import project, document, testcase, qa_ruleset
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    with engine.connect() as conn:
        # documents 테이블 신규 컬럼
        for stmt in [
            "ALTER TABLE documents ADD COLUMN tc_level INTEGER DEFAULT 2",
            "ALTER TABLE documents ADD COLUMN progress_current INTEGER DEFAULT 0",
            "ALTER TABLE documents ADD COLUMN progress_total INTEGER DEFAULT 0",
            "ALTER TABLE documents ADD COLUMN tc_started_at DATETIME",
            "ALTER TABLE documents ADD COLUMN state_inventory TEXT",
            "ALTER TABLE documents ADD COLUMN flow_tree TEXT",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass

        # testcases 테이블 신규 컬럼
        for col, definition in [
            ("review_status", "VARCHAR DEFAULT 'pending'"),
            ("review_note", "TEXT"),
            ("change_type", "VARCHAR DEFAULT 'unknown'"),
            ("spec_page", "VARCHAR(50)"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE testcases ADD COLUMN {col} {definition}"))
                conn.commit()
            except Exception:
                pass

        # 기존 행 NULL → 기본값, Enum name 대소문자 정규화
        conn.execute(text("UPDATE testcases SET review_status = 'pending' WHERE review_status IS NULL"))
        conn.execute(text("UPDATE testcases SET change_type = 'unknown' WHERE change_type IS NULL"))
        # SQLAlchemy Enum은 대문자 이름(PENDING)으로 저장하지만 migration DEFAULT는 소문자였음
        # → 대문자로 저장된 기존 데이터를 소문자로 정규화
        conn.execute(text("""
            UPDATE testcases SET review_status = CASE review_status
                WHEN 'PENDING'        THEN 'pending'
                WHEN 'APPROVED'       THEN 'approved'
                WHEN 'NEEDS_REVISION' THEN 'needs_revision'
                WHEN 'ADMIN_REQUIRED' THEN 'admin_required'
                WHEN 'DELETED'        THEN 'deleted'
                ELSE review_status
            END
            WHERE review_status IN ('PENDING','APPROVED','NEEDS_REVISION','ADMIN_REQUIRED','DELETED')
        """))
        conn.commit()

        # projects 테이블 신규 컬럼
        for stmt in [
            "ALTER TABLE projects ADD COLUMN ruleset_id INTEGER",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass

        # qa_rulesets 테이블 신규 컬럼
        for stmt in [
            "ALTER TABLE qa_rulesets ADD COLUMN flow_rules TEXT",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass

    # 기본 룰셋 시드 (없을 때만)
    from app.models.qa_ruleset import QARuleSet, DEFAULT_TREE_RULES, DEFAULT_TC_RULES, DEFAULT_FLOW_RULES
    seed_db = SessionLocal()
    try:
        system_rs = seed_db.query(QARuleSet).filter(QARuleSet.is_system == True).first()
        if not system_rs:
            default_rs = QARuleSet(
                name="웹 서비스 공통",
                description="입력란/버튼/팝업/표시영역 등 UI 요소별 체계적 커버리지 룰. 모든 웹 서비스에 기본 적용됩니다.",
                service_type="공통",
                tree_rules=DEFAULT_TREE_RULES,
                tc_rules=DEFAULT_TC_RULES,
                flow_rules=DEFAULT_FLOW_RULES,
                is_default=True,
                is_system=True,
            )
            seed_db.add(default_rs)
            seed_db.commit()
            print("[룰셋] 기본 룰셋 생성 완료")
        # 주의: 최초 생성 이후에는 절대 자동 덮어쓰지 않는다. DB에 저장된 룰셋(웹에서 사용자가
        # 직접 편집한 내용 포함)이 정본이다 — 코드의 DEFAULT_*는 "신규 설치 시 초기값"일 뿐,
        # 매 재시작마다 DB를 코드 값으로 되돌리면 웹에서 편집한 내용이 소리없이 사라진다.
    finally:
        seed_db.close()
