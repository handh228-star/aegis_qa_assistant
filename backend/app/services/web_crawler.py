"""
XpERP 웹 크롤러 - Playwright 기반 UI 자동 탐색 및 RAG 지식 구축
- 로그인 → 사이드바 메뉴 파싱 → MenuCall 순회 → 화면 정보 추출 → 벡터 DB 저장
"""

import asyncio
import re
from typing import List, Dict, Optional
from app.services.web_knowledge_ingestion import ingest_ui_pages, delete_domain_knowledge


# 크롤링에서 제외할 메뉴 코드 접두사 (공통 시스템 메뉴 등)
SKIP_MENU_PREFIXES = ["SYS", "COM_"]

# 로그인 폼 선택자 후보 (우선순위 순) - hidden 타입은 _find_element에서 자동 제외
_ID_SELECTORS = [
    'input[name="user_id"]', 'input[name="id"]', 'input[name="userId"]',
    'input[name="loginId"]', 'input[name="login_id"]', 'input[name="empNo"]',
    '#user_id', '#userId', '#id', '#loginId', '#empNo',
    'input[type="text"]',  # fallback: visible text input
]
_PW_SELECTORS = [
    'input[name="user_pw"]', 'input[name="pw"]', 'input[name="password"]',
    'input[name="passwd"]', 'input[name="loginPw"]', 'input[name="userPw"]',
    '#user_pw', '#password', '#passwd', '#userPw',
    'input[type="password"]',  # fallback: any password input
]
_SUBMIT_SELECTORS = [
    'button[type="submit"]', 'input[type="submit"]',
    'button:has-text("로그인")', 'a:has-text("로그인")',
    '.btn-login', '#btnLogin', '#btnLogin2', 'button.login', '.login-btn',
]


def _parse_cookie_string(cookie_str: str, base_url: str) -> List[Dict]:
    """'name=value; name2=value2' 형식의 쿠키 문자열을 Playwright add_cookies 형식으로 변환"""
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    domain = parsed.netloc  # 예: stg.xperp.co.kr
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
            })
    return cookies


async def _find_element(page, selectors: List[str]):
    """선택자 목록 중 visible하고 hidden이 아닌 첫 번째 요소 반환"""
    for sel in selectors:
        try:
            locator = page.locator(sel)
            count = await locator.count()
            for i in range(count):
                el = locator.nth(i)
                # hidden input 제외
                el_type = await el.get_attribute("type") or ""
                if el_type.lower() == "hidden":
                    continue
                if await el.is_visible():
                    return el
        except Exception:
            continue
    return None


