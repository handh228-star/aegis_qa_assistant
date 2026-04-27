# Aegis QA Assistant — 프로젝트 사양서

> 작성일: 2026-04-23
> 최종 수정: 2026-04-27
> 버전: v0.5.1
> 작성자: ITERP 개발팀 (iterp@aegisep.com)

---

## 1. 프로젝트 개요

### 목적
기획서(PDF) 기반으로 AI가 테스트케이스(TC)를 자동 생성하여 QA 단계의 인력·비용·시간을 절감한다.
나아가 사용자 매뉴얼, 과거 테스트 결함 이력, 과거 TC 이력을 학습(RAG)하여 테스트 사이클이 반복될수록 TC 품질이 자동으로 고도화되는 구조를 목표로 한다.

### 핵심 가치
- 기획 완료 후 QA TC 작성 시간을 AI로 대폭 단축
- 실제 서비스 매뉴얼 기반으로 구체적인 입력값·제약·오류 조건을 TC에 반영
- 과거 결함 이력이 누적될수록 비정상/경계값 케이스가 자동 강화
- 과거 TC 이력이 누적될수록 TC 구조·품질이 자동으로 고도화
- 웹 UI에서 TC 검토·수정·관리자확인 플래그·AI 재생성까지 원스톱 처리

### 대상 서비스
고객 대상 상용 웹 애플리케이션 (XpERP / XpBIZ)

### 기획서 포맷
- Excel → PDF 변환본 (텍스트 기반)
- Figma → PDF 변환본 (이미지 기반)
- 두 포맷 자동 감지 후 최적 처리 방식 적용

---

## 2. 진행 현황 (2026-04-27 기준)

| 항목 | 상태 | 비고 |
|------|------|------|
| FastAPI 백엔드 셋업 | ✅ 완료 | |
| DB 모델 설계 및 생성 | ✅ 완료 | SQLite |
| PDF 파싱 서비스 | ✅ 완료 | pypdf 사용 |
| Google Gemini API 연동 | ✅ 완료 | gemini-2.5-flash-lite |
| TC 생성 서비스 | ✅ 완료 | |
| Excel 리포트 생성 | ✅ 완료 | |
| **RAG - 매뉴얼 이력** | ✅ 완료 | 매뉴얼 PDF 벡터화, TC 생성에 반영 |
| **RAG - 결함 이력** | ✅ 완료 | 테스트 결과 Excel → Fail TC 벡터화 |
| **RAG - TC 이력** | ✅ 완료 | 생성된 TC 자동 벡터화, 다음 TC 생성에 참고 |
| **TC 검토 UI (프론트엔드)** | ✅ 완료 | React + Vite |
| **TC 승인/수정요청/관리자확인/AI재생성** | ✅ 완료 | admin_required 플래그 포함 |
| **변경유형(ChangeType) 자동 감지** | ✅ 완료 | 기능 단위 new_feature/modification/bug_fix 분기 |
| TC 재시도 로직 (503 대응) | ✅ 완료 | 1회 자동 재시도 |
| GitHub 협업 설정 | ✅ 완료 | Collaborator 등록 완료 |
| 프론트엔드 + 백엔드 통합 배포 | ⏳ 예정 | npm run build 후 FastAPI 단일 서빙 |
| TC 수동 테스트 결과 기록 기능 | ⏳ 예정 | Phase 5 |
| Playwright 자동화 테스트 연동 | ⏳ 예정 | Phase 6 |

---

## 3. 개발 경과 요약 (주요 기술 결정 이유)

### 3-1. AI 제공자 변경: Anthropic Claude → Google Gemini

초기에는 Anthropic Claude API(claude-sonnet-4-6)를 사용하려 했으나 두 가지 문제로 Google Gemini로 전환:

1. **33페이지 PDF 용량 초과 (413 오류)** → pypdf로 텍스트 추출 방식으로 우회
2. **법인카드 결제 불가 (402 오류)** → platform.claude.com 에서 카드 결제 버튼 비활성화

Google AI Studio에서 Gemini API 키를 발급받아 전환. `google-generativeai` 패키지 사용 시도 중 FutureWarning 발생, 최종적으로 신규 패키지 `google-genai` 로 재전환.

**사용 모델:** `gemini-2.5-flash-lite`
- 기존 시도했던 `gemini-2.0-flash`, `gemini-2.0-flash-001`은 신규 계정에서 404 오류 발생하여 제외
- `gemini-2.5-flash` 사용 중 503 오류(수요 폭증) 반복 발생 → `gemini-2.5-flash-lite`로 전환

