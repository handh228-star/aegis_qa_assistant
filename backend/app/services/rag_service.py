from typing import List
from app.services.manual_ingestion import get_chroma_collection
from app.services.defect_ingestion import get_defect_collection
from app.services.tc_ingestion import get_tc_collection


def search_manual(query: str, n_results: int = 5) -> str:
    try:
        collection = get_chroma_collection()
        total = collection.count()
        if total == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, total),
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            parts.append(f"[출처: {meta['filename']} / {meta['page']}페이지]\n{doc}")

        return "\n\n".join(parts)

    except Exception:
        return ""


def search_defects(query: str, n_results: int = 5) -> str:
    try:
        collection = get_defect_collection()
        total = collection.count()
        if total == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, total),
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            jira = f" ({meta['jira']})" if meta.get("jira") else ""
            parts.append(f"[과거결함{jira}]\n{doc}")

        return "\n\n".join(parts)

    except Exception:
        return ""


def search_tc_history(query: str, n_results: int = 5) -> str:
    try:
        collection = get_tc_collection()
        total = collection.count()
        if total == 0:
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, total),
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            parts.append(f"[과거TC: {meta.get('tc_id','')} / {meta.get('tc_type','')}]\n{doc}")

        return "\n\n".join(parts)

    except Exception:
        return ""


def build_rag_context(feature_categories: List[str]) -> str:
    query = " ".join(feature_categories)

    manual_ctx = search_manual(query, n_results=8)
    defect_ctx = search_defects(query, n_results=5)
    tc_ctx = search_tc_history(query, n_results=5)

    parts = []
    if manual_ctx:
        parts.append(f"[매뉴얼 스펙]\n{manual_ctx}")
    if defect_ctx:
        parts.append(f"[과거 테스트 결함 이력]\n{defect_ctx}")
    if tc_ctx:
        parts.append(f"[과거 TC 이력]\n{tc_ctx}")

    return "\n\n".join(parts)
