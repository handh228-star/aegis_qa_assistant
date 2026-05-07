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

TC_LEVEL_CONFIG = {
    1: {"label": "핵심 검증",  "target": 100,  "per_feature": "2~3",  "depth": "대표 정상/비정상 케이스 위주로 간결하게. 리스크 낮은 기능에 적합합니다."},
    2: {"label": "표준 검증",  "target": 200,  "per_feature": "4~6",  "depth": "정상/비정상/경계값/예외를 균형 있게 포함하세요."},
    3: {"label": "정밀 검증",  "target": 400,  "per_feature": "8~12", "depth": "다양한 입력값, 상태 조합, 업무 규칙 예외를 포함하세요."},
    4: {"label": "심층 검증",  "target": 800,  "per_feature": "14~20","depth": "조합 케이스, 데이터 변형, 경계 조건, 연동 시나리오를 상세히 검증하세요."},
    5: {"label": "전수 검증",  "target": 1600, "per_feature": "25~35","depth": "모든 엣지케이스와 시나리오 조합을 빠짐없이 생성하세요."},
}

ANALYZE_PROMPT = """당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템에 정통합니다. 회계(예산/결산/수납/미납관리), 관리비 부과(세대별 부과·감면·할인·연체가산), 인사급여(급여계산·4대보험·근태), 검침(수도·전기·가스 세대/공동 검침·오류보정), 입주관리(세대정보·이사·주차·민원) 전 영역의 업무 흐름과 공동주택관리법·회계처리기준 등 규정 제약을 숙지하고 있습니다. 기획서를 보면 어떤 업무 규칙이 관여되는지, 어디서 데이터 오류나 권한 오류가 발생할 수 있는지, 어떤 연동 케이스를 놓치기 쉬운지를 직관적으로 파악합니다. 지금부터 이 문서를 분석하여 테스트해야 할 기능 목록을 추출해주세요.

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

TC_GENERATE_PROMPT = """당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템에 정통합니다. 회계(예산/결산/수납/미납관리), 관리비 부과(세대별 부과·감면·할인·연체가산), 인사급여(급여계산·4대보험·근태), 검침(수도·전기·가스 세대/공동 검침·오류보정), 입주관리(세대정보·이사·주차·민원) 전 영역의 업무 흐름과 공동주택관리법·회계처리기준 등 규정 제약을 숙지하고 있습니다. 경계값 분석, 동등 분할, 탐색적 테스트, 결함 예측 기법을 실무에서 적극 활용하며, 실제 운영 환경에서 관리자·입주자·회계담당자가 마주칠 수 있는 문제를 사전에 발견하는 것을 최우선으로 합니다. 아래 기능 하나에 대해 테스트케이스(TC)를 생성해주세요.

대상 기능:
{feature}

{rag_context}

TC 생성 전략 (change_type 기준):
- new_feature (신규 기능): 정상/비정상/경계값/예외를 포괄적으로 생성
- modification (기능 수정): 변경된 동작 검증 TC + 기존 연관 기능 회귀 테스트 TC 포함
- bug_fix (버그 수정): 수정된 버그 재현 방지 케이스 집중 + 유사 시나리오 포함
- unknown: 포괄적으로 생성

커버리지 레벨: {level_label} (레벨 {level}/5)
이 기능에 대해 TC를 {per_feature}개 생성하세요.
커버리지 지침: {level_depth}

공통 요구사항:
- 이 기능의 TC만 생성 (다른 기능 포함 금지)
- 정상 40%, 비정상 30%, 경계값 20%, 예외 10% 비율 권장
- 각 TC는 명확하고 재현 가능한 단계로 작성할 것
- 매뉴얼 스펙이 있다면 실제 스펙(입력값 조건, 제약, 오류 메시지 등)을 TC에 반영할 것
- 과거 결함 이력이 있다면 해당 기능의 비정상/경계값/예외 케이스를 반드시 강화할 것
- TC ID는 {tc_id_start}번부터 순서대로 부여 (TC-{tc_id_start:03d} 형식)
- 품질이 우선이므로 의미 없는 케이스는 만들지 마세요