**API Key 이력**
- 초기: 개인 결제 계정 (handh228@gmail.com) — 토큰 한도 초과로 503 반복
- 현재: 회사 개발 계정 (aegis_tf1@aegisep.com) — 2026-04-27 전환

### 3-2. PDF 파싱 라이브러리: PyMuPDF → pypdf

PyMuPDF(fitz) 설치 시 사내 SSL 인증서 검사로 인해 MuPDF 소스 다운로드 실패. 순수 Python 패키지인 `pypdf`로 대체. 컴파일 없이 설치 가능.

### 3-3. RAG와 벡터 DB의 관계

**RAG(Retrieval-Augmented Generation)** 는 특정 도구가 아니라 기법(아키텍처)이다.
"외부 데이터를 검색(Retrieval)하여 AI 프롬프트에 주입하고, 그것을 바탕으로 생성(Generation)한다"는 방식 자체를 의미한다.

**벡터 DB(Vector Database)** 는 RAG에서 검색 저장소로 사용되는 도구다.
ChromaDB, Pinecone, Weaviate 등이 대표적이며, RAG 전용이 아니라 임베딩 벡터를 저장하고 유사도 검색을 지원하는 DB다.

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
- ChromaDB와 동일한 인터페이스 유지 (코드 변경 최소화)
- 8개 매뉴얼 PDF / 386개 청크 규모에서 충분한 성능

### 3-5. SQLite Enum 컬럼 호환성

SQLAlchemy의 `Enum` 타입은 PostgreSQL에서는 DB 네이티브 ENUM으로, SQLite에서는 VARCHAR + 선택적 CHECK 제약으로 동작한다.
개발 환경(SQLite)에서 기존 컬럼이 없는 상태에서 `ALTER TABLE ADD COLUMN`으로 추가된 Enum 컬럼에 NULL 또는 기존 데이터가 있을 경우, SQLAlchemy가 로딩 시 유효성 검사 오류를 일으킬 수 있다.

**해결 방법:** 동적으로 추가되는 컬럼(change_type 등)은 `String(50)`으로 선언하고, API 응답 직렬화 단계(Pydantic)에서 enum으로 변환한다.
- SQLAlchemy 모델: `Column(String(50), default="unknown", nullable=True)`
- Pydantic 응답: `change_type: Optional[ChangeType]` → Pydantic이 문자열을 enum으로 자동 변환
- DB 마이그레이션: `ALTER TABLE` 후 `UPDATE ... SET change_type = 'unknown' WHERE change_type IS NULL` 실행

---

## 4. 시스템 전체 플로우

