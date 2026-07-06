# Aegis QA Assistant — 시스템 동작 다이어그램

> Mermaid 다이어그램 (VS Code에서 Markdown Preview로 렌더링 가능)

---

## 1. 전체 시스템 플로우

```mermaid
flowchart TD
    A([👤 사용자]) --> B

    subgraph SETUP["① 프로젝트 등록"]
        B[프로젝트 생성\nQA 룰셋 선택]
        B --> C[기획서 PDF 업로드\nTC 레벨 선택 Lv.1~5]
    end

    subgraph ANALYZE["② AI 자동 분석 (백그라운드)"]
        C --> D1

        D1["🤖 Gemini 1차\n구조적 트리 추출\n화면 계층 파악\n모듈 > 화면 > 영역 > 기능"]
        D1 --> D2

        D2["🤖 Gemini 2차\n상태 매트릭스 추출\n권한·코드·이력 등\n도메인 상태 차원 도출"]
        D2 --> D3

        D3[/"구조적 트리 JSON\n+ 상태 매트릭스 JSON\nDB 저장"/]
    end

    subgraph REVIEW1["③ 사용자 검토"]
        D3 --> E[TreeViewPage\n화면 계층 구조 확인\n불필요 항목 제외]
    end

    subgraph FLOWTREE["④ 흐름 트리 생성 (2단계 파이프라인)"]
        E --> F1
        F1["화면 골격 생성\n구조적 트리 → '화면 > 기능' 목록"]
        F1 --> F2
        F2["🤖 Gemini 3차\n흐름 트리 생성\nPR/C/D/T/H/V 노드\n+ 화면 골격으로 중복 루트 방지"]
        F2 --> F3
        F3["🤖 Gemini 4차\n자동 커버리지 점검\nnot_followed / spec_limited 분류"]
        F3 --> F4{위반 있음?}
        F4 -- "not_followed\n위반 존재" --> F5
        F4 -- "위반 없음" --> F6
        F5["🤖 Gemini 5차\n자동 교정\n기획서 원문 참조\n팝업 분해·spec_page 보완 등"]
        F5 --> F6
        F6[/"흐름 트리 JSON\nDB 저장 완료"/]
    end

    subgraph REVIEW2["⑤ 흐름 트리 검토"]
        F6 --> G[TreeViewPage 흐름 탭\n노드 구조 확인]
        G --> G1["🤖 AI 교정 리포트\n추가 수동 점검 가능"]
        G --> G2["재추출\n전체 재생성"]
    end

    subgraph OUTPUT["⑥ 출력"]
        G --> H1
        G --> H2
        G --> H3

        H1["📥 흐름트리 Excel\n사람 QA 양식\nStep 헤더 + 노드 그리드"]

        H2["📥 흐름트리 + TC Excel\n🌟 핵심 산출물\n흐름 트리 좌 + TC 우\n1:1 행 매핑"]

        H3["📥 구조적 TC Excel\n기존 경로\n기능별 다중 TC\npositive/negative/boundary/exception"]
    end

    style SETUP fill:#e0f2fe,stroke:#0284c7
    style ANALYZE fill:#fef3c7,stroke:#d97706
    style REVIEW1 fill:#dcfce7,stroke:#16a34a
    style FLOWTREE fill:#fde8d8,stroke:#ea580c
    style REVIEW2 fill:#dcfce7,stroke:#16a34a
    style OUTPUT fill:#ede9fe,stroke:#7c3aed

    style H2 fill:#7c3aed,color:#fff,stroke:#6d28d9
```

---

## 2. 흐름트리 + TC Excel 생성 상세

