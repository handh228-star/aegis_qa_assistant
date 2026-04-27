from typing import List, Dict
from app.services.manual_ingestion import SimpleVectorStore, _get_embedding_fn
from app.core.config import settings


def get_tc_collection() -> SimpleVectorStore:
    return SimpleVectorStore(settings.VECTOR_DB_DIR, _get_embedding_fn(), name="tc_history")


def _tc_to_text(tc: Dict) -> str:
    steps_text = ""
    if tc.get("steps"):
        steps_text = "\n".join(
            f"  {s.get('step', i + 1)}. {s.get('action', '')}"
            for i, s in enumerate(tc["steps"])
        )
    return (
        f"[{tc.get('category', '')}] {tc.get('title', '')}\n"
        f"유형: {tc.get('tc_type', '')} / 우선순위: {tc.get('priority', '')}\n"
        f"목적: {tc.get('objective', '')}\n"
        f"기대결과: {tc.get('expected_result', '')}"
        + (f"\n단계:\n{steps_text}" if steps_text else "")
    )


def ingest_testcases(document_id: int, testcases: List[Dict]) -> int:
    """TC 목록을 벡터 스토어에 저장. 동일 document_id의 기존 데이터는 교체."""
    collection = get_tc_collection()

    existing = collection.get(where={"document_id": document_id})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    if not testcases:
        return 0

    batch_size = 50
    total = 0
    for i in range(0, len(testcases), batch_size):
        batch = testcases[i:i + batch_size]
        collection.add(
            ids=[f"tc_{document_id}_{tc.get('tc_id', i + idx)}" for idx, tc in enumerate(batch)],
            documents=[_tc_to_text(tc) for tc in batch],
            metadatas=[{
                "document_id": document_id,
                "tc_id": tc.get("tc_id", ""),
                "category": tc.get("category", ""),
                "tc_type": tc.get("tc_type", ""),
                "priority": tc.get("priority", ""),
            } for tc in batch],
        )
        total += len(batch)

    print(f"[TC 이력 저장] document_id={document_id}, {total}개 TC → tc_history")
    return total