```
[기획팀]
  기획서 작성 (Excel 또는 Figma)
      ↓
  PDF 변환
      ↓
[Aegis QA Assistant - 웹 UI]
  ① PDF 업로드
      ↓
  ② AI 분석 (문서 → 기능 목록 추출 + 기능별 변경유형 자동 판단)
     └── change_type: new_feature / modification / bug_fix / unknown
      ↓
  ③ RAG 컨텍스트 조회
     ├── 매뉴얼 벡터 DB 검색 → 실제 스펙(입력값, 제약, 오류 메시지 등)
     ├── 결함 이력 벡터 DB 검색 → 과거 유사 결함 패턴
     └── TC 이력 벡터 DB 검색 → 과거 유사 TC 구조 참고
      ↓
  ④ AI TC 자동 생성 (매뉴얼 스펙 + 결함 이력 + TC 이력 반영)
      ↓
  ⑤ DB 저장 + TC 이력 벡터 DB 업데이트
      ↓
  ⑥ TC 검토 화면
     ├── ✓ 승인
     ├── ✏️ 수정 요청 (메모 입력)
     ├── 👑 관리자 확인 필요 (AI 재생성 제외)
     └── ✗ 삭제
      ↓
  ⑦ AI 보완 요청 (수정 요청된 TC만 재생성 → TC 이력 갱신)
      ↓
  ⑧ Excel 리포트 다운로드
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
| AI 모델 | gemini-2.5-flash-lite | Google Gemini API |
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
| 비동기 파일 I/O | aiofiles | 24.1.0 |
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
│
├── backend/                         ← FastAPI 백엔드
│   ├── requirements.txt
│   ├── .venv/                       ← Python 3.12 가상환경 (Git 제외)
│   └── app/
│       ├── main.py                  ← FastAPI 앱 설정, 라우터 등록, 정적파일 서빙
│       ├── core/
│       │   └── config.py            ← 환경변수 설정
│       ├── models/
│       │   ├── database.py          ← DB 엔진, 세션, init_db() (컬럼 자동 마이그레이션 포함)
│       │   ├── project.py
│       │   ├── document.py          ← DocumentStatus (uploaded/tc_generating/tc_retrying/tc_generated/failed)
│       │   └── testcase.py          ← TestCase + ReviewStatus (pending/approved/needs_revision/admin_required/deleted)
│       ├── api/
│       │   ├── projects.py          ← 프로젝트 CRUD
│       │   ├── documents.py         ← PDF 업로드 + 백그라운드 TC 생성 (1회 자동 재시도) + TC이력 저장
│       │   ├── testcases.py         ← TC 조회/검토/재생성/Excel 내보내기 + TC이력 갱신
│       │   ├── manuals.py           ← 매뉴얼 PDF 인제스트/조회/삭제
│       │   └── defects.py           ← 테스트 결과 Excel 업로드 → 결함 이력 저장
│       └── services/
│           ├── document_parser.py   ← PDF 텍스트 추출, 타입 감지, 청크 분할
│           ├── tc_generator.py      ← Gemini API 연동, TC 생성/재생성 파이프라인
│           ├── report_generator.py  ← TC → Excel 리포트 생성
│           ├── manual_ingestion.py  ← SimpleVectorStore 정의, 매뉴얼 PDF 청킹·임베딩·저장
│           ├── defect_ingestion.py  ← 테스트 결과 Excel 파싱, Fail TC 추출·임베딩·저장
│           ├── tc_ingestion.py      ← 생성된 TC 임베딩·저장 (tc_history 컬렉션)
│           └── rag_service.py       ← 매뉴얼 + 결함이력 + TC이력 통합 검색, TC 생성용 컨텍스트 빌드
│
├── frontend/                        ← React 프론트엔드
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                  ← React Router 설정
│       ├── index.css                ← 전역 스타일
│       ├── api.js                   ← Axios 기반 API 클라이언트 (window.location.hostname 동적 처리)
│       └── pages/
│           ├── ProjectsPage.jsx     ← 프로젝트 목록/생성
│           ├── DocumentsPage.jsx    ← PDF 업로드, 처리 상태 폴링
│           └── TCReviewPage.jsx     ← TC 검토 (승인/수정요청/관리자확인/삭제/AI재생성)
│
├── vectordb/                        ← 벡터 DB 파일 (Git 제외)
│   ├── manual_xperp.pkl             ← 매뉴얼 임베딩 데이터
│   ├── defect_history.pkl           ← 결함 이력 임베딩 데이터
│   └── tc_history.pkl               ← TC 이력 임베딩 데이터 (자동 누적)
│
├── manual_xperp/                    ← 사용자 매뉴얼 PDF (Git 제외)
│   └── *.pdf                        ← 검침, 단지관리, 민원관리, 부과, 수납, 인사급여, 입주자, 회계
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
| created_at | DateTime | |

### Document (기획서)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| project_id | Integer FK | |
| filename | String(300) | 저장 파일명 (UUID 접두사) |
| original_filename | String(300) | 원본 파일명 |
| file_path | String(500) | |
| total_pages | Integer | |
| status | Enum | 처리 상태 |
| error_message | Text | 오류 메시지 |

**Document Status 전이**
```
uploaded → tc_generating → tc_generated
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
| category | String(200) | 기능 카테고리 |
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

**Change Type (변경 유형)**
| 값 | 설명 | TC 생성 전략 |
|----|------|-------------|
| new_feature | 신규 기능 추가 | 정상/비정상/경계값/예외 포괄 생성 |
| modification | 기존 기능 수정 | 변경 동작 검증 + 연관 기능 회귀 테스트 |
| bug_fix | 버그 수정 | 버그 재현 방지 케이스 집중 + 유사 시나리오 |
| unknown | 판단 불가 (일반 기획서) | 포괄적 생성 |

> 문서 분석 1단계에서 AI가 기능별로 자동 판단. 한 PDF 안에 여러 개발자의 변경사항이 혼재해도 기능 단위로 분기 처리.
> `change_type` 컬럼은 SQLite Enum 타입 호환성 문제로 String(50)으로 저장, Pydantic 응답 모델에서 ChangeType enum으로 변환.

