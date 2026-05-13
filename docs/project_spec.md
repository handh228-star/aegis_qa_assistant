# Aegis QA Assistant — 프로젝트 사양서

> 작성일: 2026-04-23
> 최종 수정: 2026-05-07
> 버전: v0.9.0
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

## 2. 진행 현황 (2026-05-07 기준)

| 항목 | 상태 | 비고 |
|------|------|------|
| FastAPI 백엔드 셋업 | ✅ 완료 | |
| DB 모델 설계 및 생성 | ✅ 완료 | SQLite |
| PDF 파싱 서비스 | ✅ 완료 | pypdf 사용 |
| Google Gemini API 연동 | ✅ 완료 | gemini-2.5-flash 계열 |
| TC 생성 서비스 | ✅ 완료 | |
| Excel 리포트 생성 | ✅ 완료 | |
| RAG - 매뉴얼 이력 | ✅ 완료 | 매뉴얼 PDF 벡터화, TC 생성에 반영 |
| RAG - 결함 이력 | ✅ 완료 | 테스트 결과 Excel → Fail TC 벡터화 |
| RAG - TC 이력 | ✅ 완료 | 생성된 TC 자동 벡터화, 다음 TC 생성에 참고 |
| TC 검토 UI (프론트엔드) | ✅ 완료 | React + Vite |
| TC 승인/수정요청/관리자확인/AI재생성 | ✅ 완료 | admin_required 플래그 포함 |
| 변경유형(ChangeType) 자동 감지 | ✅ 완료 | 기능 단위 new_feature/modification/bug_fix 분기 |
| TC 생성 레벨 시스템 (1~5) | ✅ 완료 | 레벨명 전문 용어화, 기본값 Lv.3 |
| TC 재시도 로직 (503 대응) | ✅ 완료 | 1회 자동 재시도 |
| **메뉴트리 추출 및 검토 플로우** | ✅ 완료 | PDF → 메뉴트리 → 사용자 검토 → TC 생성 |
| **메뉴트리 4단계 계층 구조** | ✅ 완료 | 모듈 > 화면 > 영역 > 기능 |
| **메뉴트리 Excel 다운로드** | ✅ 완료 | TreeViewPage + TCReviewPage 양쪽 지원 |
| **QA 룰셋 관리 시스템** | ✅ 완료 | 메뉴트리 추출 지침 + TC 생성 지침 관리 |
| **AI 프롬프트 도메인 특화** | ✅ 완료 | 아파트 ERP 전문 QA 엔지니어 역할 반영 |
| GitHub 협업 설정 | ✅ 완료 | Collaborator 등록 완료 |
| 프론트엔드 + 백엔드 통합 배포 | ⏳ 예정 | Phase 5 |
| TC 수동 테스트 결과 기록 기능 | ⏳ 예정 | Phase 6 |
| Playwright 자동화 테스트 연동 | ⏳ 예정 | Phase 7 |

---

## 3. 개발 경과 요약 (주요 기술 결정 이유)

### 3-1. AI 제공자 변경: Anthropic Claude → Google Gemini

초기에는 Anthropic Claude API(claude-sonnet-4-6)를 사용하려 했으나 두 가지 문제로 Google Gemini로 전환:

1. **33페이지 PDF 용량 초과 (413 오류)** → pypdf로 텍스트 추출 방식으로 우회
2. **법인카드 결제 불가 (402 오류)** → platform.claude.com 에서 카드 결제 버튼 비활성화

Google AI Studio에서 Gemini API 키를 발급받아 전환. `google-generativeai` 패키지 사용 시도 중 FutureWarning 발생, 최종적으로 신규 패키지 `google-genai` 로 재전환.

**사용 모델 이력:**
- `gemini-2.0-flash`, `gemini-2.0-flash-001`: 신규 계정에서 404 오류 → 제외
- `gemini-2.5-flash`: 503 오류(수요 폭증) 반복 → `gemini-2.5-flash-lite`로 전환
- 현재: 역할별 모델 분리 운영 (GEMINI_MODEL_EXTRACT, GEMINI_MODEL_TC 등 .env에서 설정)

