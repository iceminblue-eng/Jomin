#!/usr/bin/env python3
"""네이버 플레이스 진단 리포트(마크다운) + 브랜드 카드 → 보완·수정 기입용 Excel(.xlsx)

사용법:
    python3 tools/naver_place_xlsx.py 리포트.md 카드.md 출력.xlsx

시트 구성 (노란색 칸이 입력칸 — 원자료 실습 워크시트와 같은 규약):
    README          사용법 · 색 범례
    1_액션플랜      리포트 §5 'N개월 차' 표(30일 단위) → 담당·목표일·상태·완료일·실제 적용 문구 기입
                    (내부 리포트처럼 §3 P0/P1/P2 구조면 그 표를 읽는다)
    2_32항목체크    카드 [32항목 체크] → 진단 시 충족 / 재점검 충족(Y·N·부분) 기입, 완료율 자동
    3_영역별판정    리포트 §7(또는 §2) 영역 판정 표 → 재점검 판정 기입
    4_확인할숫자    리포트 §6 KPI 표 + 자료 목록 → 실측값·측정일·출처 기입
    5_기준반영      내부 리포트 §9가 있을 때만 생성
"""
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

YELLOW = PatternFill("solid", fgColor="FFF2CC")
GREY = PatternFill("solid", fgColor="EDEDED")
HEAD = PatternFill("solid", fgColor="DDE5F0")
P0 = PatternFill("solid", fgColor="F8CBAD")
P1 = PatternFill("solid", fgColor="FFE699")
P2 = PatternFill("solid", fgColor="C6E0B4")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=13)


# ---------------------------------------------------------------- markdown helpers
def section(md: str, heading_regex: str) -> str:
    """'## ' 제목이 정규식에 맞는 절의 본문(다음 '## ' 전까지)."""
    m = re.search(r"^##\s*" + heading_regex + r".*$", md, re.M)
    if not m:
        return ""
    rest = md[m.end():]
    n = re.search(r"^##\s", rest, re.M)
    return rest[: n.start()] if n else rest


def subsections(text: str):
    """'### ' 단위로 (제목, 본문) 목록."""
    parts = re.split(r"^###\s+", text, flags=re.M)
    out = []
    for p in parts[1:]:
        title, _, body = p.partition("\n")
        out.append((title.strip(), body))
    return out


def tables(text: str):
    """본문 안의 마크다운 표들을 [[헤더], [행], ...] 목록으로."""
    res, cur = [], []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells):
                continue
            cur.append([clean(c) for c in cells])
        else:
            if cur:
                res.append(cur)
                cur = []
    if cur:
        res.append(cur)
    return res


def bullets(text: str):
    return [clean(re.sub(r"^\s*[-*]\s+", "", l)) for l in text.splitlines() if re.match(r"^\s*[-*]\s+", l)]


def clean(s: str) -> str:
    s = s.replace("\\|", "|")
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    return s.strip()


def col_index(header, *names, default=None):
    for n in names:
        for i, h in enumerate(header):
            if n in h:
                return i
    return default


# ---------------------------------------------------------------- sheet helpers
def write_header(ws, row, headers, widths):
    for c, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.font = BOLD
        cell.fill = HEAD
        cell.alignment = CENTER
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def put(ws, row, col, value, fill=None, center=False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.alignment = CENTER if center else WRAP
    cell.border = BORDER
    if fill is not None:
        cell.fill = fill
    return cell


def status_validation(ws, col_letter, first, last, options="대기,진행,완료,보류"):
    dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col_letter}{first}:{col_letter}{last}")


