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
from app.services.tc_generator import generate_tc_from_pdf, generate_tc_from_tree, build_menu_tree, build_flow_tree
from app.services.flow_tree_report import render_flow_tree_excel, flow_tree_stats

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    original_filename: str
    total_pages: int
    tc_level: int = 3
    status: str
    progress_current: int = 0
    progress_total: int = 0
    tc_started_at: Optional[datetime] = None
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
            spec_page=(str(tc_data.get("spec_page") or "").strip() or None),
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
        tree = build_menu_tree(doc.file_path, ruleset=ruleset, original_filename=doc.original_filename)
        doc.menu_tree = json.dumps(tree, ensure_ascii=False)

        # 상태 매트릭스(권한·코드 상태·이력 등 도메인 상태 차원) 추출 — 실패해도 진행
        from app.services.tc_generator import extract_state_inventory
        try:
            state_inv = extract_state_inventory(
                doc.file_path,
                original_filename=doc.original_filename,
                ruleset=ruleset,
            )
            doc.state_inventory = json.dumps(state_inv, ensure_ascii=False)
            n_dims = len(state_inv.get("state_dimensions", []))
            print(f"[상태 매트릭스] {n_dims}개 차원 도출")
        except Exception as e:
            print(f"[상태 매트릭스 추출 실패 — 무시] {e}")
            doc.state_inventory = json.dumps({"state_dimensions": []}, ensure_ascii=False)

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
        doc.progress_current = 0
        doc.progress_total = 0
        doc.tc_started_at = datetime.utcnow()
        db.commit()

        def update_progress(current, total, tc_count):
            try:
                _db = SessionLocal()
                _doc = _db.query(Document).filter(Document.id == document_id).first()
                if _doc:
                    _doc.progress_current = current
                    _doc.progress_total = total
                    _db.commit()
                _db.close()
            except Exception:
                pass

        ruleset = _get_ruleset(db, document_id)
        state_inventory = None
        if doc.state_inventory:
            try:
                state_inventory = json.loads(doc.state_inventory)
            except Exception:
                state_inventory = None

        if doc.menu_tree:
            tree = json.loads(doc.menu_tree)
            result = generate_tc_from_tree(
                tree, tc_level=tc_level, ruleset=ruleset,
                on_progress=update_progress, state_inventory=state_inventory,
            )
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


