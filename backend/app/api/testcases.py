from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.database import get_db
from app.models.testcase import TestCase, TCType, TCPriority, TCStatus, ReviewStatus, ChangeType
from app.models.document import Document
from app.models.project import Project
from app.core.config import settings
from app.services.report_generator import generate_tc_report

router = APIRouter(prefix="/testcases", tags=["testcases"])


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    objective: Optional[str] = None
    preconditions: Optional[List[str]] = None
    steps: Optional[List[dict]] = None
    expected_result: Optional[str] = None
    tc_type: Optional[TCType] = None
    priority: Optional[TCPriority] = None
    status: Optional[TCStatus] = None


class ReviewUpdate(BaseModel):
    review_status: ReviewStatus
    review_note: Optional[str] = None


class TestCaseResponse(BaseModel):
    id: int
    document_id: int
    tc_id: str
    category: str
    title: str
    objective: str
    preconditions: Optional[List[str]]
    steps: List[dict]
    expected_result: str
    tc_type: TCType
    priority: TCPriority
    change_type: Optional[ChangeType]
    status: TCStatus
    review_status: ReviewStatus
    review_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/document/{document_id}", response_model=List[TestCaseResponse])
def list_testcases(
    document_id: int,
    tc_type: Optional[TCType] = None,
    priority: Optional[TCPriority] = None,
    review_status: Optional[ReviewStatus] = None,
    change_type: Optional[ChangeType] = None,
    db: Session = Depends(get_db),
):
    query = db.query(TestCase).filter(TestCase.document_id == document_id)
    if tc_type:
        query = query.filter(TestCase.tc_type == tc_type)
    if priority:
        query = query.filter(TestCase.priority == priority)
    if review_status:
        query = query.filter(TestCase.review_status == review_status)
    if change_type:
        query = query.filter(TestCase.change_type == change_type)
    return query.order_by(TestCase.tc_id).all()


@router.get("/document/{document_id}/summary")
def get_tc_summary(document_id: int, db: Session = Depends(get_db)):
    testcases = db.query(TestCase).filter(TestCase.document_id == document_id).all()
    total = len(testcases)

    type_dist = {}
    priority_dist = {}
    review_dist = {}

    for tc in testcases:
        type_dist[tc.tc_type.value] = type_dist.get(tc.tc_type.value, 0) + 1
        priority_dist[tc.priority.value] = priority_dist.get(tc.priority.value, 0) + 1
        rs = tc.review_status if tc.review_status else "pending"
        review_dist[rs] = review_dist.get(rs, 0) + 1

    return {
        "total": total,
        "type_distribution": type_dist,
        "priority_distribution": priority_dist,
        "review_distribution": review_dist,
        "categories": list({tc.category for tc in testcases}),
    }


