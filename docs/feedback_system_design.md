# QA 피드백 반영 시스템 설계서 (초안)

> 목적: QA팀이 생성된 트리/TC를 검토하고 준 개선 피드백을, **다음 문서에도 재발하지 않도록** 체계적으로 흡수하는 구조를 사전 준비한다.
> 상태: 설계 단계 (구현 전). 피드백 수령 형태 확정 후 단계적 구현.
> 작성: 2026-06-18

---

## 1. 대원칙 — 피드백은 두 레벨, 절대 섞지 않는다

| 레벨 | 정의 | 예시 | 반영처 |
|------|------|------|--------|
| **인스턴스(instance)** | 이 건 하나만 고치면 끝 | "이 TC 스텝 틀림", "이 노드명 오타" | DB 직접 수정 / 단건 재생성 |
| **규칙(rule)** | 일반화되는 패턴. 안 잡으면 매 문서 재발 | "신청 플로우엔 항상 중복신청 케이스", "권한 분기 누락", "exception 과생성", "도메인 용어 X=Y" | 룰셋 / few-shot 예시 / 프롬프트 |

**핵심 리스크:** 모든 피드백을 인스턴스로만 처리하면 시스템이 학습되지 않아 QA팀이 매 문서 같은 지적을 반복한다. **준비 작업의 본질 = rule 레벨을 포착·분류·반영·측정하는 통로를 까는 것.**

---

## 2. 권장 피드백 수령 형태 (현재 미정 → 제안)

우리 구조(노드↔TC 연결, spec_page, 룰셋)에 가장 유리한 형태는 **하이브리드**:

### (A) 주 채널 — "수정 Excel 라운드트립" (권장)
- QA팀은 어차피 Excel로 작업한다. 우리가 내보낸 **메뉴트리 Excel(노드+TC 하위 행)**을 그대로 검토 대상으로 삼는다.
- Excel에 **피드백 전용 열**을 추가해 QA가 채운다: `[분류]`, `[스코프]`, `[코멘트/정답]`.
- QA는 (1) 셀을 직접 고치거나, (2) 행을 추가/삭제(누락 TC 추가·잘못된 TC 삭제), (3) 피드백 열에 메모.
- 우리는 재임포트 → 우리 결과와 **diff** → 갭을 정량화 + 피드백 레코드 자동 생성.
- 장점: QA 작업 흐름에 자연스럽고, 동시에 **골든 레퍼런스**를 공짜로 확보. 이미 `docs/human_Aegis_...최종.xlsx`가 그 예시.
- 전제: 자유 편집은 파싱이 깨지므로 **고정 템플릿 + node path/TC ID를 키로** 유지.

### (B) 보조 채널 — 프로그램 내 구조화 태깅
- TCReviewPage에서 건별 `분류 + 스코프 + 코멘트`를 찍는다(자유 텍스트 `review_note` 확장).
- 즉시·세밀한 rule 포착에 유리. (A)가 놓치는 "이건 일반 규칙이다" 신호를 정확히 남김.

> 결론: **(A)를 1차로 깔고 (B)를 병행.** (A)가 갭의 "양"을, (B)가 갭의 "의도(rule 여부)"를 잡는다.

---

## 3. 데이터 모델 변경

### 3.1 신규 테이블 `feedback`
```
id              INTEGER PK
document_id     FK
target_type     'tree_node' | 'testcase' | 'global'
target_ref      노드 전체 경로(category) 또는 tc_id, global이면 NULL
spec_page       VARCHAR(50)  -- 노드/TC에서 상속, 추적용
category        'structure' | 'missing' | 'type_misclassify'
                | 'priority' | 'wording' | 'domain_knowledge'
                | 'over_generation' | 'other'
scope           'instance' | 'rule'      -- ★ 가장 중요한 칸
comment         TEXT          -- QA 원문
suggested_fix   TEXT/JSON     -- 정답(있으면)
status          'open' | 'applied' | 'wont_fix' | 'converted_to_rule'
applied_ref     반영처 (ruleset_id / example_id 등)
source          'excel_import' | 'in_app' | 'meeting'
created_at / created_by
```
- `target_ref`가 노드 경로/ TC ID인 덕분에 **node↔TC 연결 + spec_page**(이미 구현됨)로 정확히 어느 화면·페이지의 문제인지 역추적 가능.

### 3.2 스냅샷/버전 (`document_snapshot`)
```
id, document_id, version INTEGER, label,
tree_json TEXT, tc_json TEXT, created_at
```
- 규칙 적용 **전/후** 트리·TC를 스냅샷 → 개선 효과를 diff로 측정. 골든 비교의 기준선도 됨.

### 3.3 few-shot 예시 뱅크
- 기존 `SimpleVectorStore`(numpy 기반, [manual_ingestion.py](../backend/app/services/manual_ingestion.py)) 재사용.
- 새 컬렉션 `qa_gold`: `(context: 노드 경로+description+key_points, gold_tc: 정답 TC, label)`.
- QA 승인본/정답에서 적재. TC 이력 RAG와 분리해 **"QA가 승인한 정답"으로 라벨링**.

