"""흐름 트리(Flow Tree) → QA 양식 Excel 그리드 렌더러.

PoC(docs/PoC_FlowTree_doc82_v3.xlsx)의 trie→grid 렌더링을 정식화.
노드를 좌→우 트라이로 펼쳐, 각 노드를 (타입, 내용) 열 쌍으로 배치한다.
설계: docs/flow_tree_schema_design.md §6.4
"""
import io
from typing import Dict, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# 타입별 셀 배경색
TYPE_FILL = {
    "PR": "fef3c7", "C": "dbeafe", "D": "dcfce7", "T": "fae8ff",
    "H": "e0e7ff", "V": "fee2e2", "RC": "dbeafe", "DC": "dbeafe", "DD": "dbeafe",
}
# 범례 (사람 골든 기준)
LEGEND = [
    ("D", "Display"), ("C", "Click"), ("RC", "우클릭"), ("DC", "더블클릭"),
    ("T", "input"), ("H", "Hover"), ("DD", "Drag Down"),
    ("PR", "Pre-condition"), ("V", "Verify"),
]


def render_flow_tree_excel(flow_tree: Dict) -> io.BytesIO:
    """흐름 트리 dict → xlsx BytesIO.

    flow_tree: {"title": str, "tree": [node, ...]}
      node: {"type", "content", "spec_page"?, "menu_path"?, "children": [...]}
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "흐름트리"

    thin = Side(style="thin", color="d1d5db")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # r1: 제목
    title = (flow_tree or {}).get("title", "")
    ws.cell(1, 2, f"흐름 메뉴트리 — {title}").font = Font(bold=True, size=13)

    # r2: 범례
    col = 2
    for code, label in LEGEND:
        c = ws.cell(2, col, code)
        c.font = Font(bold=True, size=9)
        c.fill = PatternFill("solid", fgColor=TYPE_FILL.get(code, "eeeeee"))
        ws.cell(2, col + 1, label).font = Font(size=9, italic=True)
        col += 2

    tree = (flow_tree or {}).get("tree", []) or []
    state = {"row": 4, "max_col": 2}

    def write_cell(r: int, depth: int, node: Dict):
        tcol = 2 + 2 * depth
        ccol = tcol + 1
        state["max_col"] = max(state["max_col"], tcol)
        ntype = node.get("type", "?")
        # 내용 셀: 루트 PR은 menu_path를 앞에 노출
        content = node.get("content", "")
        a = ws.cell(r, tcol, ntype)
        a.font = Font(bold=True, size=9, color="374151")
        a.fill = PatternFill("solid", fgColor=TYPE_FILL.get(ntype, "f3f4f6"))
        a.alignment = Alignment(horizontal="center", vertical="top")
        a.border = border
        b = ws.cell(r, ccol, content)
        b.font = Font(size=9)
        b.alignment = Alignment(vertical="top", wrap_text=True)
        b.border = border

    def render(node: Dict, depth: int):
        write_cell(state["row"], depth, node)
        children = node.get("children") or []
        for i, ch in enumerate(children):
            if i > 0:
                state["row"] += 1
            render(ch, depth + 1)

    for root in tree:
        render(root, 0)
        state["row"] += 1

    # r3: Step 헤더
    n_steps = (state["max_col"] - 2) // 2
    for k in range(n_steps + 1):
        label = "사전조건" if k == 0 else f"Step{k}"
        c = ws.cell(3, 2 + 2 * k, label)
        c.font = Font(bold=True, size=9, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="374151")
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(2 + 2 * k)].width = 5
        ws.column_dimensions[get_column_letter(3 + 2 * k)].width = 34

    ws.freeze_panes = "B4"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def flow_tree_stats(flow_tree: Dict) -> Dict:
    """노드 타입 분포·최대 깊이·총 노드 수 (요약·검증용)."""
    counts: Dict[str, int] = {}
    max_depth = [0]
    total = [0]

    def walk(node: Dict, depth: int):
        total[0] += 1
        counts[node.get("type", "?")] = counts.get(node.get("type", "?"), 0) + 1
        max_depth[0] = max(max_depth[0], depth)
        for ch in node.get("children") or []:
            walk(ch, depth + 1)

    for root in (flow_tree or {}).get("tree", []) or []:
        walk(root, 0)
    return {"types": counts, "max_depth": max_depth[0], "total": total[0]}
