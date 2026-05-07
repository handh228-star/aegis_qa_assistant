from typing import List, Optional
from app.services.manual_ingestion import get_chroma_collection
from app.services.defect_ingestion import get_defect_collection
from app.services.tc_ingestion import get_tc_collection
from app.services.web_knowledge_ingestion import get_web_knowledge_collection

# 유사도 임계값: 이 값 미만의 청크는 RAG 컨텍스트에서 제외
MANUAL_THRESHOLD = 0.50
DEFECT_THRESHOLD = 0.45
TC_HISTORY_THRESHOLD = 0.45
WEB_KNOWLEDGE_THRESHOLD = 0.50


def search_manual(query: str, n_results: int = 8) -> str:
    try:
        collection = get_chroma_collection()
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            score_threshold=MANUAL_THRESHOLD,
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        scores = results.get("scores", [[]])[0]

        if not docs:
            return ""

        parts = []
        for doc, meta, score in zip(docs, metas, scores):
            parts.append(f"[출처: {meta['filename']} / {meta['page']}페이지 (유사도:{score:.2f})]\n{doc}")

        print(f"  [RAG 매뉴얼] {len(parts)}개 청크 사용 (임계값 {MANUAL_THRESHOLD})")
        return "\n\n".join(parts)

    except Exception as e:
        print(f"  [RAG 매뉴얼 오류] {e}")
        return ""


def search_defects(query: str, n_results: int = 5) -> str:
    try:
        collection = get_defect_collection()
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            score_threshold=DEFECT_THRESHOLD,
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        if not docs:
            return ""

        parts = []
        for doc, meta in zip(docs, metas):
            jira = f" ({meta['jira']})" if meta.get("jira") else ""
            parts.append(f"[과거결함{jira}]\n{doc}")

        print(f"  [RAG 결함] {len(parts)}개 사용 (임계값 {DEFECT_THRESHOLD})")
        return "\n\n".join(parts)

    except Exception as e:
        print(f"  [RAG 결함 오류] {e}")
        return ""


def search_tc_history(query: str, n_results: int = 5) -> str:
    try:
        collection = get_tc_collection()
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            score_threshold=TC_HISTORY_THRESHOLD,
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        if not docs:
            return ""

        parts = []
        for doc, meta in zip(docs, metas):
            parts.append(f"[과거TC: {meta.get('tc_id','')} / {meta.get('tc_type','')}]\n{doc}")

        print(f"  [RAG TC이력] {len(parts)}개 사용 (임계값 {TC_HISTORY_THRESHOLD})")
        return "\n\n".join(parts)

    except Exception as e:
        print(f"  [RAG TC이력 오류] {e}")
        return ""


def search_web_knowledge(query: str, domain: str, n_results: int = 5) -> str:
    try:
        collection = get_web_knowledge_collection(domain)
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            score_threshold=WEB_KNOWLEDGE_THRESHOLD,
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        if not docs:
            return ""

        parts = []
        for doc, meta in zip(docs, metas):
            parts.append(f"[UI 화면: {meta.get('menu_path', '')}]\n{doc}")

        print(f"  [RAG UI지식] {len(parts)}개 화면 사용 (도메인: {domain}, 임계값 {WEB_KNOWLEDGE_THRESHOLD})")
        return "\n\n".join(parts)

    except Exception as e:
        print(f"  [RAG UI지식 오류] {e}")
        return ""


def build_rag_context(feature_categories: List[str], domain: Optional[str] = None) -> str:
    query = " ".join(feature_categories)

    manual_ctx = search_manual(query)
    defect_ctx = search_defects(query)
    tc_ctx = search_tc_history(query)
    web_ctx = search_web_knowledge(query, domain) if domain else ""

    parts = []
    if manual_ctx:
        parts.append(f"[매뉴얼 스펙]\n{manual_ctx}")
    if web_ctx:
        parts.append(f"[UI 화면 정보]\n{web_ctx}")
    if defect_ctx:
        parts.append(f"[과거 테스트 결함 이력]\n{defect_ctx}")
    if tc_ctx:
        parts.append(f"[과거 TC 이력]\n{tc_ctx}")

    return "\n\n".join(parts)