# ---------------------------------------------------------------- builders
def build_readme(wb, brand, report_path, card_path, sheets_desc):
    ws = wb.active
    ws.title = "README"
    ws["A1"] = f"{brand} — 네이버 플레이스 보완·수정 기입 시트"
    ws["A1"].font = TITLE
    ws["A2"] = f"근거 리포트: {report_path.name}   ·   브랜드 카드: {card_path.name}"
    ws["A4"] = "시트"; ws["B4"] = "설명"
    for c in ("A4", "B4"):
        ws[c].font = BOLD; ws[c].fill = HEAD; ws[c].border = BORDER
    r = 5
    for name, desc in sheets_desc:
        ws.cell(row=r, column=1, value=name).border = BORDER
        cell = ws.cell(row=r, column=2, value=desc); cell.border = BORDER; cell.alignment = WRAP
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="색 범례").font = BOLD; r += 1
    for fill, text in ((YELLOW, "노란색 칸 — 매장/담당자가 직접 기입하는 칸"),
                       (GREY, "회색 칸 — 리포트에서 가져온 진단 결과 (수정하지 않음)"),
                       (P0, "1개월 차 (1~30일) — 혜택이 보이게 / 시급"), (P1, "2개월 차 (31~60일) — 검색 재료 채우기 / 보완"), (P2, "3개월 차 (61~90일) — 객단가·재방문 / 양호")):
        ws.cell(row=r, column=1).fill = fill
        ws.cell(row=r, column=1).border = BORDER
        ws.cell(row=r, column=2, value=text)
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="사용 순서").font = BOLD; r += 1
    for t in ("① 1_액션플랜 에서 항목별 담당·목표일을 정한다 (1개월 차 → 2개월 차 → 3개월 차 순).",
              "② 조치 후 '실제 적용 문구'에 플레이스에 올린 문구·가격·쿠폰명을 그대로 적는다 — 다음 진단 때 정합성 확인 근거가 된다.",
              "③ 상태를 '완료'로 바꾸면 상단 완료율이 집계된다.",
              "④ 2_32항목체크 에서 재점검 시 충족 여부를 다시 매긴다. 재점검 카드로 스크립트를 다시 돌리면 리포트 v2가 나온다.",
              "⑤ 4_확인할숫자 의 값이 채워지면 가중평균 객단가·컷 비중 목표를 확정하고 리포트를 갱신한다."):
        ws.cell(row=r, column=1, value=t).alignment = WRAP
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        ws.row_dimensions[r].height = 30
        r += 1
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 110


def build_actions(wb, report_md):
    """리포트의 액션 플랜 → 기입 시트. '## 5' 아래 'N개월 차' 소절이 있으면 30일 단위 구조,
    없으면 '## 3' 아래 P0/P1/P2 구조를 읽는다."""
    ws = wb.create_sheet("1_액션플랜")
    ws["A1"] = "1. 액션 플랜 — 30일 단위로 진행하고, 한 일은 '실제 적용 문구'에 그대로 남겨요"; ws["A1"].font = TITLE
    ws["A2"] = "완료율"; ws["A2"].font = BOLD
    headers = ["구분", "#", "무엇을 하나요", "왜 하나요", "이렇게 되면 완료예요", "담당", "목표일", "상태", "완료일", "실제 적용 문구 (플레이스에 올린 그대로)", "메모"]
    widths = [14, 5, 46, 40, 36, 10, 11, 8, 11, 40, 24]
    write_header(ws, 4, headers, widths)
    r = 5
    month_sec = section(report_md, r"5\.")
    month_subs = [(t, b) for t, b in subsections(month_sec) if "개월 차" in t]
    fills = [P0, P1, P2]
    if month_subs:
        for k, (title, body) in enumerate(month_subs):
            label = re.match(r"(\d개월 차[^—-]*)", title)
            label = label.group(1).strip() if label else title
            fill = fills[min(k, 2)]
            for tbl in tables(body):
                hdr, rows = tbl[0], tbl[1:]
                i_no = col_index(hdr, "#", default=0)
                i_what = col_index(hdr, "무엇을", default=1)
                i_why = col_index(hdr, "왜", default=2)
                i_done = col_index(hdr, "완료", default=3)
                for row in rows:
                    g = lambda i: row[i] if i is not None and i < len(row) else ""
                    put(ws, r, 1, label, fill, center=True)
                    put(ws, r, 2, g(i_no), GREY, center=True)
                    put(ws, r, 3, g(i_what), GREY)
                    put(ws, r, 4, g(i_why), GREY)
                    put(ws, r, 5, g(i_done), GREY)
                    for c in range(6, 12):
                        put(ws, r, c, None, YELLOW)
                    r += 1
    else:
        sec = section(report_md, r"3\.")
        deadline = {"P0": "14일", "P1": "30일", "P2": "90일"}
        for title, body in subsections(sec):
            grade = re.match(r"(P\d)", title)
            grade = grade.group(1) if grade else ""
            fill = {"P0": P0, "P1": P1, "P2": P2}.get(grade, GREY)
            for tbl in tables(body):
                hdr, rows = tbl[0], tbl[1:]
                i_no = col_index(hdr, "#", default=0)
                i_item = col_index(hdr, "항목", default=2)
                i_cur = col_index(hdr, "현재", default=3)
                i_rx = col_index(hdr, "처방", default=len(hdr) - 1)
                for row in rows:
                    g = lambda i: row[i] if i is not None and i < len(row) else ""
                    put(ws, r, 1, f"{grade} ({deadline.get(grade, '')})", fill, center=True)
                    put(ws, r, 2, g(i_no), GREY, center=True)
                    put(ws, r, 3, g(i_item), GREY)
                    put(ws, r, 4, g(i_cur), GREY)
                    put(ws, r, 5, g(i_rx), GREY)
                    for c in range(6, 12):
                        put(ws, r, c, None, YELLOW)
                    r += 1
    last = r - 1
    if last >= 5:
        ws["B2"] = f'=IF(COUNTA(C5:C{last})=0,"",COUNTIF(H5:H{last},"완료")/COUNTA(C5:C{last}))'
        ws["B2"].number_format = "0%"
        ws["C2"] = "1개월 차 완료"; ws["D2"] = f'=COUNTIFS(A5:A{last},"1개월 차*",H5:H{last},"완료")&" / "&COUNTIF(A5:A{last},"1개월 차*")'
        status_validation(ws, "H", 5, last)
    return last - 4


