from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List
from app.services.manual_ingestion import (
    ingest_manual,
    ingest_all_manuals,
    delete_manual,
    get_manual_stats,
)
from app.core.config import settings

router = APIRouter(prefix="/manuals", tags=["manuals"])


@router.post("/ingest-all")
def ingest_all(background_tasks: BackgroundTasks):
    """manual_xperp 폴더의 모든 PDF를 벡터 DB에 저장 (백그라운드)"""
    background_tasks.add_task(_run_ingest_all)
    return {"message": f"{settings.MANUAL_DIR} 폴더 매뉴얼 일괄 처리 시작"}


def _run_ingest_all():
    results = ingest_all_manuals()
    total_chunks = sum(r.get("chunks", 0) for r in results)
    print(f"[매뉴얼 일괄 처리 완료] {len(results)}개 파일, 총 {total_chunks}개 청크 저장")


@router.post("/ingest/{filename}")
def ingest_one(filename: str):
    """특정 매뉴얼 파일 처리"""
    pdf_path = settings.MANUAL_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} 파일을 찾을 수 없습니다")
    result = ingest_manual(str(pdf_path))
    return result


@router.get("/stats")
def get_stats():
    """저장된 매뉴얼 목록 및 청크 수 조회"""
    stats = get_manual_stats()
    total_chunks = sum(s["chunks"] for s in stats)
    return {
        "total_files": len(stats),
        "total_chunks": total_chunks,
        "files": stats,
    }


@router.delete("/{filename}")
def remove_manual(filename: str):
    """특정 매뉴얼 삭제"""
    deleted = delete_manual(filename)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"{filename} 데이터를 찾을 수 없습니다")
    return {"message": f"{filename} 삭제 완료"}


@router.get("/list-files")
def list_manual_files():
    """manual_xperp 폴더의 PDF 파일 목록 조회"""
    files = list(settings.MANUAL_DIR.glob("*.pdf"))
    return [{"filename": f.name, "size_mb": round(f.stat().st_size / 1024 / 1024, 2)} for f in files]
