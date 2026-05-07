import shutil
import uuid
import json
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from pathlib import Path
from app.models.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.testcase import TestCase, TCType, TCPriority, TCStatus, ChangeType
from app.models.project import Project
from app.models.qa_ruleset import QARuleSet
from app.core.config import settings
from app.services.document_parser import get_pdf_page_count
from app.services.tc_generator import generate_tc_from_pdf, generate_tc_from_tree, build_menu_tree

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    original_filename: str
    total_pages: int
    tc_level: int = 2
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


_VALID_TC_TYPES = {"positive", "negative", "boundary", "exception"}
_VALID_PRIORITIES = {"high", "medium", "low"}
_VALID_CHANGE_TYPES = {"new_feature", "modification", "bug_fix", "unknown"}


def _save_testcases(db, doc, result):
    for i, tc_data in enumerate(result["testcases"], start=1):
        tc_type_val = tc_data.get("tc_type", "positive")
        if tc_type_val not in _VALID_TC_TYPES:
            tc_type_val = "positive"

        priority_val = tc_data.get("priority", "medium")
        if priority_val not in _VALID_PRIORITIES:
            priority_val = "medium"

        change_type_val = tc_data.get("change_type", "unknown")
        if change_type_val not in _VALID_CHANGE_TYPES:
            change_type_val = "unknown"

        tc = TestCase(
            document_id=doc.id,
            tc_id=tc_data.get("tc_id", f"TC-{i:03d}"),
            category=tc_data.get("category", "기타"),
            title=tc_data.get("title", ""),
            objective=tc_data.get("objective", ""),
            preconditions=tc_data.get("preconditions", []),
            steps=tc_data.get("steps", []),
            expected_result=tc_data.get("expected_result", ""),
            tc_type=TCType(tc_type_val),
            priority=TCPriority(priority_val),
            change_type=change_type_val,
            status=TCStatus.DRAFT,
        )
        db.add(tc)


def _get_ruleset(db, document_id: int):
    """문서의 프로젝트에 연결된 룰셋 반환 (없으면 기본 룰셋)"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None
    project = db.query(Project).filter(Project.id == doc.project_id).first()
    if project and project.ruleset_id:
        return db.query(QARuleSet).filter(QARuleSet.id == project.ruleset_id).first()
    return db.query(QARuleSet).filter(QARuleSet.is_default == True).first()


def _analyze_document(document_id: int):
    """백그라운드에서 메뉴트리 생성"""
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
        doc.status = DocumentStatus.ANALYZING
        db.commit()

        ruleset = _get_ruleset(db, document_id)
        tree = build_menu_tree(doc.file_path, ruleset=ruleset)
        doc.menu_tree = json.dumps(tree, ensure_ascii=False)
        doc.status = DocumentStatus.ANALYZED
        doc.error_message = None
        db.commit()
        print(f"[메뉴트리 완료] doc_id={document_id}, 룰셋: {ruleset.name if ruleset else '없음'}")
    except Exception as e:
        print(f"[메뉴트리 실패] {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


def _process_document(document_id: int, tree_json: str = None):
    """백그라운드에서 TC 생성 처리 (기능 단위 재시도 포함)"""
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        tc_level = doc.tc_level or 3
        doc.status = DocumentStatus.TC_GENERATING
        db.commit()

        ruleset = _get_ruleset(db, document_id)
        if doc.menu_tree:
            tree = json.loads(doc.menu_tree)
            result = generate_tc_from_tree(tree, tc_level=tc_level, ruleset=ruleset)
        else:
            result = generate_tc_from_pdf(doc.file_path, tc_level=tc_level)

        if not result.get("testcases"):
            raise ValueError("생성된 TC가 없습니다. 문서 분석 결과를 확인하세요.")

        _save_testcases(db, doc, result)
        doc.status = DocumentStatus.TC_GENERATED
        doc.error_message = None
        db.commit()

        try:
            from app.services.tc_ingestion import ingest_testcases
            ingest_testcases(doc.id, result["testcases"])
        except Exception as e:
            print(f"[TC 이력 저장 실패] {e}")

    except Exception as e:
        print(f"[TC생성 실패] {e}")
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
    tc_level: int = Form(3),
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
        tc_level=max(1, min(5, tc_level)),
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 메뉴트리 먼저 생성 (사용자 검토 후 TC 생성)
    background_tasks.add_task(_analyze_document, doc.id)

    return doc


@router.get("/{document_id}/tree")
def get_tree(document_id: int, db: Session = Depends(get_db)):
    """메뉴트리 조회"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    if not doc.menu_tree:
        raise HTTPException(status_code=404, detail="메뉴트리가 아직 생성되지 않았습니다")
    return json.loads(doc.menu_tree)