**TC 유형 권장 분포**
| 유형 | 설명 | 권장 비율 |
|------|------|------|
| positive | 정상 케이스 | 40% |
| negative | 비정상 케이스 | 30% |
| boundary | 경계값 테스트 | 20% |
| exception | 예외/오류 처리 | 10% |

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

---

## 9. API 엔드포인트

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api`
**API 문서:** `http://localhost:8000/docs` (Swagger UI, 개발 모드)

### Projects
| Method | URL | 설명 |
|--------|-----|------|
| GET | /api/projects/ | 목록 |
| POST | /api/projects/ | 생성 |
| GET | /api/projects/{id} | 상세 |
| DELETE | /api/projects/{id} | 삭제 |

### Documents
| Method | URL | 설명 |
|--------|-----|------|
| POST | /api/documents/{project_id}/upload | PDF 업로드 + TC 생성 시작 |
| GET | /api/documents/{project_id}/ | 목록 |
| GET | /api/documents/status/{document_id} | 처리 상태 + error_message |

### TestCases
| Method | URL | 설명 |
|--------|-----|------|
| GET | /api/testcases/document/{doc_id} | TC 목록 (tc_type / priority / review_status / change_type 필터) |
| GET | /api/testcases/document/{doc_id}/summary | 유형·우선순위·검토 현황 통계 |
| PATCH | /api/testcases/{tc_id}/review | 검토 상태 + 메모 저장 |
| PATCH | /api/testcases/{tc_id} | TC 내용 직접 수정 |
| DELETE | /api/testcases/{tc_id} | TC 삭제 |
| POST | /api/testcases/document/{doc_id}/regenerate | needs_revision TC AI 재생성 (admin_required 제외) |
| GET | /api/testcases/document/{doc_id}/export | Excel 리포트 다운로드 (deleted 제외) |

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
| POST | /api/defects/ingest | 테스트 결과 Excel 업로드 → Fail TC 추출·저장 |
| GET | /api/defects/stats | 저장된 결함 이력 통계 |

---

## 10. TC 생성 파이프라인 (핵심 로직)

```
PDF 업로드
    ↓
[백그라운드 처리 시작 - status: tc_generating]
    ↓
1단계: PDF 타입 자동 감지
  ├── 텍스트 기반 (Excel→PDF): 페이지당 평균 50자 이상
  └── 이미지 기반 (Figma→PDF): 페이지당 평균 50자 미만
    ↓
2단계: Gemini API — 기능 분석 + 변경유형 판단
  ├── 텍스트 기반: 텍스트 추출 (최대 20,000자) → 텍스트 메시지로 전달
  └── 이미지 기반: 5페이지씩 청크 → PDF document 타입으로 전달
  → 응답: { features: [{category, description, key_points, change_type, change_summary}] }
  ※ 한 PDF 안에 여러 개발자 변경사항이 혼재해도 기능 단위로 change_type 자동 분류
    ↓
3단계: RAG 컨텍스트 조회
  ├── 매뉴얼 벡터 DB 검색 (기능 카테고리 기반, 상위 8개 청크)
  ├── 결함 이력 벡터 DB 검색 (기능 카테고리 기반, 상위 5개 결함)
  └── TC 이력 벡터 DB 검색 (기능 카테고리 기반, 상위 5개 과거 TC)
  → 프롬프트에 [매뉴얼 스펙] + [과거 결함 이력] + [과거 TC 이력] 섹션으로 주입
    ↓
4단계: Gemini API — TC 생성
  → 기능 목록 + RAG 컨텍스트 기반 TC 생성
  → 응답: { testcases: [{tc_id, category, title, ...}] }
    ↓
5단계: DB 저장 + TC 이력 벡터 DB 저장 (tc_history.pkl 자동 갱신)
    ↓
[완료 - status: tc_generated]
```

**오류 발생 시 (503 등):**
```
1차 실패 → status: tc_retrying → 30초 대기 → 재시도
              재시도 성공 → tc_generated
              재시도 실패 → failed (error_message에 원인 저장)
```

**AI 재생성 시:**
```
needs_revision TC만 대상 (admin_required, approved, deleted 제외)
  → 재생성 완료 후 review_status = pending 으로 초기화
  → tc_history 벡터 DB도 해당 document의 전체 TC로 갱신
```