---

## 4. 구성 요소

### 4.1 구조화 피드백 캡처 [1순위]
- API: `POST /documents/{id}/feedback`, `GET /documents/{id}/feedback`
- TCReviewPage: 건별 `분류 + 스코프 + 코멘트` 입력 UI (기존 승인/수정요청 옆).
- 기존 `review_status`/`review_note`는 유지하되, 구조화 레코드로 승격.

### 4.2 골든 임포트 + diff/갭 리포트 [1순위, 형태 (A) 채택 시]
- 임포트: QA 수정 Excel(우리 템플릿) → `{노드 경로별 TC 목록 + 피드백 열}` 파싱.
- diff 엔진: **노드 경로**로 1차 매칭, TC는 **제목/목적 임베딩 유사도**로 매칭 →
  - `matched` / `missed`(정답엔 있고 우리에 없음=누락) / `extra`(우리에만 있음=과생성) / `type_mismatch`(유형 분류 불일치)
- 산출: 갭 리포트(노드별 누락/과생성 카운트, 유형 분포 비교) + **피드백 레코드 자동 시드**.
- 스펙 로드맵 `Phase 4.11 정량 재검증`을 인프라화한 것.

### 4.3 비파괴 + 노드 단위 재생성 [2순위]
- 현재 재생성([testcases.py:139](../backend/app/api/testcases.py))은 `NEEDS_REVISION` TC만 단건 개선 → 인스턴스 레벨은 이미 OK.
- 추가 필요:
  - **노드 단위 재생성**: `POST /documents/{id}/nodes/regenerate-tc` (노드 경로 지정) → 그 리프의 TC만 `generate_testcases`로 재생성 후 머지. "누락 보강"에 사용.
  - **승인 잠금**: `approved` TC는 어떤 재생성에서도 보호. 후보 생성 → diff → 머지.
  - 전체 규칙 적용 후에도 승인분 보존.

### 4.4 피드백 → 룰셋 반자동화 [3순위]
- `scope='rule'` 피드백을 `category`별로 클러스터 → 룰셋(tree_rules/tc_rules) **추가 문구 초안 제안** → 사람 검토 후 반영.
- 룰셋 시스템은 이미 존재([qa_ruleset.py](../backend/app/models/qa_ruleset.py)).

### 4.5 few-shot 주입 [3순위]
- `generate_testcases` 프롬프트에 `qa_gold`에서 검색한 정답 예시를 RAG 컨텍스트로 주입.

### 4.6 개선 효과 측정 루프 [4순위]
- 규칙 적용 후 동일 문서 재생성 → 골든 대비 갭 delta(누락 −N, 과생성 −M, 분류 일치율 +x%) 리포트.
- "주관적 잔소리"를 측정 가능한 수치로 닫는다.

---

## 5. 이미 갖춰진 토대
- ✅ QA 룰셋 시스템 — rule 반영 종착지
- ✅ review_status / review_note — 인스턴스 채널 (구조화로 승격 예정)
- ✅ **node↔TC 연결(category=리프 경로) + spec_page** — 피드백 정밀 타겟팅의 전제 (2026-06-17 구현)
- ✅ 단건 재생성(`NEEDS_REVISION`, 승인분 보존)
- ✅ TC 이력 RAG / SimpleVectorStore — few-shot 뱅크 기초

---

## 6. 단계별 구현 계획

| 단계 | 내용 | 선행 조건 |
|------|------|-----------|
| **A. 토대** | `feedback` 테이블 + 캡처 API/UI, `document_snapshot` 버전, 승인 잠금 + 노드 단위 재생성 | 피드백 형태 무관하게 선반영 가능 |
| **B. 골든 루프** | 수정 Excel 임포트 + diff/갭 리포트 + 피드백 자동 시드 | 형태 (A) 확정 시 |
| **C. 학습 반영** | few-shot 뱅크 주입 + 피드백→룰셋 반자동화 | A·B의 데이터 축적 후 |
| **D. 측정** | 규칙 적용 전/후 갭 delta 리포트 | A~C |

> 권장 출발점: **A + B**. 무엇을 어느 레벨에 고칠지가 데이터로 보여야 C(룰셋·예시)가 추측이 아니게 된다.

---

## 7. 미결 질문
1. QA 피드백 수령 형태 최종 확정 (Excel 라운드트립 / 인앱 / 서술형 중) → §2 (A) 권장.
2. 골든 비교 시 TC 매칭 기준 — 임베딩 유사도 임계값, 사람 확인 단계 둘지.
3. 룰셋 반영을 어디까지 자동화할지 (제안까지만 vs 자동 반영).
4. 스냅샷 보관 정책 (문서당 버전 수 제한).