@router.put("/{document_id}/tree")
def update_tree(document_id: int, tree: Any, db: Session = Depends(get_db)):
    """사용자가 수정한 메뉴트리 저장"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    doc.menu_tree = json.dumps(tree, ensure_ascii=False)
    db.commit()
    return {"message": "저장되었습니다"}


@router.get("/{document_id}/tree/export")
def export_tree_excel(document_id: int, db: Session = Depends(get_db)):
    """메뉴트리를 Excel로 내보내기"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not doc.menu_tree:
        raise HTTPException(status_code=404, detail="메뉴트리가 없습니다")

    tree_data = json.loads(doc.menu_tree)

    CHANGE_LABEL = {
        "new_feature": "신규", "modification": "수정",
        "bug_fix": "버그수정", "unknown": "일반",
    }
    DEPTH_STYLES = [
        {"fill": "1e40af", "font_color": "FFFFFF", "font_size": 12, "bold": True},   # 1단계
        {"fill": "3b82f6", "font_color": "FFFFFF", "font_size": 11, "bold": True},   # 2단계
        {"fill": "bfdbfe", "font_color": "1e3a8a", "font_size": 11, "bold": False},  # 3단계
        {"fill": "eff6ff", "font_color": "1e3a8a", "font_size": 10, "bold": False},  # 4단계
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "메뉴트리"

    thin = Side(style="thin", color="d1d5db")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ["계층", "기능명", "변경유형", "설명", "검증포인트"]
    col_widths = [8, 40, 10, 40, 50]
    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor="374151")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[1].height = 22

    row_num = 2

    def write_node(node, depth=0):
        nonlocal row_num
        style = DEPTH_STYLES[min(depth, len(DEPTH_STYLES) - 1)]
        indent = "  " * depth
        key_points = "\n".join(f"• {kp}" for kp in (node.get("key_points") or []))

        values = [
            depth + 1,
            indent + node.get("name", ""),
            CHANGE_LABEL.get(node.get("change_type", "unknown"), "일반"),
            node.get("description", ""),
            key_points,
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.fill = PatternFill("solid", fgColor=style["fill"])
            cell.font = Font(bold=style["bold"], color=style["font_color"], size=style["font_size"])
            cell.alignment = Alignment(vertical="center", wrap_text=True,
                                       horizontal="center" if col == 1 else "left")
            cell.border = border

        if key_points:
            ws.row_dimensions[row_num].height = max(18, len(key_points.splitlines()) * 16)
        else:
            ws.row_dimensions[row_num].height = 20

        row_num += 1
        for child in node.get("children") or []:
            write_node(child, depth + 1)

    for node in tree_data.get("tree", []):
        write_node(node)

    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"menutree_{document_id}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{document_id}/generate-tc")
def start_generate_tc(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """메뉴트리 검토 완료 후 TC 생성 시작"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    if doc.status == DocumentStatus.TC_GENERATING:
        raise HTTPException(status_code=409, detail="이미 TC 생성 중입니다")

    # 기존 TC 삭제 (재생성 시)
    db.query(TestCase).filter(TestCase.document_id == document_id).delete()
    db.commit()

    background_tasks.add_task(_process_document, document_id)
    return {"message": "TC 생성을 시작했습니다", "document_id": document_id}


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
        "tc_level": doc.tc_level or 3,
        "tc_count": tc_count,
        "error_message": doc.error_message,
    }
