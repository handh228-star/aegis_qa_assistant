from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.database import Base


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"    # 메뉴트리 생성 중
    ANALYZED = "analyzed"      # 메뉴트리 생성 완료 → 사용자 검토 대기
    PARSING = "parsing"
    PARSED = "parsed"
    TC_GENERATING = "tc_generating"
    TC_RETRYING = "tc_retrying"
    TC_GENERATED = "tc_generated"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(300), nullable=False)
    original_filename = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    total_pages = Column(Integer, default=0)
    tc_level = Column(Integer, default=3)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    menu_tree = Column(Text, nullable=True)   # JSON 메뉴트리
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
    testcases = relationship("TestCase", back_populates="document", cascade="all, delete-orphan")