async def _login(page, base_url: str, user_id: str, password: str, on_status=None) -> bool:
    """
    XpERP 로그인.
    OTP 페이지가 나타나면 브라우저 창에서 사용자가 직접 입력할 때까지 대기(최대 5분).
    """
    OTP_WAIT_MS = 300_000  # 5분

    def _notify(msg: str):
        print(f"  [크롤러] {msg}")
        if on_status:
            on_status(msg)

    try:
        await page.goto(base_url, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")

        id_el = await _find_element(page, _ID_SELECTORS)
        pw_el = await _find_element(page, _PW_SELECTORS)
        submit_el = await _find_element(page, _SUBMIT_SELECTORS)

        if not id_el or not pw_el:
            _notify(f"로그인 폼을 찾을 수 없습니다. URL: {page.url}")
            return False

        await id_el.fill(user_id)
        await pw_el.fill(password)

        if submit_el:
            await submit_el.click()
        else:
            await pw_el.press("Enter")

        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        current_url = page.url
        _notify(f"로그인 후 URL → {current_url}")

        # OTP 페이지 감지 → 사용자 입력 대기
        if "otp" in current_url.lower():
            _notify("OTP 인증 화면 감지 → 브라우저 창에서 OTP를 직접 입력해 주세요 (최대 5분 대기)")
            try:
                await page.wait_for_url(
                    lambda url: "otp" not in url.lower(),
                    timeout=OTP_WAIT_MS,
                )
                _notify("OTP 인증 완료 → 메뉴 로딩 대기 중...")
                # MenuCall 요소가 렌더링될 때까지 대기 (최대 20초)
                try:
                    await page.wait_for_selector("nav.nav_wrap", timeout=20000)
                    _notify(f"메뉴 로딩 완료 (현재 URL: {page.url})")
                except Exception:
                    _notify(f"메뉴 로딩 타임아웃 → 현재 URL: {page.url}")
                    await page.wait_for_timeout(3000)  # 추가 대기 후 파싱 시도
                return True
            except Exception:
                _notify("OTP 입력 대기 시간 초과 (5분)")
                return False

        # 여전히 로그인 폼이 보이면 실패
        pw_count = await page.locator('input[type="password"]').filter(has=page.locator(':visible')).count()
        if pw_count > 0:
            _notify("로그인 실패 (아이디/패스워드 오류)")
            return False

        _notify("로그인 성공")
        return True

    except Exception as e:
        _notify(f"로그인 예외: {e}")
        return False


async def _dismiss_confirm_modal(page) -> bool:
    """최대화면 초과 등 확인 모달이 있으면 '확인' 버튼 클릭. 처리 시 True 반환."""
    try:
        # 모달 오버레이 감지
        modal = page.locator("text=최대화면 개수가 초과")
        if await modal.count() > 0:
            confirm = page.locator("button:has-text('확인')").last
            await confirm.click()
            await page.wait_for_timeout(800)
            return True
    except Exception:
        pass
    return False


async def _close_all_internal_tabs(page):
    """XpERP 내부 탭 전체 닫기.
    window.confirm을 오버라이드하고, 커스텀 DOM 모달(Home 메뉴 닫기 불가 등)도 처리.
    """
    try:
        result = await page.evaluate("""() => {
            if (typeof fnCloseAll === 'undefined') return 'no_fn';
            const origConfirm = window.confirm;
            window.confirm = () => true;
            try { fnCloseAll(); return 'ok'; }
            catch(e) { return 'err:' + e.message; }
            finally { window.confirm = origConfirm; }
        }""")
        if result == "no_fn":
            return
        await page.wait_for_timeout(100)

        # "Home 메뉴는 닫을 수 없습니다" 같은 커스텀 DOM 모달 처리
        try:
            btn = page.locator("button:has-text('확인')")
            if await btn.count() > 0:
                await btn.last.click()
                await page.wait_for_timeout(50)
        except Exception:
            pass
    except Exception as e:
        print(f"  [크롤러] 탭닫기 오류: {e}")


async def _dismiss_modal(page):
    """XpERP 공통 팝업(오늘 업무 마무리, 확인 모달 등) 닫기."""
    try:
        await page.evaluate("""() => {
            var selectors = [
                '#commonModal .btn-close',
                '#commonModal button',
                '.modal.show .btn-close',
                '.modal.show button[data-dismiss]',
                '.layer-popup .btn-close',
                '.popup-wrap .close',
            ];
            for (var s of selectors) {
                var el = document.querySelector(s);
                if (el && el.offsetParent !== null) { el.click(); break; }
            }
        }""")
        await page.wait_for_timeout(200)
    except Exception:
        pass


def _describe_screenshot(screenshot_bytes: bytes, menu_path: str, menu_code: str) -> str:
    """Gemini Vision으로 스크린샷 분석 → UI 구성요소 텍스트 추출 (동기)"""
    from google import genai
    from google.genai import types
    from app.core.config import settings

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    prompt = (
        f"이 이미지는 XpERP ERP 시스템의 '{menu_path}' 화면입니다.\n"
        "화면 우측 메인 콘텐츠 영역을 분석하여 아래 항목을 한국어로 추출하세요.\n"
        "없는 항목은 생략하고 간결하게 작성하세요.\n\n"
        "1. 화면 제목\n"
        "2. 검색/조회 조건 필드명 (라벨 텍스트)\n"
        "3. 입력 폼 필드명 및 유형\n"
        "4. 버튼 목록 (조회·저장·삭제 등)\n"
        "5. 그리드/목록 컬럼명\n"
        "6. 탭 목록\n"
        "7. 화면 주요 기능 요약 (1~2줄)"
    )
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL_VISION,
            contents=[
                types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
                prompt,
            ],
        )
        description = (response.text or "").strip()
    except Exception as e:
        description = f"Vision 분석 실패: {e}"

    return f"[XpERP 화면: {menu_path} (코드: {menu_code})]\n{description}"


