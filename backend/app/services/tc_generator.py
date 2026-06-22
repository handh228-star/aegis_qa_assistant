from google import genai
from google.genai import types
import json
from typing import List, Dict
from app.core.config import settings
from app.services.document_parser import (
    extract_text_from_pdf,
    pdf_to_base64_chunks,
    is_text_based_pdf,
)

client = genai.Client(api_key=settings.GOOGLE_API_KEY)

# 모든 추출/생성 응답은 JSON. 응답 형식을 JSON으로 강제해 코드펜스·중간 구문 깨짐을 차단하고,
# 출력 토큰 상한을 크게 잡아 대용량 트리(리프 수백 개)의 truncation을 방지한다.
_JSON_GEN_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    max_output_tokens=65536,
)

# 레벨은 "한 UI 요소·기능당 얼마나 잘게 분해해서 TC를 만들지(분해도)"를 결정한다.
# 개수는 기획서·매뉴얼·결함이력에 근거가 있는 만큼만 나오며, 목표치를 채우려고 추측성 케이스를 만들지 않는다.
# 단, 같은 UI 요소도 레벨이 올라갈수록 정상·비정상·상태조합·권한 등을 더 잘게 분리해 별도 TC로 작성한다.
# 예: "로그아웃 버튼"
#   - Lv.1: 클릭 → 로그아웃 처리 (1건)
#   - Lv.3: 클릭 → 처리 / 로그아웃 확인 팝업의 확인·취소 / 권한별 분기 (3~5건)
#   - Lv.5: 위 + 세션 만료 상태에서 클릭 / 비밀번호 변경 직후 / 다중 탭 동기화 등 (8~15건, 근거 있는 한)
TC_LEVEL_CONFIG = {
    1: {"label": "핵심 검증",
        "depth": "각 UI 요소·기능당 **가장 핵심적인 정상 사용 흐름 1~2건만** 생성하세요. "
                 "기획서에 명시된 대표 실패/거부 케이스 1건만 포함. "
                 "변이·상태 조합·권한 분기는 생략. "
                 "리프 노드 1개당 평균 1~2개 TC."},
    2: {"label": "표준 검증",
        "depth": "각 UI 요소·기능당 **정상 흐름 + 기획서 명시된 주요 비정상/실패 케이스**까지 (보통 2~4건). "
                 "상태 차원이 명백히 영향 미치는 경우에만 핵심 조합 1~2건 추가. "
                 "리프 노드 1개당 평균 2~4개 TC."},
    3: {"label": "정밀 검증",
        "depth": "각 UI 요소·기능당 **정상 + 비정상 + 명시된 상태 분기 + 입력값 경계**까지 (보통 4~7건). "
                 "권한·코드 상태·이력 등 상태 차원이 영향 미치면 의미 있는 모든 조합을 별도 TC로 분리. "
                 "한 UI 요소의 마우스 호버·클릭·표시·포커스 등 인터랙션이 기획서에 언급되면 각각 별도 TC. "
                 "리프 노드 1개당 평균 4~7개 TC."},
    4: {"label": "심층 검증",
        "depth": "위에 더해, 기획서·매뉴얼에 근거가 있는 **조합 케이스·연동 지점·데이터 변형 시나리오**까지 상세히 (보통 6~10건). "
                 "권한 × 상태 × 입력값의 의미 있는 조합을 잘게 분리. "
                 "리프 노드 1개당 평균 6~10개 TC."},
    5: {"label": "전수 검증",
        "depth": "각 UI 요소·기능당 **도출 가능한 모든 변이**를 망라 — 정상·비정상·경계·예외 + 모든 권한 × 상태 × 데이터 조합 (보통 8~15건). "
                 "기획서가 인터랙션(클릭/호버/입력/포커스/표시)을 언급한 모든 경우, 각각 별도 TC로 분해. "
                 "같은 액션이라도 사전조건(상태)이 다르면 별도 TC. "
                 "단, 어디까지나 기획서·매뉴얼·결함이력에 근거가 있는 변이만. 근거 없는 추측성 케이스는 여전히 금지. "
                 "리프 노드 1개당 평균 8~15개 TC."},
}

ANALYZE_PROMPT = """당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템(회계·부과·인사급여·검침·입주관리·전자결재·커뮤니티·민원·문의관리 등 다양한 업무 모듈)에 정통합니다. 기획서를 보면 어떤 업무 규칙이 관여되는지, 어디서 데이터 오류나 권한 오류가 발생할 수 있는지, 어떤 연동 케이스를 놓치기 쉬운지를 직관적으로 파악합니다. 지금부터 이 문서를 분석하여 테스트해야 할 기능 목록을 추출해주세요.

[중요 — category 명명 원칙]
- category는 **기획서 본문에 명시된 실제 사이트 메뉴 경로**(예: "수납 > 미납조회 > 미납대장" 같은 breadcrumb)를 그대로 사용하세요.
- 본문에 "A > B > C > D", "게재 위치 : ...", "메뉴 경로 : ..." 같은 표기가 있으면 그것이 가장 신뢰할 수 있는 카테고리 출처입니다.
- 파일명·표지의 분류 라벨(예: "전자결재")은 QA팀 그룹명일 수 있고 실제 사이트 메뉴와 다를 수 있습니다. 본문 breadcrumb이 있으면 그쪽을 우선합니다.
- "회계", "관리" 같은 추상적 상위 분류로 임의 분류하지 마세요.

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

TC_GENERATE_PROMPT = """당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템(회계·부과·인사급여·검침·입주관리·전자결재·커뮤니티·민원·문의관리 등 다양한 업무 모듈)에 정통합니다. 경계값 분석, 동등 분할, 탐색적 테스트, 결함 예측 기법을 실무에서 적극 활용하며, 실제 운영 환경에서 관리자·입주자·회계담당자가 마주칠 수 있는 문제를 사전에 발견하는 것을 최우선으로 합니다. 아래 기능 하나에 대해 테스트케이스(TC)를 생성해주세요.

대상 기능:
{feature}

[이 기획서의 상태 매트릭스 — 매우 중요. TC 생성 시 반드시 고려]
{state_matrix}

[상태 매트릭스 활용 원칙 — 적용 가능 여부 먼저 판단, 무차별 적용 금지]

**Step 1 — 적용 가능성 게이팅 (가장 중요)**
상태 매트릭스를 이 기능에 적용하기 전, 먼저 다음 조건을 모두 확인하세요:
  (a) 이 기능이 **사용자가 직접 조작·확인하는 UI 요소**인가? (버튼, 입력란, 체크박스, 표시 영역 등)
       → NO (예: 백엔드 API 노드, 시스템 검증 로직 노드)면 **상태 매트릭스 적용하지 마세요.** 일반 TC도 만들지 마세요 — 이런 노드는 트리에 있어서는 안 되며, 있더라도 사용자 행위 단위가 아니므로 TC 생성 대상이 아닙니다.
  (b) 위 상태 매트릭스의 각 차원에 `affects` 필드가 있습니다. **이 기능의 category·name과 `affects`에 명시된 화면·기능이 직접 매칭되는 차원만** 사용하세요. 매칭 안 되면 그 차원은 이 기능에 영향 없음.
  (c) 차원이 매칭돼도 의미 있는 조합만. 예: 권한 3종 × 코드 3종 = 9개를 무조건 만들지 말고, 기획서가 명시한 분기 흐름만 (보통 3~5개).

**Step 2 — 차원 매칭이 안 되면 일반 TC만 생성**
이 기능에 영향 미치는 차원이 없다고 판단되면, **상태 조합 TC는 0건**입니다. 일반 정상/비정상 케이스만 만드세요. 억지로 상태를 끼워 넣지 마세요.