**API Key 이력**
- 초기: 개인 결제 계정 (handh228@gmail.com) — 토큰 한도 초과로 503 반복
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
              └── 이 프로젝트: SimpleVectorStore (numpy 기반 자체 구현)
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
- 회계/부과/인사급여/검침/입주관리 도메인 지식 명시
- 공동주택관리법·회계처리기준 규정 제약 숙지 명시
- 경계값 분석, 동등 분할, 탐색적 테스트, 결함 예측 기법 명시
- 세 프롬프트 모두 적용 (ANALYZE_PROMPT, TC_GENERATE_PROMPT, TREE_PROMPT)

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
  ③ AI 분석 — 메뉴트리 추출 (status: analyzing → analyzed)
     └── 4단계 계층 구조: 모듈 > 화면 > 영역 > 기능
     └── 각 노드: change_type 자동 판단 + key_points 추출
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
  ⑦ AI TC 자동 생성 (레벨 + 룰셋 + RAG 컨텍스트 반영)
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
│       │   ├── document.py          ← Document + DocumentStatus (analyzing/analyzed 포함)
│       │   ├── testcase.py          ← TestCase + ReviewStatus
│       │   └── qa_ruleset.py        ← QARuleSet (메뉴트리/TC 생성 지침, 기본 룰 정의)
│       ├── api/
│       │   ├── projects.py          ← 프로젝트 CRUD (ruleset_id 포함)
│       │   ├── documents.py         ← PDF 업로드, 메뉴트리 생성/조회/수정/Excel 내보내기, TC 생성 시작
│       │   ├── testcases.py         ← TC 조회/검토/재생성/Excel 내보내기
│       │   ├── rulesets.py          ← QA 룰셋 CRUD (기본값 설정, 시스템 룰셋 보호)
│       │   ├── manuals.py           ← 매뉴얼 PDF 인제스트/조회/삭제
│       │   └── defects.py           ← 테스트 결과 Excel 업로드 → 결함 이력 저장
│       └── services/
│           ├── tc_generator.py      ← Gemini API 연동, 메뉴트리 추출 + TC 생성 파이프라인 (레벨 + 룰셋 지원)
│           ├── document_parser.py   ← PDF 텍스트 추출, 타입 감지, 청크 분할
│           ├── report_generator.py  ← TC → Excel 리포트 생성
│           ├── rag_service.py       ← 매뉴얼 + 결함이력 + TC이력 통합 검색
│           ├── manual_ingestion.py  ← SimpleVectorStore 정의, 매뉴얼 PDF 벡터화
│           ├── defect_ingestion.py  ← 테스트 결과 Excel 파싱, Fail TC 벡터화
│           └── tc_ingestion.py      ← 생성된 TC 자동 벡터화 (tc_history)
│
├── frontend/                        ← React 프론트엔드
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                  ← React Router 설정 (5개 라우트)
│       ├── index.css                ← 전역 스타일
│       ├── api.js                   ← Axios 기반 API 클라이언트
│       └── pages/
│           ├── ProjectsPage.jsx     ← 프로젝트 목록/생성 (룰셋 선택 포함)
│           ├── DocumentsPage.jsx    ← TC 레벨 선택 + PDF 업로드 + 처리 상태 폴링
│           ├── TreeViewPage.jsx     ← 메뉴트리 검토/편집 + TC 생성 시작 + Excel 다운로드
│           ├── TCReviewPage.jsx     ← TC 검토 (승인/수정요청/관리자확인/삭제/AI재생성) + 메뉴트리 조회
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
    └── project_spec.md              ← 본 문서
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
| menu_tree | Text | 추출된 메뉴트리 JSON |
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
| category | String(200) | 기능 카테고리 (메뉴트리 경로) |
| title | String(500) | TC 제목 |
| objective | Text | 테스트 목적 |
| preconditions | JSON | 사전 조건 목록 |
| steps | JSON | 테스트 단계 [{step, action, expected}] |
| expected_result | Text | 최종 기대 결과 |
| tc_type | Enum | positive / negative / boundary / exception |
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

**TC 유형 권장 분포**
| 유형 | 설명 | 권장 비율 |
|------|------|------|
| positive | 정상 케이스 | 40% |
| negative | 비정상 케이스 | 30% |
| boundary | 경계값 테스트 | 20% |
| exception | 예외/오류 처리 | 10% |

> 이 분포는 TC 레벨(1~5)에 관계없이 동일하게 적용된다. 레벨은 각 유형의 케이스 수(깊이)를 조절할 뿐, 특정 유형을 생략하지 않는다.

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
| tree_rules | Text | 메뉴트리 추출 지침 (AI 프롬프트에 추가) |
| tc_rules | Text | TC 생성 지침 (AI 프롬프트에 추가) |
| is_default | Boolean | 기본 룰셋 여부 (1개만 가능) |
| is_system | Boolean | 시스템 제공 룰셋 (삭제 불가) |
| created_at | DateTime | |
| updated_at | DateTime | |

---

## 9. TC 생성 레벨 시스템

업로드 전에 TC 생성 레벨(1~5)을 선택하여 검증 깊이를 조절한다. **기본값은 Lv.3 (정밀 검증).**