async def _parse_sidebar_menus(page) -> List[Dict]:
    """
    XpERP 메뉴 수집 - 4가지 전략 순차 시도:
    1. window.* 전역변수 (menuList 등)
    2. 사이드바 상위 카테고리 클릭 → 서브메뉴 수집
    3. 전체 DOM [onclick]/[href] 탐색
    4. 전체 페이지 HTML regex
    """
    menus = []
    seen_codes = set()
    call_pattern = re.compile(r"MenuCall\(['\"]([^'\"]+)['\"]\)")

    def _add(code, label, top_menu):
        code = (code or "").strip()
        label = (label or code).strip()[:60]
        top_menu = (top_menu or "기타").strip()[:40]
        if not code or code in seen_codes:
            return False
        if any(code.startswith(p) for p in SKIP_MENU_PREFIXES):
            return False
        seen_codes.add(code)
        menus.append({"top_menu": top_menu, "label": label, "code": code, "path": f"{top_menu} > {label}"})
        return True

    main_frame = page.main_frame

    # ── 메뉴 데이터 AJAX 대기 (최대 5초) ─────────────────────────────────────
    try:
        await main_frame.wait_for_function(
            r"""() => {
                return (
                    (window.MENU_JSON && window.MENU_JSON !== '[]') ||
                    (window.mainLnbMenu && (Array.isArray(window.mainLnbMenu) ? window.mainLnbMenu.length > 0 : !!window.mainLnbMenu)) ||
                    (window.menuInfos   && (Array.isArray(window.menuInfos)   ? window.menuInfos.length   > 0 : !!window.menuInfos)) ||
                    (window.dDataSet_menu && typeof window.dDataSet_menu.getRowCount === 'function'
                        && window.dDataSet_menu.getRowCount() > 0)
                );
            }""",
            timeout=5000,
        )
        print("  [크롤러] 메뉴 데이터 준비됨")
    except Exception:
        print("  [크롤러] 메뉴 데이터 대기 타임아웃 - 계속 진행")

    # ── 전략 1: window 전역변수 탐색 (DevOn Dataset 포함) ────────────────────
    try:
        win_result = await main_frame.evaluate(r"""() => {
            const items = [];
            const seen = new Set();
            const inspection = {};

            // DevOn/Nexacro Dataset 객체를 일반 배열로 변환
            function devonToRows(ds) {
                if (!ds) return null;
                // 방법 A: getRowCount/getValue API
                if (typeof ds.getRowCount === 'function') {
                    try {
                        const rowCount = ds.getRowCount();
                        const colCount = typeof ds.getColumnCount === 'function' ? ds.getColumnCount() : 0;
                        const cols = [];
                        for (let i = 0; i < colCount; i++) {
                            const col = ds.getColumn(i);
                            cols.push(col ? (col.columnId || col.id || col.columnid || String(i)) : String(i));
                        }
                        const rows = [];
                        for (let r = 0; r < rowCount; r++) {
                            const row = {};
                            cols.forEach(c => { row[c] = ds.getValue(r, c); });
                            rows.push(row);
                        }
                        return rows;
                    } catch(e) { return null; }
                }
                // 방법 B: 일반 배열/rows 속성
                if (Array.isArray(ds)) return ds;
                if (Array.isArray(ds.rows)) return ds.rows;
                if (Array.isArray(ds.data)) return ds.data;
                if (Array.isArray(ds._rows)) return ds._rows;
                return null;
            }

            function extractCode(m) {
                // XpERP MENU_JSON uses MENU_ID
                return m.MENU_ID || m.menuId || m.MENU_CD || m.menuCd
                     || m.MENU_CODE || m.menuCode || m.CD || m.cd || m.code || '';
            }
            function extractLabel(m, fallback) {
                return m.MENU_NM || m.menuNm || m.MENU_NAME || m.menuName
                     || m.NM || m.name || m.label || fallback || '';
            }
            function extractParentCode(m) {
                // XpERP MENU_JSON uses HRANK_MENU_ID for parent
                return m.HRANK_MENU_ID || m.hRankMenuId || m.UP_MENU_ID
                     || m.UP_MENU_CD || m.upMenuCd || m.UP_CD || m.upCd
                     || m.PARENT_CD || m.parentCd || m.parentCode || '';
            }
            function isLeafMenu(m) {
                // ISLEAF=1 means actual navigable menu; ISLEAF=0 means folder
                if (m.ISLEAF === 1 || m.ISLEAF === '1' || m.ISLEAF === true) return true;
                if (m.ISLEAF === 0 || m.ISLEAF === '0' || m.ISLEAF === false) return false;
                return true; // unknown: treat as leaf
            }

            // 평면 배열 → 계층 맵 → items 변환
            function processFlat(rows) {
                if (!rows || rows.length === 0) return;

                // code → {label, parentCode} 맵 (전체 행 포함 - 조상 경로 계산용)
                const codeMap = {};
                rows.forEach(m => {
                    const code = extractCode(m);
                    if (!code) return;
                    codeMap[code] = {
                        label: extractLabel(m, code),
                        parentCode: extractParentCode(m),
                        raw: m,
                    };
                });

                // 재귀적으로 조상 경로 계산
                function getPath(code, visited) {
                    visited = visited || new Set();
                    if (!code || !codeMap[code] || visited.has(code)) return [];
                    visited.add(code);
                    const { label, parentCode } = codeMap[code];
                    if (!parentCode || !codeMap[parentCode]) return [label];
                    return [...getPath(parentCode, visited), label];
                }

                // 리프 메뉴만 items에 추가
                rows.forEach(m => {
                    const code = extractCode(m);
                    if (!code || seen.has(code)) return;
                    // ISLEAF 필드가 있으면 우선 사용, 없으면 자식 보유 여부로 판단
                    const hasIsLeaf = m.ISLEAF !== undefined && m.ISLEAF !== null;
                    if (hasIsLeaf && !isLeafMenu(m)) return;  // 카테고리 제외
                    if (!hasIsLeaf) {
                        const hasChildren = rows.some(r => extractParentCode(r) === code);
                        if (hasChildren) return;
                    }
                    seen.add(code);
                    const path = getPath(code, new Set());
                    const label = path[path.length - 1] || extractLabel(m, code);
                    const topMenu = path.length > 1 ? path[0] : '기타';
                    // ROOT처럼 최상위 더미 노드는 topMenu에서 제외
                    const meaningfulPath = path.filter((p, i) => !(i === 0 && p.length <= 3));
                    const fullPath = meaningfulPath.join(' > ') || label;
                    const finalTop = meaningfulPath[0] || topMenu;
                    const urlPath2 = m.URL_PATH2 || m.urlPath2 || '';
                    const urlPath = m.URL_PATH || m.url_path || m.urlPath || m.URL || '';
                    items.push({ code, label, topMenu: finalTop, fullPath, urlPath, urlPath2 });
                });
            }

            // 재귀 트리 구조 플래트닝
            function flatten(arr, ancestors) {
                if (!Array.isArray(arr)) return;
                arr.forEach(m => {
                    const code = extractCode(m);
                    const label = extractLabel(m, code);
                    const children = m.children || m.subMenu || m.items || m.menuList || m.SUB_MENU;
                    if (children && children.length > 0) {
                        flatten(children, [...ancestors, label]);
                    } else if (code && !seen.has(code)) {
                        seen.add(code);
                        const topMenu = ancestors[0] || '기타';
                        const fullPath = [...ancestors, label].join(' > ');
                        items.push({ code, label, topMenu, fullPath });
                    }
                });
            }

            // ── 실제 XpERP 변수들 처리 ──
            // 1. dDataSet_menu (DevOn Dataset - 가장 완전한 데이터)
            if (window.dDataSet_menu) {
                const rows = devonToRows(window.dDataSet_menu);
                inspection.dDataSet_menu = rows
                    ? `rows=${rows.length}, sample=${JSON.stringify(rows[0] || {}).substring(0, 200)}`
                    : `keys=${Object.keys(window.dDataSet_menu).join(',')}`;
                if (rows) processFlat(rows);
            }

            // 2. MENU_JSON
            if (window.MENU_JSON) {
                try {
                    const parsed = typeof window.MENU_JSON === 'string'
                        ? JSON.parse(window.MENU_JSON) : window.MENU_JSON;
                    const arr = Array.isArray(parsed) ? parsed
                        : (parsed.menuList || parsed.list || parsed.data || []);
                    inspection.MENU_JSON = `arr=${arr.length}, sample=${JSON.stringify(arr[0] || {}).substring(0, 200)}`;
                    if (arr.length > 0 && extractCode(arr[0])) {
                        processFlat(arr);
                    } else {
                        flatten(arr, []);
                    }
                } catch(e) { inspection.MENU_JSON = 'err:' + e.message; }
            }

            // 3. mainLnbMenu (LNB = Left Nav Bar)
            if (window.mainLnbMenu) {
                const arr = Array.isArray(window.mainLnbMenu) ? window.mainLnbMenu : [];
                inspection.mainLnbMenu = `len=${arr.length}, sample=${JSON.stringify(arr[0] || {}).substring(0, 200)}`;
                flatten(arr, []);
            }

            // 4. menuInfos
            if (window.menuInfos) {
                const arr = Array.isArray(window.menuInfos) ? window.menuInfos : [];
                inspection.menuInfos = `len=${arr.length}, sample=${JSON.stringify(arr[0] || {}).substring(0, 200)}`;
                processFlat(arr);
            }

            const menuVarNames = Object.getOwnPropertyNames(window)
                .filter(k => /menu/i.test(k) && typeof window[k] !== 'function')
                .slice(0, 30);

            return { items, menuVarNames, inspection };
        }""")

        var_names = win_result.get("menuVarNames", [])
        items = win_result.get("items", [])
        inspection = win_result.get("inspection", {})
        print(f"  [크롤러] window 메뉴변수: {var_names}")
        for k, v in inspection.items():
            print(f"  [{k}] {v}")
        print(f"  [크롤러] 전략1(window) → {len(items)}개")
        for it in items:
            code = it.get("code", "")
            label = it.get("label", code)
            top_menu = it.get("topMenu", "기타")
            full_path = it.get("fullPath") or f"{top_menu} > {label}"
            if not code or code in seen_codes:
                continue
            if any(code.startswith(p) for p in SKIP_MENU_PREFIXES):
                continue
            seen_codes.add(code)
            menus.append({
                "top_menu": top_menu,
                "label": label,
                "code": code,
                "path": full_path,
                "url_path2": it.get("urlPath2", ""),
            })
    except Exception as e:
        print(f"  [크롤러] 전략1 오류: {e}")

    # ── 전략 2: 사이드바 data-* 속성 + DOM 트리 계층 탐색 ───────────────────
    if len(menus) < 10:
        print("  [크롤러] 전략2: 사이드바 data 속성 탐색")
        try:
            sidebar_result = await main_frame.evaluate(r"""() => {
                const sidebar = document.querySelector('#sidebar, nav.nav_wrap, .nav_wrap, .sidebar');
                if (!sidebar) return null;

                // 1) sidebar 내 data-* 속성명 목록 (진단용)
                const dataAttrs = new Set();
                sidebar.querySelectorAll('*').forEach(el => {
                    Array.from(el.attributes).forEach(a => {
                        if (a.name.startsWith('data-')) dataAttrs.add(a.name);
                    });
                });

                // 2) 각 data-* 속성을 후보 메뉴코드로 탐색
                const CODE_ATTRS = [
                    'data-menu-cd','data-menucd','data-menu-code','data-menucode',
                    'data-code','data-cd','data-id','data-menu-id','data-menuid',
                    'data-url','data-href','data-param',
                ];
                const callPat = /MenuCall\(['"]([^'"]+)['"]\)/;
                const items = [];
                const seen = new Set();

                CODE_ATTRS.forEach(attr => {
                    sidebar.querySelectorAll('[' + attr + ']').forEach(el => {
                        const val = el.getAttribute(attr) || '';
                        // val 자체가 코드이거나, MenuCall('CODE') 패턴 포함
                        let code = '';
                        const m = callPat.exec(val);
                        if (m) {
                            code = m[1];
                        } else if (/^[A-Z]{2,6}\d{4}/.test(val)) {
                            code = val;
                        }
                        if (!code || seen.has(code)) return;
                        seen.add(code);

                        const label = (el.textContent || '').trim()
                            .replace(/\s+/g, ' ').substring(0, 60) || code;

                        // 조상 li 텍스트로 계층 구성
                        const ancestors = [];
                        let cur = el.parentElement;
                        while (cur && cur !== sidebar) {
                            if (cur.tagName === 'LI') {
                                const a = cur.querySelector(':scope > a, :scope > span, :scope > p');
                                const t = (a ? a.textContent : cur.textContent || '')
                                    .trim().replace(/\s+/g, ' ').split('\n')[0].substring(0, 40);
                                if (t && t !== label) ancestors.unshift(t);
                            }
                            cur = cur.parentElement;
                        }
                        const topMenu = ancestors[0] || '기타';
                        const fullPath = [...ancestors, label].join(' > ');
                        items.push({ code, label, topMenu, fullPath, foundAttr: attr });
                    });
                });

                return {
                    dataAttrNames: Array.from(dataAttrs),
                    items,
                    sidebarHtml: sidebar.outerHTML.substring(0, 800),
                };
            }""")

            if sidebar_result:
                print(f"  [사이드바 data-* 속성]: {sidebar_result.get('dataAttrNames', [])}")
                items = sidebar_result.get("items", [])
                print(f"  [크롤러] 전략2(data-attr) → {len(items)}개")
                if not items:
                    print(f"  [사이드바 HTML 일부]\n{sidebar_result.get('sidebarHtml','')}")
                for it in items:
                    code = it.get("code", "")
                    label = it.get("label", code)
                    top_menu = it.get("topMenu", "기타")
                    full_path = it.get("fullPath") or f"{top_menu} > {label}"
                    if not code or code in seen_codes:
                        continue
                    if any(code.startswith(p) for p in SKIP_MENU_PREFIXES):
                        continue
                    seen_codes.add(code)
                    menus.append({
                        "top_menu": top_menu,
                        "label": label,
                        "code": code,
                        "path": full_path,
                    })
        except Exception as e:
            print(f"  [크롤러] 전략2 오류: {e}")

    # ── 전략 3: 전체 DOM [onclick]/[href] 탐색 ───────────────────────────────
    if len(menus) < 10:
        print("  [크롤러] 전략3: 전체 DOM onclick/href 탐색")
        try:
            dom_items = await main_frame.evaluate(r"""() => {
                const callPat = /MenuCall\(['"]([^'"]+)['"]\)/;
                const results = [];
                const seen = new Set();
                document.querySelectorAll('[onclick*="MenuCall"], [href*="MenuCall"]').forEach(el => {
                    const attr = el.getAttribute('onclick') || el.getAttribute('href') || '';
                    const m = callPat.exec(attr);
                    if (!m || seen.has(m[1])) return;
                    seen.add(m[1]);
                    const label = (el.textContent || '').trim().replace(/\s+/g,' ').substring(0,60) || m[1];
                    results.push({ code: m[1], label });
                });
                return results;
            }""")
            print(f"  [크롤러] 전략3 → {len(dom_items)}개")
            for it in dom_items:
                _add(it.get("code"), it.get("label"), "기타")
        except Exception as e:
            print(f"  [크롤러] 전략3 오류: {e}")

    # ── 전략 4: 전체 페이지 HTML regex ───────────────────────────────────────
    if len(menus) < 10:
        print("  [크롤러] 전략4: 전체 페이지 HTML regex")
        try:
            full_html = await main_frame.evaluate("() => document.documentElement.outerHTML")
            codes = call_pattern.findall(full_html)
            print(f"  [크롤러] 전략4 → HTML에서 MenuCall {len(codes)}개 (유니크: {len(set(codes))}개)")
            for code in codes:
                _add(code, code, "기타")
        except Exception as e:
            print(f"  [크롤러] 전략4 오류: {e}")

    print(f"  [크롤러] 최종 메뉴 {len(menus)}개 수집")
    return menus