---

## 11. RAG 시스템 구조

### 컬렉션 구성

| 컬렉션 | 파일 | 내용 | 인제스트 시점 |
|--------|------|------|--------------|
| manual_xperp | vectordb/manual_xperp.pkl | 서비스 매뉴얼 PDF 청크 | 수동 (API 호출) |
| defect_history | vectordb/defect_history.pkl | 과거 테스트 Fail TC | 수동 (Excel 업로드) |
| tc_history | vectordb/tc_history.pkl | 생성된 TC 이력 | 자동 (TC 생성/재생성 시) |

### 인제스트 파이프라인

```
[매뉴얼 인제스트]
  manual_xperp/*.pdf
      ↓ pypdf 텍스트 추출
      ↓ 800자 청크 분할 (100자 오버랩)
      ↓ Gemini Embedding API (배치 50개)
      → vectordb/manual_xperp.pkl

[결함 이력 인제스트]
  테스트 결과 Excel (검증결과 컬럼 기준 Fail 행 추출)
      ↓ "기능영역 / 결함내용 / 재현절차 / Jira이슈" 포맷
      ↓ Gemini Embedding API
      → vectordb/defect_history.pkl

[TC 이력 인제스트 - 자동]
  TC 생성 완료 시 / AI 재생성 완료 시 자동 호출
      ↓ "[카테고리] 제목 / 유형 / 목적 / 기대결과 / 단계" 포맷
      ↓ Gemini Embedding API (배치 50개)
      → vectordb/tc_history.pkl (document_id 단위로 교체)
```

### TC 생성 시 RAG 조회 흐름
```
기능 카테고리 목록 → 쿼리 텍스트
    ↓
  ┌── 매뉴얼 검색 (상위 8개) → 실제 스펙·제약·오류 메시지
  ├── 결함 이력 검색 (상위 5개) → 과거 유사 결함 패턴
  └── TC 이력 검색 (상위 5개) → 과거 유사 TC 구조 예시
    ↓
  프롬프트 주입 → AI가 스펙·결함·TC 패턴 반영하여 TC 생성
```

**현재 매뉴얼 현황 (XpERP)**
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

## 12. TC 검토 UI 흐름

```
[프론트엔드 - localhost:5173 / 배포 시 :8000]

프로젝트 목록 (/)
    ↓ 클릭
문서 목록 (/projects/{id})
  - PDF 업로드
  - 처리 상태 3초 폴링 (tc_generating → tc_retrying → tc_generated)
    ↓ TC 완료 문서 클릭
TC 검토 화면 (/review/{document_id})
  - 통계 바: 전체 / 검토대기 / 승인 / 수정요청 / 관리자확인 / 삭제예정
  - 필터: 유형별 / 우선순위별 / 검토상태별 (admin_required 포함) / 변경유형별 (전체/신규/수정/버그픽스)
  - TC 테이블 (행 클릭 → 상세 펼침: 목적/사전조건/단계/기대결과)
  - 액션 버튼:
      ✓  승인 (재클릭 시 pending 토글)
      ✏️  수정 요청 (메모 입력 모달)
      👑  관리자 확인 필요 (AI 재생성 제외, 재클릭 시 pending 토글)
      ✗  삭제
  - [AI 보완 요청]: needs_revision TC만 Gemini로 재생성 (admin_required 제외)
  - [Excel 다운로드]: deleted 제외하고 내보내기
```

**검토 상태별 배지 색상**
| 상태 | 색상 |
|------|------|
| pending | 회색 |
| approved | 초록 |
| needs_revision | 노랑 |
| admin_required | 보라 |
| deleted | 빨강 |

---

## 13. 환경변수 설정 (.env)

```env
# 회사 개발 계정 (aegis_tf1@aegisep.com)
GOOGLE_API_KEY=...                    # Google AI Studio API Key (필수)
GEMINI_MODEL=gemini-2.5-flash-lite    # TC 생성 모델
```

> `.env`는 Git 제외 (`.gitignore` 처리)
> 신규 팀원은 `.env.example` 참고하여 `.env` 생성

---

## 14. Google Gemini API 과금 구조