| 레벨 | 이름 | 참고 목표 수량 | 기능당 생성 수 | 기준 |
|------|------|:---:|:---:|------|
| 1 | 핵심 검증 | ~100개 | 2~3개 | 대표 케이스 위주, 리스크 낮거나 일정 촉박한 경우 |
| 2 | 표준 검증 | ~200개 | 4~6개 | 정상/비정상/경계값/예외 균형, 일반 프로젝트에 적합 |
| **3** | **정밀 검증** | **~400개** | **8~12개** | **세부 시나리오·업무 규칙 예외 포함, 중요도 높은 기능에 권장 (기본값)** |
| 4 | 심층 검증 | ~800개 | 14~20개 | 조합 케이스·연동 시나리오까지, 고품질 검증이 필요한 경우 |
| 5 | 전수 검증 | ~1600개 | 25~35개 | 모든 엣지케이스 망라, 대형 릴리즈·고위험 프로젝트 |

**설계 원칙**
- **목표 수량은 참고값(soft guideline)**이다. 품질이 우선이므로 의미 없는 케이스를 수량 채우기 위해 억지로 만들지 않는다.
- **모든 레벨에서 4가지 유형(정상/비정상/경계값/예외) 분포를 유지**한다.
- TC 검토 화면 하단에 생성 레벨과 참고 목표 수량을 표시하되, 부수적인 정보로 제공한다.

**구현 위치:** `backend/app/services/tc_generator.py` → `TC_LEVEL_CONFIG` 딕셔너리

---

## 10. QA 룰셋 시스템

### 개념
QA 룰셋은 메뉴트리 추출과 TC 생성 시 AI에게 전달하는 추가 지침을 저장하는 단위다. 프로젝트 생성 시 룰셋을 선택하면 해당 프로젝트의 모든 기획서 분석·TC 생성에 일관된 규칙이 적용된다.

### 주입 방식
- `tree_rules` → `TREE_PROMPT` 뒤에 `[추가 지침]` 섹션으로 추가
- `tc_rules` → TC 생성 프롬프트의 `rag_context` 섹션으로 추가

### 시스템 기본 룰셋 ("웹 서비스 공통")
서버 최초 기동 시 자동 생성. 삭제 불가 (is_system=True). 주요 내용:
- 입력 필드: 정상 입력, 필수값 미입력, 최대 길이 초과, 특수문자, 공백 케이스
- 버튼: 클릭 후 팝업/화면 전환, 비활성화 상태, 권한 없는 경우
- 드롭다운/셀렉트: 기본값, 빈 목록, 단일/복수 선택
- 모달: 열기/닫기, 배경 클릭 닫기, ESC 닫기, 데이터 저장 여부
- 권한 분기: 일반/관리자/미로그인 상태별 접근 제어

### 룰셋 관리 UI
경로: `/rulesets`
- 전체 룰셋 목록 조회 (기본 확장 표시)
- 신규 룰셋 생성 / 수정 / 삭제 (시스템 룰셋 제외)
- 기본값 설정 (한 번에 1개만)
- 프로젝트 생성 시 룰셋 선택 드롭다운 자동 연동

---

## 11. AI 프롬프트 구조

### 역할 프롬프팅 (공통)
세 개의 메인 프롬프트(ANALYZE_PROMPT, TC_GENERATE_PROMPT, TREE_PROMPT) 모두 동일한 도메인 전문가 역할로 시작:

```
당신은 10년 이상 경력의 고도의 QA 전문가이며, 아파트·공동주택 관리 ERP 시스템에 정통합니다.
회계(예산/결산/수납/미납관리), 관리비 부과(세대별 부과·감면·할인·연체가산), 인사급여(급여계산·4대보험·근태),
검침(수도·전기·가스 세대/공동 검침·오류보정), 입주관리(세대정보·이사·주차·민원) 전 영역의 업무 흐름과
공동주택관리법·회계처리기준 등 규정 제약을 숙지하고 있습니다.
```

### TREE_PROMPT (메뉴트리 추출용)
- 4단계 계층 구조 강제: 모듈 > 화면 > 영역 > 기능
- 단순한 화면은 2~3단계 허용, 복잡한 화면은 4단계 세분화
- 리프 노드에 key_points(검증 포인트 목록) 포함 요구

### TC_GENERATE_PROMPT (TC 생성용)
- change_type 기반 TC 생성 전략 분기
- tc_level별 per_feature 수량 및 depth 지침 주입
- RAG 컨텍스트 (매뉴얼 스펙 + 결함 이력 + TC 이력) 주입

