from google import genai
import json
from typing import List, Dict
from app.core.config import settings
from app.services.document_parser import (
    extract_text_from_pdf,
    pdf_to_base64_chunks,
    is_text_based_pdf,
)

client = genai.Client(api_key=settings.GOOGLE_API_KEY)

ANALYZE_PROMPT = """당신은 QA 전문가입니다. 이 문서를 분석하여 테스트해야 할 기능 목록을 추출해주세요.

각 기능에 대해 change_type을 반드시 판단해주세요:
- new_feature: 신규 기능 추가
- modification: 기존 기능 수정/개선
- bug_fix: 버그 수정
- unknown: 판단 불가 (일반 기획서이거나 명확하지 않은 경우)

다음 JSON 형식으로만 응답해주세요 (```json 코드블록 없이 순수 JSON만):
{
  "features": [
    {
      "category": "기능 카테고리명",
      "description": "기능 설명",
      "key_points": ["핵심 검증 포인트1", "핵심 검증 포인트2"],
      "change_type": "new_feature|modification|bug_fix|unknown",
      "change_summary": "변경 내용 요약 (change_type이 unknown이면 빈 문자열)"
    }
  ]
}"""

TC_GENERATE_PROMPT = """당신은 QA 전문가입니다. 아래 기능 목록을 기반으로 고품질의 테스트케이스(TC)를 생성해주세요.

기능 목록:
{features}

{rag_context}

기능별 TC 생성 전략 (change_type 기준):
- new_feature (신규 기능): 정상/비정상/경계값/예외를 포괄적으로 생성
- modification (기능 수정): 변경된 동작 검증 TC + 기존 연관 기능 회귀 테스트 TC 포함
- bug_fix (버그 수정): 수정된 버그 재현 방지 케이스 집중 + 유사 시나리오 포함
- unknown: 포괄적으로 생성

공통 요구사항:
- 전체 TC 중 정상 40%, 비정상 30%, 경계값 20%, 예외 10% 비율 권장
- 각 TC는 명확하고 재현 가능한 단계로 작성할 것
- 매뉴얼 스펙이 있다면 실제 스펙(입력값 조건, 제약, 오류 메시지 등)을 TC에 반영할 것
- 과거 결함 이력이 있다면 해당 기능의 비정상/경계값/예외 케이스를 반드시 강화할 것

다음 JSON 형식으로만 응답해주세요 (```json 코드블록 없이 순수 JSON만):
{
  "testcases": [
    {
      "tc_id": "TC-001",
      "category": "기능 카테고리",
      "title": "TC 제목",
      "objective": "테스트 목적",
      "change_type": "new_feature|modification|bug_fix|unknown",
      "tc_type": "positive|negative|boundary|exception",
      "priority": "high|medium|low",
      "preconditions": ["사전조건1", "사전조건2"],
      "steps": [
        {"step": 1, "action": "수행할 액션", "expected": "예상 결과"}
      ],
      "expected_result": "최종 기대 결과"
    }
  ]
}"""


def _parse_json_response(text: str) -> Dict:
    import re
    original = text
    text = text.strip()

    # 코드블록 제거
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError(f"JSON 객체를 찾을 수 없습니다. 원본 응답:\n{original[:500]}")

    json_str = text[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n원본 응답:\n{original[:500]}")


def _analyze_text_based(pdf_path: str) -> Dict:
    text = extract_text_from_pdf(pdf_path)
    if len(text) > 20000:
        text = text[:20000] + "\n\n[이하 생략]"

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=f"다음은 기획서 내용입니다:\n\n{text}\n\n{ANALYZE_PROMPT}",
    )
    print(f"[ANALYZE 응답 원본]\n{response.text[:300]}\n---")
    return _parse_json_response(response.text)


def _analyze_image_based(pdf_path: str) -> Dict:
    import base64
    chunks = pdf_to_base64_chunks(pdf_path, chunk_size=5)
    all_features = []

    for chunk_b64 in chunks:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                {"inline_data": {"mime_type": "application/pdf", "data": chunk_b64}},
                ANALYZE_PROMPT,
            ],
        )
        result = _parse_json_response(response.text)
        all_features.extend(result.get("features", []))

    return {"features": all_features}


def analyze_document(pdf_path: str) -> Dict:
    if is_text_based_pdf(pdf_path):
        return _analyze_text_based(pdf_path)
    else:
        return _analyze_image_based(pdf_path)


def generate_testcases(features: List[Dict], use_rag: bool = True) -> Dict:
    from app.services.rag_service import build_rag_context

    features_text = json.dumps(features, ensure_ascii=False, indent=2)

    rag_context = ""
    if use_rag:
        categories = [f.get("category", "") for f in features]
        raw_context = build_rag_context(categories)
        if raw_context:
            rag_context = f"참고 매뉴얼 내용 (실제 서비스 스펙):\n{raw_context}"

    prompt = TC_GENERATE_PROMPT.replace("{features}", features_text)
    prompt = prompt.replace("{rag_context}", rag_context)

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )
    print(f"[TC생성 응답 원본]\n{response.text[:300]}\n---")
    return _parse_json_response(response.text)


REGENERATE_PROMPT = """다음 테스트케이스를 검토 의견을 반영하여 개선해주세요.

기존 TC:
{tc_data}

검토 의견: {review_note}

동일한 JSON 형식으로 개선된 TC 1개를 반환해주세요 (```json 코드블록 없이 순수 JSON만):
{{
  "tc_id": "...",
  "category": "...",
  "title": "...",
  "objective": "...",
  "tc_type": "positive|negative|boundary|exception",
  "priority": "high|medium|low",
  "preconditions": ["..."],
  "steps": [{{"step": 1, "action": "...", "expected": "..."}}],
  "expected_result": "..."
}}"""


def regenerate_tc(tc_data: Dict, review_note: str) -> Dict:
    prompt = REGENERATE_PROMPT.replace("{tc_data}", json.dumps(tc_data, ensure_ascii=False, indent=2))
    prompt = prompt.replace("{review_note}", review_note or "전반적으로 개선해주세요")
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )
    return _parse_json_response(response.text)


def generate_tc_from_pdf(pdf_path: str) -> Dict:
    analysis = analyze_document(pdf_path)
    features = analysis.get("features", [])
    tc_result = generate_testcases(features)

    return {
        "features": features,
        "testcases": tc_result.get("testcases", []),
    }
