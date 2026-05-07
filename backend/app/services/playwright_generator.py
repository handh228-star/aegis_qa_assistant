"""
Playwright 테스트 스크립트 자동 생성 서비스
TC 목록 + 웹 크롤러 UI 지식(RAG) → 실행 가능한 Playwright Python 파일
"""

import re
import json
from google import genai
from typing import List, Dict, Optional
from datetime import datetime
from app.core.config import settings
from app.services.rag_service import search_web_knowledge, search_manual

client = genai.Client(api_key=settings.GOOGLE_API_KEY)

# ── 프롬프트 ──────────────────────────────────────────────────────────────────

_SYSTEM_CONTEXT = """당신은 XpERP QA 자동화 엔지니어입니다.
TC를 Playwright Python async 코드로 변환합니다.

[XpERP 공통 패턴]
- 메뉴 이동: await page.evaluate("MenuCall('메뉴코드')")
- 페이지 로드: await page.wait_for_load_state("networkidle", timeout=15000)
- 팝업 열림 대기: await page.wait_for_selector('.popup', state='visible')
- 조회 버튼: page.locator('button:has-text("조회")')
- 저장 버튼: page.locator('button:has-text("저장")')
- 그리드 행: page.locator('.grid-row').nth(0)
- 검증: from playwright.async_api import expect → await expect(locator).to_have_text(...)
- 없는 선택자: # TODO: 선택자 확인 필요 주석으로 표시

[출력 규칙]
1. 함수 정의만 출력. 설명 텍스트, 마크다운 코드블록 없음.
2. 함수명: test_{tc_id_snake}_{title_snake} (소문자, 공백→_)
3. docstring에 TC ID / 제목 / 기대결과 포함
4. 각 단계를 # 주석으로 구분
5. 최소 1개의 assert 또는 expect() 포함
6. UI 정보에 실제 선택자가 있으면 반드시 사용
"""

_BATCH_PROMPT = """{system}

다음 {count}개의 TC를 각각 하나의 async 함수로 변환하세요.
함수들을 연속으로 출력하고 그 외 텍스트는 일체 출력하지 마세요.

[관련 화면 UI 정보]
{ui_context}

[TC 목록]
{tc_block}
"""

# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _to_snake(text: str) -> str:
    """한글/특수문자 포함 텍스트를 snake_case 식별자로 변환"""
    text = re.sub(r"[^\w\s가-힣]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:40] or "test"


def _format_tc_for_prompt(tc) -> str:
    steps_text = ""
    for s in (tc.steps or []):
        num = s.get("step", "")
        action = s.get("action", "")
        expected = s.get("expected", "")
        steps_text += f"  {num}. {action}"
        if expected:
            steps_text += f" → {expected}"
        steps_text += "\n"

    precond = "\n".join(tc.preconditions or []) or "없음"
    return (
        f"TC_ID: {tc.tc_id}\n"
        f"카테고리: {tc.category}\n"
        f"제목: {tc.title}\n"
        f"목적: {tc.objective}\n"
        f"유형: {tc.tc_type.value} / 우선순위: {tc.priority.value}\n"
        f"사전조건:\n  {precond}\n"
        f"테스트 단계:\n{steps_text}"
        f"기대결과: {tc.expected_result}\n"
    )


def _generate_with_retry(prompt: str, max_retries: int = 2) -> str:
    import time
    wait = 30
    last_err = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            return response.text or ""
        except Exception as e:
            last_err = e
            err = str(e)
            if ("503" in err or "429" in err or "UNAVAILABLE" in err) and attempt < max_retries - 1:
                time.sleep(wait)
                wait = min(wait * 2, 120)
            else:
                raise
    raise last_err


def _clean_code_output(text: str) -> str:
    """AI 출력에서 마크다운 펜스 제거"""
    text = re.sub(r"```python\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


# ── 핵심 생성 함수 ────────────────────────────────────────────────────────────

def _generate_batch(tcs: list, ui_context: str) -> str:
    """같은 카테고리의 TC 묶음을 한 번의 API 호출로 생성"""
    tc_block = "\n---\n".join(_format_tc_for_prompt(tc) for tc in tcs)
    prompt = _BATCH_PROMPT.format(
        system=_SYSTEM_CONTEXT,
        count=len(tcs),
        ui_context=ui_context or "해당 화면 정보 없음 - 추정하여 작성",
        tc_block=tc_block,
    )
    raw = _generate_with_retry(prompt)
    return _clean_code_output(raw)


def _build_ui_context(category: str, domain: Optional[str]) -> str:
    """카테고리에 맞는 UI 지식을 RAG에서 검색"""
    parts = []
    if domain:
        web_ctx = search_web_knowledge(category, domain, n_results=3)
        if web_ctx:
            parts.append(web_ctx)
    manual_ctx = search_manual(category, n_results=3)
    if manual_ctx:
        parts.append(manual_ctx)
    return "\n\n".join(parts)


# ── 파일 생성 ─────────────────────────────────────────────────────────────────

_FILE_HEADER = '''"""
자동 생성된 Playwright 테스트 스크립트
프로젝트: {project_name}
문서: {doc_name}
생성일: {generated_at}
생성 TC 수: {tc_count}

사용법:
  pip install playwright pytest-playwright
  playwright install chromium
  pytest {filename} -v
"""

import pytest
from playwright.async_api import async_playwright, expect

BASE_URL = "{base_url}"
TEST_USER_ID = "테스트계정아이디"   # TODO: 실제 테스트 계정으로 변경
TEST_PASSWORD = "비밀번호"          # TODO: 실제 비밀번호로 변경


@pytest.fixture(scope="function")
async def page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(viewport={{"width": 1440, "height": 900}})
        pg = await context.new_page()

        # 로그인
        await pg.goto(BASE_URL)
        await pg.wait_for_load_state("domcontentloaded")
        await pg.locator('input[type="text"]').first.fill(TEST_USER_ID)
        await pg.locator('input[type="password"]').first.fill(TEST_PASSWORD)
        await pg.locator('button[type="submit"], button:has-text("로그인")').first.click()
        await pg.wait_for_load_state("networkidle", timeout=15000)

        yield pg
        await browser.close()


# ════════════════════════════════════════════════════════════
# 아래부터 AI가 생성한 테스트 함수들
# ════════════════════════════════════════════════════════════

'''


def generate_playwright_script(
    testcases: list,
    project_name: str,
    doc_name: str,
    output_path,
    domain: Optional[str] = None,
    base_url: str = "",
) -> Dict:
    """
    TC 목록 → Playwright .py 파일 생성 후 저장.
    카테고리별로 묶어 API를 호출해 비용 절감.
    Returns: {"path": str, "tc_count": int, "categories": int, "errors": list}
    """
    base_url = base_url or settings.XPERP_BASE_URL or "https://your-app-url.com"
    filename = f"test_{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    output_file = output_path / filename

    header = _FILE_HEADER.format(
        project_name=project_name,
        doc_name=doc_name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        tc_count=len(testcases),
        filename=filename,
        base_url=base_url,
    )

    # 카테고리별 그룹화
    from collections import defaultdict
    groups: Dict[str, list] = defaultdict(list)
    for tc in testcases:
        groups[tc.category].append(tc)

    all_functions = []
    errors = []
    BATCH_SIZE = 5  # 한 번에 생성할 TC 수

    for category, tcs in groups.items():
        print(f"  [Playwright] '{category}' ({len(tcs)}개 TC) 코드 생성 중...")
        ui_context = _build_ui_context(category, domain)

        # 배치 단위로 나눠 생성
        for i in range(0, len(tcs), BATCH_SIZE):
            batch = tcs[i:i + BATCH_SIZE]
            try:
                code = _generate_batch(batch, ui_context)
                if code:
                    all_functions.append(f"# ── {category} ({'~'.join(tc.tc_id for tc in batch)}) ──")
                    all_functions.append(code)
            except Exception as e:
                err_msg = f"{category} 배치 {i//BATCH_SIZE + 1}: {e}"
                errors.append(err_msg)
                print(f"  [Playwright 오류] {err_msg}")
                # 실패한 TC는 스텁으로 대체
                stubs = _generate_stubs(batch)
                all_functions.append(stubs)

    body = "\n\n\n".join(all_functions)
    output_file.write_text(header + body, encoding="utf-8")

    print(f"  [Playwright] {output_file} 저장 완료 ({len(testcases)}개 TC)")
    return {
        "path": str(output_file),
        "filename": filename,
        "tc_count": len(testcases),
        "categories": len(groups),
        "errors": errors,
    }


def _generate_stubs(tcs: list) -> str:
    """AI 생성 실패 시 TODO 스텁 코드 생성"""
    stubs = []
    for tc in tcs:
        fn_name = f"test_{_to_snake(tc.tc_id)}_{_to_snake(tc.title)}"
        stubs.append(
            f"async def {fn_name}(page):\n"
            f'    """\n'
            f"    {tc.tc_id}: {tc.title}\n"
            f"    기대결과: {tc.expected_result}\n"
            f'    """\n'
            f"    # TODO: 자동 생성 실패 - 수동으로 작성 필요\n"
            f"    pytest.skip('미구현')\n"
        )
    return "\n\n".join(stubs)