def build_checklist(wb, card_md):
    ws = wb.create_sheet("2_32항목체크")
    ws["A1"] = "2. 셋팅 체크리스트 32항목 — 진단 시 충족과 재점검 충족"; ws["A1"].font = TITLE
    ws["A2"] = "진단 시 충족률"; ws["A2"].font = BOLD
    ws["C2"] = "재점검 충족률"; ws["C2"].font = BOLD
    headers = ["#", "항목", "진단 시 충족", "진단 근거", "재점검 충족 (Y/N/부분)", "재점검일", "메모"]
    widths = [5, 40, 12, 50, 16, 12, 30]
    write_header(ws, 4, headers, widths)
    sec = section(card_md, r"\[32항목 체크\]")
    r = 5
    for tbl in tables(sec):
        for row in tbl[1:]:
            if not row or not row[0].isdigit():
                continue
            put(ws, r, 1, int(row[0]), GREY, center=True)
            put(ws, r, 2, row[1] if len(row) > 1 else "", GREY)
            st = row[2] if len(row) > 2 else ""
            put(ws, r, 3, st, {"Y": P2, "N": P0, "부분": P1}.get(st, GREY), center=True)
            put(ws, r, 4, row[3] if len(row) > 3 else "", GREY)
            put(ws, r, 5, None, YELLOW, center=True)
            put(ws, r, 6, None, YELLOW, center=True)
            put(ws, r, 7, None, YELLOW)
            r += 1
    last = r - 1
    if last >= 5:
        ws["B2"] = f'=COUNTIF(C5:C{last},"Y")/COUNTA(C5:C{last})'; ws["B2"].number_format = "0%"
        ws["D2"] = f'=IF(COUNTA(E5:E{last})=0,"",COUNTIF(E5:E{last},"Y")/COUNTA(A5:A{last}))'; ws["D2"].number_format = "0%"
        status_validation(ws, "E", 5, last, options="Y,N,부분")


