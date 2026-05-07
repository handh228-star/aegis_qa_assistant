# Aegis QA Assistant

AI 기반 테스트케이스(TC) 자동 생성 시스템.
기획서(PDF) → 메뉴트리 추출 → 사용자 검토 → TC 생성 → Excel 리포트 출력

## 핵심 플로우
1. PDF 기획서 업로드 (Excel/Figma → PDF 변환본)
2. Google Gemini API로 기획서 분석 → 메뉴트리(4단계 계층) 추출
3. 사용자가 메뉴트리 검토·편집 후 TC 생성 시작
4. Gemini API로 TC 자동 생성 (정상/비정상/경계값/예외 유형 포함, 레벨 1~5)
5. TC 검토/수정 후 Excel 리포트 출력

## 프로젝트 구조
```
backend/
  app/
    api/          # FastAPI 라우터 (projects, documents, testcases, rulesets, manuals, defects)
    models/       # SQLAlchemy DB 모델 (project, document, testcase, qa_ruleset)
    services/     # 핵심 비즈니스 로직 (tc_generator, rag_service, document_parser 등)
    core/         # 설정 (config.py)
  requirements.txt
frontend/
  src/
    pages/        # ProjectsPage, DocumentsPage, TreeViewPage, TCReviewPage, RulesetsPage
    api.js        # Axios API 클라이언트
uploads/          # 업로드된 PDF 저장
reports/          # 생성된 Excel 리포트
vectordb/         # 벡터 DB (매뉴얼, 결함이력, TC이력)
docs/
  project_spec.md # 전체 사양서 (최신)
```

## 기술 스택
- Backend: Python 3.12 + FastAPI
- DB: SQLite (개발) → PostgreSQL (운영)
- AI: Google Gemini API (gemini-2.5-flash / gemini-2.5-flash-lite, 역할별 분리)
- PDF 처리: pypdf (텍스트 기반), Gemini Vision (이미지 기반)
- 벡터 DB: SimpleVectorStore (numpy 기반 자체 구현, pickle 저장)
- 프론트엔드: React + Vite
- 리포트: openpyxl

## TC 품질 기준
- 유형 분포: 정상 40% / 비정상 30% / 경계값 20% / 예외 10%
- 필수 필드: tc_id, category, title, objective, preconditions, steps, expected_result
- 우선순위: high / medium / low
- 기본 TC 생성 레벨: Lv.3 정밀 검증 (~400개)

## 환경 설정
- `.env` 파일에 GOOGLE_API_KEY 필수 (Google AI Studio에서 발급)
- Python 3.12 필수 (3.14 사용 불가 — pydantic-core 휠 미제공)
- 가상환경: `py -3.12 -m venv backend/.venv`
- pip 설치 시 사내 SSL 우회: `--trusted-host pypi.org --trusted-host files.pythonhosted.org`
