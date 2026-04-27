import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.defect_ingestion import ingest_test_result, get_defect_stats

router = APIRouter(prefix="/defects", tags=["defects"])


@router.post("/ingest")
async def ingest_defects(file: UploadFile = File(...)):
    """테스트 결과 Excel 업로드 → Fail TC를 결함 이력 DB에 저장"""
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Excel 파일(.xlsx)만 업로드 가능합니다")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    result = ingest_test_result(tmp_path)
    result["filename"] = file.filename
    return result


@router.get("/stats")
def stats():
    """저장된 결함 이력 통계 조회"""
    return get_defect_stats()
