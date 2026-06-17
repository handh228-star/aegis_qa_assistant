import pickle
import numpy as np
from google import genai
from pypdf import PdfReader
from pathlib import Path
from typing import List, Dict
from app.core.config import settings


class SimpleVectorStore:
    """numpy 기반 순수 Python 벡터 스토어 (ChromaDB 대체)"""

    def __init__(self, path: Path, embedding_fn, name: str = "collection"):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.index_file = path / f"{name}.pkl"
        self.embedding_fn = embedding_fn
        self._load()

    def _load(self):
        if self.index_file.exists():
            with open(self.index_file, "rb") as f:
                data = pickle.load(f)
            self.ids = data["ids"]
            self.documents = data["documents"]
            self.embeddings = data["embeddings"]
            self.metadatas = data["metadatas"]
        else:
            self.ids: List[str] = []
            self.documents: List[str] = []
            self.embeddings: List[List[float]] = []
            self.metadatas: List[Dict] = []

    def _save(self):
        with open(self.index_file, "wb") as f:
            pickle.dump({
                "ids": self.ids,
                "documents": self.documents,
                "embeddings": self.embeddings,
                "metadatas": self.metadatas,
            }, f)

    def count(self) -> int:
        return len(self.ids)

    def get(self, where: Dict = None) -> Dict:
        if where is None:
            return {"ids": list(self.ids), "documents": list(self.documents), "metadatas": list(self.metadatas)}
        result_ids, result_docs, result_metas = [], [], []
        for id_, doc, meta in zip(self.ids, self.documents, self.metadatas):
            if all(meta.get(k) == v for k, v in where.items()):
                result_ids.append(id_)
                result_docs.append(doc)
                result_metas.append(meta)
        return {"ids": result_ids, "documents": result_docs, "metadatas": result_metas}

    def delete(self, ids: List[str]):
        id_set = set(ids)
        keep = [i for i, id_ in enumerate(self.ids) if id_ not in id_set]
        self.ids = [self.ids[i] for i in keep]
        self.documents = [self.documents[i] for i in keep]
        self.embeddings = [self.embeddings[i] for i in keep]
        self.metadatas = [self.metadatas[i] for i in keep]
        self._save()

    def add(self, ids: List[str], documents: List[str], metadatas: List[Dict]):
        new_embeddings = self.embedding_fn(documents)
        existing_ids = set(self.ids)
        for id_, doc, emb, meta in zip(ids, documents, new_embeddings, metadatas):
            if id_ not in existing_ids:
                self.ids.append(id_)
                self.documents.append(doc)
                self.embeddings.append(list(emb))
                self.metadatas.append(meta)
        self._save()

    def query(self, query_texts: List[str], n_results: int = 5, score_threshold: float = 0.0) -> Dict:
        if not self.embeddings:
            return {"documents": [[]], "metadatas": [[]], "scores": [[]]}

        query_embedding = self.embedding_fn(query_texts)[0]
        query_vec = np.array(query_embedding, dtype=np.float32)
        stored = np.array(self.embeddings, dtype=np.float32)

        norms = np.linalg.norm(stored, axis=1)
        query_norm = np.linalg.norm(query_vec)
        safe_norms = np.where(norms == 0, 1e-10, norms)
        similarities = (stored @ query_vec) / (safe_norms * (query_norm or 1e-10))

        top_k = min(n_results, len(similarities))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # 임계값 이상인 결과만 반환
        filtered = [(i, float(similarities[i])) for i in top_indices if similarities[i] >= score_threshold]

        return {
            "documents": [[self.documents[i] for i, _ in filtered]],
            "metadatas": [[self.metadatas[i] for i, _ in filtered]],
            "scores": [[score for _, score in filtered]],
        }


def _get_embedding_fn():
    """Embedding 함수를 반환한다.

    - 진짜 배치 호출: embed_content(contents=[...])로 묶어서 호출하여 API 호출 수를 줄임.
    - 재시도: 429(rate limit) / 503 / UNAVAILABLE 발생 시 지수 백오프 후 재시도.
    - 배치 사이즈는 보수적으로 100. 안전하게 quota 회피.
    """
    import time

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    BATCH = 100
    MAX_RETRIES = 4

    def _embed_batch(chunk: List[str]) -> List[List[float]]:
        wait = 30
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                result = client.models.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=chunk,
                )
                # embeddings는 contents 순서와 동일한 리스트
                return [list(e.values) for e in result.embeddings]
            except Exception as e:
                err = str(e)
                last_err = e
                is_transient = (
                    "429" in err or "RESOURCE_EXHAUSTED" in err
                    or "503" in err or "UNAVAILABLE" in err
                )
                if is_transient and attempt < MAX_RETRIES - 1:
                    print(f"  [임베딩 재시도 {attempt+1}/{MAX_RETRIES-1}] {err[:80]} → {wait}초 대기...")
                    time.sleep(wait)
                    wait = min(wait * 2, 120)
                else:
                    raise
        raise last_err  # pragma: no cover

    def embed(texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for i in range(0, len(texts), BATCH):
            chunk = texts[i:i + BATCH]
            results.extend(_embed_batch(chunk))
        return results

    return embed


def get_chroma_collection() -> SimpleVectorStore:
    return SimpleVectorStore(settings.VECTOR_DB_DIR, _get_embedding_fn(), name="manual_xperp")


def _extract_chunks(pdf_path: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict]:
    reader = PdfReader(pdf_path)
    filename = Path(pdf_path).stem
    chunks = []

    for page_num, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if not text:
            continue

        start = 0
        chunk_idx = 0
        while start < len(text):
            chunk_text = text[start:start + chunk_size].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "filename": filename,
                    "page": page_num + 1,
                    "chunk_idx": chunk_idx,
                    "id": f"{filename}_p{page_num + 1}_c{chunk_idx}",
                })
                chunk_idx += 1
            start += chunk_size - overlap

    return chunks


def ingest_manual(pdf_path: str) -> Dict:
    collection = get_chroma_collection()
    filename = Path(pdf_path).stem

    existing = collection.get(where={"filename": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    chunks = _extract_chunks(pdf_path)
    if not chunks:
        return {"filename": filename, "chunks": 0, "status": "no_text"}

    batch_size = 50  # Gemini 임베딩 API 한도 고려
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{"filename": c["filename"], "page": c["page"], "chunk_idx": c["chunk_idx"]} for c in batch],
        )
        print(f"  배치 {i // batch_size + 1} 완료 ({len(batch)}개 청크)")

    return {"filename": filename, "chunks": len(chunks), "status": "success"}


def ingest_all_manuals() -> List[Dict]:
    results = []
    pdf_files = list(settings.MANUAL_DIR.glob("*.pdf"))

    for pdf_path in pdf_files:
        print(f"[매뉴얼 처리 중] {pdf_path.name}")
        result = ingest_manual(str(pdf_path))
        result["file"] = pdf_path.name
        results.append(result)
        print(f"  → {result['chunks']}개 청크 저장 완료")

    return results


def delete_manual(filename: str) -> bool:
    collection = get_chroma_collection()
    existing = collection.get(where={"filename": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        return True
    return False


def get_manual_stats() -> List[Dict]:
    collection = get_chroma_collection()
    all_data = collection.get()

    stats = {}
    for meta in all_data["metadatas"]:
        fname = meta["filename"]
        stats[fname] = stats.get(fname, 0) + 1

    return [{"filename": k, "chunks": v} for k, v in sorted(stats.items())]
