from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.core.config import settings
from app.services.web_knowledge_ingestion import get_web_knowledge_stats, delete_domain_knowledge

router = APIRouter(prefix="/crawler", tags=["crawler"])

# 크롤링 진행 상태 (단일 워커 모델)
_status: dict = {
    "running": False,
    "domain": None,
    "done": 0,
    "total": 0,
    "current": "",
    "result": None,
    "error": None,
    "stop_requested": False,
}


class CrawlRequest(BaseModel):
    domain: str = "xperp"
    base_url: Optional[str] = None
    user_id: Optional[str] = None
    password: Optional[str] = None
    target_modules: Optional[List[str]] = None
    # OTP 우회용: 브라우저에서 복사한 Cookie 헤더 문자열
    # 예: "JSESSIONID=abc123; XPERP_TOKEN=xyz789"
    session_cookie: Optional[str] = None


def _progress_callback(done: int, total: int, current: str):
    _status["current"] = current
    if done >= 0:  # -1이면 상태 메시지만 업데이트 (로그인/OTP 단계)
        _status["done"] = done
        _status["total"] = total


def _run_crawl(req: CrawlRequest):
    from app.services.web_crawler import run_crawl_sync

    _status["running"] = True
    _status["stop_requested"] = False
    _status["domain"] = req.domain
    _status["done"] = 0
    _status["total"] = 0
    _status["current"] = "로그인 중..."
    _status["result"] = None
    _status["error"] = None

    try:
        base_url = req.base_url or settings.XPERP_BASE_URL
        user_id = req.user_id or settings.XPERP_USER_ID
        password = req.password or settings.XPERP_PASSWORD

        if not base_url or not user_id or not password:
            raise ValueError("XPERP_BASE_URL, XPERP_USER_ID, XPERP_PASSWORD 설정이 필요합니다")

        result = run_crawl_sync(
            base_url=base_url,
            user_id=user_id,
            password=password,
            domain=req.domain,
            target_modules=req.target_modules,
            on_progress=_progress_callback,
            session_cookie=req.session_cookie,
        )
        _status["result"] = result
        _status["current"] = "완료"
        print(f"[크롤러] 완료: {result['crawled']}개 저장, {result['skipped']}개 건너뜀")
    except Exception as e:
        _status["error"] = str(e)
        _status["current"] = "오류"
        print(f"[크롤러] 실패: {e}")
    finally:
        _status["running"] = False


@router.get("/debug")
def debug_env():
    """서버 Python 환경 진단"""
    import sys, importlib.util
    playwright_spec = importlib.util.find_spec("playwright")
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "playwright_found": playwright_spec is not None,
        "playwright_location": str(playwright_spec.origin) if playwright_spec else None,
    }


@router.post("/start")
def start_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    """웹 크롤링 시작 (백그라운드 실행)"""
    if _status["running"]:
        raise HTTPException(status_code=409, detail="이미 크롤링이 실행 중입니다")

    background_tasks.add_task(_run_crawl, req)
    return {
        "message": f"크롤링 시작 ({req.domain})",
        "domain": req.domain,
        "target_modules": req.target_modules or "전체",
    }


@router.post("/stop")
def stop_crawl():
    """실행 중인 크롤링 중단 요청"""
    if not _status["running"]:
        raise HTTPException(status_code=400, detail="실행 중인 크롤링이 없습니다")
    _status["stop_requested"] = True
    _status["current"] = "중단 요청됨 - 현재 메뉴 완료 후 중단"
    return {"message": "중단 요청됨"}


@router.get("/status")
def get_crawl_status():
    """크롤링 진행 상태 조회"""
    return {
        "running": _status["running"],
        "domain": _status["domain"],
        "progress": f"{_status['done']}/{_status['total']}",
        "current": _status["current"],
        "error": _status["error"],
        "result": _status["result"],
    }


@router.get("/stats/{domain}")
def get_domain_stats(domain: str):
    """도메인별 수집된 UI 지식 통계 조회"""
    return get_web_knowledge_stats(domain)


@router.get("/sample/{domain}")
def get_sample_pages(domain: str, n: int = 3):
    """수집된 UI 지식 샘플 조회 (내용 확인용)"""
    from app.services.web_knowledge_ingestion import get_web_knowledge_collection
    collection = get_web_knowledge_collection(domain)
    all_data = collection.get()
    ids = all_data.get("ids", [])
    docs = all_data.get("documents", [])
    metas = all_data.get("metadatas", [])
    samples = []
    for i in range(min(n, len(ids))):
        doc = docs[i]
        samples.append({
            "menu_path": metas[i].get("menu_path", ""),
            "menu_code": metas[i].get("menu_code", ""),
            "content_length": len(doc),
            "content_head": doc[:200],
            "content_tail": doc[-500:] if len(doc) > 500 else "",
        })
    return {"total": len(ids), "samples": samples}


@router.delete("/knowledge/{domain}")
def delete_knowledge(domain: str):
    """도메인 UI 지식 전체 삭제"""
    if _status["running"] and _status["domain"] == domain:
        raise HTTPException(status_code=409, detail="크롤링 중에는 삭제할 수 없습니다")
    deleted = delete_domain_knowledge(domain)
    return {"domain": domain, "deleted_pages": deleted}