def build_verdicts(wb, report_md):
    ws = wb.create_sheet("3_영역별판정")
    ws["A1"] = "3. 영역별 판정 — 재점검 때 다시 매겨요"; ws["A1"].font = TITLE
    headers = ["영역", "판정 (진단 시)", "재점검 판정", "재점검일", "메모"]
    widths = [22, 26, 16, 12, 40]
    write_header(ws, 3, headers, widths)
    r = 4
    src = section(report_md, r"7\.") or section(report_md, r"2\.")
    for tbl in tables(src):
        hdr = tbl[0]
        if "영역" not in hdr[0] or "판정" not in "".join(hdr):
            continue
        for row in tbl[1:]:
            v = row[1] if len(row) > 1 else ""
            fill = P0 if "시급" in v else P2 if "양호" in v else P1
            put(ws, r, 1, row[0], GREY)
            put(ws, r, 2, v, fill)
            put(ws, r, 3, None, YELLOW, center=True)
            put(ws, r, 4, None, YELLOW, center=True)
            put(ws, r, 5, None, YELLOW)
            r += 1
    if r > 4:
        status_validation(ws, "C", 4, r - 1, options="양호·유지,보완,시급")


def build_numbers(wb, report_md):
    ws = wb.create_sheet("4_확인할숫자")
    ws["A1"] = "4. 숫자로 확인할 것 — 매장 자료가 오면 값을 채워요"; ws["A1"].font = TITLE
    src = section(report_md, r"6\.")
    r = 3
    for tbl in tables(src):
        hdr = tbl[0]
        write_header(ws, r, hdr + ["실측값", "측정일", "출처", "메모"], [26, 22, 22, 34, 14, 12, 20, 24][: len(hdr) + 4])
        r += 1
        for row in tbl[1:]:
            for c, v in enumerate(row):
                put(ws, r, c + 1, v, GREY)
            for c in range(len(hdr) + 1, len(hdr) + 5):
                put(ws, r, c, None, YELLOW)
            r += 1
        r += 1
    items = bullets(src) or bullets(section(report_md, r"8\."))
    if items:
        ws.cell(row=r, column=1, value="매장에서 뽑아 주셔야 하는 자료").font = BOLD; r += 1
        write_header(ws, r, ["자료 (리포트)", "값 / 파일명", "기간", "입수일", "담당", "메모"], [60, 22, 16, 12, 10, 30])
        r += 1
        for b in items:
            put(ws, r, 1, b, GREY)
            for c in range(2, 7):
                put(ws, r, c, None, YELLOW)
            r += 1


def build_feedback(wb, report_md):
    if not bullets(section(report_md, r"9\.")):
        return
    ws = wb.create_sheet("5_기준반영")
    ws["A1"] = "6. 기준 문서에 반영할 것 — 이 진단에서 나온 기준 수정 제안"; ws["A1"].font = TITLE
    headers = ["제안 (리포트 §9)", "결정 (채택/보류/기각)", "반영 버전", "메모"]
    widths = [90, 16, 12, 30]
    write_header(ws, 3, headers, widths)
    r = 4
    for b in bullets(section(report_md, r"9\.")):
        put(ws, r, 1, b, GREY)
        for c in range(2, 5):
            put(ws, r, c, None, YELLOW)
        r += 1
    if r > 4:
        status_validation(ws, "B", 4, r - 1, options="채택,보류,기각")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    report_path, card_path, out_path = map(Path, sys.argv[1:4])
    report_md = report_path.read_text(encoding="utf-8")
    card_md = card_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s*비교분석 보고서\s*[—-]\s*(.+)$", report_md, re.M)
    brand = m.group(1).strip() if m else report_path.stem

    wb = Workbook()
    build_readme(wb, brand, report_path, card_path, [
        ("1_액션플랜", "리포트의 30일 단위 액션 플랜 전부. 담당·목표일·상태·실제 적용 문구를 기입. 완료율 자동 집계"),
        ("2_32항목체크", "셋팅 체크 32항목의 진단 결과. 재점검 시 충족(Y/N/부분)을 다시 매기면 재점검 충족률 자동 집계"),
        ("3_영역별판정", "9개 영역 판정. 재점검 때 다시 매김"),
        ("4_확인할숫자", "KPI 목표·현재·경고선과 매장에서 뽑아 줘야 하는 자료. 값·측정일·출처 기입"),
    ])
    n = build_actions(wb, report_md)
    build_checklist(wb, card_md)
    build_verdicts(wb, report_md)
    build_numbers(wb, report_md)
    build_feedback(wb, report_md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"wrote {out_path} — 보완점 {n}건, 시트 {len(wb.sheetnames)}개")


if __name__ == "__main__":
    main()