@router.get("/{document_id}/state-inventory")
def get_state_inventory(document_id: int, db: Session = Depends(get_db)):
    """상태 매트릭스(권한·코드 상태·이력 등 도메인 상태 차원) 조회"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    if not doc.state_inventory:
        return {"state_dimensions": []}
    try:
        return json.loads(doc.state_inventory)
    except Exception:
        return {"state_dimensions": []}


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

    # 리프 노드 ↔ TC 매핑 (category = 리프 전체 경로). 삭제 예정 TC 제외.
    tcs = (
        db.query(TestCase)
        .filter(TestCase.document_id == document_id)
        .filter((TestCase.review_status != "deleted") | (TestCase.review_status.is_(None)))
        .order_by(TestCase.id)
        .all()
    )
    tc_by_path = {}
    for tc in tcs:
        tc_by_path.setdefault(tc.category, []).append(tc)

    CHANGE_LABEL = {
        "new_feature": "신규", "modification": "수정",
        "bug_fix": "버그수정", "unknown": "일반",
    }
    TC_TYPE_LABEL = {"positive": "정상", "negative": "비정상",
                     "boundary": "경계값", "exception": "예외"}
    PRIORITY_LABEL = {"high": "높음", "medium": "중간", "low": "낮음"}
    PRIORITY_COLOR = {"high": "dc2626", "medium": "d97706", "low": "16a34a"}
    TC_ROW_FILL = "f9fafb"

    def _enum_val(v):
        return getattr(v, "value", v)
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

    headers = ["계층", "기능명", "변경유형", "기획서페이지", "설명", "검증포인트"]
    col_widths = [8, 40, 10, 12, 40, 50]
    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor="374151")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[1].height = 22

    row_num = 2

    def write_tc_row(tc, depth):
        """리프 노드 아래에 매핑된 TC를 하위 행으로 펼친다."""
        nonlocal row_num
        indent = "    " * depth
        prio = _enum_val(tc.priority)
        values = [
            "TC",
            f"{indent}└ [{tc.tc_id}] {tc.title}",
            TC_TYPE_LABEL.get(_enum_val(tc.tc_type), ""),
            str(tc.spec_page or "").strip(),
            tc.objective or "",
            tc.expected_result or "",
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.fill = PatternFill("solid", fgColor=TC_ROW_FILL)
            color = PRIORITY_COLOR.get(prio, "374151") if col == 2 else "6b7280"
            cell.font = Font(size=9, color=color, bold=(col == 2 and prio == "high"))
            cell.alignment = Alignment(vertical="top", wrap_text=True,
                                       horizontal="center" if col in (1, 3, 4) else "left")
            cell.border = border
        longest = max(len(tc.objective or ""), len(tc.expected_result or ""), 1)
        ws.row_dimensions[row_num].height = max(16, (longest // 28 + 1) * 14)
        row_num += 1

    def write_node(node, depth=0, parent_path=""):
        nonlocal row_num
        style = DEPTH_STYLES[min(depth, len(DEPTH_STYLES) - 1)]
        indent = "  " * depth
        name = node.get("name", "")
        current_path = f"{parent_path} > {name}" if parent_path else name
        key_points = "\n".join(f"• {kp}" for kp in (node.get("key_points") or []))
        children = node.get("children") or []

        values = [
            depth + 1,
            indent + name,
            CHANGE_LABEL.get(node.get("change_type", "unknown"), "일반"),
            str(node.get("spec_page") or "").strip(),
            node.get("description", ""),
            key_points,
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.fill = PatternFill("solid", fgColor=style["fill"])
            cell.font = Font(bold=style["bold"], color=style["font_color"], size=style["font_size"])
            cell.alignment = Alignment(vertical="center", wrap_text=True,
                                       horizontal="center" if col in (1, 4) else "left")
            cell.border = border

        if key_points:
            ws.row_dimensions[row_num].height = max(18, len(key_points.splitlines()) * 16)
        else:
            ws.row_dimensions[row_num].height = 20

        row_num += 1

        if children:
            for child in children:
                write_node(child, depth + 1, current_path)
        else:
            # 리프 노드: 이 노드 경로에 매핑된 실제 TC를 하위 행으로 펼침
            for tc in tc_by_path.get(current_path, []):
                write_tc_row(tc, depth + 1)

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


# ============================================================================
# 흐름 트리(Flow Tree) — 행동 흐름 메뉴트리. menu_tree(구조적)와 별도 보관.
# ============================================================================
def _build_flow_tree_bg(document_id: int):
    """백그라운드: PDF에서 흐름 트리 추출 → doc.flow_tree에 저장."""
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
        ruleset = _get_ruleset(db, document_id)
        flow = build_flow_tree(doc.file_path, ruleset=ruleset, original_filename=doc.original_filename)
        doc.flow_tree = json.dumps(flow, ensure_ascii=False)
        db.commit()
        st = flow_tree_stats(flow)
        print(f"[흐름트리 완료] doc_id={document_id}, 노드 {st['total']}개, 깊이 {st['max_depth']}, 타입 {st['types']}")
    except Exception as e:
        print(f"[흐름트리 실패] doc_id={document_id}: {str(e)[:200]}")
    finally:
        db.close()


@router.post("/{document_id}/flow-tree")
def start_build_flow_tree(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """흐름 트리 추출 시작 (백그라운드). 완료 후 GET /flow-tree 로 조회."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    background_tasks.add_task(_build_flow_tree_bg, document_id)
    return {"message": "흐름 트리 추출을 시작했습니다", "document_id": document_id}


@router.get("/{document_id}/flow-tree")
def get_flow_tree(document_id: int, db: Session = Depends(get_db)):
    """저장된 흐름 트리 JSON 조회 (아직 없으면 ready=False)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    if not doc.flow_tree:
        return {"ready": False}
    flow = json.loads(doc.flow_tree)
    return {"ready": True, "flow_tree": flow, "stats": flow_tree_stats(flow)}


@router.get("/{document_id}/flow-tree/export")
def export_flow_tree_excel(document_id: int, db: Session = Depends(get_db)):
    """흐름 트리를 QA 양식 Excel 그리드로 내보내기."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not doc.flow_tree:
        raise HTTPException(status_code=404, detail="흐름 트리가 없습니다")
    buf = render_flow_tree_excel(json.loads(doc.flow_tree))
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=flowtree_{document_id}.xlsx"},
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
        "progress_current": doc.progress_current or 0,
        "progress_total": doc.progress_total or 0,
        "tc_started_at": doc.tc_started_at.isoformat() if doc.tc_started_at else None,
    }