**Step 3 — 차원이 매칭되면 사전조건으로 분리**
  - **의미 있는 상태 조합 × 사용자 액션 = 별도 TC 1건.** 동일 액션이라도 상태가 다르면 별도 TC로 분리.
  - 사전조건(preconditions)에 상태 조합을 명시적으로 적습니다. (예: "사용자 권한이 '사용안함' 상태")
  - 차원 1개의 모든 값(예: 권한 3종)에 대해 TC를 만드는 게 기본이지만, 기대결과가 같으면 묶을 수 있습니다 (예: 권한 '읽기만'·'사용안함' 모두 같은 알럿 → 한 TC에 사전조건 OR로 묶기 또는 대표 1건만).

예시 1 — 적용 O: "알림톡 안내문 발송하러 가기 버튼 선택" (UI 액션, '권한' 차원 affects 매칭)
  - TC: 권한이 '읽기만' 또는 '사용안함' 상태 → 알럿팝업 출력 ("…사용자만 발송 가능합니다.")
  - TC: 권한이 '읽기/쓰기' 상태 → 알림톡 발송 팝업 출력

예시 2 — 적용 X: "팝업 타이틀 텍스트 표시" (단순 표시 요소, 상태 차원 영향 없음)
  - TC: 팝업 타이틀이 기획서 명시 문구대로 출력 (1건)
  - 권한별/코드별 TC 만들지 마세요. 모든 상태에서 동일하게 표시됨.

예시 3 — 적용 X (절대 금지): "시스템 > 동호 검증 API" (백엔드 노드, UI 아님)
  - 이런 노드는 TC 생성 대상이 아닙니다. 동호 검증의 결과 분기는 해당 신청 화면 TC의 사전조건·기대결과로 표현되어야 합니다.

{rag_context}

TC 생성 전략 (change_type 기준):
- new_feature (신규 기능): 정상/비정상/경계값/예외를 포괄적으로 생성
- modification (기능 수정): 변경된 동작 검증 TC + 기존 연관 기능 회귀 테스트 TC 포함
- bug_fix (버그 수정): 수정된 버그 재현 방지 케이스 집중 + 유사 시나리오 포함
- unknown: 포괄적으로 생성

[TC 유형(tc_type) 분류 결정 규칙 — 위에서 아래로 순서대로 적용. 첫 매치에서 멈춤]
Q1. 측정 가능한 수치 경계를 검증하는가? (입력 길이, 파일 크기, 개수, 날짜·시간 경계 등)
    → YES: **boundary**. 단, 기획서가 그 경계값을 명시한 경우에만 생성.
Q2. 시스템적 예외 상황을 검증하는가? (외부 API 실패, 시스템 장애, 통신 지연 폴백 등)
    → YES: **exception**. 단, 기획서가 그 상황을 명시한 경우에만 생성.
Q3. 사용자가 형식·필수 입력을 어겨 발생하는 거부인가? (잘못된 형식의 동/호 입력, 필수 누락, 잘못된 형식의 휴대폰번호 등)
    → YES: **negative**
Q4. 그 외 모두 — 시스템이 기획서대로 동작하는 케이스 (정상 흐름 + 정책상 차단)
    → **positive**

[정책상 차단도 positive입니다 — 매우 중요한 명시]
- 다음 케이스들은 사용자 실수가 아니라 시스템이 기획된 정책대로 정상 동작하는 것이므로 모두 **positive**입니다:
  · 권한이 '사용안함'/'읽기만'인 사용자가 발송 버튼 클릭 → 권한 안내 알럿 (정책: 권한 검증)
  · 이미 신청한 세대가 재신청 시도 → 중복 신청 안내 (정책: 중복 방지)
  · 대상 외 단지 사용자 접근 → 미노출/안내 페이지 (정책: 대상 단지 검증)
  · 정보 불일치 상태에서 신청 → "일치하지 않아요" 토스트 (정책: 본인 검증)
  · 미계약/해지 코드 → 신청 불가 안내 (정책: 계약 상태 검증)
- 이런 상태 변이는 **사전조건(preconditions)에 명시**해 같은 액션의 positive TC들을 구분하세요.
- 사람 QA 표준: 같은 액션 + 다른 상태 = 같은 positive 유형, 다른 사전조건, 다른 기대결과로 별도 TC 분리.

[TC 우선순위(priority) 결정 규칙 — 엄격히 적용]
priority는 케이스의 중요도가 아니라 **"실패 시 다른 TC 검증까지 막히는 정도"** 로 판단합니다. 모든 TC를 high로 찍지 마세요. 실제 분포는 **high 5~15%, medium 60~75%, low 15~30%** 가 정상입니다.

- **high — Smoke 게이트 케이스만** (전체의 5~15%):
  · 메뉴 진입·화면 로딩·기본 표시 같은 **진입점** TC (예: "미납대장 메뉴 클릭 → 미납대장 화면이 정상 표시되는가")
  · 핵심 정책 게이트 (예: "유효한 QR 스캔 → 신청 페이지 진입") — 이게 깨지면 그 뒤 모든 TC 검증이 불가능
  · 신청·해지 완료 같은 **메인 비즈니스 종료 동작** (해당 흐름의 마지막 단계)
  · 판단 기준: "이 TC가 실패하면 같은 화면의 다른 TC들도 의미가 없어진다"

- **medium — 일반 검증** (전체의 60~75%, 가장 많아야 함):
  · 정상 흐름의 개별 단계 (입력란 입력·체크박스 토글·버튼 클릭으로 다음 단계 진입 등)
  · 주요 비정상 케이스 (정보 불일치, 권한 부족, 중복 신청 등)
  · 정책 차단 분기 검증
  · 사용자가 실제로 마주칠 만한 모든 상호작용
  · 판단 기준: "이 TC가 실패해도 다른 TC는 독립적으로 검증 가능"

- **low — 보조·표시·드문 예외** (전체의 15~30%):
  · 단순 라벨·문구·툴팁·placeholder 정확도 검증
  · 시각적 표시 디테일 (아이콘·색상·정렬 — 기획서가 명시한 경우만)
  · 자주 발생하지 않는 예외 시나리오
  · 닫기·취소 같은 보조 액션
  · 판단 기준: "이게 틀려도 비즈니스 영향이 작고 다른 TC와 무관"

[금지]
- 신규 기능이라고 해서 모든 TC를 high로 찍지 마세요. 신규 기능 안에서도 진입점·메인·보조의 위계가 있습니다.
- "이거 중요한 TC인 것 같으니 high" 식의 직감적 판단 금지. 위 결정 기준에 명시적으로 매칭되는지 확인하세요.

[가장 중요한 원칙 — 근거 기반 생성]
- TC 개수에는 목표치나 할당량이 없습니다. 위 검증 깊이 안에서, 기획서·업무 규칙·매뉴얼 스펙·결함 이력에 실제 근거가 있는 케이스만 생성하세요.
- 근거가 빈약하면 케이스 수가 적어도 됩니다. 억지로 채우지 말고, 의미 있고 검증 가치가 있는 케이스만 남기세요.
- "혹시 모르니" 식의 추측성 가정, 기획서 범위를 벗어난 일반론적 예외는 금지합니다.