async def _extract_all_frames_text(page) -> str:
    """메인 프레임 + 모든 iframe에서 텍스트 추출"""
    texts = []
    frames = page.frames
    for frame in frames:
        try:
            text = await frame.evaluate("""() => {
                const skip = new Set(['SCRIPT','STYLE','NOSCRIPT','META','HEAD']);
                function walk(node) {
                    if (skip.has(node.tagName)) return '';
                    if (node.nodeType === 3) return node.textContent.trim();
                    return Array.from(node.childNodes).map(walk).join(' ');
                }
                return walk(document.body || document.documentElement);
            }""")
            if text and len(text.strip()) > 50:
                texts.append(text.strip())
        except Exception:
            continue
    return " ".join(texts)


_EXTRACT_JS = r"""() => {
    const r = { title:'', tabs:[], fields:[], columns:[], buttons:[], visibleText:'' };
    // 제목: 표준 태그 + XpERP 커스텀 클래스
    const titleEl = document.querySelector(
        'h1,h2,h3,.page-title,.title,.header-title,.screen-title,' +
        '.scrn-title,.menu-title,.form-title,[class*="title"],[class*="Title"]'
    );
    if (titleEl) r.title = (titleEl.innerText||'').trim().split('\n')[0].substring(0,60);

    // 탭
    document.querySelectorAll(
        '.tab-menu li,.tab li,[role="tab"],.nav-tab li,' +
        '[class*="tab"] li,[class*="Tab"] li'
    ).forEach(t => {
        const s = (t.innerText||'').trim(); if (s && s.length<30) r.tabs.push(s);
    });

    // 버튼 (XpERP 커스텀 btn 클래스 포함)
    document.querySelectorAll(
        'button,input[type="button"],input[type="submit"],' +
        'a.btn,.btn,[class*="btn"],[class*="Btn"],[class*="button"]'
    ).forEach(b => {
        const t = ((b.innerText||b.value||b.title)||'').trim().split('\n')[0];
        if (t && t.length < 20 && !r.buttons.includes(t)) r.buttons.push(t);
    });
    r.buttons = r.buttons.slice(0,20);

    // 가시 텍스트 전체 수집 (XpERP 커스텀 컴포넌트 대응)
    const skipTags = new Set(['SCRIPT','STYLE','NOSCRIPT','HEAD']);
    function collectText(el, depth) {
        if (depth > 15 || !el) return '';
        if (skipTags.has(el.tagName)) return '';
        if (el.nodeType === 3) {
            const t = (el.textContent||'').trim();
            return t.length > 1 ? t + ' ' : '';
        }
        // 숨겨진 요소 제외
        try {
            const st = window.getComputedStyle(el);
            if (st.display==='none' || st.visibility==='hidden') return '';
        } catch(e) {}
        return Array.from(el.childNodes).map(c => collectText(c, depth+1)).join('');
    }
    const body = document.body || document.documentElement;
    const raw = collectText(body, 0).replace(/\s+/g,' ').trim();
    // 중복 단어 제거 없이 최대 800자
    r.visibleText = raw.substring(0, 8000);

    // 컬럼 헤더
    document.querySelectorAll(
        'th,.grid-header,[data-column-id],[class*="col-header"],[class*="ColHeader"]'
    ).forEach(th => {
        const t = (th.innerText||'').trim().split('\n')[0];
        if (t && t.length < 30 && !r.columns.includes(t)) r.columns.push(t);
    });
    r.columns = r.columns.slice(0,30);

    return r;
}"""


