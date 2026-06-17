from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.database import Base


class ChangeType(str, enum.Enum):
    NEW_FEATURE = "new_feature"    # 신규 기능 추가
    MODIFICATION = "modification"  # 기존 기능 수정
    BUG_FIX = "bug_fix"           # 버그 수정
    UNKNOWN = "unknown"            # 판단 불가 (일반 기획서)


class TCType(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    EXCEPTION = "exception"


class TCPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TCStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    MODIFIED = "modified"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"               # 검토 대기
    APPROVED = "approved"             # 승인
    NEEDS_REVISION = "needs_revision" # 수정 필요
    ADMIN_REQUIRED = "admin_required" # 관리자 확인 필요
    DELETED = "deleted"               # 삭제 예정


class TestCase(Base):
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    tc_id = Column(String(50), nullable=False)
    category = Column(String(200), nullable=False)
    title = Column(String(500), nullable=False)
    objective = Column(Text, nullable=False)
    spec_page = Column(String(50), nullable=True)  # 기획서 페이지 참조 (예: "5p", "8p-9p"). 추적성·근거 검증용.
    preconditions = Column(JSON, nullable=True)
    steps = Column(JSON, nullable=False)
    expected_result = Column(Text, nullable=False)
    tc_type = Column(Enum(TCType), default=TCType.POSITIVE)
    priority = Column(Enum(TCPriority), default=TCPriority.MEDIUM)
    status = Column(Enum(TCStatus), default=TCStatus.DRAFT)
    change_type = Column(String(50), default="unknown", nullable=True)
    review_status = Column(String(50), default="pending", nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="testcases")
