from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.models.database import Base


class QARuleSet(Base):
    __tablename__ = "qa_rulesets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(String(100), nullable=True)   # ERP, 쇼핑몰, 모바일앱 등

    tree_rules = Column(Text, nullable=True)   # 메뉴트리 추출 추가 지침
    tc_rules = Column(Text, nullable=True)     # TC 생성 추가 지침

    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # 시스템 제공 룰셋(삭제 불가)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


DEFAULT_TREE_RULES = """화면의 모든 인터랙티브 요소를 누락 없이 추출하세요.

[계층 구조 원칙]
- 화면명 > 영역명 > 세부영역 > UI요소 (최대 4단계)
- 리프 노드는 반드시 테스트 가능한 최소 단위 UI 요소로 구성

[추출 대상 UI 요소]
- 입력란(input): 텍스트박스, 검색창, 날짜입력, 숫자입력 등
- 버튼(button): 조회, 저장, 삭제, 취소, 팝업 트리거 버튼 등
- 표시영역(display): 목록, 상세정보, 라벨, 타이틀, 카운트 등
- 드롭다운(dropdown): 셀렉트박스, 콤보박스 등
- 체크박스/라디오(checkbox): 단일/다중 선택 요소
- 탭(tab): 탭 메뉴의 각 항목
- 모달/팝업(modal): 레이어 팝업, 확인/취소 팝업

[상태 분기 처리]
- 권한 있음/없음에 따라 UI가 달라지는 요소는 별도 노드로 분리
- 시스템 설정값에 따라 표시/숨김이 달라지는 요소는 별도 노드
- 버튼 활성/비활성 조건이 있는 경우 조건 명시

[key_points 작성]
- 해당 요소에서 검증해야 할 핵심 포인트를 구체적으로 명시
- 입력란: 허용 문자 유형, 길이 제한, 필수 여부
- 버튼: 클릭 후 예상 결과, 팝업 발생 여부
- 표시영역: 출력해야 할 필수 항목 목록"""


DEFAULT_TC_RULES = """각 UI 요소 유형별로 다음 체크리스트에 따라 TC를 빠짐없이 생성하세요.

[입력란(input) 필수 커버리지]
1. 화면 표시 및 플레이스홀더 텍스트 확인
2. 유효한 값 입력 → 정상 처리 확인
3. 입력 유형 제한 케이스 (각각 별도 TC):
   - 숫자만 허용 필드: 영문 입력, 한글 입력, 특수문자 입력 → 제한 여부
   - 특수문자 제한: 허용 특수문자 vs 미허용 특수문자
4. 길이 경계값 TC:
   - 최대 허용 길이 정확히 입력 → 반영
   - 최대 허용 길이 초과 입력 → 제한
5. 공백 입력, 미입력 상태에서 저장/조회 시도

[버튼(button) 필수 커버리지]
1. 화면 표시 확인
2. 클릭 → 정상 결과 확인
3. 팝업/모달 발생 시 반드시 아래 각각 별도 TC:
   - 확인(저장) 버튼 클릭 → 처리 완료 확인
   - 취소 버튼 클릭 → 팝업 닫힘, 변경사항 미반영
   - 닫기(X) 버튼 클릭 → 팝업 닫힘
4. 버튼 비활성화(disabled) 조건이 있으면 조건별 별도 TC

[표시영역(display) 필수 커버리지]
1. 필수 항목/컬럼이 모두 출력되는지 확인
2. 조건별 표시/숨김 여부 (권한, 설정에 따라)
3. 데이터 없을 때 빈 화면 처리 또는 안내 문구 출력 확인

[드롭다운/목록(dropdown/list) 필수 커버리지]
1. 항목 목록 표시 확인
2. 항목 선택 후 결과 반영 확인
3. 첫 번째 항목, 마지막 항목 각각 선택

[마우스 이벤트]
- 호버(Hover): 툴팁 출력 여부 확인
- 우클릭, 더블클릭: 해당 기능이 있는 요소에만 적용

[공통 원칙]
- 시스템 상태/권한에 따라 다른 동작이 있으면 각 상태별 별도 TC
- 사전조건(Pre-condition)이 필요한 TC는 사전조건을 구체적으로 명시
- 팝업/모달: 열기 → 내용 확인 → 닫기/확인/취소 각각 별도 TC
- 연속 액션(클릭 → 팝업 → 확인 → 결과)도 각 단계별로 TC 분리"""
