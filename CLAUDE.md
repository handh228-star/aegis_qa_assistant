# Aegis QA Assistant

AI 기반 테스트케이스(TC) 자동 생성 시스템.
기획서(PDF) → 기능 분석 → TC 생성 → Excel 리포트 출력

## 핵심 플로우
1. PDF 기획서 업로드 (Excel/Figma → PDF 변환본)
2. Claude Vision API로 기획서 페이지 이미지 분석 → 기능 목록 추출
3. Claude API로 TC 자동 생성 (정상/비정상/경계값/예외 유형 포함)
4. TC 검토/수정 후 Excel 리포트 출력

## 프로젝트 구조
```
backend/
  app/
    api/          # FastAPI 라우터
    models/       # SQLAlchemy DB 모델
    services/     # 핵심 비즈니스 로직
    core/         # 설정
  requirements.txt
uploads/          # 업로드된 PDF 저장
reports/          # 생성된 Excel 리포트
```

## 기술 스택
- Backend: Python + FastAPI
- DB: SQLite (개발) → PostgreSQL (운영)
- AI: Anthropic Claude API (claude-sonnet-4-6)
- PDF 처리: PyMuPDF (fitz)
- 리포트: openpyxl

## TC 품질 기준
- 유형 분포: 정상 40% / 비정상 30% / 경계값 20% / 예외 10%
- 필수 필드: tc_id, category, title, objective, preconditions, steps, expected_result
- 우선순위: high / medium / low

## 환경 설정
- `.env` 파일에 ANTHROPIC_API_KEY 필수
- Python 3.12+ 권장