[다음 유형의 케이스는 절대 만들지 마세요 — 기획서에 명시·암시가 있을 때만 예외적으로 허용]
1. 인프라/환경 추측: 세션 만료, 네트워크 끊김, Wi-Fi 비활성화, 타임아웃, API 응답 지연, OS 오류, 동시성/병렬 처리, 브라우저 뒤로가기 외 일반 동작
2. 브라우저/UI 일반론: 새로고침(F5/Ctrl+R) 시 동작, 다국어 표시, 브라우저 호환성, 반응형 레이아웃, 팝업 크기 변경(최대화/최소화), 탭 전환, 오래된 브라우저
3. 스펙 미명시 경계값: 기획서에 길이·크기·개수 제약이 명시되지 않은 항목에 대한 "최대 길이/최대 파일 크기/최대 입력 개수 초과" 케이스
4. 일반 텍스트 검수: 오탈자/띄어쓰기/문법 오류 확인, 글머리 기호 포맷, 특수문자(@#$%^&*) 노출 확인, "기획서에 명시되지 않은 특수 문자" 처리
5. 백오피스 가정: 이미지/파일이 "비정상 파일 형식·손상·없음" 일 때의 처리 — 해당 업로드/등록 기능이 기획서 범위에 포함될 때만 허용
6. 메타-검수: "시각적으로 명확하게 구분되는지", "사용자에게 유용한 정보 제공", "가독성을 해치지 않는지" 같은 주관적·디자인 평가성 TC

[기획서 문구 인용 — 매우 중요]
- 기대결과(expected, expected_result)와 사전조건(preconditions)에는 가능한 한 기획서의 **실제 문구·라벨·메시지·버튼명**을 그대로 인용하세요.
- "정확하게 표시되는지 확인", "정상적으로 표시된다", "명확하게 구분된다" 같은 **추상적·동어반복적 표현은 금지**합니다.
- 좋은 예: 기대결과에 `"신청가능 정보와 일치하지 않아요." 토스트 팝업이 출력된다 (3초 후 페이드 아웃)` 처럼 기획서의 정확한 문구를 인용.
- 나쁜 예: `"오류 메시지가 정확하게 표시된다"`, `"안내 문구가 명확하게 노출된다"`.
- 기획서 원문을 알 수 없으면 그 자리에 `<기획서 인용 필요>` 라고 명시하세요 (추상화하지 말 것).

[상태 분기를 사전조건으로 표현 — 권장 패턴]
- 권한(읽기만/사용안함/읽기쓰기), 외부 코드 상태(유효/미계약/해지), 데이터 이력(미신청/기신청/해지내역), 정보 일치 여부 같은 **상태 차원**은 동일 액션이라도 사전조건을 달리해 별도 TC로 분리하세요.
- 한 TC = 하나의 (상태 조합 × 사용자 액션 × 기대결과). 다층적·복합적 TC 한 개로 묶지 말고 잘게 나누는 것이 사람 작성 TC의 표준 패턴입니다.

공통 요구사항:
- 이 기능의 TC만 생성 (다른 기능 포함 금지)
- 정상/비정상/경계값/예외 유형은 기능 특성에 따라 자연스럽게 분포시키세요. 특정 비율을 맞추려고 비정상·경계값·예외 케이스를 억지로 만들지 마세요.
- 각 TC는 명확하고 재현 가능한 단계로 작성할 것
- 매뉴얼 스펙이 있다면 실제 스펙(입력값 조건, 제약, 오류 메시지 등)을 TC에 반영할 것
- 과거 결함 이력이 있다면 해당 기능의 관련 비정상/경계값/예외 케이스를 강화할 것
- TC ID는 {tc_id_start}번부터 순서대로 부여 (TC-{tc_id_start:03d} 형식)
- 품질이 우선이므로 의미 없는 케이스는 만들지 마세요

[기획서 페이지 출처(spec_page) — 노드 값을 그대로 상속]
- 위 [대상 기능]의 JSON에 `spec_page` 값이 들어 있습니다. 이 값은 기획서를 직접 보고 추출 단계에서 확정한 출처 페이지입니다.
- **모든 TC의 `spec_page`에는 이 노드의 spec_page 값을 그대로 복사하세요.** 새로 페이지를 추론하거나 지어내지 마세요.
- 노드의 spec_page가 비어 있으면("") TC의 spec_page도 빈 문자열("")로 두세요. **절대 임의의 숫자나 필드명·설명 문구("key_points", "description" 등)를 채워 넣지 마세요.**

다음 JSON 형식으로만 응답해주세요 (```json 코드블록 없이 순수 JSON만):
{{
  "testcases": [
    {{
      "tc_id": "TC-{tc_id_start:03d}",
      "category": "기능 카테고리",
      "title": "TC 제목",
      "objective": "테스트 목적",
      "spec_page": "위 [대상 기능] 노드의 spec_page 값을 그대로 복사 (비어 있으면 \"\")",
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
    text = (text or "").strip()

    # 코드블록 제거 (JSON 모드에선 안 나오지만 안전하게 유지)
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    start = text.find("{")
    if start == -1:
        raise ValueError(f"JSON 객체를 찾을 수 없습니다. 원본 응답:\n{original[:500]}")

    body = text[start:]
    end = body.rfind("}") + 1
    json_str = body[:end] if end > 0 else body

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as first_err:
        # 잘린 응답(max token 초과 등) 복구 시도: 마지막 완결 컨테이너에서 끊고 열린 괄호를 닫는다.
        repaired = _repair_truncated_json(body)
        if repaired is not None and repaired != json_str:
            try:
                result = json.loads(repaired)
                print(f"  [JSON 복구] 잘린 응답을 복구해 파싱 성공 "
                      f"({len(body):,}자 → {len(repaired):,}자). 일부 후행 노드가 누락됐을 수 있음.")
                return result
            except json.JSONDecodeError:
                pass
        raise ValueError(f"JSON 파싱 실패: {first_err}\n원본 응답:\n{original[:500]}")


def _repair_truncated_json(s: str):
    """잘린 JSON을 마지막으로 완결된 컨테이너 경계에서 끊고, 열린 괄호를 닫아 복구한다.

    트리/TC 응답이 출력 토큰 한도로 중간에 잘렸을 때, 완전히 닫힌 노드들만 살리고
    잘린 후행 노드는 버린 뒤 유효한 JSON으로 만든다. 복구 불가하면 None.
    """
    stack = []          # 열린 컨테이너 opener 문자 ('{' 또는 '[')
    in_string = False
    escape = False
    cut = -1            # 마지막 안전 경계(컨테이너가 완결된 직후 인덱스)
    cut_stack = None    # 그 경계 시점에 아직 열려 있는 컨테이너 스냅샷

    for i, ch in enumerate(s):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            cut = i + 1
            cut_stack = list(stack)

    if cut == -1 or cut_stack is None:
        return None

    prefix = s[:cut].rstrip()
    closers = "".join("}" if c == "{" else "]" for c in reversed(cut_stack))
    return prefix + closers


def _analyze_text_based(pdf_path: str) -> Dict:
    text = extract_text_from_pdf(pdf_path)
    if len(text) > 20000:
        text = text[:20000] + "\n\n[이하 생략]"

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL_EXTRACT,
        contents=f"다음은 기획서 내용입니다:\n\n{text}\n\n{ANALYZE_PROMPT}",
        config=_JSON_GEN_CONFIG,
    )
    print(f"[ANALYZE 응답 원본]\n{response.text[:300]}\n---")
    return _parse_json_response(response.text)


def _analyze_image_based(pdf_path: str) -> Dict:
    chunks = pdf_to_base64_chunks(pdf_path, chunk_size=5)
    all_features = []

    for chunk_b64 in chunks:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL_EXTRACT,
            contents=[
                {"inline_data": {"mime_type": "application/pdf", "data": chunk_b64}},
                ANALYZE_PROMPT,
            ],
            config=_JSON_GEN_CONFIG,
        )
        result = _parse_json_response(response.text)
        all_features.extend(result.get("features", []))

    return {"features": all_features}


def analyze_document(pdf_path: str) -> Dict:
    if is_text_based_pdf(pdf_path):
        return _analyze_text_based(pdf_path)
    else:
        return _analyze_image_based(pdf_path)


def _generate_content_with_retry(
    prompt,
    max_retries: int = 2,
    model: str = None,
    fallback_model: str = None,
    config=_JSON_GEN_CONFIG,
) -> str:
    """503/429 등 일시적 오류 시 재시도. primary 모델 소진 시 fallback 모델로 자동 전환.

    동작 흐름 (예: primary=flash, fallback=flash-lite, max_retries=2):
      1) primary 1차 호출 → 성공? 종료
      2) 503/429 → 30초 대기
      3) primary 2차 → 성공? 종료
      4) 503/429 + fallback 지정됨 → fallback 모델로 전환 + max_retries 만큼 재시도
      5) fallback도 실패 → raise

    품질을 우선시하므로 primary가 먼저 충분히 시도된 뒤에만 fallback 발동.
    일시적이지 않은 에러(404 모델명 오류 등)는 재시도 없이 즉시 raise.

    prompt: 문자열 또는 contents 리스트(PDF 청크 등)
    model: primary 모델 (기본값: TC 생성 모델)
    fallback_model: primary 소진 시 사용할 모델 (None이면 폴백 안 함)
    """
    import time
    model = model or settings.GEMINI_MODEL_TC

    def _is_transient(err_str: str) -> bool:
        return (
            "503" in err_str or "UNAVAILABLE" in err_str
            or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
        )

    def _try_model(active_model: str, label: str) -> str:
        wait = 30
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=active_model,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except Exception as e:
                err = str(e)
                if _is_transient(err) and attempt < max_retries - 1:
                    print(f"  [{label} 재시도 {attempt+1}/{max_retries-1}] {err[:80]} → {wait}초 대기...")
                    time.sleep(wait)
                    wait = min(wait * 2, 120)
                else:
                    raise

    try:
        return _try_model(model, f"primary({model})")
    except Exception as primary_err:
        if _is_transient(str(primary_err)) and fallback_model and fallback_model != model:
            print(f"  [폴백 전환] {model} → {fallback_model} (primary {max_retries}회 모두 실패)")
            return _try_model(fallback_model, f"fallback({fallback_model})")
        raise


def generate_testcases(features: List[Dict], use_rag: bool = True, tc_level: int = 2, ruleset=None, on_progress=None, state_inventory: Dict = None) -> Dict:
    from app.services.rag_service import build_rag_context

    level_cfg = TC_LEVEL_CONFIG.get(tc_level, TC_LEVEL_CONFIG[2])
    all_testcases = []
    tc_counter = 1

    state_matrix_text = format_state_inventory_for_prompt(state_inventory or {})
    n_dims = len((state_inventory or {}).get("state_dimensions", []))
    if n_dims:
        print(f"[TC생성] 상태 매트릭스 {n_dims}개 차원 활용")

    for i, feature in enumerate(features):
        rag_context = ""
        if use_rag:
            raw_context = build_rag_context([feature.get("category", "")])
            if raw_context:
                rag_context = f"참고 매뉴얼 내용 (실제 서비스 스펙):\n{raw_context}"

        ruleset_hint = ""
        if ruleset and ruleset.tc_rules:
            ruleset_hint = (
                "\n\n[QA 룰셋 추가 지침 — 보조 가이드]\n"
                "아래 항목은 본 프롬프트의 원칙(근거 기반 생성·추측성 금지·기획서 문구 인용·개수 할당 없음)을 보충하는 관점 가이드입니다. "
                "본 프롬프트의 원칙과 충돌하는 항목이 있으면 본 프롬프트가 우선합니다. "
                "특히 룰셋이 '체크리스트', '빠짐없이', '경계값', '특수문자' 같은 항목을 나열하더라도, 기획서·매뉴얼·결함이력에 해당 제약·문구가 명시되지 않으면 그 케이스는 만들지 마세요.\n\n"
                f"{ruleset.tc_rules}"
            )

        prompt = (
            TC_GENERATE_PROMPT
            .replace("{feature}", json.dumps(feature, ensure_ascii=False, indent=2))
            .replace("{state_matrix}", state_matrix_text)
            .replace("{rag_context}", rag_context + ruleset_hint)
            .replace("{level}", str(tc_level))
            .replace("{level_label}", level_cfg["label"])
            .replace("{level_depth}", level_cfg["depth"])
            .replace("{tc_id_start:03d}", f"{tc_counter:03d}")
            .replace("{tc_id_start}", str(tc_counter))
        )

        print(f"[TC생성] 기능 {i+1}/{len(features)}: {feature.get('category', '')} (TC-{tc_counter:03d}~)")
        try:
            text = _generate_content_with_retry(
                prompt,
                fallback_model=settings.GEMINI_MODEL_TC_FALLBACK or None,
            )
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
            # category는 모델이 임의로 작명하지 않도록 리프 노드 전체 경로로 강제.
            # 이 값이 트리 노드 ↔ TC 매핑의 안정적인 키가 된다 (트리 커버리지 표시·추적성).
            tc["category"] = feature.get("category") or tc.get("category", "")
            tc_counter += 1

        all_testcases.extend(tcs)
        print(f"  → {len(tcs)}개 생성 (누적 {len(all_testcases)}개)")

        if on_progress:
            on_progress(i + 1, len(features), len(all_testcases))

    return {"testcases": all_testcases}


REGENERATE_PROMPT = """다음 테스트케이스를 검토 의견을 반영하여 개선해주세요.

기존 TC:
{tc_data}

검토 의견: {review_note}

동일한 JSON 형식으로 개선된 TC 1개를 반환해주세요 (```json 코드블록 없이 순수 JSON만).
spec_page(기획서 페이지 출처)는 기존 값을 유지하고, 검토 의견에서 페이지 변경 요청이 있을 때만 수정하세요.
{{
  "tc_id": "...",
  "category": "...",
  "title": "...",
  "objective": "...",
  "spec_page": "...",
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


TREE_PROMPT = """당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템(회계·부과·인사급여·검침·입주관리·전자결재·커뮤니티·민원·문의관리 등 다양한 업무 모듈)에 정통합니다. 기획서를 읽으면 테스트 범위를 즉시 구조화할 수 있습니다. 지금부터 이 기획서를 분석하여 테스트 대상 기능의 계층 구조(메뉴트리)를 추출해주세요.

[중요] 기획서에 실제로 기술된 화면·기능만 트리에 포함하세요. 기획서에 없는 화면이나 기능을 "일반적으로 있을 법한 것"으로 추측해 추가하지 마세요. 트리는 기획서의 구조를 충실히 반영하는 것이지, 시스템 전체를 망라하는 것이 아닙니다.

[모듈/화면 경로 결정 원칙 — 매우 중요. 다음 우선순위를 반드시 지키세요]

1순위 — 기획서 본문의 메뉴 경로(breadcrumb):
  기획서 페이지에 "A > B > C > D" 또는 "A > B > C" 형식으로 명시된 메뉴 경로가 있다면, **이것이 실제 사이트의 메뉴 네비게이션이며 가장 신뢰할 수 있는 근거**입니다. 이 경로를 트리 1~3단계로 그대로 사용하세요.
  - 예: 기획서에 "XpERP > 수납 > 미납조회 > 미납대장" 이라고 적혀 있으면, 1단계=수납, 2단계=미납조회, 3단계=미납대장. (제품명 XpERP는 멀티 채널 구분이 필요할 때만 별도 표기)
  - 페이지 상단 헤더, "게재 위치 : ...", "메뉴 경로 : ..." 같은 표기를 적극적으로 찾으세요.

2순위 — 기획서 본문의 화면 제목·섹션 헤더:
  breadcrumb이 없으면 본문에서 명시적으로 쓰인 화면명·섹션명을 그대로 발췌.

3순위 — 파일명/표지(가장 약한 단서):
  위 둘 다 없을 때만 파일명에서 추론. 파일명은 종종 제품군·작업명·기능명을 담을 뿐 실제 메뉴 경로가 아닐 수 있으므로 본문 정보가 있으면 항상 본문이 우선합니다.

[하지 말 것]
- "회계", "부과", "관리" 같은 추상적 상위 분류로 끌어올리지 마세요. 기획서가 명시하지 않은 상위 모듈을 임의로 추가하지 마세요.
- 화면명에 "...화면", "...메뉴", "(XpERP)" 같은 임의 접미사를 붙이지 마세요. 기획서가 "미납대장" 이라고만 하면 그대로 "미납대장"으로 적습니다. (같은 화면이 XpERP/XpBIZ 양 채널에 존재해 구분이 필요할 때만 채널명을 별도 노드로 분리)
- 파일명 토큰(예: "전자결재")이 본문 메뉴 경로(예: "수납 > 미납조회 > 미납대장")와 다르면 본문을 우선합니다. 파일명은 QA팀 분류 라벨일 수 있고 실제 사이트 메뉴가 아닐 수 있습니다.

[절대 금지 — 백엔드/시스템 로직을 트리 노드로 만들지 마세요]
메뉴 트리는 **사용자가 실제로 보거나 조작하는 화면 요소만** 담는 사이트 메뉴 구조입니다. 화면 뒤에서 일어나는 동작은 트리에 포함하지 마세요.

다음 이름·패턴의 노드는 **절대 만들지 마세요** (1단계 모듈이든 하위 노드든):
- "시스템", "백엔드", "서버", "내부 로직", "비즈니스 로직"
- "XX API", "XX 호출", "XX 응답", "XX 검증 로직"
- "XX 프로세스", "XX 처리 흐름", "XX 단계"
- "XX 정책", "XX 규칙", "XX 정합성 검증"
- "XX DB", "XX 데이터 흐름"

기획서의 "프로세스 요약" 섹션이나 API 호출 명세는 트리 추출의 참고 정보일 뿐, **트리 노드로 직접 매핑하지 마세요.** 이런 백엔드 동작의 결과 분기(예: API가 미계약 코드 반환, 검증 실패 등)는 **해당 사용자 화면의 사전조건·기대결과·key_points로 표현**됩니다.

올바른 처리 예시:
- ❌ 잘못: 1단계 "시스템" > 2단계 "동호 검증 API"
- ✅ 옳음: "동호 검증 API"의 결과 분기(일치/불일치)는 해당 신청 화면의 key_points와 사전조건에 명시되고, 실제 트리는 사용자 화면(예: "신청 정보 입력 바텀시트")까지만.

1단계 모듈은 **사이트의 실제 사용자 화면 진입점**이어야 합니다 (예: "수납", "입주민 모바일 웹", "관리자", "마이페이지" 등). "시스템"·"API" 같은 1단계 모듈이 등장했다면 그 자체가 잘못된 분류입니다.

규칙:
- 모듈 > 화면 > 영역 > 기능 단위로 최대 4단계 계층 구성. 단계 수는 기획서 메뉴 경로의 깊이에 맞추세요.
  - 1단계(최상위 모듈): 본문 breadcrumb의 첫 마디 (예: "수납")
  - 2단계(중간 분류): breadcrumb의 두번째 마디 (예: "미납조회")
  - 3단계(화면): breadcrumb의 세번째 마디 (예: "미납대장")
  - 4단계(기능/영역): 화면 내 테스트 대상 기능 단위 (예: "간편전자고지서 QR 안내문 다운로드 버튼") ← 리프 노드

[리프 노드 분해 원칙 — 매우 중요. TC 양과 직결됨]
리프 노드(트리의 끝 노드)는 사용자가 실제로 보거나 조작하는 **최소 단위 UI 요소**여야 합니다. 한 화면 안에 여러 요소가 있으면 각각 별도 리프로 분리하세요.

- 기획서가 언급한 UI 요소를 **모두** 별도 리프로 분리:
  · 입력란/검색창/날짜선택/체크박스/라디오/드롭다운 — 각각 별도 리프
  · 버튼(조회·저장·취소·삭제·전송·확인·닫기·X 등) — **버튼 1개 = 리프 1개**
  · 표시 영역(타이틀·라벨·카운트·툴팁·플레이스홀더·안내 문구) — 별도 리프
  · 팝업/모달/바텀시트의 내부 요소(타이틀·서브카피·본문·각 버튼) — 각각 별도 리프
  · 리스트·테이블의 행 / 카드 UI / 탭 / 아코디언 — 각각 별도 리프

- **잘못된 묶음 예시 (절대 금지)**:
  ❌ "내정보" 한 리프로 묶음 → ✅ "내정보 드롭다운 토글", "마이페이지 링크", "로그아웃 버튼", "프로필 사진 표시"로 분리
  ❌ "헤더" 한 리프로 묶음 → ✅ 헤더 안의 로고·메뉴검색·알림·내정보·로그아웃 각각 별도 리프
  ❌ "다운로드 팝업" 한 리프로 묶음 → ✅ 팝업 내부의 타이틀·안내문·다운로드 버튼·닫기 버튼 각각 별도 리프

- **분해의 한계**: 기획서가 실제로 언급한 요소만. 기획서에 없는 일반적인 UI 요소(예: "기본적으로 있을 법한 도움말 아이콘")를 추측으로 추가하지 마세요. 기획서가 5개 요소를 그림·텍스트로 명시하면 리프 5개, 10개를 명시하면 리프 10개.

- 계층 깊이: 기획서 구조에 맞춰 자연스럽게. 한 화면에 분해 가능한 UI 요소가 많으면 4단계로 깊어지는 게 정상입니다 (영역 단위로 묶고 그 안에 UI 요소 리프). 단순 화면은 2~3단계로 충분.

- 각 노드에 id(계층 번호), name(기능명), description(설명), change_type(신규/수정/버그수정/불명) 포함
- 리프 노드에는 key_points(검증 포인트 목록) 포함 — 그 요소에서 검증해야 할 핵심 동작·상태
- change_type 값: new_feature | modification | bug_fix | unknown

[spec_page — 기획서 출처 페이지, 리프 노드 필수]
- 리프 노드에는 spec_page를 채워, 그 요소가 기획서의 몇 페이지에 나오는지 명시하세요 (예: "5", "5-6", "8").
- **지금 기획서를 직접 보고 있으므로 반드시 실제 페이지를 적을 수 있습니다.** 기획서에 페이지 번호 표기가 있으면 그 번호를, 없으면 PDF 페이지 인덱스(1부터 시작)를 적습니다.
- 여러 페이지에 걸친 요소면 "5-7"처럼 범위로 적습니다.
- 출처 페이지를 도저히 특정할 수 없으면 빈 문자열("")로 두세요. **추측으로 아무 값이나, 또는 필드명·설명 문구를 적지 마세요.**
- 상위(비-리프) 노드의 spec_page는 빈 문자열("")로 둡니다.

다음 JSON 형식으로만 응답 (```json 코드블록 없이 순수 JSON만):
{
  "title": "기획서 제목",
  "tree": [
    {
      "id": "1",
      "name": "모듈명",
      "description": "설명",
      "change_type": "new_feature",
      "spec_page": "",
      "key_points": [],
      "children": [
        {
          "id": "1-1",
          "name": "화면명",
          "description": "화면 설명",
          "change_type": "new_feature",
          "spec_page": "",
          "key_points": [],
          "children": [
            {
              "id": "1-1-1",
              "name": "영역명",
              "description": "영역 설명",
              "change_type": "new_feature",
              "spec_page": "",
              "key_points": [],
              "children": [
                {
                  "id": "1-1-1-1",
                  "name": "기능명",
                  "description": "기능 설명",
                  "change_type": "modification",
                  "spec_page": "5",
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


STATE_INVENTORY_PROMPT = """당신은 10년 이상 경력의 QA 전문가입니다. 기획서 전체를 읽고, TC 생성의 핵심 변수가 되는 "상태 차원(state dimensions)"을 도출하세요.

[상태 차원이란]
동일한 사용자 액션이라도 결과를 다르게 만드는 외부 조건의 집합입니다. 사람이 작성하는 우수한 TC는 각 상태 조합마다 별도 케이스로 분리되어 있습니다.

전형적인 상태 차원의 예:
- **사용자 권한**: 읽기만 / 사용안함 / 읽기쓰기 (같은 버튼이라도 권한별로 동작 분기)
- **외부 코드/계약 상태**: 유효 / 미계약 / 해지 / 에러 (같은 인증이라도 결과 분기)
- **이력/신청 상태**: 미신청 / 기신청 / 해지내역 있음 / 해지내역 없음
- **정보 일치 여부**: 일치 / 불일치
- **세션/연결 상태**: 정상 / 외부 시스템 오류 (기획서가 명시한 경우에만)
- **데이터 존재 여부**: 데이터 있음 / 없음 (기획서가 빈 데이터 동작을 명시한 경우)

[근거 기반 원칙 — 매우 중요]
- 기획서·매뉴얼이 명시·암시한 상태 차원·값만 도출하세요. 일반론적 추측 금지.
- "정상/오류" 같은 추상 차원은 만들지 마세요. **구체적 도메인 상태**만 도출.
- 한 차원의 값은 기획서가 명시한 표현 그대로 (예: "사용안함", "1004 에러" 등).
- 페이지 번호(spec_page)를 반드시 명시 — 그 상태가 기획서 어느 페이지에 나오는지.

[출력 형식 — 순수 JSON만, 코드블록 없이]
{
  "state_dimensions": [
    {
      "name": "상태 차원 이름 (예: 사용자 권한)",
      "spec_page": "기획서 페이지 번호 (예: '5', '5-6')",
      "description": "이 차원이 의미하는 바",
      "values": [
        {
          "value": "상태값 (기획서 표현 그대로)",
          "description": "이 상태의 의미·조건",
          "expected_behavior": "이 상태에서의 예상 동작 (기획서 명시 내용)"
        }
      ],
      "affects": "이 상태 차원이 영향을 미치는 화면·기능 (간단히)"
    }
  ]
}

상태 차원이 전혀 없다고 판단되면 `{"state_dimensions": []}` 로 응답하세요."""


def extract_state_inventory(pdf_path: str, original_filename: str = None, ruleset=None) -> Dict:
    """PDF 전체에서 도메인 상태 차원(권한·코드 상태·이력 등)을 추출.

    TC 생성 시 모든 feature에 주입되어, 상태 매트릭스 × 액션 = 별도 TC 분리를 유도한다.
    실패 시 빈 상태 인벤토리 반환 (전체 파이프라인은 계속 진행).
    """
    prompt = STATE_INVENTORY_PROMPT
    if ruleset and ruleset.tree_rules:
        # 룰셋의 트리 규칙에 상태 분기 관련 힌트가 있으면 보조 사용 (현재는 가벼운 참고용)
        pass

    filename_hint = ""
    if original_filename:
        filename_hint = f"[기획서 원본 파일명] {original_filename}\n\n"

    try:
        if is_text_based_pdf(pdf_path):
            text = extract_text_from_pdf(pdf_path)
            if len(text) > 20000:
                text = text[:20000] + "\n\n[이하 생략]"
            response_text = _generate_content_with_retry(
                f"{filename_hint}다음은 기획서 내용입니다:\n\n{text}\n\n{prompt}",
                model=settings.GEMINI_MODEL_EXTRACT,
                fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
            )
        else:
            chunks = pdf_to_base64_chunks(pdf_path, chunk_size=10)
            contents = []
            for chunk_b64 in chunks:
                contents.append({"inline_data": {"mime_type": "application/pdf", "data": chunk_b64}})
            contents.append(filename_hint + prompt if filename_hint else prompt)
            response_text = _generate_content_with_retry(
                contents,
                model=settings.GEMINI_MODEL_EXTRACT,
                fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
            )
        result = _parse_json_response(response_text)
        dims = result.get("state_dimensions", []) if isinstance(result, dict) else []
        return {"state_dimensions": dims}
    except Exception as e:
        print(f"[상태 매트릭스 추출 실패 — 빈 인벤토리로 진행] {str(e)[:120]}")
        return {"state_dimensions": []}


def format_state_inventory_for_prompt(inventory: Dict) -> str:
    """상태 인벤토리를 TC 생성 프롬프트에 주입할 텍스트로 포맷."""
    dims = (inventory or {}).get("state_dimensions") or []
    if not dims:
        return "(이 기획서에서 도출된 상태 차원이 없습니다. 일반적인 정상/비정상 케이스만 고려하세요.)"
    lines = []
    for d in dims:
        name = d.get("name", "")
        page = d.get("spec_page", "")
        desc = d.get("description", "")
        affects = d.get("affects", "")
        lines.append(f"• [{name}] (p.{page}) — {desc}")
        for v in d.get("values", []):
            val = v.get("value", "")
            v_desc = v.get("description", "")
            beh = v.get("expected_behavior", "")
            lines.append(f"    - {val}: {v_desc}" + (f" → {beh}" if beh else ""))
        if affects:
            lines.append(f"    (영향 범위: {affects})")
    return "\n".join(lines)


def build_menu_tree(pdf_path: str, ruleset=None, original_filename: str = None) -> Dict:
    """PDF 기획서에서 메뉴트리(계층 구조) 추출

    original_filename: 사용자가 업로드한 원본 파일명. 모듈명 추론의 보조 단서로 전달한다.
    (단, 본문에 'A > B > C' breadcrumb이 있으면 본문이 항상 우선)
    """
    if ruleset and ruleset.tree_rules:
        extra = (
            "\n\n[추가 지침 — 보조 가이드]\n"
            "아래 항목은 본 프롬프트의 원칙(기획서 본문 우선·근거 기반·추측성 금지)을 보충하는 관점 가이드입니다. "
            "본 프롬프트의 원칙과 충돌하는 항목이 있으면 본 프롬프트가 우선합니다. "
            "특히 기획서에 스펙·제약·문구가 명시되지 않은 검증 항목은 추가하지 마세요.\n\n"
            f"{ruleset.tree_rules}"
        )
    else:
        extra = ""
    prompt = TREE_PROMPT + extra

    filename_hint = ""
    if original_filename:
        filename_hint = (
            f"[기획서 원본 파일명] {original_filename}\n"
            f"(참고용. 파일명은 제품군·작업명·기능명을 담을 뿐 실제 사이트 메뉴 경로가 아닐 수 있습니다. "
            f"본문에 'A > B > C' 형식의 메뉴 경로(breadcrumb)가 있으면 본문을 우선하세요.)\n\n"
        )

    if is_text_based_pdf(pdf_path):
        text = extract_text_from_pdf(pdf_path)
        if len(text) > 20000:
            text = text[:20000] + "\n\n[이하 생략]"
        response_text = _generate_content_with_retry(
            f"{filename_hint}다음은 기획서 내용입니다:\n\n{text}\n\n{prompt}",
            model=settings.GEMINI_MODEL_EXTRACT,
            fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
        )
    else:
        chunks = pdf_to_base64_chunks(pdf_path, chunk_size=10)
        contents = []
        for chunk_b64 in chunks:
            contents.append({"inline_data": {"mime_type": "application/pdf", "data": chunk_b64}})
        contents.append(filename_hint + prompt if filename_hint else prompt)
        response_text = _generate_content_with_retry(
            contents,
            model=settings.GEMINI_MODEL_EXTRACT,
            fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
        )
    return _parse_json_response(response_text)


# ============================================================================
# 흐름 트리(Flow Tree) — 행동 흐름 메뉴트리 추출 (정식 전환 1단계, 비파괴 추가)
# 설계: docs/flow_tree_schema_design.md  |  PoC: docs/PoC_FlowTree_doc82_v3.xlsx
# 기존 구조적 트리(build_menu_tree)는 그대로 두고, 흐름 트리를 별도 함수로 제공.
# 태깅 관례(§4)는 QA 합의 전 기본값이며 프롬프트 문구로 조정 가능.
# ============================================================================
FLOW_PROMPT = """당신은 10년 경력의 QA 전문가입니다. 이 기획서를 읽고, 사람 QA가 테스트 설계로 쓰는 **상호작용 흐름 메뉴트리**를 만드세요.
단순 UI 요소 나열이 아니라 "어떤 상태에서, 무엇을 하면, 무엇이 표시되는가"의 **행동 흐름**을 좌→우로 펼친 트리입니다.

[노드 타입 (각 노드 type 1개 필수) — 사람(골든) 관례 기준]
- PR = 사전조건/상태 (메뉴 진입 상태, 권한 상태, 코드 상태 등 분기 조건)
- C = 클릭/선택/터치 액션
- T = **입력 행위** (예: "동 입력", "휴대폰 번호 입력"). ※ "입력란 출력"·"플레이스홀더 출력"은 D
- H = 마우스오버/툴팁 | DC = 더블클릭 | RC = 우클릭 | DD = Drag Down
- D = 화면 표시/결과 (노출되는 모든 것)
- V = **수동 확인이 필요한 검증만** (예: "다운로드된 PDF 내용 확인", "암호화 코드 일치 확인"). 일반 화면 출력은 V가 아니라 D

[★ 정밀도 규칙 — 사람 수준으로 빠짐없이 잘게]
1. **표시 요소는 하나하나 개별 D 노드로 분해하라. 절대 뭉치지 마라.**
   - 팝업/화면 하나에 타이틀·서브카피·본문·각 버튼·썸네일·안내문구·장점 항목이 있으면 전부 개별 D. 목록은 항목마다 D (장점 4개 → 장점1·2·3·4).
2. **화면의 모든 형제 UI 요소를 포함하라 — 신규 기능만 보지 마라.** 같은 화면의 기존 버튼·필터·영역(조회·인쇄·새로고침 버튼·조회 필터 등)도 D로. 화면 진입 시 기본 표시 요소를 먼저 D로 나열한 뒤 흐름 전개.
3. **상태 차원의 각 값마다 반드시 별도 PR 분기. 결과가 같아도 합치지 마라.** (권한 읽기만/사용안함/읽기쓰기, 코드 정상/미계약/해지, 설치/미설치 등 각각 PR)
4. **기획서의 모든 화면·페이지를 빠짐없이 다뤄라.** 진입점이 여러 개면 PR 루트도 그만큼.
5. **흐름은 종료 지점까지 끝까지 전개.** 액션(C/T)과 결과(D)는 **별도 노드**로 분리: 액션(C/T) → 결과(D) → 그 안의 또 다른 액션 → 결과 … 깊게.
6. D 노드 content엔 **기획서 실제 문구를 그대로 인용(요약 금지)**. 추상 표현 금지. 기획서에 없는 건 만들지 마라.
7. 각 노드에 spec_page(출처 페이지 번호; 모르면 "")를 넣어라. 루트 PR content엔 "메뉴 경로 + 진입 상태"를 함께 쓰고, menu_path(메뉴 경로)도 별도로 넣어라.
8. 분량을 아끼지 마라. 빠짐없이 전개가 요약보다 훨씬 중요하다.

[출력 — 순수 JSON만, 코드블록 없이]
{
  "title": "기획서 제목",
  "tree": [
    {"type":"PR","content":"미납대장 진입된 상태","menu_path":"XpERP > 수납 > 미납조회 > 미납대장","spec_page":"5","children":[
      {"type":"D","content":"타이틀 출력 - 미납대장","spec_page":"5","children":[]},
      {"type":"C","content":"간편전자고지서 QR안내문 다운로드 버튼 클릭","spec_page":"6","children":[
        {"type":"D","content":"<결과 기획서 문구>","spec_page":"6","children":[]}
      ]}
    ]}
  ]
}"""


def _assign_flow_ids(nodes: List[Dict], prefix: str = "") -> None:
    """흐름 트리 노드에 계층 id를 부여 (피드백·TC 추적의 안정 키). in-place."""
    for i, node in enumerate(nodes, start=1):
        node["id"] = f"{prefix}{i}" if not prefix else f"{prefix}-{i}"
        children = node.get("children") or []
        if children:
            _assign_flow_ids(children, node["id"])


def build_flow_tree(pdf_path: str, ruleset=None, original_filename: str = None) -> Dict:
    """PDF 기획서에서 흐름 트리(행동 흐름 메뉴트리)를 추출한다.

    기존 build_menu_tree(구조적 트리)와 병존하는 별도 추출 경로. 결과에 format="flow"를
    표기하고 각 노드에 계층 id를 코드로 부여한다. (설계: docs/flow_tree_schema_design.md)
    """
    extra = ""
    if ruleset and ruleset.tree_rules:
        extra = (
            "\n\n[추가 지침 — 보조 가이드]\n"
            "아래는 본 프롬프트 원칙(기획서 근거·추측 금지)을 보충하는 관점 가이드입니다. "
            "충돌 시 본 프롬프트가 우선합니다.\n\n"
            f"{ruleset.tree_rules}"
        )
    prompt = FLOW_PROMPT + extra

    filename_hint = ""
    if original_filename:
        filename_hint = f"[기획서 원본 파일명] {original_filename}\n\n"

    if is_text_based_pdf(pdf_path):
        text = extract_text_from_pdf(pdf_path)
        if len(text) > 20000:
            text = text[:20000] + "\n\n[이하 생략]"
        response_text = _generate_content_with_retry(
            f"{filename_hint}다음은 기획서 내용입니다:\n\n{text}\n\n{prompt}",
            model=settings.GEMINI_MODEL_EXTRACT,
            fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
        )
    else:
        chunks = pdf_to_base64_chunks(pdf_path, chunk_size=10)
        contents = [{"inline_data": {"mime_type": "application/pdf", "data": b}} for b in chunks]
        contents.append(filename_hint + prompt if filename_hint else prompt)
        response_text = _generate_content_with_retry(
            contents,
            model=settings.GEMINI_MODEL_EXTRACT,
            fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
        )

    result = _parse_json_response(response_text)
    result["format"] = "flow"
    _assign_flow_ids(result.get("tree", []))
    return result


_FLOW_ACTION_TYPES = {"C", "T", "H", "DC", "RC", "DD"}


def linearize_flow_tree(flow_tree: Dict) -> Dict:
    """흐름 트리를 TC 목록으로 선형화 (설계 §5: 트리=마스터, TC=파생).

    각 루트→종단(leaf) 경로 1개 = TC 1건.
      - 경로의 PR 노드 → preconditions
      - 액션(C/T/H/DC/RC/DD) → steps[].action, 직후 D/V → 해당 step의 expected
      - 마지막 D/V → expected_result
      - category = 루트 menu_path, spec_page = 경로 종단부터 첫 비어있지 않은 값
    """
    testcases: List[Dict] = []
    counter = [1]

    def emit(path: List[Dict]):
        root = path[0]
        menu_path = root.get("menu_path") or root.get("content", "")
        preconditions = [n.get("content", "") for n in path
                         if n.get("type") == "PR" and n.get("content")]

        seq = [n for n in path if n.get("type") != "PR"]  # 액션/표시 시퀀스
        actions = [n.get("content", "") for n in seq if n.get("type") in _FLOW_ACTION_TYPES]
        all_displays = [n.get("content", "") for n in seq if n.get("type") in ("D", "V") and n.get("content")]

        # 스텝 구성: 액션 단위로 그룹화. 액션 전 표시는 진입 스텝으로 묶고, "화면 진입" 가짜 스텝은 쓰지 않음.
        steps: List[Dict] = []
        entry_displays: List[str] = []   # 첫 액션 이전에 노출되는 표시(진입 화면 표시)
        cur = None
        for n in seq:
            t = n.get("type")
            content = n.get("content", "")
            if t in _FLOW_ACTION_TYPES:
                if cur is None and entry_displays:
                    steps.append({"step": len(steps) + 1,
                                  "action": "대상 화면/팝업에 진입한다",
                                  "expected": "\n".join(entry_displays)})
                elif cur is not None:
                    steps.append(cur)
                cur = {"step": len(steps) + 1, "action": content, "expected": ""}
            elif t in ("D", "V") and content:
                if cur is None:
                    entry_displays.append(content)
                else:
                    cur["expected"] = (cur["expected"] + "\n" + content).strip() if cur["expected"] else content
        if cur is not None:
            steps.append(cur)
        elif entry_displays:
            # 액션이 전혀 없는 순수 표시 확인 경로
            steps.append({"step": 1,
                          "action": "해당 화면/팝업의 표시 항목을 확인한다",
                          "expected": "\n".join(entry_displays)})

        # 기대결과: 마지막 스텝의 결과(없으면 경로의 마지막 표시)
        expected_result = ""
        if steps and steps[-1].get("expected"):
            expected_result = steps[-1]["expected"]
        elif all_displays:
            expected_result = all_displays[-1]

        spec_page = ""
        for n in reversed(path):
            if n.get("spec_page"):
                spec_page = n["spec_page"]
                break

        # 제목: 마지막 사용자 액션이 있으면 그 액션, 없으면 종단 표시
        core = (actions[-1] if actions else (path[-1].get("content") or "")).strip()
        core_short = core[:80] + ("…" if len(core) > 80 else "")
        title = core_short or "흐름 시나리오"
        # 목적: 메뉴 경로 + 핵심 동작/표시 + (대표 상태)
        state_txt = f", {preconditions[-1]}에서" if preconditions else ""
        verb_phrase = "동작하는지" if actions else "표시되는지"
        objective = f"[{menu_path}]{state_txt} '{core_short}'이(가) 기획서 명세대로 {verb_phrase} 검증한다."

        joined = " ".join(n.get("content", "") for n in path)
        tc_type = "negative" if any(k in joined for k in ["오류", "실패", "잘못", "유효하지", "불가", "에러"]) else "positive"

        testcases.append({
            "tc_id": f"TC-{counter[0]:03d}",
            "category": menu_path,
            "title": title,
            "objective": objective,
            "spec_page": spec_page,
            "tc_type": tc_type,
            "priority": "medium",
            "preconditions": preconditions,
            "steps": steps,
            "expected_result": expected_result,
            "change_type": "unknown",
        })
        counter[0] += 1

    def walk(node: Dict, path: List[Dict]):
        path = path + [node]
        children = node.get("children") or []
        if not children:
            emit(path)
        else:
            for ch in children:
                walk(ch, path)

    for root in flow_tree.get("tree", []) or []:
        walk(root, [])
    return {"testcases": testcases}


def flow_tree_outline(flow_tree: Dict, max_len: int = 18000) -> str:
    """흐름 트리를 들여쓰기 텍스트 개요로 평탄화 (커버리지 점검 프롬프트용, 컴팩트)."""
    lines: List[str] = []

    def walk(node: Dict, depth: int):
        t = node.get("type", "?")
        c = (node.get("content", "") or "").replace("\n", " ")
        mp = node.get("menu_path")
        suffix = f"  [menu: {mp}]" if mp else ""
        lines.append(f"{'  ' * depth}- {t}: {c}{suffix}")
        for ch in node.get("children") or []:
            walk(ch, depth + 1)

    for root in (flow_tree or {}).get("tree", []) or []:
        walk(root, 0)
    text = "\n".join(lines)
    return text[:max_len] + ("\n…(이하 생략)" if len(text) > max_len else "")


COVERAGE_CHECK_PROMPT = """당신은 QA 리드입니다. 아래 [QA 규칙]을 기준으로 [흐름 트리]를 점검하여, **규칙을 충족하지 못한(누락·위반) 항목만** 찾아내세요.

원칙:
- 규칙에 부합하는 부분은 보고하지 마세요. 누락/위반만.
- 흐름 트리에 실제로 없는 것을 근거로만 지적하세요. 추측·일반론 금지.
- 규칙이 트리 구조와 무관하면 무시하세요.

[QA 규칙]
{rules}

[흐름 트리 (타입: PR 상태 / C 클릭 / T 입력 / H 호버 / D 표시 / V 검증)]
{outline}

다음 JSON으로만 응답 (코드블록 없이):
{
  "findings": [
    {
      "rule": "관련 규칙 요약(한 줄)",
      "severity": "missing 또는 violation",
      "where": "관련 화면/노드 경로(있으면)",
      "detail": "무엇이 빠졌거나 어긋났는지 구체적으로",
      "suggestion": "흐름 트리에 어떻게 반영하면 되는지(룰셋 재추출 시 반영될 형태)"
    }
  ]
}
누락/위반이 없으면 {"findings": []} 로 응답하세요."""


def check_flow_coverage(flow_tree: Dict, rules_text: str) -> Dict:
    """흐름 트리를 룰셋 규칙과 대조해 누락·위반 항목을 찾는다 (AI 점검).

    rules_text가 비어 있으면 빈 결과. 실패해도 빈 결과로 안전 반환.
    """
    if not (rules_text or "").strip():
        return {"findings": [], "note": "룰셋에 트리 규칙이 없습니다."}
    outline = flow_tree_outline(flow_tree)
    if not outline.strip():
        return {"findings": [], "note": "흐름 트리가 비어 있습니다."}
    prompt = COVERAGE_CHECK_PROMPT.replace("{rules}", rules_text).replace("{outline}", outline)
    try:
        text = _generate_content_with_retry(
            prompt,
            model=settings.GEMINI_MODEL_EXTRACT,
            fallback_model=settings.GEMINI_MODEL_EXTRACT_FALLBACK or None,
        )
        result = _parse_json_response(text)
        findings = result.get("findings", []) if isinstance(result, dict) else []
        return {"findings": findings}
    except Exception as e:
        print(f"[커버리지 점검 실패] {str(e)[:150]}")
        return {"findings": [], "error": str(e)[:200]}


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
                "spec_page": (str(node.get("spec_page") or "").strip()),
                "change_summary": "",
            })
        else:
            features.extend(_collect_leaf_nodes(children, current_path))
    return features


def generate_tc_from_tree(tree: Dict, tc_level: int = 2, ruleset=None, on_progress=None, state_inventory: Dict = None) -> Dict:
    """메뉴트리를 기반으로 TC 생성 (PDF 재분석 없음). state_inventory는 도메인 상태 매트릭스."""
    features = _collect_leaf_nodes(tree.get("tree", []))
    if not features:
        raise ValueError("메뉴트리에 기능이 없습니다.")
    print(f"[트리 기반 TC생성] {len(features)}개 기능 추출, 룰셋: {ruleset.name if ruleset else '없음'}")
    tc_result = generate_testcases(
        features, tc_level=tc_level, ruleset=ruleset,
        on_progress=on_progress, state_inventory=state_inventory,
    )
    return {
        "features": features,
        "testcases": tc_result.get("testcases", []),
    }