async def _extract_page_info_frame(frame, menu_path: str, menu_code: str) -> str:
    """단일 frame(iframe_content 등)에서 직접 추출."""
    parts = [f"[XpERP 화면: {menu_path} (코드: {menu_code})]"]
    try:
        d = await frame.evaluate(_EXTRACT_JS)
        if d.get("title"):
            parts.append(f"화면 제목: {d['title']}")
        if d.get("tabs"):
            parts.append(f"탭: {' | '.join(d['tabs'])}")
        if d.get("columns"):
            parts.append(f"목록 컬럼: {', '.join(d['columns'])}")
        if d.get("buttons"):
            parts.append(f"버튼: {' | '.join(d['buttons'])}")
        if d.get("visibleText"):
            combined = " ".join(d["visibleText"].split())[:5000]
            parts.append(f"화면 텍스트: {combined}")
    except Exception as e:
        parts.append(f"추출 오류: {e}")
    return "\n".join(parts)


async def _extract_page_info(page, menu_path: str, menu_code: str) -> str:
    """프레임별 구조화 추출 + 가시 텍스트 fallback."""
    parts = [f"[XpERP 화면: {menu_path} (코드: {menu_code})]"]
    seen_titles: set = set()
    all_visible: list = []

    # 메인 프레임 + 콘텐츠 iframe (최대 4개)
    frames = page.frames[:4]
    for frame in frames:
        try:
            d = await frame.evaluate(_EXTRACT_JS)
        except Exception:
            continue
        if d.get("title") and d["title"] not in seen_titles:
            seen_titles.add(d["title"])
            parts.append(f"화면 제목: {d['title']}")
        if d.get("tabs"):
            parts.append(f"탭: {' | '.join(d['tabs'])}")
        if d.get("columns"):
            parts.append(f"목록 컬럼: {', '.join(d['columns'])}")
        if d.get("buttons"):
            parts.append(f"버튼: {' | '.join(d['buttons'])}")
        if d.get("visibleText"):
            all_visible.append(d["visibleText"])

    # 가시 텍스트로 내용 보강 (구조화 추출이 부족할 때)
    if all_visible:
        combined = " ".join(all_visible)
        combined = " ".join(combined.split())[:5000]
        parts.append(f"화면 텍스트: {combined}")

    return "\n".join(parts)


