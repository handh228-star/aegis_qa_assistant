# Aegis QA Assistant — 프로젝트 사양서

> 작성일: 2026-04-23
> 최종 수정: 2026-07-03
> 버전: v0.14.0
> 작성자: ITERP (iterp@aegisep.com)

---

## 1. 프로젝트 개요

### 목적
기획서(PDF) 기반으로 AI가 테스트케이스(TC)를 자동 생성하여 QA 단계의 인력·비용·시간을 절감한다.
나아가 사용자 매뉴얼, 과거 테스트 결함 이력, 과거 TC 이력을 RAG 데이터로 등록하여 테스트 사이클이 반복될수록 TC 품질이 자동으로 고도화되는 구조를 목표로 한다.

### 핵심 가치
- 기획 완료 후 QA TC 작성 시간을 AI로 대폭 단축
- PDF → 메뉴트리 추출 → 사용자 검토 → TC 생성으로 품질과 투명성 확보
- TC 생성 레벨(1~5)로 검증 깊이를 상황에 맞게 조절 (핵심 검증 ↔ 전수 검증)
- QA 룰셋으로 프로젝트별 TC 생성 규칙을 정의하고 재사용
- 실제 서비스 매뉴얼 기반으로 구체적인 입력값·제약·오류 조건을 TC에 반영
- 과거 결함 이력이 누적될수록 비정상/경계값 케이스가 자동 강화
- 과거 TC 이력이 누적될수록 TC 구조·품질이 자동으로 고도화
- 웹 UI에서 TC 검토·수정·관리자확인 플래그·AI 재생성까지 원스톱 처리

### 대상 서비스
고객 대상 상용 웹 애플리케이션 (XpERP / XpBIZ) — 아파트·공동주택 관리 ERP 시스템

### 기획서 포맷
- Excel → PDF 변환본 (텍스트 기반)
- Figma → PDF 변환본 (이미지 기반)
- 두 포맷 자동 감지 후 최적 처리 방식 적용

---

## 2. 진행 현황 (2026-07-03 기준)