```mermaid
flowchart LR
    A["흐름트리 JSON\n(DB 저장된 트리)"] --> B

    subgraph RENDER["1단계: 흐름 트리 렌더링"]
        B["render_flow_tree_excel()\n사람 QA 양식으로 변환"]
        B --> B1["각 행 렌더링\nPR·C·D 노드를\n열(Step) 방향으로 펼침"]
        B1 --> B2[/"path_tracker 수집\nrow번호 → 노드경로 누적\n{4:[PR,C,PR,D,D,D...],\n 5:[PR,C,PR,C,D],\n ...77:[PR,V,D]}"/]
    end

    subgraph GENERATE["2단계: Gemini 자연어 TC 생성"]
        B2 --> C1["경로 30개씩 배치 분할\n77행 → 3배치\n600행 → 20배치"]
        C1 --> C2["🤖 Gemini 호출 (배치당 1회)\n경로 텍스트 전달\nFLOW_TC_ENRICH_PROMPT"]
        C2 --> C3[/"자연어 TC 반환\n{'tcs':[{row:4, title:...,\npreconditions:...,\nsteps:...,\nexpected_result:...}]}"/]
        C3 --> C4{배치 실패?}
        C4 -- "실패" --> C5["해당 배치 스킵\n기계적 선형화로 폴백"]
        C4 -- "성공" --> C6["row번호로 TC 매핑"]
        C5 --> C6
        C6 --> C1
    end

    subgraph WRITE["3단계: 통합 Excel 생성"]
        C6 --> D1["render_flow_tree_excel\n(include_tc=True, tc_data=...)"]
        D1 --> D2["흐름트리 (B~AT열)\nStep 헤더 + PR/C/D 노드\n타입별 배경색"]
        D1 --> D3["TC (AW열~)\nTC ID / 사전조건 / 테스트스텝\n기대결과 / 기획서페이지"]
        D2 --> E["최종 Excel .xlsx\n각 행 = 흐름트리 경로 + TC 1건\n완전한 1:1 대응"]
        D3 --> E
    end

    style RENDER fill:#fef3c7,stroke:#d97706
    style GENERATE fill:#fde8d8,stroke:#ea580c
    style WRITE fill:#ede9fe,stroke:#7c3aed
    style E fill:#7c3aed,color:#fff
```

---

## 3. QA 룰셋 구조 및 적용 흐름

```mermaid
flowchart TD
    subgraph RULESET["QA 룰셋 (DB)"]
        R1["🌐 시스템 룰셋\n웹 서비스 공통 XPERP\nis_system=True\n정본, 모든 프로젝트 기반"]
        R2["📁 프로젝트 룰셋\n(필요 시 추가 생성)\n기본값 없으면 시스템 사용"]
    end

    subgraph COMPOSITION["룰셋 합성 _get_composed_ruleset()"]
        C1["flow_rules\n= 시스템 룰셋 (항상 기반)\n+ 프로젝트 추가 레이어"]
        C2["tree_rules\n= 프로젝트 우선\n없으면 시스템 폴백"]
    end

    subgraph CONTENT["flow_rules 구성"]
        F1["📐 정밀도 규칙 (1~10)\n표시요소 개별 D 분해\n형제 UI 전부 포함\n상태값마다 PR 분기\n기획서 원문 인용 필수\nT 입력 행위 노드 필수 등"]
        F2["🏗️ 구조 문법 규칙 (1~13)\nPR 동작 직전에만\nPR depth 절대규칙\nPR→D 직결 금지\nD→D 체이닝\n단일 동작 원칙\n중복 루트 금지 등"]
        F3["💡 Few-shot 예시\n잘못된 예 vs 올바른 예\n3가지 핵심 패턴"]
        F4["✅ 자가 점검 체크리스트\n출력 전 5개 항목 확인"]
    end

    subgraph APPLY["프롬프트 주입"]
        A1["FLOW_PROMPT (코드)\n노드 타입 정의\nJSON 스키마 뼈대만"]
        A2["[추가 지침 — 반드시 따라야 할 구조 문법]\n= flow_rules 전체 주입"]
        A3["[추가 지침 — 보조 가이드]\n= tree_rules 주입"]
    end

    R1 --> COMPOSITION
    R2 --> COMPOSITION
    COMPOSITION --> CONTENT
    F1 & F2 & F3 & F4 --> APPLY
    APPLY --> G["🤖 Gemini 흐름트리 생성"]

    style RULESET fill:#fef3c7,stroke:#d97706
    style COMPOSITION fill:#e0f2fe,stroke:#0284c7
    style CONTENT fill:#dcfce7,stroke:#16a34a
    style APPLY fill:#ede9fe,stroke:#7c3aed
```

---

## 4. 자동 교정 루프 상세

```mermaid
sequenceDiagram
    participant BG as 백그라운드 작업
    participant G3 as Gemini 3차
    participant G4 as Gemini 4차
    participant G5 as Gemini 5차
    participant DB as Database

    BG->>G3: PDF + 화면 골격 + 룰셋
    G3-->>BG: 흐름 트리 JSON (1차)
    Note over BG,G3: ① 흐름 트리 생성

    BG->>G4: 흐름 트리 텍스트 + 룰셋 규칙
    G4-->>BG: findings [{rule, fixability, detail, suggestion}]
    Note over BG,G4: ② 자동 커버리지 점검

    alt not_followed 위반 존재
        BG->>G5: 위반 목록 + 흐름 트리 JSON + PDF
        Note right of G5: 기획서 원문 참조하여<br/>팝업 분해, spec_page 보완<br/>PR 문구 수정 등
        G5-->>BG: 교정된 흐름 트리 JSON
        BG->>DB: 교정된 트리 저장
        Note over BG,DB: ③ 자동 교정 완료
    else 위반 없음
        BG->>DB: 1차 트리 그대로 저장
    end
```

