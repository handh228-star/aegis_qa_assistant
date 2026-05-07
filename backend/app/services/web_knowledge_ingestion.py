from typing import List, Dict
from app.services.manual_ingestion import SimpleVectorStore, _get_embedding_fn
from app.core.config import settings


def get_web_knowledge_collection(domain: str) -> SimpleVectorStore:
    return SimpleVectorStore(settings.VECTOR_DB_DIR, _get_embedding_fn(), name=f"web_ui_{domain}")


def ingest_ui_pages(pages: List[Dict], domain: str) -> int:
    """크롤링된 UI 페이지 정보를 도메인별 벡터 스토어에 저장.
    pages: [{"menu_path": str, "menu_code": str, "content": str}]
    """
    collection = get_web_knowledge_collection(domain)

    batch_size = 50
    total_added = 0
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        before = collection.count()
        collection.add(
            ids=[f"{domain}_{p['menu_code']}" for p in batch],
            documents=[p["content"] for p in batch],
            metadatas=[{
                "domain": domain,
                "menu_code": p["menu_code"],
                "menu_path": p["menu_path"],
            } for p in batch],
        )
        total_added += collection.count() - before

    print(f"[UI 지식 저장] domain={domain}, {total_added}개 화면 저장 완료")
    return total_added


def delete_domain_knowledge(domain: str) -> int:
    collection = get_web_knowledge_collection(domain)
    all_data = collection.get()
    if all_data["ids"]:
        collection.delete(ids=all_data["ids"])
        return len(all_data["ids"])
    return 0


def get_web_knowledge_stats(domain: str) -> Dict:
    collection = get_web_knowledge_collection(domain)
    all_data = collection.get()

    paths = [m.get("menu_path", "") for m in all_data["metadatas"]]
    top_menus = {}
    for p in paths:
        root = p.split(" > ")[0] if " > " in p else p
        top_menus[root] = top_menus.get(root, 0) + 1

    return {
        "domain": domain,
        "total_pages": collection.count(),
        "top_menus": [{"menu": k, "pages": v} for k, v in sorted(top_menus.items())],
    }