| 항목 | 상태 | 비고 |
|------|------|------|
| FastAPI 백엔드 셋업 | ✅ 완료 | |
| DB 모델 설계 및 생성 | ✅ 완료 | SQLite + 자체 ALTER TABLE 마이그레이션 |
| PDF 파싱 서비스 | ✅ 완료 | pypdf 사용 |
| Google Gemini API 연동 | ✅ 완료 | gemini-2.5-flash 계열, 503 지수 백오프 재시도 |
| TC 생성 서비스 | ✅ 완료 | |
| Excel 리포트 생성 | ✅ 완료 | "기획서 페이지" 컬럼 포함 |
| RAG - 매뉴얼 이력 | ✅ 완료 | 매뉴얼 PDF 벡터화, TC 생성에 반영 |
| RAG - 결함 이력 | ✅ 완료 | 테스트 결과 Excel → Fail TC 벡터화 |
| RAG - TC 이력 | ✅ 완료 | 생성된 TC 자동 벡터화, 다음 TC 생성에 참고 |
| TC 검토 UI (프론트엔드) | ✅ 완료 | React + Vite |
| TC 승인/수정요청/관리자확인/AI재생성 | ✅ 완료 | admin_required 플래그 포함 |
| 변경유형(ChangeType) 자동 감지 | ✅ 완료 | 기능 단위 new_feature/modification/bug_fix 분기 |
| TC 생성 레벨 시스템 (1~5) | ✅ 완료 | 레벨명 전문 용어화, 기본값 Lv.3 |
| 메뉴트리 추출 및 검토 플로우 | ✅ 완료 | PDF → 메뉴트리 → 사용자 검토 → TC 생성 |
| 메뉴트리 4단계 계층 구조 | ✅ 완료 | 모듈 > 화면 > 영역 > 기능 |
| 메뉴트리 Excel 다운로드 | ✅ 완료 | TreeViewPage + TCReviewPage 양쪽 지원 |
| QA 룰셋 관리 시스템 | ✅ 완료 | 메뉴트리 추출 지침 + TC 생성 지침 관리 |
| **TC 레벨 시스템 재설계 (개수 할당 폐지)** | ✅ 완료 | 개수 강제 → 검증 깊이만 차등, 근거 기반 생성 |
| **추측성 6범주 금지 명시** | ✅ 완료 | 인프라/UI일반론/스펙 미명시 경계값 등 금지 |
| **메뉴 경로 우선순위 정정 (본문 breadcrumb 우선)** | ✅ 완료 | 5종 모듈 강제 제거, 파일명 약화 |
| **spec_page 추적성 재설계** | ✅ 완료 | 트리 추출 시 페이지 확정 → TC 상속 (환각 제거), 트리 Excel·칩 표시 |
| **JSON 파싱 견고화** | ✅ 완료 | JSON 응답 모드 + 토큰 상한 65K + 잘린 응답 복구 폴백 |
| **노드↔TC 연결 고정 + 트리 커버리지** | ✅ 완료 | TC category=리프 경로 강제, 트리 Excel에 노드별 TC 하위 행 펼침 |
| **룰셋 vs 프롬프트 충돌 정리** | ✅ 완료 | 메타룰 + 기본 룰셋 "관점 가이드"로 재설계 |
| **상태 매트릭스 도출 단계 (Phase 1 #1)** | ✅ 완료 | 권한·코드·이력 등 도메인 상태 차원 자동 추출 |
| **TC 분류 결정 트리 (Q1~Q4)** | ✅ 완료 | 정책상 차단 = positive 명시, 흔들림 제거 |
| **프로젝트 목록 리스트화 + 페이지네이션** | ✅ 완료 | 카드 → 테이블, 검색·페이지 크기 옵션 |
| **흐름 트리(Flow Tree) 정식 구현** | ✅ 완료 | 추출·저장·Excel·TC 선형화·탭 UI (사람 골든 양식, PR/C/D/T/H/V) |
| **TC 선형화 (트리=마스터)** | ✅ 완료 | 흐름 트리 경로→TC, AI 미사용·결정적 |
| **룰셋 능동화 (커버리지 점검 + 피드백 루프)** | ✅ 완료 | 점검 게이트·fixability 분류·clone-on-write·dedupe |
| **흐름 트리 렌더러 품질 개선** | ✅ 완료 | PR 독립 행·D→액션 행 분리(R2-1)·D 캐스케이드·path_tracker 누적 |
| **흐름 트리 2단계 파이프라인** | ✅ 완료 | 구조적 트리→화면 골격→흐름 트리, 중복 루트 방지 |
| **자동 교정 루프** | ✅ 완료 | 생성 후 자동 점검→Gemini 교정 패스, 기획서 참조 |
| **룰셋 구조 대폭 개편** | ✅ 완료 | flow_rules 필드, 코드→DB 이전, Few-shot+체크리스트, 상속 모델 |
| **흐름트리+TC 통합 Excel 다운로드** | ✅ 완료 | 1:1 행 매핑, Gemini 자연어 TC, 30개 배치, fetch 방식 UX |
| **QA 태깅 규칙 정비** | ✅ 완료 | PR→V 직결 금지, R9-6/R9-7/R3-2 추가, 여집합 정책 정정 |
| GitHub 협업 설정 | ✅ 완료 | Collaborator 등록 완료 |
| 프론트엔드 + 백엔드 통합 배포 | ⏳ 예정 | Phase 5 |
| TC 수동 테스트 결과 기록 기능 | ⏳ 예정 | Phase 6 |
| Playwright 자동화 테스트 연동 | ⏳ 예정 | Phase 7 (현재는 보조 기능, TC는 사람 중심) |

---

## 3. 개발 경과 요약 (주요 기술 결정 이유)

### 3-1. AI 제공자 변경: Anthropic Claude → Google Gemini

1. **33페이지 PDF 용량 초과 (413 오류)** → pypdf로 텍스트 추출 방식으로 우회

**사용 모델 이력:**
- `gemini-2.0-flash`, `gemini-2.0-flash-001`: 신규 계정에서 404 오류 → 제외
- `gemini-2.5-flash`: 503 오류(수요 폭증) 반복 → `gemini-2.5-flash-lite`로 전환
- 현재: 역할별 모델 분리 운영 (GEMINI_MODEL_EXTRACT, GEMINI_MODEL_TC 등 .env에서 설정)

**API Key 이력**
- 현재: 회사 개발 계정 (aegis_tf1@aegisep.com) — 2026-04-27 전환

### 3-2. PDF 파싱 라이브러리: PyMuPDF → pypdf

PyMuPDF(fitz) 설치 시 사내 SSL 인증서 검사로 인해 MuPDF 소스 다운로드 실패. 순수 Python 패키지인 `pypdf`로 대체. 컴파일 없이 설치 가능.

### 3-3. RAG와 벡터 DB의 관계

**RAG(Retrieval-Augmented Generation)** 는 특정 도구가 아니라 기법(아키텍처)이다.
"외부 데이터를 검색(Retrieval)하여 AI 프롬프트에 주입하고, 그것을 바탕으로 생성(Generation)한다"는 방식 자체를 의미한다.

```
RAG (기법)
  └── 검색 단계에서 벡터 유사도 검색이 필요
        └── 벡터 DB 선택: ChromaDB / Pinecone / Weaviate / 자체 구현 등
              └── 이 프로젝트: SimpleVectorStore (numpy 기반)
```

### 3-4. 벡터 DB: ChromaDB → 자체 구현 SimpleVectorStore

RAG 시스템 구현 시 ChromaDB 설치를 시도했으나 `chroma-hnswlib` 패키지가 C++ 컴파일을 요구함. 사내 환경에 MSVC(Microsoft Visual C++) 미설치로 빌드 실패.

numpy 기반 자체 벡터 스토어(SimpleVectorStore)를 구현:
- 벡터를 pickle 파일로 로컬 저장
- 코사인 유사도로 검색
- 8개 매뉴얼 PDF / 362+ 청크 규모에서 충분한 성능

### 3-5. SQLite Enum 컬럼 호환성

SQLAlchemy의 `Enum` 타입은 SQLite에서 VARCHAR + 선택적 CHECK 제약으로 동작한다.
동적으로 추가되는 컬럼(change_type 등)은 `String(50)`으로 선언하고, API 응답 직렬화 단계(Pydantic)에서 enum으로 변환한다.

### 3-6. TC 생성 동시성 모델 (단일 워커)

FastAPI `BackgroundTasks`를 사용하여 백그라운드에서 처리. 현재 단일 워커로 운영하며 순차 처리. 운영 스케일 아웃 필요 시 Celery + Redis 큐 도입 예정 (Phase 8).

> **주의:** Ctrl+C 한 번은 백그라운드 작업 완료 대기 모드 진입. TC 생성 중 강제 종료 시 Ctrl+C 두 번 또는 `taskkill /PID {pid} /F` 사용.

### 3-7. 메뉴트리 기반 TC 생성 플로우 도입 (2026-05)

초기 구조(PDF → TC 직접 생성)에서 중간 단계를 추가:
- PDF → **메뉴트리 추출** → **사용자 검토/편집** → TC 생성
- 장점: 사용자가 TC 생성 범위를 직접 확인·조정 가능, AI 오추출 사전 수정 가능
- 메뉴트리는 4단계 계층(모듈 > 화면 > 영역 > 기능)으로 구성, 리프 노드 1개 = TC 생성 단위

### 3-8. QA 룰셋 시스템 도입 (2026-05)

서비스 유형마다 다른 TC 생성 규칙을 체계적으로 관리하기 위해 룰셋 시스템 도입:
- 메뉴트리 추출 지침 (tree_rules): AI에게 어떤 기준으로 트리를 만들지 지시
- TC 생성 지침 (tc_rules): 어떤 기준으로 TC를 만들지 지시
- 프로젝트 생성 시 룰셋 선택 → 해당 프로젝트의 모든 기획서 분석에 자동 적용
- 시스템 기본 룰셋("웹 서비스 공통") + 사용자 정의 룰셋 지원

### 3-9. AI 프롬프트 도메인 특화 (2026-05)

단순 "QA 전문가"에서 아파트·공동주택 관리 ERP 특화 역할로 강화:
- 회계/부과/인사급여/검침/입주관리/전자결재/커뮤니티/민원/문의관리 등 다양한 업무 모듈 도메인 명시
- 경계값 분석, 동등 분할, 탐색적 테스트, 결함 예측 기법 명시
- 세 프롬프트 모두 적용 (ANALYZE_PROMPT, TC_GENERATE_PROMPT, TREE_PROMPT)
- 초기에는 5종 모듈(회계/부과/인사급여/검침/입주관리)을 anchor로 박았으나, 다른 모듈 기획서가 강제 매핑되는 문제 발견 → 풀어쓰기로 약화 (3-12 참조)

### 3-10. TC 생성 레벨 재설계 — 개수 할당 폐지 (2026-05-28)

기존 레벨 시스템이 "기능당 N개 강제" 방식이라 모델이 추측성 케이스로 빈자리를 채우는 문제 발견 (예: doc 40에서 50개짜리 기획서가 265개로 폭증):

- `TC_LEVEL_CONFIG`에서 `target`/`per_feature`(개수 강제) 제거 → **레벨별 "검증 깊이(depth)"만 차등**
- TC 생성 프롬프트의 "기능당 N개 생성" 지시 삭제
- 비율 강제 (정상 40% / 비정상 30% / 경계값 20% / 예외 10%) → **자연 분포**로 완화
- **추측성 6범주 절대 금지 섹션 추가**: 인프라 추측, 브라우저/UI 일반론, 스펙 미명시 경계값, 일반 텍스트 검수, 백오피스 가정, 메타-검수
- **기획서 문구 인용 강제**: 추상 표현 ("정확하게 표시되는지 확인") 금지, 모르면 `<기획서 인용 필요>`로 명시

### 3-11. spec_page 필드 추가 — TC 출처 추적성 (2026-05-28)

> ⚠️ 이 섹션의 "TC가 직접 페이지를 명시" 방식은 **3-18(2026-06-17)에서 재설계**됨 (환각 문제로 트리 추출 시 페이지를 잡고 TC가 상속하는 방식으로 변경). 아래는 도입 당시 기록.

자기검증 효과를 위해 모든 TC에 출처 페이지 번호 강제:

- `testcases` 테이블에 `spec_page VARCHAR(50)` 컬럼 추가
- TC 생성 프롬프트에 "spec_page 없는 TC = 추측성 TC로 간주" 명시
- Excel 리포트에 "기획서 페이지" 컬럼 추가 (TC ID 다음 2번째 열)
- TCReviewPage에서 TC ID 옆에 `p.5` 형식 chip으로 표시 (줄바꿈으로 다른 컬럼 배치 영향 없음)
- 모델이 페이지를 명시해야 하므로 출처 없는 TC 생성이 어려워짐 → 추측성 자연 감소

### 3-12. 메뉴 경로 우선순위 정정 — 본문 breadcrumb 우선 (2026-05-28)

doc 40에서 카테고리가 "회계 > 미납대장 화면"으로 잘못 분류된 문제 발견. 실제 기획서/사이트 메뉴는 `XpERP > 수납 > 미납조회 > 미납대장`이었음.

원인:
1. 프롬프트에 5종 모듈(회계/부과/인사급여/검침/입주관리)을 anchor로 박아둠 → 다른 모듈 기획서가 가장 가까운 분류로 강제 매핑됨
2. PDF 원본 파일명이 프롬프트에 전달되지 않음

수정:
- TREE_PROMPT/ANALYZE_PROMPT의 5종 강제 풀어쓰기 ("...등 다양한 업무 모듈")
- **모듈/화면 경로 결정 원칙 3단계 우선순위** 신설:
  - 1순위 — **기획서 본문의 "A > B > C" breadcrumb** (예: "게재 위치: XpERP > 수납 > 미납조회 > 미납대장")
  - 2순위 — 본문의 화면 제목·섹션 헤더
  - 3순위 — 파일명/표지 (QA팀 분류 라벨일 수 있어 가장 약한 단서)
- `build_menu_tree(pdf_path, ruleset, original_filename)` 시그니처에 파일명 추가
- "회계/관리 등 추상적 상위 분류 임의 추가 금지", "...화면/...메뉴 임의 접미사 금지" 명시

### 3-13. 룰셋 vs 프롬프트 충돌 정리 (2026-05-28)

기본 룰셋(`DEFAULT_TREE_RULES`/`DEFAULT_TC_RULES`)이 "빠짐없이 생성", "최대 길이 초과 TC", "특수문자 입력 TC" 같은 체크리스트를 강제하여, 우리가 잡으려던 추측성 금지 원칙을 무력화하고 있었음.

수정:
- **메타룰 추가**: 룰셋 주입 직전에 "이 가이드는 본 프롬프트 원칙의 보조 가이드이며, 충돌 시 본 프롬프트가 우선합니다" 박음
- **기본 룰셋 재설계** ("XPERP 서비스 룰셋" → "웹 서비스 공통 (관점 가이드)"):
  - "빠짐없이 / 체크리스트" 강제 → "관점 가이드" 톤
  - "최대 길이 초과 TC" 등 → "기획서가 명시한 경우에만"
  - 권한 분기를 트리 노드 분리 → TC 사전조건 표현 권장으로 변경 (이중 분리 방지)
- DB의 기존 룰셋도 자동 갱신

### 3-14. 상태 매트릭스 도출 단계 — Phase 1 #1 (2026-05-29)

사람 작성 TC와 AI TC를 비교한 결과, 핵심 누락 패턴이 **상태 분기**(권한·코드·이력별)에 있음을 확인 (해지 시나리오 14개 누락, 약관 동의 분기 7개 누락 등).

`extract_state_inventory()` 함수 신설:
- PDF 전체에서 도메인 상태 차원(권한·계약/코드 상태·이력·일치 여부 등) 추출하는 별도 LLM 호출
- 메뉴트리 추출 직후 1회 실행, `documents.state_inventory` JSON 컬럼에 저장
- TC 생성 시 모든 feature에 주입되어 "상태 조합 × 액션 = 별도 TC" 분리 유도
- 실패 시 빈 인벤토리로 graceful degrade (전체 파이프라인 차단 안 함)
- API: `GET /api/documents/{id}/state-inventory` 로 결과 조회 가능

### 3-15. TC 분류 결정 트리 — 흔들림 제거 (2026-05-29)

다른 LLM 리뷰에서 "정책검증" 5번째 유형 추가 권고를 받았으나, **5타입 추가 대신 4타입 분류 결정 규칙 명시**로 해결.

[TC_GENERATE_PROMPT](backend/app/services/tc_generator.py#L78)에 결정 트리 추가:
- Q1 측정 수치 경계 → `boundary` (기획서 명시 있을 때만)
- Q2 시스템 예외 → `exception` (기획서 명시 있을 때만)
- Q3 사용자 입력 형식 오류 → `negative`
- Q4 그 외 모두 (정상 흐름 + **정책상 차단**) → `positive`

**핵심 명시**: 정책상 차단(권한 미달, 중복 신청, 대상 외 단지, 정보 불일치, 미계약 코드 등)은 사용자 실수가 아니라 시스템이 기획대로 동작하는 것이므로 **모두 positive**. 상태 변이는 사전조건에 명시. 사람 엑셀의 "전부 정상으로 분류 + 사전조건으로 변이 표현" 패턴과 정합.

### 3-16. 503 재시도 로직 확대 적용 (2026-05-27)

기존엔 TC 생성에만 적용되던 `_generate_content_with_retry`를 메뉴트리 추출에도 적용. 30→60→120초 지수 백오프, 최대 3회. 함수를 일반화하여 model/contents 모두 받도록 시그니처 확장.

### 3-17. 프로젝트 목록 UI 리스트화 (2026-05-29)

프로젝트 수가 늘어남에 따라 카드 그리드 → 테이블 + 클라이언트 페이지네이션 전환:
- 컬럼: Proj-ID / 프로젝트명 / 설명 / 룰셋 / 생성일
- 검색 필터 (이름·설명 부분 일치)
- 페이지 크기 선택 (10/20/50)
- 페이지 번호 + ellipsis (1 … 4 5 6 … 12)
- 기존 `.tc-table` 스타일 재사용으로 TC 검토 화면과 일관성 유지

### 3-18. spec_page 추적성 재설계 + JSON 파싱 견고화 (2026-06-17)

**문제 1 — spec_page 환각.** 기존엔 TC 생성 프롬프트가 "모든 TC에 spec_page 필수, 없으면 추측성"이라고 요구했지만, 정작 TC 생성 단계는 PDF도 페이지 정보도 못 본다(리프 노드 JSON만 받음). 모델이 페이지를 알 길이 없어 빈칸 대신 `"Key Points"`, `"description"` 같은 **필드명·문구를 출처 페이지 자리에 채워 넣는 환각**이 발생. Excel "기획서 페이지" 열이 무의미해짐.

**재설계 — 페이지는 트리 추출 때 잡고, TC는 상속만.**
- TREE_PROMPT의 리프 노드 스키마에 `spec_page` 추가 → **PDF를 직접 보는 추출 단계**에서 출처 페이지 확정 (못 찾으면 빈 문자열, 추측 금지). 상위(비-리프) 노드는 빈 문자열.
- `_collect_leaf_nodes`가 노드의 `spec_page`를 feature로 전달.
- TC 생성 프롬프트를 **"노드의 spec_page 값을 그대로 복사, 비면 빈칸, 필드명·문구 절대 금지"**로 변경 (더 이상 모델이 페이지를 지어내지 않음).
- 메뉴트리 Excel export에 "기획서페이지" 열 추가, TreeViewPage 노드에 `p.5` 칩 표시 → 사람이 트리 검토 단계에서 페이지를 한 번에 확인·수정, 그 아래 TC들이 상속.
- 검증(라이브): CDD 기획서 리프 156개 전부 페이지 번호 형식, 환각 0개.
- 마이그레이션: 기존 트리엔 spec_page가 없으므로 빈칸. 채우려면 트리 재추출 필요(신규 프로젝트는 자동).

**문제 2 — 대용량 트리 JSON 파싱 실패.** 리프 수백 개 트리에서 Gemini 응답이 출력 토큰 한도로 잘리거나 중간 구문이 깨져 `json.loads` 전체 실패 → 트리 추출 자체가 간헐적으로 무산(같은 PDF가 50KB는 성공, 94KB는 실패).

**견고화 — 3중 방어 (`tc_generator.py`).**
- **JSON 응답 모드**: 모든 추출/생성 호출에 `response_mime_type="application/json"` 적용 → 코드펜스·중간 구문 깨짐 원천 차단.
- **출력 토큰 상한 65,536** (`max_output_tokens`): 대용량 트리 truncation 방지 (기본 8K → 8배).
- **`_repair_truncated_json` 복구 폴백**: 그래도 잘리면 마지막 완결 컨테이너에서 끊고 열린 괄호를 닫아, 완결된 노드만 살리고 잘린 후행 노드는 버린 뒤 유효 JSON으로 복구(전체 실패 대신 부분 성공). 복구 시 로그로 경고.

### 3-19. 노드↔TC 연결 고정 + 트리 커버리지 표시 (2026-06-17)

**문제 — 트리와 TC가 따로 논다.** QA팀이 "메뉴트리 Excel의 검증포인트에 1~2개만 나오고 실제 TC가 다 안 보인다"고 지적. 실제 DB(문서 31)를 점검하니 더 근본적인 단절이 드러남:
- `검증포인트(key_points)`는 **트리 추출 시점의 간략한 힌트**(룰셋이 "기획서 근거 있는 항목만"으로 강하게 제약)이지 TC 목록이 아님. 별도 패스로 생성되는 실제 TC와 처음부터 개수가 안 맞음.
- 더 심각하게, **TC가 노드에 연결되지 않음**: TC 생성 프롬프트가 노드 전체 경로를 넘겨도 출력 스키마(`"category": "기능 카테고리"`)대로 모델이 임의 묶음 이름(`"헤더 (Header) 기능"` 등)을 지어냄. 리프 42개 vs TC distinct category 11개, **정확 일치 0개** → 어느 TC가 어느 노드에서 나왔는지 역추적 불가.

**해법 1 — 연결 고정 (코드 강제).** [generate_testcases](backend/app/services/tc_generator.py)에서 TC 생성 후 `tc.category`를 **리프 노드 전체 경로로 덮어씀**(`tc_id` 강제 방식과 동일). 모델의 자유 작명을 신뢰하지 않고 코드가 경로를 박아넣어, 노드↔TC 매핑이 100% 신뢰 가능한 키가 됨.

**해법 2 — 트리 Excel에 TC 하위 행 펼침.** 메뉴트리 export([documents.py](backend/app/api/documents.py))가 TC를 경로별로 묶어, 각 **리프 노드 행 아래에 실제 생성된 TC를 하위 행**으로 표시: `└ [TC-001] 제목` + 유형 / 기획서페이지 / 목적 / 기대결과(우선순위별 색상). deleted TC 제외. TC가 없으면(생성 전) 기존처럼 트리만 표시(하위 호환).

- 결과: 검증포인트는 추출 힌트로 남고, **실제 커버리지는 트리에 매달린 TC 목록**으로 노출 → "트리=커버리지 마스터 뷰"(노드 1:N TC) 구조 완성.
- 검증: 실제 export 코드로 매핑된 TC가 리프 하위 행으로 렌더됨을 확인(DB 미변경 롤백 테스트).
- 마이그레이션: 연결 고정은 **신규 생성 TC에만** 적용. 기존 TC는 category가 모델 작명이라 트리에 안 붙음 → 기존 문서는 **TC 재생성** 필요.

### 3-20. 트리 정의 재검토 — "구조적 트리" → "흐름 트리" 방향 설정 (2026-06-22)

QA 골든 레퍼런스(`docs/human_Aegis_*.xlsx`) 분석 결과, QA팀의 "메뉴트리"는 우리의 얇은 요소 계층이 아니라 **상태→액션→표시결과→검증의 행동 흐름 설계도**(타입 태깅 PR/C/D/T/H/V, 좌→우 트라이)임이 드러남. 그들에겐 트리 = 완성된 테스트 설계.

- **PoC 검증(3차)**: 흐름 지향 추출 프롬프트로 [PoC_FlowTree_doc82_v1~v3.xlsx](PoC_FlowTree_doc82_v3.xlsx) 생성 → 사람 레퍼런스와 **동급의 구조·상태분기·입도·문구인용** 확인. 남은 차이는 태깅 관례 수준.
- **방향 결정**: 트리를 흐름 트리로 정식 전환하고, **TC는 흐름 트리를 선형화한 파생물**로 재정의. → [flow_tree_schema_design.md](flow_tree_schema_design.md)
- **피드백 흡수 설계**: QA 피드백을 인스턴스/규칙 레벨로 분리해 룰셋·few-shot·골든 비교로 반영하는 시스템 설계 → [feedback_system_design.md](feedback_system_design.md)
- 구현 선행 조건: QA팀과 **태깅 관례 합의**(입력 T/D, V 분리, 중복표기). 이후 추출→Excel→TC선형화→편집UI 순.

### 3-21. 흐름 트리 정식 구현 (2026-06-23)

태깅 관례 12항 전부 합의(사람 골든 기준 그대로) 후 정식 구현. → [QA_flowtree_tagging_agreement.md](QA_flowtree_tagging_agreement.md)

- **추출**: `build_flow_tree()` + `FLOW_PROMPT`(PR/C/D/T/H/V). `documents.flow_tree`(JSON, `format:"flow"`) 컬럼에 저장, 노드별 계층 id 부여. `menu_tree`(구조적)와 별도 보관(하위호환).
- **TC 선형화**: `linearize_flow_tree()` — 루트→종단 경로 1개 = TC 1건. PR→preconditions, 액션+직후 D/V→steps, 종단→expected_result. **AI 미사용·결정적·무료** (TC=트리 파생). 목적/제목/단계 표현 품질 개선.
- **Excel**: `flow_tree_report.render_flow_tree_excel()` — 사람 양식(범례+Step 헤더+트라이 그리드).
- **프론트**: TreeViewPage에 흐름/구조적 **탭 분리**(흐름=마스터 기본), 흐름 트리 렌더(타입 배지)·추출·재추출·Excel·TC생성 버튼. 기획서 목록에 트리/TC 보기 액션.
- 엔드포인트: `POST/GET /documents/{id}/flow-tree`, `/flow-tree/export`, `/flow-tree/generate-tc`.
- 실사용 검증(doc82): 추출 112노드→Excel→선형화 71 TC, end-to-end 통과.

### 3-22. 룰셋 능동화 — 커버리지 점검 + 피드백 루프 (2026-06-23~24)

거의 안 쓰이던 룰셋을 흐름 트리 품질을 관장하는 **능동 도구**로 전환.

- **커버리지 점검 게이트**: `check_flow_coverage()` — 흐름 트리를 룰셋(tree_rules)과 대조해 누락·위반을 찾음. `POST /documents/{id}/flow-tree/coverage-check`. 흐름 카드 "🔎 룰셋 점검" 버튼 + 결과 패널.
- **피드백→룰셋 원클릭**: `POST /documents/{id}/ruleset/append-rule` — finding/자유의견을 룰셋에 추가. **시스템 룰셋은 clone-on-write로 프로젝트 전용 룰셋 복제 후 추가**(공유 룰셋 보호). 루프: 점검→룰셋 보강→재추출→개선.
- **해결가능성 분류(fixability)**: 각 finding을 `not_followed`(룰셋 강화/재추출로 개선) / `spec_limited`(기획서에 근거 없어 추가 무의미→"기획서 보강 필요") 로 분류. spec_limited엔 추가 버튼 미노출 → **점검 무한반복 해소**.
- **중복 추가 방지(dedupe)** + 조건부 규칙 과잉검출 차단(“기획서 명시한 경우에만” 류는 단서 없으면 위반 미보고).
- **상태 분기 규칙 정정**: 구 구조적-트리 규칙("권한 등 상태는 트리 노드 말고 TC 사전조건으로")은 흐름 트리와 모순 → **"상태는 PR 노드로 분기"**로 교체. `init_db`가 시스템 룰셋을 코드 DEFAULT로 자동 동기화.

### 3-23. 흐름 트리 렌더러 품질 개선 (2026-06-29~30)

QA 팀 골든 레퍼런스와 태깅 합의서(R9, R2-1) 기반으로 `flow_tree_report.py`의 `render()` 함수를 전면 개선:

- **PR 항상 독립 행 (절대규칙)**: 단독 자식이어도 PR은 반드시 새 행 시작 (`ch_type == "PR"` 무조건 new_row).
- **D→새 액션 행 분리 (R2-1)**: 부모가 D 타입이고 자식이 C/DC/H/T/RC/DD(실제 액션)이면 새 행으로 분리. V는 결과로 취급해 제외. `_ROW_BREAKING_ACTIONS` 상수로 관리.
- **D 캐스케이드 보존**: 직전 자식이 D이고 현재도 D이면 같은 행에 계속 이어 나열.
- **path_tracker 누적 방식**: `path_tracker[row] = current_path`(덮어쓰기) → 첫 노드는 초기화, 이후 노드는 `append`로 누적. D→D→D 캐스케이드 행에서 중간 D들이 사라지던 버그 해결 → TC 생성 시 모든 표시 요소가 반영됨.

### 3-24. 흐름 트리 2단계 추출 파이프라인 (2026-06-30)

**문제**: 흐름 트리 단일 패스(PDF→흐름 트리) 생성 시 같은 화면이 별도 루트 PR로 중복 생성되는 패턴 반복.

**해결**: 구조적 트리(메뉴트리)를 화면 골격으로 먼저 추출하고, 그 골격을 기반으로 흐름 트리 생성하는 2단계 파이프라인 도입:

1. `_summarize_menu_tree_screens(menu_tree)` — 구조적 트리를 "화면 경로 > [기능들]" 텍스트 목록으로 평탄화.
2. `build_flow_tree(..., menu_tree=menu_tree)` — 위 목록을 "[화면 골격 — 절대 규칙]" 섹션으로 프롬프트에 주입: 각 화면당 루트 PR 1개만, 모든 기능은 형제 분기로 통합.
3. `_build_flow_tree_bg()`에서 `doc.menu_tree`가 없으면 먼저 구조적 트리 추출 후 진행.

### 3-25. 자동 교정 루프 (2026-06-30~07-01)

흐름 트리 생성 직후 커버리지 점검 + 자동 교정 2차 패스를 파이프라인에 통합:

- **`repair_flow_tree(flow_tree, findings, pdf_path, original_filename)`**: `not_followed` 위반만 대상. 기획서 PDF를 함께 전달해 팝업 내부 요소 분해·spec_page 보완 등 기획서 정보가 필요한 수정도 가능.
- **`_build_flow_tree_bg()` 자동 실행**: 1차 생성 → 자동 점검(`check_flow_coverage`) → `not_followed` 있으면 2차 교정 패스 → 최종 저장. 사용자가 별도로 "점검" 버튼 누르지 않아도 됨.
- 재추출 버튼 클릭 시 기존 `flow_tree=None` 즉시 적용 → 폴링이 "추출 중(ready=False)" 올바르게 인식 (이전 트리가 새 결과인 것처럼 표시되던 버그 수정).
- 폴링 타임아웃: 3분 → 10분 (Gemini 3패스 커버). 경과 시간 실시간 표시.

### 3-26. 룰셋 구조 대폭 개편 (2026-06-30~07-01)

**배경**: 규칙이 코드(`FLOW_PROMPT`)·DB(룰셋)·MD 파일에 분산되어 충돌·비동기 문제 반복.

**개편 내용:**

1. **`flow_rules` 필드 신규**: `QARuleSet` 모델에 `flow_rules TEXT` 추가 (흐름 트리 구조 문법 전용). `tree_rules`(관점 가이드)·`tc_rules`와 역할 구분.

2. **코드→DB 이전**: `FLOW_PROMPT`의 정밀도 규칙(1-10)·구조 배치 규칙(1-13)을 모두 `DEFAULT_FLOW_RULES`(DB)로 이전. 코드에는 노드 타입 정의 + JSON 스키마 뼈대만 남김.

3. **시스템 룰셋 자동 덮어쓰기 제거**: 이전엔 서버 재시작마다 시스템 룰셋을 코드 DEFAULT로 덮어쓰던 로직 제거 → 웹에서 편집한 내용이 사라지던 버그 해결. 신규 설치 시 시드 + 이후엔 DB 내용이 정본.

4. **상속 모델(`_get_composed_ruleset`)**: `flow_rules`는 시스템 룰셋이 항상 기반(Base), 프로젝트 룰셋이 추가 레이어로 합성 → 시스템 룰셋 업데이트 시 모든 프로젝트 즉시 반영.

5. **클론 룰셋 제거**: 기존 "점검 결과 → 클론 룰셋에 추가(clone-on-write)" 방식 폐기. 이제 적용 버튼은 `scope='project'`(현재 룰셋) 또는 `scope='system'`(시스템 전체) 중 선택.

6. **Few-shot 예시 + 자가 점검 체크리스트**: `DEFAULT_FLOW_RULES` 말미에 가장 자주 위반되는 3가지 패턴(팝업 컨테이너 D 한 줄, PR "진입된 상태", C가 D의 자식)의 잘못된 예 vs 올바른 예 추가. `FLOW_PROMPT`에 출력 전 자가 점검 5개 항목 체크리스트 추가.

7. **커버리지 점검 개선**: finding에 `target`(flow/tree) 필드 추가 → 각 위반이 어느 룰셋 영역에서 왔는지 구분. 점검 프롬프트에 `[target=flow]`/`[target=tree]` 섹션 라벨로 전달.

8. **점검 결과 UI 정비**: 각 finding에 "구조 문법/관점 가이드" 배지 표시. per-finding "룰셋 반영" 버튼 제거 (bulk 적용이 오히려 노이즈만 추가하던 구조적 문제 해결).

### 3-27. 흐름트리 + TC 통합 Excel 다운로드 (2026-07-01~03)

흐름 트리 Excel과 TC를 1:1로 나란히 붙인 통합 Excel 다운로드 기능 구현:

**핵심 구조:**
- `render_flow_tree_excel(include_tc, tc_data, _out_paths)` 확장:
  - 렌더링하면서 각 행의 루트→리프 경로를 `path_tracker`에 동시 수집.
  - `tc_data`(Gemini 생성 자연어 TC)가 있으면 그것, 없으면 기계적 선형화 사용.
  - `_out_paths`로 path_tracker를 외부로 반환 (2단계 TC 생성용).
- 흐름트리(좌) + TC(우) 1:1 배치: TC ID / 사전조건 / 테스트 스텝 / 기대결과 / 기획서 페이지.

**Gemini 자연어 TC 생성 (`generate_tcs_from_flow_paths`):**
- 규모 확장성: 30개 경로씩 배치 분할 → 600개 경로도 20배치로 처리.
- PDF 없이 노드 content(이미 기획서에서 추출된 원문)만 사용 → 70MB PDF 전송 불필요.
- 출력 형식: `{"tcs": [...]}` 래핑으로 `_parse_json_response()` 호환.
- 배치 실패해도 해당 배치만 스킵, 나머지 계속 처리.

**내보내기 API 변경**: `GET /flow-tree/export?with_tc=true` → 2단계(렌더+TC생성) 후 반환.

**UX 개선:**
- "📥 흐름트리 + TC Excel" 버튼: `<a href>` → `<button>` + `fetch()` 방식으로 변경. 클릭 시 현재 페이지에 경과 시간 타이머 표시 ("TC 생성 중... 1분 23초 경과"). 백지 로딩 화면 제거.
- 버튼 순서 정리: 재추출 / 🤖 AI 교정 리포트 / 📥 흐름트리 Excel / 📥 흐름트리+TC Excel / (비활성) 이 흐름트리로 TC 생성.

**버그 수정**: `path_tracker[row] = current_path`(덮어쓰기)로 인해 D 캐스케이드에서 중간 D들이 소실되던 문제 → 초기화+누적 방식으로 수정.

---

## 4. 시스템 전체 플로우

```
[기획팀]
  기획서 작성 (Excel 또는 Figma)
      ↓
  PDF 변환
      ↓
[Aegis QA Assistant - 웹 UI]
  ① TC 생성 레벨 선택 (1~5)
     └── Lv.1: 핵심 검증 / Lv.3: 정밀 검증 (기본) / Lv.5: 전수 검증
      ↓
  ② PDF 업로드
      ↓
  ③ AI 분석 — 메뉴트리 추출 + 상태 매트릭스 도출 (status: analyzing → analyzed)
     ├── 4단계 계층 구조: (모듈 > 화면 > 영역 > 기능) — 기획서 본문 breadcrumb 우선
     ├── 각 노드: change_type 자동 판단 + key_points 추출 + 리프 노드 spec_page(출처 페이지) 추출
     └── **상태 매트릭스**: 권한·계약/코드 상태·이력·일치 여부 등 도메인 상태 차원 자동 추출
      ↓
  ④ 사용자 메뉴트리 검토 (TreeViewPage)
     ├── 트리 구조 확인·편집
     ├── TC 생성 제외 항목 설정
     └── Excel 다운로드
      ↓
  ⑤ TC 생성 시작 (사용자 확인 후)
      ↓
  ⑥ RAG 컨텍스트 조회
     ├── 매뉴얼 벡터 DB 검색 → 실제 스펙(입력값, 제약, 오류 메시지 등)
     ├── 결함 이력 벡터 DB 검색 → 과거 유사 결함 패턴
     └── TC 이력 벡터 DB 검색 → 과거 유사 TC 구조 참고
      ↓
  ⑦ AI TC 자동 생성 (레벨 + 룰셋 + RAG 컨텍스트 + **상태 매트릭스** 반영)
     └── 결정 트리(Q1~Q4)로 유형 분류, 상태 조합 × 액션 = 별도 TC 분리
      ↓
  ⑧ DB 저장 + TC 이력 벡터 DB 업데이트
      ↓
  ⑨ TC 검토 화면 (TCReviewPage)
     ├── 메뉴트리 읽기전용 조회 + Excel 다운로드
     ├── ✓ 승인
     ├── ✏️ 수정 요청 (메모 입력)
     ├── 👑 관리자 확인 필요 (AI 재생성 제외)
     └── ✗ 삭제
      ↓
  ⑩ AI 보완 요청 (수정 요청된 TC만 재생성 → TC 이력 갱신)
      ↓
  ⑪ Excel 리포트 다운로드
      ↓
[QA팀]
  TC 기반 테스트 수행
      ↓
  테스트 결과 Excel 업로드
      ↓
[결함 이력 DB 누적]
  → 다음 프로젝트 TC 생성 시 자동 반영 (고도화)
```

### 흐름 트리 경로 (마스터, 3-21~22) — 위 ③~⑧의 대안/상위 경로
```
③' 흐름 트리 추출 (build_flow_tree) — 상태→액션→표시결과→검증을 PR/C/D/T/H/V 트라이로
      ↓
④' TreeViewPage 흐름 탭에서 검토 + 🔎 룰셋 점검(누락·위반, fixability 분류)
      ├── not_followed → 룰셋 강화 규칙 추가(clone-on-write) → 재추출 (루프)
      └── spec_limited → 기획서 보강 필요 (룰셋 추가로 해결 안 됨)
      ↓
⑤' "이 흐름트리로 TC 생성" → linearize_flow_tree (트리 경로=TC, AI 미사용)
      ↓  이후 ⑨ TC 검토 ~ ⑪ 리포트 동일
※ 흐름 트리가 마스터, TC는 트리의 선형화 파생물. 구조적 트리 경로(③~⑧)와 하위호환 병존.
```

---

## 5. 개발 환경

| 항목 | 내용 |
|------|------|
| OS | Windows 10 Pro (10.0.19045) |
| IDE | Visual Studio Code |
| AI 코딩 도구 | Claude Code (VS Code Extension, claude-sonnet-4-6) |
| Python | 3.12.x (venv 사용) |
| Node.js | 최신 LTS (프론트엔드 빌드용) |
| 패키지 관리 | pip (백엔드), npm (프론트엔드) |
| 가상환경 경로 | `backend/.venv/` |
| 형상관리 | GitHub (handh228-star/aegis_qa_assistant) |

### Python 버전 주의사항
- PC에 Python 3.14 설치되어 있으나 **3.12 사용 필수**
- 이유: pydantic-core 등 주요 패키지가 3.14 바이너리 휠 미제공 → 소스 컴파일 필요 → MSVC 미설치로 실패
- 가상환경 생성: `py -3.12 -m venv .venv`

### pip 설치 시 주의사항 (사내 SSL 인증서 환경)
```powershell
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

---

## 6. 기술 스택

### 백엔드
| 항목 | 기술 | 버전 |
|------|------|------|
| 웹 프레임워크 | FastAPI | 0.115.0 |
| ASGI 서버 | Uvicorn (standard) | 0.30.6 |
| ORM | SQLAlchemy | 2.0.35 |
| 데이터 검증 | Pydantic | 2.9.2 |
| 설정 관리 | pydantic-settings | 2.5.2 |

### AI / 문서 처리
| 항목 | 기술 | 비고 |
|------|------|------|
| AI 모델 | gemini-2.5-flash / gemini-2.5-flash-lite | 역할별 분리 (환경변수 설정) |
| AI SDK | google-genai | >=0.8.0 |
| 임베딩 모델 | models/gemini-embedding-2 | Google Gemini Embedding API |
| PDF 파싱 | pypdf | 4.3.1 |
| 벡터 스토어 | SimpleVectorStore (자체 구현) | numpy 기반, pickle 저장 |

### 프론트엔드
| 항목 | 기술 | 버전 |
|------|------|------|
| UI 프레임워크 | React | 18.3.1 |
| 빌드 도구 | Vite | 5.4.8 |
| 라우팅 | React Router DOM | 6.26.2 |
| HTTP 클라이언트 | Axios | 1.7.7 |

### 리포트 / 파일
| 항목 | 기술 | 버전 |
|------|------|------|
| Excel 생성 | openpyxl | 3.1.5 |
| 파일 업로드 | python-multipart | 0.0.12 |
| 벡터 연산 | numpy | >=1.24.0 |

### DB
| 환경 | DB |
|------|------|
| 개발 | SQLite (파일 기반, 별도 설치 불필요) |
| 운영 (예정) | PostgreSQL |

---

## 7. 프로젝트 폴더 구조

```
aegis_qa_assistant/                  ← 프로젝트 루트
│
├── .env                             ← API Key 등 환경변수 (Git 제외)
├── .env.example                     ← 환경변수 템플릿
├── .gitignore
├── CLAUDE.md                        ← Claude Code 프로젝트 컨텍스트
├── aegis_qa.db                      ← SQLite 데이터베이스
│
├── backend/                         ← FastAPI 백엔드
│   ├── requirements.txt
│   ├── .venv/                       ← Python 3.12 가상환경 (Git 제외)
│   └── app/
│       ├── main.py                  ← FastAPI 앱 설정, 라우터 등록, 정적파일 서빙
│       ├── core/
│       │   └── config.py            ← 환경변수 설정 (Gemini 모델 분리 설정 포함)
│       ├── models/
│       │   ├── database.py          ← DB 엔진, 세션, init_db() (컬럼 자동 마이그레이션 + 기본 룰셋 시딩)
│       │   ├── project.py           ← Project (ruleset_id FK 포함)
│       │   ├── document.py          ← Document + DocumentStatus + state_inventory(상태 매트릭스)
│       │   ├── testcase.py          ← TestCase + ReviewStatus + spec_page(기획서 페이지)
│       │   └── qa_ruleset.py        ← QARuleSet (관점 가이드 톤의 기본 룰)
│       ├── api/
│       │   ├── projects.py          ← 프로젝트 CRUD (ruleset_id 포함)
│       │   ├── documents.py         ← PDF 업로드, 메뉴트리·상태 매트릭스 생성/조회/수정, TC 생성 시작
│       │   ├── testcases.py         ← TC 조회/검토/재생성/Excel 내보내기 (spec_page 포함)
│       │   ├── rulesets.py          ← QA 룰셋 CRUD (기본값 설정, 시스템 룰셋 보호)
│       │   ├── manuals.py           ← 매뉴얼 PDF 인제스트/조회/삭제
│       │   └── defects.py           ← 테스트 결과 Excel 업로드 → 결함 이력 저장
│       └── services/
│           ├── tc_generator.py      ← Gemini API 연동, 메뉴트리 + 상태 매트릭스 + TC 생성 파이프라인
│           ├── document_parser.py   ← PDF 텍스트 추출, 타입 감지, 청크 분할
│           ├── report_generator.py  ← TC → Excel 리포트 생성 (기획서 페이지 컬럼 포함)
│           ├── rag_service.py       ← 매뉴얼 + 결함이력 + TC이력 통합 검색
│           ├── manual_ingestion.py  ← SimpleVectorStore 정의, 매뉴얼 PDF 벡터화
│           ├── defect_ingestion.py  ← 테스트 결과 Excel 파싱, Fail TC 벡터화
│           ├── tc_ingestion.py      ← 생성된 TC 자동 벡터화 (tc_history)
│           └── playwright_generator.py ← TC → Playwright async 코드 변환 (보조 기능)
│
├── frontend/                        ← React 프론트엔드
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                  ← React Router 설정 (5개 라우트)
│       ├── index.css                ← 전역 스타일
│       ├── api.js                   ← Axios 기반 API 클라이언트
│       └── pages/
│           ├── ProjectsPage.jsx     ← 프로젝트 목록 (테이블 + 검색 + 페이지네이션) / 생성 (룰셋 선택)
│           ├── DocumentsPage.jsx    ← TC 레벨 선택 + PDF 업로드 + 처리 상태 폴링
│           ├── TreeViewPage.jsx     ← 메뉴트리 검토/편집 + TC 생성 시작 + Excel 다운로드
│           ├── TCReviewPage.jsx     ← TC 검토 (spec_page chip 표시, 승인/수정요청/관리자확인/삭제/AI재생성)
│           └── RulesetsPage.jsx     ← QA 룰셋 관리 (생성/수정/삭제/기본값 설정)
│
├── vectordb/                        ← 벡터 DB 파일 (Git 제외)
│   ├── manual_xperp.pkl             ← 매뉴얼 임베딩 데이터
│   ├── defect_history.pkl           ← 결함 이력 임베딩 데이터
│   └── tc_history.pkl               ← TC 이력 임베딩 데이터 (자동 누적)
│
├── manual_xperp/                    ← 사용자 매뉴얼 PDF (Git 제외)
│   └── *.pdf                        ← 검침, 단지관리, 부과, 수납, 인사급여, 입주자, 회계
│
├── uploads/                         ← 업로드된 기획서 PDF (Git 제외)
├── reports/                         ← 생성된 Excel 리포트 (Git 제외)
└── docs/
    ├── project_spec.md              ← 본 문서 (전체 사양)
    ├── feedback_system_design.md    ← QA 피드백 흡수 시스템 설계 (인스턴스/규칙 레벨 분리)
    ├── flow_tree_schema_design.md   ← 흐름 트리(Flow Tree) 정식 스키마 전환 설계
    ├── QA_flowtree_tagging_agreement.md ← 태깅 관례 합의서 (12항 OK, 사람 골든 기준)
    ├── PoC_FlowTree_doc82_v*.xlsx   ← 흐름 트리 자동추출 PoC 산출물 (v1~v3)
    ├── human_Aegis_*.xlsx           ← QA 작성 골든 레퍼런스 (설계 기준·갭 비교용)
    └── mandocs/*.xlsx               ← 사람 작성 menutree+TC 골든 4종 (작성 패턴 추출용)
```

---

## 8. 데이터 모델

### Project
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| name | String(200) | 프로젝트명 |
| description | Text | 설명 |
| service_url | String(500) | 대상 서비스 URL |
| ruleset_id | Integer FK | 적용 QA 룰셋 (qa_rulesets.id, nullable) |
| created_at | DateTime | |
| updated_at | DateTime | |

### Document (기획서)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| project_id | Integer FK | |
| filename | String(300) | 저장 파일명 (UUID 접두사) |
| original_filename | String(300) | 원본 파일명 |
| file_path | String(500) | |
| total_pages | Integer | |
| tc_level | Integer | TC 생성 레벨 (1~5, **기본값 3**) |
| status | Enum | 처리 상태 |
| menu_tree | Text | 추출된 (구조적) 메뉴트리 JSON |
| flow_tree | Text | **흐름 트리 JSON** (`format:"flow"`, 행동 흐름 PR/C/D/T/H/V). menu_tree와 별도 보관 |
| state_inventory | Text | 도메인 상태 매트릭스 JSON (권한·코드·이력 등 자동 추출) |
| progress_current | Integer | TC 생성 진행 현재값 (실시간 진행률용) |
| progress_total | Integer | TC 생성 진행 총량 |
| tc_started_at | DateTime | TC 생성 시작 시각 |
| error_message | Text | 오류 메시지 |
| created_at | DateTime | |

**Document Status 전이**
```
uploaded → analyzing → analyzed
                            ↓ (사용자가 TC 생성 시작)
                       tc_generating → tc_generated
                            ↓ (1차 실패)
                       tc_retrying (30초 대기 후 재시도)
                            ↓ (2차 실패)
                          failed
```

### TestCase
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| document_id | Integer FK | |
| tc_id | String(50) | TC-001 형식 |
| category | String(200) | 리프 노드 **전체 경로** (생성 후 코드가 강제 지정) — 노드↔TC 매핑 키 (3-19) |
| title | String(500) | TC 제목 |
| objective | Text | 테스트 목적 |
| spec_page | String(50) | **기획서 출처 페이지** (예: "5", "5-6", "8p") — 트리 추출 시 리프 노드에서 확정, TC가 상속 (3-18) |
| preconditions | JSON | 사전 조건 목록 (상태 매트릭스의 상태값을 명시) |
| steps | JSON | 테스트 단계 [{step, action, expected}] |
| expected_result | Text | 최종 기대 결과 (기획서 실제 문구 인용) |
| tc_type | Enum | positive / negative / boundary / exception (Q1~Q4 결정 트리 적용) |
| priority | Enum | high / medium / low |
| change_type | String(50) | new_feature / modification / bug_fix / unknown |
| status | Enum | draft / confirmed / modified |
| review_status | Enum | pending / approved / needs_revision / admin_required / deleted |
| review_note | Text | 수정 요청 메모 |
| created_at | DateTime | |
| updated_at | DateTime | |

**Change Type (변경 유형)**
| 값 | 설명 | TC 생성 전략 |
|----|------|-------------|
| new_feature | 신규 기능 추가 | 정상/비정상/경계값/예외 포괄 생성 |
| modification | 기존 기능 수정 | 변경 동작 검증 + 연관 기능 회귀 테스트 |
| bug_fix | 버그 수정 | 버그 재현 방지 케이스 집중 + 유사 시나리오 |
| unknown | 판단 불가 (일반 기획서) | 포괄적 생성 |

**TC 유형 분류 결정 트리 (Q1 → Q4 순서대로, 첫 매치에서 멈춤)**

| 순서 | 질문 | 매치 시 유형 | 비고 |
|---|---|---|---|
| Q1 | 측정 가능한 수치 경계 검증인가? (길이/크기/개수/날짜) | **boundary** | **기획서가 해당 경계를 명시한 경우에만** |
| Q2 | 시스템적 예외 상황 검증인가? (API 실패·시스템 장애·통신 지연) | **exception** | **기획서가 해당 상황을 명시한 경우에만** |
| Q3 | 사용자가 형식·필수 입력을 어겨 발생한 거부인가? | **negative** | 잘못된 형식·필수 누락 등 |
| Q4 | 그 외 모두 (정상 흐름 + **정책상 차단**) | **positive** | 권한 차단·중복 방지·대상 검증 등 |

**정책상 차단도 positive — 핵심 명시**

권한 미달/이미 신청한 세대/대상 외 단지/정보 불일치/미계약 코드 등 **시스템이 기획대로 정상 동작하는 차단**은 모두 positive. 상태 변이는 **사전조건(preconditions)에 명시**하여 같은 액션의 positive TC들을 구분 (사람 QA 표준 패턴과 정합).

> 비율 강제 없음. 기능 특성에 따라 자연스럽게 분포. 개수 할당도 없음 — 기획서·매뉴얼·결함이력에 근거가 있는 케이스만 생성.

**Review Status 흐름**
```
(AI 생성 직후)
pending → approved          ← 검토자가 승인 (재클릭 시 pending으로 토글)
        → needs_revision    ← 검토자가 수정 요청 (메모 입력)
                ↓
          AI 재생성 후 다시 pending (TC 이력도 갱신)
        → admin_required    ← 관리자 확인 필요 플래그 (AI 재생성 대상 제외)
                              재클릭 시 pending으로 토글
        → deleted           ← 삭제 예정 (Excel 내보내기 시 제외)
```

### QARuleSet (QA 룰셋)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| name | String(200) | 룰셋 이름 |
| description | Text | 설명 |
| service_type | String(100) | 서비스 유형 (예: ERP, 쇼핑몰) |
| tree_rules | Text | 메뉴트리 추출 관점 가이드 (보조, 충돌 시 본 프롬프트 우선) |
| tc_rules | Text | TC 생성 지침 |
| **flow_rules** | **Text** | **흐름 트리 구조 문법 규칙** (정밀도 규칙 1-10 + 구조 배치 규칙 1-13, 필수 준수). 코드 DEFAULT_FLOW_RULES가 초기값, 이후 DB가 정본 |
| is_default | Boolean | 기본 룰셋 여부 (1개만 가능) |
| is_system | Boolean | 시스템 제공 룰셋 (삭제 불가, 자동 덮어쓰기 금지) |
| created_at | DateTime | |
| updated_at | DateTime | |

---

## 9. TC 생성 레벨 시스템

업로드 전에 TC 생성 레벨(1~5)을 선택하여 검증 깊이를 조절한다. **기본값은 Lv.3 (정밀 검증).**

| 레벨 | 이름 | 검증 깊이 (도출 범위) |
|------|------|------|
| 1 | 핵심 검증 | 핵심 정상 흐름 + 기획서에 명시된 대표적 실패/거부 케이스만 |
| 2 | 표준 검증 | + 기획서에 명시·암시된 주요 비정상·경계 조건 |
| **3** | **정밀 검증** | **+ 업무 규칙·제약·권한 분기에서 도출되는 예외·입력값 경계·상태 전이 (기본값)** |
| 4 | 심층 검증 | + 기획서·매뉴얼에 근거 있는 조합 케이스·연동 지점·데이터 변형 |
| 5 | 전수 검증 | + 기획서·매뉴얼·결함이력에서 도출 가능한 모든 케이스 망라 |

**설계 원칙 (개수 할당 폐지)**
- **레벨은 "검증 깊이"만 결정하고, TC 개수는 목표치·할당량 없이 기획서가 정당화하는 만큼만 생성**한다. 50개짜리 기획서는 어느 레벨이든 그 규모에 맞게 나온다.
- **근거 기반 생성**: 기획서·업무규칙·매뉴얼 스펙·결함이력에 근거가 있는 케이스만 만든다. 개수를 늘리려고 기획서에 없는 일반적인 웹/브라우저/네트워크/OS 오류를 임의로 가정하지 않는다.
- **유형 분포(정상/비정상/경계값/예외)는 비율 강제 없이** 기능 특성에 따라 자연스럽게 형성한다.
- 메뉴트리도 기획서에 실제로 기술된 화면·기능만 포함하며, 단계를 채우려고 영역·기능을 추측 생성하지 않는다.

**구현 위치:** `backend/app/services/tc_generator.py` → `TC_LEVEL_CONFIG` 딕셔너리

---

## 10. QA 룰셋 시스템

### 개념
QA 룰셋은 메뉴트리 추출과 TC 생성 시 AI에게 전달하는 추가 지침을 저장하는 단위다. 프로젝트 생성 시 룰셋을 선택하면 해당 프로젝트의 모든 기획서 분석·TC 생성에 일관된 규칙이 적용된다.

### 주입 방식 (메타룰 적용 — 2026-05-28 변경)

룰셋은 프롬프트 끝에 단순 append되지 않고, **메타룰로 감싸서 주입**된다:

```
[추가 지침 — 보조 가이드]
아래 항목은 본 프롬프트의 원칙(근거 기반 생성·추측성 금지·기획서 문구 인용·개수 할당 없음)을
보충하는 관점 가이드입니다. 본 프롬프트의 원칙과 충돌하는 항목이 있으면 본 프롬프트가 우선합니다.
특히 룰셋이 '체크리스트', '빠짐없이', '경계값', '특수문자' 같은 항목을 나열하더라도,
기획서·매뉴얼·결함이력에 해당 제약·문구가 명시되지 않으면 그 케이스는 만들지 마세요.

{ruleset_content}
```

- `tree_rules` → `TREE_PROMPT` 뒤에 위 메타룰 + 룰셋 본문 형태로 주입
- `tc_rules` → TC 생성 프롬프트의 `rag_context` 섹션에 위 메타룰 + 룰셋 본문 형태로 주입
- 사용자가 어떤 룰셋을 등록해도 핵심 원칙(근거 기반·추측성 금지)은 보장

### 시스템 기본 룰셋 ("웹 서비스 공통 (관점 가이드)")

서버 최초 기동 시 자동 생성. 삭제 불가 (is_system=True).

**톤**: "빠짐없이 체크리스트" 강제 → "**관점 가이드**"로 재설계 (2026-05-28). 기존 "최대 길이 초과 TC", "특수문자 입력 TC" 같은 quota 항목은 모두 "기획서가 명시한 경우에만" 조건부로 변경.

주요 내용:
- 입력 필드 관점: 플레이스홀더 문구·유효값 입력·입력 유형 제한·길이/크기 (기획서 명시 시만)·필수/공백
- 버튼 관점: 화면 표시·툴팁·클릭 정상 동작·팝업 트리거·활성/비활성 조건
- 표시영역 관점: 필수 출력 항목·조건별 표시/숨김·빈 데이터 처리
- 상태 분기: **흐름 트리에서 PR(사전조건/상태) 노드로 분기** (2026-06-24 정정 — 구 "트리 대신 TC 사전조건" 규칙은 흐름 트리와 모순이라 폐기). `init_db`가 시스템 룰셋을 코드 DEFAULT로 자동 동기화.
- 명시적 금지: 인프라 추측·UI 일반론·스펙 미명시 경계값·일반 텍스트 검수·메타-검수

### 룰셋 능동화 — 흐름 트리 품질 게이트 (2026-06-23~24)
룰셋이 "프롬프트 속 안 보이는 힌트"에 머물지 않도록, 흐름 트리 품질을 관장하는 능동 도구로 사용:
- **커버리지 점검**: `check_flow_coverage()`가 흐름 트리를 룰셋(tree_rules)과 대조해 누락·위반을 표시. 각 finding에 `fixability`(not_followed / spec_limited) 분류.
- **피드백→룰셋 루프**: 점검 결과/QA 의견을 `append-rule`로 룰셋에 추가(시스템 룰셋은 clone-on-write로 프로젝트 전용 복제) → 재추출 시 반영. 반복할수록 그 서비스의 룰셋이 정교화(도메인 전이).
- **안전장치**: 중복 추가 방지(dedupe), 조건부 규칙 과잉검출 차단, spec_limited 항목엔 추가 버튼 미노출(무한반복 방지).

### 룰셋 관리 UI
경로: `/rulesets`
- 전체 룰셋 목록 조회 (기본 확장 표시)
- 신규 룰셋 생성 / 수정 / 삭제 (시스템 룰셋 제외)
- 기본값 설정 (한 번에 1개만)
- 프로젝트 생성 시 룰셋 선택 드롭다운 자동 연동

---

## 11. AI 프롬프트 구조

### 역할 프롬프팅 (공통, 2026-05-28 풀어쓰기)
네 개의 메인 프롬프트(ANALYZE_PROMPT, TC_GENERATE_PROMPT, TREE_PROMPT, STATE_INVENTORY_PROMPT) 모두 동일한 도메인 전문가 역할로 시작:

```
당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템
(회계·부과·인사급여·검침·입주관리·전자결재·커뮤니티·민원·문의관리 등 다양한 업무 모듈)에 정통합니다.
```

> 초기엔 "회계(예산/결산), 부과, 인사급여, 검침, 입주관리" 5종을 anchor로 박았으나, 다른 모듈 기획서가 강제 매핑되는 문제가 있어 풀어쓰기로 약화 (3-12 참조).

### TREE_PROMPT (메뉴트리 추출용)

- **모듈/화면 경로 결정 원칙 3단계 우선순위**:
  - 1순위 — 기획서 본문의 "A > B > C" breadcrumb (예: "XpERP > 수납 > 미납조회 > 미납대장")
  - 2순위 — 본문의 화면 제목·섹션 헤더
  - 3순위 — 파일명/표지 (QA팀 분류 라벨일 수 있어 가장 약한 단서)
- 4단계 계층 구조: (1단계 모듈 → 2단계 → 3단계 화면 → 4단계 기능). 단계는 기획서 구조에 맞춰 결정 (단순한 화면은 2~3단계로)
- 기획서에 실제 기술된 화면·기능만 포함, 단계 채우기용 추측 생성 금지
- 화면명에 임의 접미사("...화면", "...메뉴") 금지 — 기획서 표현 그대로
- 리프 노드에 key_points(검증 포인트 목록) 포함 요구
- `build_menu_tree(pdf_path, ruleset, original_filename)` — 원본 파일명을 보조 단서로 전달

### STATE_INVENTORY_PROMPT (상태 매트릭스 추출용 — 신규)

PDF 전체를 한 번 더 보고 도메인 상태 차원을 추출:
- 사용자 권한 (읽기만/사용안함/읽기쓰기 등)
- 외부 코드/계약 상태 (유효/미계약/해지 등)
- 이력/신청 상태 (미신청/기신청/해지내역 등)
- 정보 일치 여부 (일치/불일치)
- 기획서가 명시·암시한 경우에 한해 추출 (추측 금지)
- 출력: `{state_dimensions: [{name, spec_page, description, values: [{value, description, expected_behavior}], affects}]}`

### TC_GENERATE_PROMPT (TC 생성용)

핵심 섹션 구성:
1. **상태 매트릭스 주입** — 위에서 추출한 state_inventory가 텍스트로 들어옴
2. **상태 매트릭스 활용 원칙** — "의미 있는 상태 조합 × 사용자 액션 = 별도 TC 1건"
3. **TC 유형 분류 결정 트리** (Q1~Q4)
4. **정책상 차단도 positive** 명시
5. **검증 깊이 레벨**(level_depth) — 개수 할당 없음
6. **근거 기반 원칙** — 추측성 금지
7. **추측성 6범주 절대 금지** — 인프라/UI일반론/스펙 미명시 경계값/일반 텍스트 검수/백오피스 가정/메타-검수
8. **기획서 문구 인용 강제** — 추상 표현 금지, 모르면 `<기획서 인용 필요>`
9. **상태 분기 사전조건 표현 권장 패턴**
10. **spec_page 상속** — 리프 노드의 출처 페이지 값을 그대로 복사 (비면 빈칸, 추론·환각 금지)
11. **RAG 컨텍스트** (매뉴얼 스펙 + 결함 이력 + TC 이력) 주입
12. **룰셋 추가 지침** (메타룰 적용) 주입
13. JSON 출력 스키마

### 룰셋 추가 지침 주입 (메타룰 적용)

10절 "주입 방식" 참조. 모든 룰셋은 "보조 가이드, 충돌 시 본 프롬프트 우선" 메타룰로 감싸서 주입.

### ⚠ 알려진 anchoring 사항

현재 TC_GENERATE_PROMPT의 일부 예시(권한·중복신청·미계약 코드 등)는 doc 40 (간편전자고지서) 케이스에서 도출된 것. 다른 도메인 기획서에선 모델이 anchor에 영향받을 가능성 있음. 메커니즘(상태 매트릭스 추출)은 도메인 무관하게 작동하므로 실질 위험은 제한적이나, 다양한 도메인 PDF 누적되면 예시 일반화 검토 예정.

---

## 12. API 엔드포인트

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api`
**API 문서:** `http://localhost:8000/docs` (Swagger UI, 개발 모드)

### Projects
| Method | URL | 설명 |
|--------|-----|------|
| GET | /api/projects/ | 목록 |
| POST | /api/projects/ | 생성 (ruleset_id 포함) |
| GET | /api/projects/{id} | 상세 |
| DELETE | /api/projects/{id} | 삭제 |

### Documents
| Method | URL | 설명 |
|--------|-----|------|
| POST | /api/documents/{project_id}/upload | PDF 업로드 (Form: file, tc_level, 기본값 3) |
| GET | /api/documents/{project_id}/ | 목록 |
| GET | /api/documents/status/{document_id} | 처리 상태 + tc_level + error_message |
| GET | /api/documents/{document_id}/tree | 메뉴트리 조회 |
| PUT | /api/documents/{document_id}/tree | 메뉴트리 수정 저장 |
| GET | /api/documents/{document_id}/tree/export | 메뉴트리 Excel 다운로드 |
| GET | /api/documents/{document_id}/state-inventory | **상태 매트릭스 조회** (권한·코드·이력 등 도메인 상태 차원) |
| POST | /api/documents/{document_id}/generate-tc | TC 생성 시작 (구조적 메뉴트리 검토 완료 후) |

### 흐름 트리 (Flow Tree) · 룰셋 능동화
| Method | URL | 설명 |
|--------|-----|------|
| POST | /api/documents/{id}/flow-tree | 흐름 트리 추출 시작 (백그라운드, 2단계 파이프라인: 구조적 트리→흐름 트리→자동 교정) |
| GET | /api/documents/{id}/flow-tree | 흐름 트리 + 통계 조회 (ready 여부, error 포함) |
| GET | /api/documents/{id}/flow-tree/export | 흐름 트리 Excel 다운로드 (`?with_tc=true`이면 TC 컬럼 1:1 포함) |
| POST | /api/documents/{id}/flow-tree/generate-tc | 흐름 트리 선형화 → TC 생성(기존 TC 교체, 현재 비활성) |
| POST | /api/documents/{id}/flow-tree/coverage-check | 룰셋(flow_rules+tree_rules) 대비 누락·위반 점검, target 분류 포함 |
| POST | /api/documents/{id}/ruleset/append-rule | 규칙을 룰셋에 추가 (`scope`: project / system) |

### TestCases
| Method | URL | 설명 |
|--------|-----|------|
| GET | /api/testcases/document/{doc_id} | TC 목록 (tc_type / priority / review_status / change_type 필터) |
| GET | /api/testcases/document/{doc_id}/summary | 유형·우선순위·검토 현황 통계 |
| PATCH | /api/testcases/{tc_id}/review | 검토 상태 + 메모 저장 |
| PATCH | /api/testcases/{tc_id} | TC 내용 직접 수정 |
| DELETE | /api/testcases/{tc_id} | TC 삭제 |
| POST | /api/testcases/document/{doc_id}/regenerate | needs_revision TC AI 재생성 |
| GET | /api/testcases/document/{doc_id}/export | Excel 리포트 다운로드 (deleted 제외) |

### RuleSets
| Method | URL | 설명 |
|--------|-----|------|
| GET | /api/rulesets/ | 목록 |
| GET | /api/rulesets/{id} | 상세 |
| POST | /api/rulesets/ | 생성 |
| PUT | /api/rulesets/{id} | 수정 (is_default 설정 포함) |
| DELETE | /api/rulesets/{id} | 삭제 (is_system 불가) |

### Manuals (RAG 소스 관리)
| Method | URL | 설명 |
|--------|-----|------|
| POST | /api/manuals/ingest-all | manual_xperp/ 전체 처리 (백그라운드) |
| POST | /api/manuals/ingest/{filename} | 특정 파일 처리 |
| GET | /api/manuals/stats | 저장된 청크 수 조회 |
| DELETE | /api/manuals/{filename} | 특정 매뉴얼 삭제 |
| GET | /api/manuals/list-files | PDF 파일 목록 조회 |

### Defects (결함 이력 관리)
| Method | URL | 설명 |
|--------|-----|------|
| POST | /api/defects/ingest | 테스트 결과 Excel → Fail TC 추출·저장 |
| GET | /api/defects/stats | 저장된 결함 이력 통계 |

---

## 13. TC 생성 파이프라인 (핵심 로직)

```
PDF 업로드 (tc_level 선택 후)
    ↓
[백그라운드 1단계 - status: analyzing]
① 메뉴트리 추출 (build_menu_tree)
  ├── 텍스트 기반 PDF: 텍스트 추출 → TREE_PROMPT로 전달
  ├── 이미지 기반 PDF: PDF document 타입으로 전달
  └── original_filename 보조 단서로 전달 (본문 breadcrumb 우선)
  → 응답: { title, tree: [계층 구조 노드] } (4단계까지)
  → DB 저장 (menu_tree 컬럼)

② 상태 매트릭스 추출 (extract_state_inventory) ← 신규
  → PDF 전체에서 도메인 상태 차원(권한·코드·이력 등) 자동 추출
  → DB 저장 (state_inventory 컬럼)
  → 실패해도 빈 인벤토리로 graceful degrade
  → status: analyzed
    ↓
[사용자 TreeViewPage에서 검토·편집]
  ├── 제외 항목 설정 가능
  ├── 상태 매트릭스 확인 (API: GET /state-inventory)
  └── Excel 다운로드 가능
    ↓
[사용자가 TC 생성 시작 클릭]
[백그라운드 2단계 - status: tc_generating]
    ↓
1단계: 메뉴트리에서 리프 노드 추출 (_collect_leaf_nodes)
  → 리프 노드 = 실제 TC 생성 대상 기능
  → category = 상위 경로 포함 전체 경로 (예: "수납 > 미납조회 > 미납대장 > 다운로드 버튼")
    ↓
2단계: RAG 컨텍스트 조회 + 상태 매트릭스 로드
  ├── 매뉴얼 벡터 DB 검색 (상위 8개)
  ├── 결함 이력 벡터 DB 검색 (상위 5개)
  ├── TC 이력 벡터 DB 검색 (상위 5개)
  └── 문서의 상태 매트릭스 전체 (모든 feature에 동일 주입)
    ↓
3단계: Gemini API — TC 생성 (기능별 순차 처리)
  → 레벨 지침 + 룰셋 지침(메타룰 적용) + RAG 컨텍스트 + change_type 전략 + 상태 매트릭스 + Q1~Q4 결정 트리 적용
  → 상태 조합 × 액션 = 별도 TC 분리
  → 각 TC의 spec_page는 리프 노드의 spec_page 값을 그대로 상속 (모델이 새로 추론 안 함)
  → 생성 후 tc_id·category를 코드가 강제 지정 (category = 리프 전체 경로 → 노드↔TC 매핑 키)
    ↓
4단계: DB 저장 + TC 이력 벡터 DB 자동 업데이트
    ↓
[완료 - status: tc_generated]
```

---

## 14. 메뉴트리 구조

### 계층 정의 (4단계)

기획서 본문의 실제 메뉴 경로(breadcrumb)를 그대로 사용한다. 사전 정의된 모듈 목록에 강제 매핑하지 않는다.

```
1단계 (최상위 모듈): 기획서 본문 breadcrumb의 첫 마디 (예: "수납")
    └── 2단계 (중간 분류): breadcrumb 두번째 마디 (예: "미납조회")
            └── 3단계 (화면): breadcrumb 세번째 마디 (예: "미납대장")
                    └── 4단계 (기능): 화면 내 테스트 대상 단위 (예: "다운로드 버튼") ← 리프 노드, TC 생성 대상
```

- 단순한 화면은 2~3단계 허용. 복잡한 화면은 4단계 세분화.
- 1단계 모듈명은 기획서가 명시한 표현 그대로 (회계/관리 같은 추상 상위 분류로 임의 묶지 않음).
- 화면명에 임의 접미사("...화면", "...메뉴") 금지.

### 노드 구조 (JSON)
```json
{
  "id": "1-1-1-1",
  "name": "세대번호 입력",
  "description": "관리비 부과 대상 세대 번호 입력 필드",
  "change_type": "modification",
  "spec_page": "5",
  "key_points": ["정상 세대번호 입력", "존재하지 않는 세대번호", "입력값 초기화"],
  "children": []
}
```

### Excel 다운로드
- 경로: `GET /api/documents/{document_id}/tree/export`
- 열: 계층 / 기능명 / 변경유형 / 기획서페이지 / 설명 / 검증포인트
- 깊이별 색상: 1단계(진한 파랑) → 4단계(연한 파랑)
- TreeViewPage와 TCReviewPage 양쪽에서 다운로드 가능

---

## 15. RAG 시스템 구조

### 컬렉션 구성
| 컬렉션 | 파일 | 내용 | 인제스트 시점 |
|--------|------|------|--------------|
| manual_xperp | vectordb/manual_xperp.pkl | 서비스 매뉴얼 PDF 청크 | 수동 (API 호출) |
| defect_history | vectordb/defect_history.pkl | 과거 테스트 Fail TC | 수동 (Excel 업로드) |
| tc_history | vectordb/tc_history.pkl | 생성된 TC 이력 | 자동 (TC 생성/재생성 시) |

### 현재 매뉴얼 현황 (XpERP)
| 매뉴얼 | 청크 수 |
|--------|--------|
| 검침 | 19 |
| 단지관리 | 78 |
| 부과 | 75 |
| 수납 | 35 |
| 인사급여 | 66 |
| 입주자 | 39 |
| 회계 | 50 |
| **합계** | **362+** |

---

## 16. TC 검토 UI 흐름

```
프로젝트 목록 (/)
  - 테이블 형태: Proj-ID / 프로젝트명 / 설명 / 룰셋 / 생성일
  - 검색 (이름·설명) + 페이지 크기 선택 (10/20/50) + 페이지네이션
  - + 새 프로젝트 (룰셋 선택 포함)
    ↓ 행 클릭
문서 목록 (/projects/{id})
  - TC 생성 레벨 선택 [1][2][3][4][5] (기본값: Lv.3 정밀 검증)
  - PDF 업로드 → 메뉴트리 생성 대기
  - 상태: analyzing → analyzed → (TC 생성 시작) → tc_generating → tc_generated
    ↓ analyzed 상태 문서 클릭
메뉴트리 검토 (/tree/{document_id})
  - AI 추출 기능 계층 구조 확인
  - 제외 항목 설정 (개별 토글)
  - Excel 다운로드
  - [TC 생성 시작 →] 버튼 클릭
    ↓ TC 완료 후 자동 이동
TC 검토 화면 (/review/{document_id})
  - 메뉴트리 접기/펼치기 (읽기전용) + Excel 다운로드
  - 통계 바: 전체 / 검토대기 / 승인 / 수정요청 / 관리자확인 / 삭제예정
  - 필터: 유형 / 우선순위 / 검토상태 / 변경유형
  - TC 테이블 (행 클릭 → 상세 펼침)
    - TC ID 옆에 spec_page chip 표시 (예: p.5) — 출처 추적성
  - 액션: ✓승인 / ✏️수정요청 / 👑관리자확인 / ✗삭제
  - [AI 보완 요청]: needs_revision TC만 재생성
  - [Excel 다운로드]: deleted 제외 내보내기
```

---

## 17. 환경변수 설정 (.env)

```env
# Google Gemini API (필수)
GOOGLE_API_KEY=...

# 모델 설정 (역할별 분리)
GEMINI_MODEL=gemini-2.5-flash-lite          # 기본 모델
GEMINI_MODEL_EXTRACT=gemini-2.5-flash       # 메뉴트리/기능 추출용
GEMINI_MODEL_TC=gemini-2.5-flash-lite       # TC 생성용
GEMINI_MODEL_VISION=gemini-2.5-flash        # 이미지 분석용
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-2

# XpERP 웹 크롤러 (선택)
XPERP_BASE_URL=https://dev.xperp.co.kr
XPERP_USER_ID=...
XPERP_PASSWORD=...
```

> `.env`는 Git 제외. 신규 팀원은 `.env.example` 참고하여 `.env` 생성.

---

## 18. Google Gemini API 과금 구조

| 항목 | 내용 |
|------|------|
| 과금 단위 | 사용 토큰 수 (입력 + 출력) |
| 관리 | Google AI Studio → 결제 관리 |
| 503 오류 | 모델 수요 폭증 시 일시 발생, 자동 지수 백오프 재시도 (30→60→120초, 최대 3회). 메뉴트리·상태 매트릭스·TC 생성 모두 적용 |
| 모델 권장 | 503 반복 시 GEMINI_MODEL_TC를 gemini-2.5-flash로 변경 |

> 33페이지 PDF 1회 처리 기준 약 $0.01~0.05 예상 (gemini-2.5-flash-lite 기준)

---

## 19. 서버 실행 방법

### 개발 모드 (백엔드 + 프론트 분리 실행)

```powershell
# 터미널 1 - 백엔드
cd backend
.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2 - 프론트엔드
cd frontend
npm run dev -- --host
```

### 서버 강제 종료
```powershell
# PID 확인 (메모리 가장 많이 사용하는 python 프로세스)
tasklist | findstr python

# 강제 종료
taskkill /PID {pid} /F
```

### 운영 모드 (단일 서버)

```powershell
# 1. 프론트엔드 빌드
cd frontend && npm run build

# 2. 백엔드 서버만 실행
cd backend
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 20. Excel 리포트 구성

### TC 리포트 (`/api/testcases/document/{id}/export`)
- 시트 1 - 요약: 프로젝트명, 생성일, 유형별/우선순위별 분포
- 시트 2 - TC 목록: TC ID / **기획서 페이지(spec_page)** / 카테고리 / 제목 / 목적 / 유형 / 우선순위 / 사전조건 / 테스트 단계 / 기대 결과
- `deleted` 상태 TC 제외, 우선순위별 색상 구분

### 메뉴트리 리포트 (`/api/documents/{id}/tree/export`)
- 열: 계층(1~4), 기능명, 변경유형, 기획서페이지, 설명, 검증포인트
- 깊이별 색상: 1단계(진한 파랑) → 4단계(연한 파랑)
- **TC 생성 후**: 각 리프 노드 행 아래에 그 노드의 실제 TC를 하위 행으로 펼침 (`└ [TC-001] 제목` + 유형/기획서페이지/목적/기대결과, 우선순위별 색상). category=리프 경로 매핑 기반, deleted 제외 (3-19)

### 흐름 트리 리포트 (`/api/documents/{id}/flow-tree/export`)
- 사람 골든 양식(좌→우 트라이 그리드): 범례(D/C/RC/DC/T/DD/PR/V) + Step1~N 헤더
- 각 노드를 (타입, 내용) 열 쌍으로 배치, 깊이 = Step 열. 타입별 셀 색상
- `flow_tree_report.render_flow_tree_excel()` (3-21)
- **`?with_tc=true`**: 흐름트리(좌) + TC(우) 1:1 통합 출력 (3-27)
  - TC 컬럼: TC ID / 사전조건 / 테스트 스텝 / 기대결과 / 기획서 페이지
  - Gemini가 노드 content 기반 자연어 TC 생성 (PDF 불필요, 30개 배치 처리)
  - 각 Excel 행 = 각 TC (path_tracker 기반 1:1 매핑 보장)

---

## 21. TC 품질 비교 검증 결과

### 21-1. 초기 검증 (2026-04-24)

동일 기획서(XpERP 홈화면 리뉴얼, 33페이지)로 3가지 방법 비교:

| 항목 | 수동 (사람) | AI (RAG 없음) | AI (RAG 적용) |
|------|------|------|------|
| TC 수 | 975개 | 179개 | 78개 |
| 평균 테스트 단계 수 | 3.0 | 1.3 | 2.8 |
| 서비스 용어 반영 | 매우 높음 | 낮음 | 높음 |
| 매뉴얼 스펙 반영 | 없음 | 없음 | 있음 |
| 종합 평가 | B+ | C+ | B |

### 21-2. 사람 vs AI 비교 분석 — doc 40 간편전자고지서 (2026-05-28)

사람 작성 Excel (114개 TC, XpERP 58 + XpBIZ 56) vs 우리 AI 생성 doc 40 (265개 TC) 비교 분석 결과:

| 지표 | 사람 | 우리 (이전) | 의미 |
|---|---|---|---|
| 총 TC 수 | 114개 | 265개 | AI가 2배 이상 양산 — 추측성 포함 |
| TC 유형 | 전부 "정상" + 사전조건 분기 | positive/negative/boundary/exception 흔들림 | 분류 일관성 부족 |
| 카테고리 | 수납 > 미납조회 > 미납대장 | 회계 > 미납대장 화면 ❌ | 프롬프트 anchor로 오분류 |
| 기획서 페이지 참조 | 전 TC 명시 (5P, 6P, 8p, 9p) | 없음 | 추적성 부재 |
| 기획서 문구 인용 | 그대로 인용 | 추상 표현 ("정확하게 표시되는지 확인") | 검수 가치 ↓ |

**핵심 누락 시나리오 (사람 작성 vs 우리 직전):**
- 해지 시나리오: 사람 14개 / 우리 **0개**
- 약관 동의 분기: 사람 7개 / 우리 **0개**
- 권한 "사용안함" 분기: 사람 8개 / 우리 **0건**
- 신청 완료 알림톡 발송 검증: 사람 명시 / 우리 **0건**

**우리만 만든 추측성 TC**:
- "최대 길이" 경계값: 우리 10건 / 사람 0건 (기획서 미명시)
- 인프라 추측 (API 응답·네트워크·F5): 우리 16건 / 사람 1건
- 팝업 크기 변경·새로고침 등 UI 일반론: 우리 다수 / 사람 0건

→ 이 분석 결과를 토대로 Phase 4.8~4.10 (TC 품질 락인 + 상태 매트릭스) 진행. 다음 동일 PDF 재생성 후 재검증 예정.

---

## 22. 향후 과업

| 단계 | 내용 | 상태 |
|------|------|------|
| Phase 1 | 백엔드 API + TC 생성 엔진 | ✅ 완료 |
| Phase 2 | RAG 시스템 (매뉴얼 + 결함 이력 + TC 이력) | ✅ 완료 |
| Phase 3 | 프론트엔드 TC 검토 UI | ✅ 완료 |
| Phase 4 | 변경 유형(ChangeType) 자동 감지 및 전략 분기 | ✅ 완료 |
| Phase 4.5 | TC 생성 레벨 시스템 (1~5단계, 전문 용어화) | ✅ 완료 |
| Phase 4.6 | 메뉴트리 추출·검토 플로우 + QA 룰셋 시스템 | ✅ 완료 |
| Phase 4.7 | AI 프롬프트 도메인 특화 | ✅ 완료 |
| **Phase 4.8** | **TC 품질 락인 — 레벨 재설계·추측성 금지·기획서 문구 인용·메뉴 경로 정정** | ✅ 완료 (2026-05-28) |
| **Phase 4.9** | **spec_page 필드 + 룰셋-프롬프트 충돌 정리** | ✅ 완료 (2026-05-28) |
| **Phase 4.10** | **상태 매트릭스 도출 + TC 분류 결정 트리 (사람 수준 시나리오 분해)** | ✅ 완료 (2026-05-29) |
| **Phase 4.12** | **spec_page 추적성 재설계(트리→TC 상속) + JSON 파싱 견고화** | ✅ 완료 (2026-06-17) |
| **Phase 4.13** | **노드↔TC 연결 고정(category 강제) + 트리 Excel 노드별 TC 커버리지 표시** | ✅ 완료 (2026-06-17) |
| **Phase 4.14** | **흐름 트리 PoC — 사람 양식(PR/C/D/T/H/V) 자동추출 검증** | ✅ 완료 (2026-06-22) |
| **Phase 5.0** | **흐름 트리 정식 전환** (스키마·추출·Excel·TC 선형화·탭 UI) → [설계서](flow_tree_schema_design.md) | ✅ 완료 (2026-06-23) |
| **Phase 5.1** | **룰셋 능동화** (커버리지 점검 게이트 + 피드백→룰셋 원클릭·clone-on-write) | ✅ 완료 (2026-06-23) |
| **Phase 5.2** | **점검 정확도** (fixability 분류·dedupe·조건부/상태 규칙 정정·시스템 룰셋 동기화) | ✅ 완료 (2026-06-24) |
| **Phase 5.3** | **흐름 트리 렌더러 품질 개선** (PR 독립 행·R2-1·D 캐스케이드·path_tracker 누적) | ✅ 완료 (2026-06-29) |
| **Phase 5.4** | **흐름 트리 2단계 파이프라인** (구조적 트리→골격→흐름 트리, 중복 루트 방지) | ✅ 완료 (2026-06-30) |
| **Phase 5.5** | **자동 교정 루프** (생성→점검→Gemini 교정 패스, 기획서 참조, 폴링 버그 수정) | ✅ 완료 (2026-06-30) |
| **Phase 5.6** | **룰셋 구조 대폭 개편** (flow_rules·코드→DB·상속 모델·클론 제거·Few-shot·체크리스트) | ✅ 완료 (2026-07-01) |
| **Phase 5.7** | **흐름트리+TC 통합 Excel** (1:1 매핑·Gemini 자연어 TC·30개 배치·fetch UX) | ✅ 완료 (2026-07-03) |
| **Phase 5.8** | **QA 태깅 규칙 정비** (PR→V 직결 금지·R9-6/R9-7/R3-2·여집합 정책·태깅 합의서 갱신) | ✅ 완료 (2026-07-02) |
| Phase 5.9 | TC 품질 정량 재검증 (사람 엑셀 vs 흐름트리 기반 TC 비교) | ⏳ 예정 |
| Phase 6 | TC 수동 테스트 결과 기록 기능 | ⏳ 예정 |
| Phase 7 | Playwright 기반 자동화 테스트 연동 (현재는 보조 기능) | ⏳ 예정 |
