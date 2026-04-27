import base64
from pypdf import PdfReader


def get_pdf_page_count(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출 (Excel 기반 PDF에 최적)"""
    reader = PdfReader(pdf_path)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(f"=== 페이지 {i + 1} ===\n{text.strip()}")
    return "\n\n".join(pages_text)


def pdf_to_base64_chunks(pdf_path: str, chunk_size: int = 5) -> list[str]:
    """PDF를 chunk_size 페이지씩 나눠 base64 리스트로 반환 (Figma 등 이미지 중심 PDF용)"""
    from pypdf import PdfWriter
    import io

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    chunks = []

    for start in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        end = min(start + chunk_size, total_pages)
        for i in range(start, end):
            writer.add_page(reader.pages[i])

        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        chunks.append(base64.standard_b64encode(buf.read()).decode("utf-8"))

    return chunks


def is_text_based_pdf(pdf_path: str, min_chars_per_page: int = 50) -> bool:
    """텍스트 기반 PDF 여부 판단 (Excel 변환 vs Figma 변환)"""
    reader = PdfReader(pdf_path)
    total_chars = sum(len(page.extract_text() or "") for page in reader.pages)
    avg_chars = total_chars / max(len(reader.pages), 1)
    return avg_chars >= min_chars_per_page
