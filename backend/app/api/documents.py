import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
from pathlib import Path
from app.models.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.testcase import TestCase, TCType, TCPriority, TCStatus, ChangeType
from app.models.project import Project
from app.core.config import settings
from app.services.document_parser import get_pdf_page_count
from app.services.tc_generator import generate_tc_from_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    original_filename: str
    total_pages: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


def _save_testcases(db, doc, result):
    for i, tc_data in enumerate(result["testcases"], start=1):
        tc = TestCase(
            document_id=doc.id,
            tc_id=tc_data.get("tc_id", f"TC-{i:03d}"),
            category=tc_data.get("category", "기타"),
            title=tc_data.get("title", ""),
            objective=tc_data.get("objective", ""),
            preconditions=tc_data.get("preconditions", []),
            steps=tc_data.get("steps", []),
            expected_result=tc_data.get("expected_result", ""),
            tc_type=TCType(tc_data.get("tc_type", "positive")),
            priority=TCPriority(tc_data.get("priority", "medium")),
            change_type=ChangeType(tc_data.get("change_type", "unknown")),
            status=TCStatus.DRAFT,
        )
        db.add(tc)


def _process_document(document_id: int):
    """백그라운드에서 TC 생성 처리 (1회 자동 재시도)"""
    import time
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = DocumentStatus.TC_GENERATING
        db.commit()

        try:
            result = generate_tc_from_pdf(doc.file_path)
        except Exception as e:
            # 1회 재시도
            print(f"[TC생성 1차 실패] {e}\n→ 30초 후 재시도...")
            doc.status = DocumentStatus.TC_RETRYING
            doc.error_message = f"1차 실패 - 재시도 중: {str(e)[:200]}"
            db.commit()
            time.sleep(30)
            result = generate_tc_from_pdf(doc.file_path)  # 실패 시 여기서 예외 발생

        _save_testcases(db, doc, result)
        doc.status = DocumentStatus.TC_GENERATED
        doc.error_message = None
        db.commit()

        # 생성된 TC를 RAG 이력에 저장
        try:
            from app.services.tc_ingestion import ingest_testcases
            ingest_testcases(doc.id, result["testcases"])
        except Exception as e:
            print(f"[TC 이력 저장 실패] {e}")

    except Exception as e:
        print(f"[TC생성 최종 실패] {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/{project_id}/upload", response_model=DocumentResponse)
async def upload_document(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = settings.UPLOAD_DIR / unique_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    page_count = get_pdf_page_count(str(file_path))

    doc = Document(
        project_id=project_id,
        filename=unique_name,
        original_filename=file.filename,
        file_path=str(file_path),
        total_pages=page_count,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_process_document, doc.id)

    return doc


@router.get("/{project_id}/", response_model=List[DocumentResponse])
def list_documents(project_id: int, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.project_id == project_id).all()


@router.get("/status/{document_id}")
def get_document_status(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    tc_count = db.query(TestCase).filter(TestCase.document_id == document_id).count()
    return {
        "id": doc.id,
        "status": doc.status,
        "total_pages": doc.total_pages,
        "tc_count": tc_count,
        "error_message": doc.error_message,
    }