### 룰셋 추가 지침 주입
- TREE_PROMPT + ruleset.tree_rules → 메뉴트리 추출 시 사용
- TC_GENERATE_PROMPT + ruleset.tc_rules → TC 생성 시 사용

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
| POST | /api/documents/{document_id}/generate-tc | TC 생성 시작 (메뉴트리 검토 완료 후) |

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
메뉴트리 추출 (build_menu_tree)
  ├── 텍스트 기반 PDF: 텍스트 추출 → TREE_PROMPT로 전달
  └── 이미지 기반 PDF: PDF document 타입으로 전달
  → 응답: { title, tree: [계층 구조 노드] } (4단계까지)
  → DB 저장 (menu_tree 컬럼)
  → status: analyzed
    ↓
[사용자 TreeViewPage에서 검토·편집]
  ├── 제외 항목 설정 가능
  └── Excel 다운로드 가능
    ↓
[사용자가 TC 생성 시작 클릭]
[백그라운드 2단계 - status: tc_generating]
    ↓
1단계: 메뉴트리에서 리프 노드 추출 (_collect_leaf_nodes)
  → 리프 노드 = 실제 TC 생성 대상 기능
  → category = 상위 경로 포함 전체 경로 (예: "회계 > 수납 화면 > 검색 영역 > 날짜 입력")
    ↓
2단계: RAG 컨텍스트 조회
  ├── 매뉴얼 벡터 DB 검색 (상위 8개)
  ├── 결함 이력 벡터 DB 검색 (상위 5개)
  └── TC 이력 벡터 DB 검색 (상위 5개)
    ↓
3단계: Gemini API — TC 생성 (기능별 순차 처리)
  → 레벨 지침 + 룰셋 지침 + RAG 컨텍스트 + change_type 전략 적용
    ↓
4단계: DB 저장 + TC 이력 벡터 DB 자동 업데이트
    ↓
[완료 - status: tc_generated]
```

---

## 14. 메뉴트리 구조

### 계층 정의 (4단계)
```
1단계 (모듈): 회계, 부과, 인사급여, 검침, 입주관리 등 업무 모듈
    └── 2단계 (화면): 관리비 부과 화면, 미납 조회 화면 등
            └── 3단계 (영역): 검색 조건 영역, 입력 폼 영역, 목록 영역 등
                    └── 4단계 (기능): 세대번호 입력, 부과 확정 버튼 등 ← TC 생성 대상 (리프 노드)
```

단순한 화면은 2~3단계 허용. 복잡한 화면은 4단계 세분화.

### 노드 구조 (JSON)
```json
{
  "id": "1-1-1-1",
  "name": "세대번호 입력",
  "description": "관리비 부과 대상 세대 번호 입력 필드",
  "change_type": "modification",
  "key_points": ["정상 세대번호 입력", "존재하지 않는 세대번호", "입력값 초기화"],
  "children": []
}
```

### Excel 다운로드
- 경로: `GET /api/documents/{document_id}/tree/export`
- 열: 계층 / 기능명 / 변경유형 / 설명 / 검증포인트
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
    ↓ 클릭
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
| 503 오류 | 모델 수요 폭증 시 일시 발생, 자동 1회 재시도 처리 |
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
- 시트 2 - TC 목록: TC ID, 카테고리, 제목, 유형, 우선순위, 사전조건, 단계, 기대결과
- `deleted` 상태 TC 제외, 우선순위별 색상 구분

### 메뉴트리 리포트 (`/api/documents/{id}/tree/export`)
- 열: 계층(1~4), 기능명, 변경유형, 설명, 검증포인트
- 깊이별 색상: 1단계(진한 파랑) → 4단계(연한 파랑)

---

## 21. TC 품질 비교 검증 결과 (2026-04-24)

동일 기획서(XpERP 홈화면 리뉴얼, 33페이지)로 3가지 방법 비교:

| 항목 | 수동 (사람) | AI (RAG 없음) | AI (RAG 적용) |
|------|------|------|------|
| TC 수 | 975개 | 179개 | 78개 |
| 평균 테스트 단계 수 | 3.0 | 1.3 | 2.8 |
| 서비스 용어 반영 | 매우 높음 | 낮음 | 높음 |
| 매뉴얼 스펙 반영 | 없음 | 없음 | 있음 |
| 종합 평가 | B+ | C+ | B |

> 메뉴트리 기반 TC 생성 + 도메인 특화 프롬프트 + QA 룰셋 적용 이후 품질 재검증 예정

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
| Phase 4.7 | AI 프롬프트 도메인 특화 (아파트 ERP) | ✅ 완료 |
| Phase 5 | 프론트+백 통합 배포 (단일 서버) | ⏳ 예정 |
| Phase 6 | TC 수동 테스트 결과 기록 기능 | ⏳ 예정 |
| Phase 7 | Playwright 기반 자동화 테스트 연동 | ⏳ 예정 |
| Phase 8 | 팀 협업 기능 (멀티유저, 권한 관리) + 워커 스케일 아웃 (Celery) | ⏳ 예정 |