---

## 5. 데이터 모델 관계

```mermaid
erDiagram
    Project {
        int id PK
        string name
        int ruleset_id FK
    }

    Document {
        int id PK
        int project_id FK
        string original_filename
        int tc_level
        string status
        text menu_tree
        text flow_tree
        text state_inventory
    }

    TestCase {
        int id PK
        int document_id FK
        string tc_id
        string category
        string spec_page
        json preconditions
        json steps
        text expected_result
        enum tc_type
        enum priority
        enum review_status
    }

    QARuleSet {
        int id PK
        string name
        text tree_rules
        text tc_rules
        text flow_rules
        bool is_system
        bool is_default
    }

    Project ||--o{ Document : "기획서 다수"
    Project }o--|| QARuleSet : "룰셋 선택"
    Document ||--o{ TestCase : "TC 다수"
```

---

## 6. 최종 Excel 출력물 구조

```mermaid
block-beta
    columns 12

    block:HEADER:12
        H["흐름트리 + TC 통합 Excel — 각 행이 하나의 테스트 시나리오"]
    end

    block:ROW_HEADER:12
        C1["사전조건\n(PR)"]
        C2["Step 1\n(C/T)"]
        C3["Step 2\n(D)"]
        C4["Step 3\n(D)"]
        C5["Step 4\n(D)"]
        C6["…"]
        C7["Step N"]
        SPACE[" "]
        T1["TC ID"]
        T2["사전조건"]
        T3["테스트 스텝"]
        T4["기대결과"]
    end

    block:ROW1:12
        R1A["PR\nXpERP>수납>\n미납조회\n진입직전"]
        R1B["C\n미납대장\n메뉴 클릭"]
        R1C["PR\n1차오픈\n대상단지\n팝업조건"]
        R1D["D\n팝업\n타이틀"]
        R1E["D\n서브\n카피"]
        R1F["D\n장점1"]
        R1G["D\n닫기버튼"]
        SPACE2[" "]
        R1H["TC-001"]
        R1I["XpERP 로그인,\n1차오픈대상,\n팝업 미해제"]
        R1J["1.미납대장클릭\n→팝업출력\n2.닫기클릭\n→팝업닫힘"]
        R1K["팝업 닫힘,\n홈접속시\n재노출"]
    end

    block:ROW2:12
        R2A[" "]
        R2B[" "]
        R2C["PR\n권한\n읽기쓰기"]
        R2D["C\n알림톡\n버튼클릭"]
        R2E["D\n알림톡\n팝업출력"]
        R2F[" "]
        R2G[" "]
        SPACE3[" "]
        R2H["TC-002"]
        R2I["XpERP 로그인,\n1차오픈대상,\n권한=읽기쓰기"]
        R2J["1.미납대장클릭\n2.알림톡버튼클릭\n→팝업출력"]
        R2K["알림톡 발송\n및 이력 팝업\n정상 출력"]
    end

    style HEADER fill:#374151,color:#fff
    style ROW_HEADER fill:#e0f2fe,stroke:#0284c7
    style T1 fill:#ede9fe,stroke:#7c3aed
    style T2 fill:#ede9fe,stroke:#7c3aed
    style T3 fill:#ede9fe,stroke:#7c3aed
    style T4 fill:#ede9fe,stroke:#7c3aed
    style R1H fill:#ede9fe,stroke:#7c3aed
    style R1I fill:#ede9fe,stroke:#7c3aed
    style R1J fill:#ede9fe,stroke:#7c3aed
    style R1K fill:#ede9fe,stroke:#7c3aed
    style R2H fill:#ede9fe,stroke:#7c3aed
    style R2I fill:#ede9fe,stroke:#7c3aed
    style R2J fill:#ede9fe,stroke:#7c3aed
    style R2K fill:#ede9fe,stroke:#7c3aed
    style C1 fill:#fef3c7
    style R1A fill:#fef3c7
    style R2A fill:#fef3c7
    style R2C fill:#fef3c7
    style R1C fill:#fef3c7
```

---

## 렌더링 방법

### VS Code에서 확인
1. 이 파일(.md) 열기
2. `Ctrl+Shift+V` (Markdown Preview 열기)
3. Mermaid 확장 설치 필요: `Markdown Preview Mermaid Support` (shd101wyy)

### 온라인 확인
- [Mermaid Live Editor](https://mermaid.live) — 각 코드블록 내용 붙여넣기

### 이미지 변환
- VS Code: `Markdown PDF` 확장으로 PDF/PNG 변환
- CLI: `mmdc -i system_flow_diagram.md -o output.png`