@router.patch("/{tc_id}/review", response_model=TestCaseResponse)
def review_testcase(tc_id: int, data: ReviewUpdate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == tc_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TC를 찾을 수 없습니다")
    tc.review_status = data.review_status
    tc.review_note = data.review_note
    db.commit()
    db.refresh(tc)
    return tc


@router.patch("/{tc_id}", response_model=TestCaseResponse)
def update_testcase(tc_id: int, data: TestCaseUpdate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == tc_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TC를 찾을 수 없습니다")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tc, field, value)
    if data.title or data.steps or data.expected_result:
        tc.status = TCStatus.MODIFIED
    db.commit()
    db.refresh(tc)
    return tc


@router.delete("/{tc_id}")
def delete_testcase(tc_id: int, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == tc_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TC를 찾을 수 없습니다")
    db.delete(tc)
    db.commit()
    return {"message": "삭제되었습니다"}


@router.post("/document/{document_id}/regenerate")
def regenerate_testcases(document_id: int, db: Session = Depends(get_db)):
    from app.services.tc_generator import regenerate_tc

    tcs = db.query(TestCase).filter(
        TestCase.document_id == document_id,
        TestCase.review_status == ReviewStatus.NEEDS_REVISION,
        # admin_required는 AI 재생성 대상에서 제외
    ).all()

    if not tcs:
        raise HTTPException(status_code=400, detail="수정 요청된 TC가 없습니다")

    updated = 0
    for tc in tcs:
        try:
            tc_data = {
                "tc_id": tc.tc_id,
                "category": tc.category,
                "title": tc.title,
                "objective": tc.objective,
                "tc_type": tc.tc_type.value,
                "priority": tc.priority.value,
                "preconditions": tc.preconditions or [],
                "steps": tc.steps or [],
                "expected_result": tc.expected_result,
            }
            new_data = regenerate_tc(tc_data, tc.review_note or "")
            tc.title = new_data.get("title", tc.title)
            tc.objective = new_data.get("objective", tc.objective)
            tc.preconditions = new_data.get("preconditions", tc.preconditions)
            tc.steps = new_data.get("steps", tc.steps)
            tc.expected_result = new_data.get("expected_result", tc.expected_result)
            try:
                tc.tc_type = TCType(new_data.get("tc_type", tc.tc_type.value))
                tc.priority = TCPriority(new_data.get("priority", tc.priority.value))
            except ValueError:
                pass
            tc.review_status = ReviewStatus.PENDING
            tc.review_note = None
            tc.status = TCStatus.MODIFIED
            updated += 1
        except Exception as e:
            print(f"[재생성 실패] TC {tc.tc_id}: {e}")

    db.commit()

    # 재생성된 TC로 RAG 이력 갱신
    try:
        from app.services.tc_ingestion import ingest_testcases
        all_tcs = db.query(TestCase).filter(TestCase.document_id == document_id).all()
        tc_dicts = [{
            "tc_id": t.tc_id, "category": t.category, "title": t.title,
            "objective": t.objective, "tc_type": t.tc_type.value,
            "priority": t.priority.value, "steps": t.steps or [],
            "expected_result": t.expected_result,
        } for t in all_tcs]
        ingest_testcases(document_id, tc_dicts)
    except Exception as e:
        print(f"[TC 이력 갱신 실패] {e}")

    return {"regenerated": updated, "total": len(tcs)}


@router.post("/document/{document_id}/playwright")
def generate_playwright(
    document_id: int,
    domain: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """TC 목록으로 Playwright 테스트 스크립트(.py) 생성 후 다운로드"""
    from app.services.playwright_generator import generate_playwright_script

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    testcases = db.query(TestCase).filter(
        TestCase.document_id == document_id,
        TestCase.review_status != ReviewStatus.DELETED,
    ).order_by(TestCase.tc_id).all()

    if not testcases:
        raise HTTPException(status_code=404, detail="생성된 TC가 없습니다")

    project = db.query(Project).filter(Project.id == doc.project_id).first()
    project_name = project.name if project else "Unknown"

    result = generate_playwright_script(
        testcases=testcases,
        project_name=project_name,
        doc_name=doc.original_filename,
        output_path=settings.REPORT_DIR,
        domain=domain,
        base_url=settings.XPERP_BASE_URL,
    )

    if not result["path"]:
        raise HTTPException(status_code=500, detail="스크립트 생성 실패")

    return FileResponse(
        path=result["path"],
        filename=result["filename"],
        media_type="text/x-python",
        headers={
            "X-TC-Count": str(result["tc_count"]),
            "X-Categories": str(result["categories"]),
        },
    )


@router.get("/document/{document_id}/export")
def export_testcases(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    testcases = db.query(TestCase).filter(
        TestCase.document_id == document_id,
        TestCase.review_status != ReviewStatus.DELETED,
    ).order_by(TestCase.tc_id).all()

    if not testcases:
        raise HTTPException(status_code=404, detail="생성된 TC가 없습니다")

    project = db.query(Project).filter(Project.id == doc.project_id).first()
    project_name = project.name if project else "Unknown"

    report_path = generate_tc_report(testcases, project_name, settings.REPORT_DIR)

    return FileResponse(
        path=report_path,
        filename=f"TC_Report_{project_name}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