| 항목 | 내용 |
|------|------|
| 과금 단위 | 사용 토큰 수 (입력 + 출력) |
| 관리 | Google AI Studio → 결제 관리 |
| 무료 티어 | 분당 요청 수 제한 있음 (초과 시 429 오류) |
| 유료 티어 | 결제 수단 등록 후 한도 상향 |
| 503 오류 | 모델 수요 폭증 시 일시 발생, 자동 1회 재시도 처리 |

> 33페이지 PDF 1회 처리 기준 약 $0.01~0.05 예상 (gemini-2.5-flash-lite 기준)

---

## 15. 서버 실행 방법

### 개발 모드 (백엔드 + 프론트 분리 실행)

```powershell
# 터미널 1 - 백엔드
cd backend
.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# → http://localhost:8000 또는 http://{내IP}:8000

# 터미널 2 - 프론트엔드
cd frontend
npm run dev -- --host
# → http://localhost:5173 또는 http://{내IP}:5173
```

### 운영 모드 (단일 서버)

```powershell
# 1. 프론트엔드 빌드
cd frontend
npm run build
# → frontend/dist/ 생성

# 2. 백엔드 서버만 실행 (프론트 포함 서빙)
cd backend
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
# → http://{내IP}:8000 으로 프론트+백 모두 접속
```

> `main.py`가 `frontend/dist/` 존재 여부를 자동 감지하여 정적 파일 서빙 활성화
> `api.js`는 `window.location.hostname`을 동적 참조하므로 IP 접속 시 별도 설정 불필요

---

## 16. Excel 리포트 구성

**파일명:** `TC_Report_프로젝트명.xlsx`

**시트 1 - 요약**
- 프로젝트명 / 생성일 / 총 TC 수
- 유형별 분포 (정상/비정상/경계값/예외)
- 우선순위별 분포 (높음/중간/낮음)

**시트 2 - TC 목록**
- TC ID / 카테고리 / 제목 / 유형 / 우선순위 / 사전조건 / 테스트 단계 / 기대 결과
- `deleted` 상태 TC 제외
- 우선순위별 색상 구분 (높음: 빨강, 중간: 주황, 낮음: 초록)

---

## 17. TC 품질 비교 검증 결과 (2026-04-24)

동일 기획서(XpERP 홈화면 리뉴얼, 33페이지)로 3가지 방법 비교:

| 항목 | 수동 (사람) | AI (RAG 없음) | AI (RAG 적용) |
|------|------|------|------|
| TC 수 | 975개 (XpERP 기준) | 179개 | 78개 |
| 평균 테스트 단계 수 | 3.0 | 1.3 | 2.8 |
| 서비스 용어 반영 | 매우 높음 | 낮음 | 높음 |
| 매뉴얼 스펙 반영 | 없음 | 없음 | 있음 (파일명 인용) |
| 결함 추적 가능성 | Jira 연동 | 없음 | 있음 (매뉴얼 참조) |
| 정상 케이스 비중 | 미분류 | 72% | 69% |
| 종합 평가 | B+ | C+ | B |

**RAG 적용 시 개선 효과:**
- 실제 매뉴얼 경로/조건 인용 (예: `검침 > 검침입력하기 (매뉴얼 '2025_검침 20250925' 참조)`)
- 데이터 상태값 구체화 (예: `민원 '접수' 5건, '처리 중' 3건`)
- null 처리 스펙 반영 (예: `검침 데이터 null 시 '미사용' 문구 출력`)

**공통 과제:** 정상 케이스 편중(~70%) → 목표(40%) 대비 미달, 프롬프트 개선 예정

---

## 18. 향후 과업

| 단계 | 내용 | 상태 |
|------|------|------|
| Phase 1 | 백엔드 API + TC 생성 엔진 | ✅ 완료 |
| Phase 2 | RAG 시스템 (매뉴얼 + 결함 이력 + TC 이력) | ✅ 완료 |
| Phase 3 | 프론트엔드 TC 검토 UI (승인/수정/관리자확인/삭제) | ✅ 완료 |
| Phase 4 | 변경 유형(ChangeType) 자동 감지 및 전략 분기 | ✅ 완료 |
| Phase 5 | 프론트+백 통합 배포 (단일 서버) | ⏳ 예정 |
| Phase 6 | TC 수동 테스트 결과 기록 기능 | ⏳ 예정 |
| Phase 7 | Playwright 기반 자동화 테스트 연동 | ⏳ 예정 |
| Phase 8 | 팀 협업 기능 (멀티유저, 권한 관리) | ⏳ 예정 |