async def crawl_xperp(
    base_url: str,
    user_id: str,
    password: str,
    domain: str,
    target_modules: Optional[List[str]] = None,
    on_progress=None,
    session_cookie: Optional[str] = None,
) -> Dict:
    """
    XpERP 전체(또는 지정 모듈) 크롤링 실행.
    target_modules: 상위 메뉴명 필터 (예: ["단지관리", "부과", "수납"]). None이면 전체.
    on_progress: 진행 콜백 fn(done, total, current_path)
    """
    from playwright.async_api import async_playwright

    results = {"domain": domain, "crawled": 0, "skipped": 0, "errors": [], "pages": []}

    # 기존 도메인 지식 초기화
    deleted = delete_domain_knowledge(domain)
    if deleted:
        print(f"  [크롤러] 기존 {deleted}개 페이지 삭제 후 재수집")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=0)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = await context.new_page()
        # window.confirm / window.alert 등 네이티브 다이얼로그 자동 수락
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

        # 1. 인증 (쿠키 주입 또는 아이디/패스워드 로그인)
        from app.core.config import settings
        screenshot_dir = str(settings.UPLOAD_DIR)

        if session_cookie:
            await page.goto(base_url, timeout=30000)
            await page.wait_for_load_state("domcontentloaded")
            parsed_cookies = _parse_cookie_string(session_cookie, base_url)
            await context.add_cookies(parsed_cookies)
            await page.reload()
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            current_url = page.url
            print(f"  [크롤러] 쿠키 주입 후 URL → {current_url}")
            if "otp" in current_url.lower() or "login" in current_url.lower():
                await browser.close()
                results["errors"].append("세션 쿠키 만료 - 브라우저에서 다시 로그인+OTP 완료 후 쿠키를 복사해 주세요")
                return results
            logged_in = True
        else:
            logged_in = await _login(page, base_url, user_id, password, on_status=on_progress and (lambda msg: on_progress(-1, -1, msg)))

        if not logged_in:
            await browser.close()
            results["errors"].append("로그인 실패")
            return results

        # 2. 메뉴 파싱
        all_menus = await _parse_sidebar_menus(page)
        if not all_menus:
            # 사이드바 HTML이 동적으로 로드되는 경우 잠시 대기
            await page.wait_for_timeout(3000)
            all_menus = await _parse_sidebar_menus(page)

        if target_modules:
            menus = [m for m in all_menus if m["top_menu"] in target_modules]
        else:
            menus = all_menus

        print(f"  [크롤러] 총 {len(menus)}개 메뉴 크롤링 시작 (전체 {len(all_menus)}개)")

        # 2-1. 메인 홈 화면 먼저 수집 (홈 AJAX 완료 대기)
        try:
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            home_content = await _extract_page_info(page, "메인 홈", "HOME")
            if home_content and len(home_content) > 80:
                ingest_ui_pages([{
                    "menu_path": "메인 홈",
                    "menu_code": "HOME",
                    "content": home_content,
                }], domain)
                results["crawled"] += 1
                print(f"  [크롤러] 메인 홈 화면 수집 완료 ({len(home_content)}자)")
        except Exception as e:
            print(f"  [크롤러] 메인 홈 수집 실패: {e}")

        # 3. 메뉴 순회
        ui_pages = []
        SAVE_EVERY = 10  # N개마다 중간 저장

        def _flush(pages: list):
            """수집된 페이지를 즉시 벡터 DB에 저장하고 리스트 비우기."""
            if pages:
                saved = ingest_ui_pages(pages, domain)
                results["crawled"] += saved
                print(f"  [크롤러] 중간 저장 {saved}개 (누적 {results['crawled']}개)")
                pages.clear()

        for idx, menu in enumerate(menus):
            try:
                from app.api.crawler import _status as _crawl_status
                if _crawl_status.get("stop_requested"):
                    print(f"  [크롤러] 중단 요청으로 종료 ({idx}/{len(menus)} 완료)")
                    break
            except Exception:
                pass

            path = menu["path"]
            code = menu["code"]

            if on_progress:
                on_progress(idx, len(menus), path)

            try:
                import time as _time
                _t0 = _time.time()

                # ── 1. 메뉴 이동 ──────────────────────────────────────────────────────
                content_frame = page.frame(name="iframe_content")
                url_path2 = menu.get("url_path2", "")

                nav_ok = False
                if url_path2 and content_frame:
                    full_url = base_url.rstrip("/") + "/" + url_path2.lstrip("/")
                    try:
                        await content_frame.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                        nav_ok = True
                    except Exception as nav_err:
                        print(f"  [{idx+1}] frame.goto 실패({nav_err}) → MenuCall 시도")

                if not nav_ok:
                    await page.evaluate(f"if(typeof MenuCall!=='undefined') MenuCall('{code}')")

                # ── 2. 렌더링 대기 + 팝업 닫기 ───────────────────────────────────────
                await page.wait_for_timeout(3000)
                await _dismiss_modal(page)

                # ── 3. 스크린샷 캡처 (iframe 영역 우선, 실패 시 전체 페이지) ──────────
                screenshot_bytes = None
                if content_frame:
                    try:
                        iframe_el = await content_frame.frame_element()
                        screenshot_bytes = await iframe_el.screenshot(type="png")
                    except Exception:
                        pass
                if screenshot_bytes is None:
                    screenshot_bytes = await page.screenshot(type="png")

                # ── 4. Gemini Vision 분석 ─────────────────────────────────────────────
                content = await asyncio.to_thread(_describe_screenshot, screenshot_bytes, path, code)

                _elapsed = _time.time() - _t0

                if content and len(content) > 80:
                    ui_pages.append({
                        "menu_path": path,
                        "menu_code": code,
                        "content": content,
                    })
                    print(f"  [{idx+1}/{len(menus)}] {path} → {len(content)}자 ({_elapsed:.1f}s)")
                    # 일정 개수마다 중간 저장
                    if len(ui_pages) >= SAVE_EVERY:
                        _flush(ui_pages)
                else:
                    results["skipped"] += 1
                    print(f"  [{idx+1}/{len(menus)}] {path} → 건너뜀 ({_elapsed:.1f}s)")

            except Exception as e:
                results["errors"].append(f"{path}: {e}")
                results["skipped"] += 1
                print(f"  [{idx+1}/{len(menus)}] {path} → 오류: {e}")

            # 루프 종료 후 잔여 페이지 저장
        _flush(ui_pages)
        await browser.close()

    print(f"  [크롤러] 전체 저장 완료: {results['crawled']}개")

    return results


def run_crawl_sync(base_url, user_id, password, domain, target_modules=None, on_progress=None, session_cookie=None):
    """동기 래퍼 - FastAPI BackgroundTask에서 호출용.
    Windows SelectorEventLoop는 subprocess를 지원하지 않으므로 ProactorEventLoop를 명시적으로 생성.
    """
    import sys
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            crawl_xperp(base_url, user_id, password, domain, target_modules, on_progress, session_cookie)
        )
    finally:
        loop.close()