다음 JSON 형식으로만 응답해주세요 (```json 코드블록 없이 순수 JSON만):
{{
  "testcases": [
    {{
      "tc_id": "TC-{tc_id_start:03d}",
      "category": "기능 카테고리",
      "title": "TC 제목",
      "objective": "테스트 목적",
      "change_type": "new_feature|modification|bug_fix|unknown",
      "tc_type": "positive|negative|boundary|exception",
      "priority": "high|medium|low",
      "preconditions": ["사전조건1", "사전조건2"],
      "steps": [
        {{"step": 1, "action": "수행할 액션", "expected": "예상 결과"}}
      ],
      "expected_result": "최종 기대 결과"
    }}
  ]
}}}"""


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
        model=settings.GEMINI_MODEL_EXTRACT,
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
            model=settings.GEMINI_MODEL_EXTRACT,
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


def _generate_content_with_retry(prompt: str, max_retries: int = 3) -> str:
    """503 등 일시적 오류 시 기능 단위로 재시도 (지수 백오프)"""
    import time
    wait = 30
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_TC,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            err = str(e)
            is_transient = "503" in err or "UNAVAILABLE" in err or "429" in err or "RESOURCE_EXHAUSTED" in err
            if is_transient and attempt < max_retries - 1:
                print(f"  [재시도 {attempt+1}/{max_retries-1}] {err[:80]} → {wait}초 대기...")
                time.sleep(wait)
                wait = min(wait * 2, 120)
            else:
                raise


def generate_testcases(features: List[Dict], use_rag: bool = True, tc_level: int = 2, ruleset=None) -> Dict:
    from app.services.rag_service import build_rag_context

    level_cfg = TC_LEVEL_CONFIG.get(tc_level, TC_LEVEL_CONFIG[2])
    all_testcases = []
    tc_counter = 1

    for i, feature in enumerate(features):
        rag_context = ""
        if use_rag:
            raw_context = build_rag_context([feature.get("category", "")])
            if raw_context:
                rag_context = f"참고 매뉴얼 내용 (실제 서비스 스펙):\n{raw_context}"

        ruleset_hint = ""
        if ruleset and ruleset.tc_rules:
            ruleset_hint = f"\n\n[QA 룰셋 추가 지침]\n{ruleset.tc_rules}"

        prompt = (
            TC_GENERATE_PROMPT
            .replace("{feature}", json.dumps(feature, ensure_ascii=False, indent=2))
            .replace("{rag_context}", rag_context + ruleset_hint)
            .replace("{level}", str(tc_level))
            .replace("{level_label}", level_cfg["label"])
            .replace("{per_feature}", level_cfg["per_feature"])
            .replace("{level_depth}", level_cfg["depth"])
            .replace("{tc_id_start:03d}", f"{tc_counter:03d}")
            .replace("{tc_id_start}", str(tc_counter))
        )

        print(f"[TC생성] 기능 {i+1}/{len(features)}: {feature.get('category', '')} (TC-{tc_counter:03d}~)")
        try:
            text = _generate_content_with_retry(prompt)
        except Exception as e:
            print(f"  [기능 스킵] 재시도 모두 실패, 다음 기능으로 넘어갑니다. 오류: {str(e)[:120]}")
            continue

        try:
            result = _parse_json_response(text)
        except Exception as e:
            print(f"  [파싱 실패] {str(e)[:120]} — 이 기능 스킵")
            continue

        tcs = result.get("testcases", [])
        for tc in tcs:
            tc["tc_id"] = f"TC-{tc_counter:03d}"
            tc_counter += 1

        all_testcases.extend(tcs)
        print(f"  → {len(tcs)}개 생성 (누적 {len(all_testcases)}개)")

    return {"testcases": all_testcases}


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


TREE_PROMPT = """당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템에 정통합니다. 회계(예산/결산/수납/미납관리), 관리비 부과(세대별 부과·감면·할인·연체가산), 인사급여(급여계산·4대보험·근태), 검침(수도·전기·가스 세대/공동 검침·오류보정), 입주관리(세대정보·이사·주차·민원) 전 영역의 업무 흐름과 공동주택관리법·회계처리기준 등 규정 제약을 숙지하고 있습니다. 기획서를 읽으면 테스트 범위를 즉시 구조화할 수 있으며, 누락되기 쉬운 예외 기능·권한 분기·연동 케이스를 빠짐없이 식별합니다. 지금부터 이 기획서를 분석하여 테스트 대상 기능의 계층 구조(메뉴트리)를 추출해주세요.

규칙:
- 모듈 > 화면 > 영역 > 기능 단위로 최대 4단계 계층 구성
  - 1단계(모듈): 회계, 부과, 인사급여, 검침, 입주관리 등 업무 모듈
  - 2단계(화면): 해당 모듈의 개별 화면 (예: 관리비 부과 화면, 미납 조회 화면)
  - 3단계(영역): 화면 내 기능 영역 (예: 검색 조건 영역, 입력 폼 영역, 목록 영역)
  - 4단계(기능): 실제 테스트 대상 기능 단위 (예: 세대번호 입력, 부과 확정 버튼) ← 리프 노드
- 단순한 화면은 2~3단계로 줄여도 무방하나, 복잡한 화면은 반드시 4단계로 세분화
- 각 노드에 id(계층 번호), name(기능명), description(설명), change_type(신규/수정/버그수정/불명) 포함
- 리프 노드(실제 기능, 4단계 또는 마지막 단계)에는 key_points(검증 포인트 목록) 포함
- change_type 값: new_feature | modification | bug_fix | unknown

다음 JSON 형식으로만 응답 (```json 코드블록 없이 순수 JSON만):
{
  "title": "기획서 제목",
  "tree": [
    {
      "id": "1",
      "name": "모듈명",
      "description": "설명",
      "change_type": "new_feature",
      "key_points": [],
      "children": [
        {
          "id": "1-1",
          "name": "화면명",
          "description": "화면 설명",
          "change_type": "new_feature",
          "key_points": [],
          "children": [
            {
              "id": "1-1-1",
              "name": "영역명",
              "description": "영역 설명",
              "change_type": "new_feature",
              "key_points": [],
              "children": [
                {
                  "id": "1-1-1-1",
                  "name": "기능명",
                  "description": "기능 설명",
                  "change_type": "modification",
                  "key_points": ["검증포인트1", "검증포인트2"],
                  "children": []
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}"""


def build_menu_tree(pdf_path: str, ruleset=None) -> Dict:
    """PDF 기획서에서 메뉴트리(계층 구조) 추출"""
    extra = f"\n\n[추가 지침]\n{ruleset.tree_rules}" if ruleset and ruleset.tree_rules else ""
    prompt = TREE_PROMPT + extra

    if is_text_based_pdf(pdf_path):
        text = extract_text_from_pdf(pdf_path)
        if len(text) > 20000:
            text = text[:20000] + "\n\n[이하 생략]"
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL_EXTRACT,
            contents=f"다음은 기획서 내용입니다:\n\n{text}\n\n{prompt}",
        )
    else:
        chunks = pdf_to_base64_chunks(pdf_path, chunk_size=10)
        contents = []
        for chunk_b64 in chunks:
            contents.append({"inline_data": {"mime_type": "application/pdf", "data": chunk_b64}})
        contents.append(prompt)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL_EXTRACT,
            contents=contents,
        )
    return _parse_json_response(response.text)


def generate_tc_from_pdf(pdf_path: str, tc_level: int = 2) -> Dict:
    analysis = analyze_document(pdf_path)
    features = analysis.get("features", [])
    tc_result = generate_testcases(features, tc_level=tc_level)

    return {
        "features": features,
        "testcases": tc_result.get("testcases", []),
    }


def _collect_leaf_nodes(nodes: List[Dict], parent_path: str = "") -> List[Dict]:
    """메뉴트리에서 리프 노드(실제 테스트 대상 기능)를 feature 형식으로 추출"""
    features = []
    for node in nodes:
        current_path = f"{parent_path} > {node['name']}" if parent_path else node["name"]
        children = node.get("children") or []
        if not children:
            features.append({
                "category": current_path,
                "description": node.get("description", ""),
                "key_points": node.get("key_points", []),
                "change_type": node.get("change_type", "unknown"),
                "change_summary": "",
            })
        else:
            features.extend(_collect_leaf_nodes(children, current_path))
    return features


def generate_tc_from_tree(tree: Dict, tc_level: int = 2, ruleset=None) -> Dict:
    """메뉴트리를 기반으로 TC 생성 (PDF 재분석 없음)"""
    features = _collect_leaf_nodes(tree.get("tree", []))
    if not features:
        raise ValueError("메뉴트리에 기능이 없습니다.")
    print(f"[트리 기반 TC생성] {len(features)}개 기능 추출, 룰셋: {ruleset.name if ruleset else '없음'}")
    tc_result = generate_testcases(features, tc_level=tc_level, ruleset=ruleset)
    return {
        "features": features,
        "testcases": tc_result.get("testcases", []),
    }
