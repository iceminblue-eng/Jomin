#!/usr/bin/env python3
"""네이버 플레이스 GAP 산출기.

브랜드 카드(마크다운)의 [정량 지표]·[32항목 체크] 표를 읽어
기준 문서(네이버플레이스/00-정의-및-최적화-기준.md)의 기준값·판정 규칙에 대입한 뒤
비교분석 보고서 뼈대(마크다운)를 출력한다.

사용법:
    python3 tools/naver_place_gap.py 네이버플레이스/02-비교브랜드/브랜드명.md
    python3 tools/naver_place_gap.py 카드.md -o 네이버플레이스/03-분석보고서/브랜드명-YYYYMMDD.md
    python3 tools/naver_place_gap.py 카드.md --type 로컬      # 카드의 '비즈니스 타입' 행을 덮어씀

비즈니스 타입(기준 문서 §0)은 카드의 '| 비즈니스 타입 | ... |' 행에서 읽는다.
'프랜차이즈'가 들어 있으면 프랜차이즈 고객수 타입(기준 A 이가자 · 상위 B 로한),
'로컬'이 들어 있으면 지역 로컬 고객수 타입(기준 L 온앤어스 · 상위 A 이가자)으로 판정한다.

정성 판단(한 줄 결론·처방 문안·로드맵 세부)은 출력된 뼈대 위에 사람이/Claude가 채운다.
기준값을 바꾸려면 아래 BENCH·ITEMS 를 고치지 말고 00-정의 문서를 먼저 개정한 뒤 여기에 반영한다.
"""
import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 기준값 (00-정의-및-최적화-기준.md §2·§4 와 동기화)
# ---------------------------------------------------------------------------

# 정량 지표 (타입별): 지표명 → (기준값, 상위값, 성격, 미달 시 등급)
BENCH_BY_TYPE = {
    # 프랜차이즈 고객수: 기준 A 이가자헤어비스 신도림점 · 상위 B 로한(디얼스 목동41타워점)
    "프랜차이즈": {
        "평점":        (4.92, 4.96, "품질",     None),
        "방문자 리뷰":  (14132, 30170, "축적형", "P2"),
        "블로그 리뷰":  (1172, 1689, "축적형",  "P2"),
        "스타일정보":   (300, 300, "단기충전",   "P1"),
        "가격표 이미지": (10, 1, "단기충전",     "P1"),
    },
    # 지역 로컬 고객수: 기준 L 온앤어스헤어 불당점(축적형은 실측, 단기충전은 90일 목표) · 상위 A 이가자
    "로컬": {
        "평점":        (4.94, 4.92, "품질",     None),
        "방문자 리뷰":  (5451, 14132, "축적형",  "P2"),
        "블로그 리뷰":  (397, 1172, "축적형",    "P2"),
        "스타일정보":   (300, 300, "단기충전",   "P1"),
        "가격표 이미지": (10, 10, "단기충전",    "P1"),
    },
}
TYPE_LABEL = {
    "프랜차이즈": ("프랜차이즈 고객수", "A 이가자헤어비스 신도림점", "B 로한 (디얼스 목동41타워점)"),
    "로컬":      ("지역 로컬 고객수",  "L 온앤어스헤어 불당점",   "A 이가자헤어비스 신도림점"),
}
RESERVE_STRUCT = {
    "프랜차이즈": "디자이너 5 + 안내형 1 + 이벤트형 1",
    "로컬":      "디자이너 5~6 + 추천형 1 + 이벤트형 1 (90일 목표 7)",
}
RESERVE_TOP = {"프랜차이즈": "11개", "로컬": "5 + 2"}

# 쿠폰 퍼널 4축: 지표명 → 미충족 시 등급
FUNNEL = {
    "쿠폰 유입":  "P0",
    "쿠폰 방문":  "P0",
    "쿠폰 리뷰":  "P1",
    "쿠폰 재방문": "P1",
}

ANCHOR_LO, ANCHOR_HI = 60000, 79000   # 앵커 목표 구간
VERIFY_GAP = 15000                     # 앵커-가중평균 격차 경고선

# 32항목: 번호 → (영역, 항목명, 미충족 시 등급)
ITEMS = {
    1: ("① 기본정보·위치", "업체명 브랜드+지점 표기 (키워드 삽입 금지)", "P0"),
    2: ("① 기본정보·위치", "카테고리 '미용실' 단일 등록", "P0"),
    3: ("① 기본정보·위치", "영업시간·휴무일 등록", "P0"),
    4: ("① 기본정보·위치", "0507 스마트콜 번호 연결", "P1"),
    5: ("① 기본정보·위치", "주소 층·호수까지 입력", "P1"),
    6: ("① 기본정보·위치", "SNS(블로그·인스타·예약) 링크 연결", "P1"),
    7: ("① 기본정보·위치", "찾아오는 길 도보 서술 (출구·미터·경유지)", "P1"),
    8: ("① 기본정보·위치", "주차 위치·요금·진입 동선 안내 + 탭 간 정합", "P0"),
    9: ("① 기본정보·위치", "편의시설·서비스 전 항목 체크", "P1"),
    10: ("② 소개문", "'[지역]미용실' 결합 키워드 3회 이상", "P1"),
    11: ("② 소개문", "여성·남성 시술명 구체적 나열", "P1"),
    12: ("② 소개문", "외국어 시술 키워드 병기", "P1"),
    13: ("③ 가격 설계", "전 상품 할인 라벨 표기", "P0"),
    14: ("③ 가격 설계", "대표 배지 = 주력 6~7만원대 상품", "P0"),
    15: ("③ 가격 설계", "미끼-주력-업셀 3단 구성", "P1"),
    16: ("③ 가격 설계", "기장 추가요금 명시", "P0"),
    17: ("③ 가격 설계", "가격표 이미지 등록 (10장)", "P1"),
    18: ("④ 쿠폰", "첫방문 대형할인 쿠폰 (매장 통일)", "P0"),
    19: ("④ 쿠폰", "포토리뷰 할인 쿠폰", "P1"),
    20: ("④ 쿠폰", "길찾기 방문 이벤트 쿠폰", "P0"),
    21: ("④ 쿠폰", "월 한정 케어 쿠폰", "P1"),
    22: ("⑤ 소식·이벤트", "월간 이벤트 소식 등록 (기간 명시)", "P0"),
    23: ("⑤ 소식·이벤트", "이달의 추천 디자이너 소식", "P1"),
    24: ("⑤ 소식·이벤트", "블로그 글 주 1회 이상 연동", "P2"),
    25: ("⑥ 예약 상품", "디자이너별 예약 상품 등록", "P0"),
    26: ("⑥ 예약 상품", "소개문 3요소 공식 적용 + 할인율 통일", "P0"),
    27: ("⑥ 예약 상품", "안내형 상품 1개 등록", "P1"),
    28: ("⑥ 예약 상품", "이벤트 예약 상품 등록", "P1"),
    29: ("⑦ 스타일정보·사진", "스타일정보 300장 (고민 카피 제목)", "P1"),
    30: ("⑦ 스타일정보·사진", "사진 탭 전 카테고리 + 클립 등록", "P1"),
    31: ("⑧ 리뷰 시스템", "리뷰 확보 3중 장치 (쿠폰·현장·답글) 가동", "P1"),
    32: ("⑧ 리뷰 시스템", "리뷰 답글률 100% (5단 공식)", "P1"),
}
# 영역 ⑨ 재방문 장치는 체크 항목 21(월 한정 쿠폰)과 카드의 '재방문 장치' 절로 판정한다.
AREAS = ["① 기본정보·위치", "② 소개문", "③ 가격 설계", "④ 쿠폰", "⑤ 소식·이벤트",
         "⑥ 예약 상품", "⑦ 스타일정보·사진", "⑧ 리뷰 시스템", "⑨ 재방문 장치"]
DEADLINE = {"P0": "14일", "P1": "30일", "P2": "90일"}

# ---------------------------------------------------------------------------
# 카드 파싱
# ---------------------------------------------------------------------------

def _rows(md: str, heading: str):
    """heading 아래 첫 표의 데이터 행을 [[cell, ...], ...] 로 돌려준다."""
    m = re.search(r"^##\s*" + re.escape(heading) + r"\s*$", md, re.M)
    if not m:
        sys.exit(f"카드에 '## {heading}' 절이 없습니다.")
    body = md[m.end():]
    nxt = re.search(r"^##\s", body, re.M)
    if nxt:
        body = body[: nxt.start()]
    rows = []
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue  # 구분선
        rows.append(cells)
    return rows[1:] if rows else []  # 헤더 제외


def _num(s: str):
    """'14,132' '~100' '4.94' '20~30' → float 또는 None. 범위는 하한."""
    s = s.strip().lstrip("~").replace(",", "")
    m = re.match(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None


def _yn(s: str):
    s = s.strip().upper()
    if s.startswith("Y"):
        return "Y"
    if s.startswith("N"):
        return "N"
    if "부분" in s:
        return "부분"
    return None


def parse_card(path: Path):
    md = path.read_text(encoding="utf-8")
    title = re.search(r"^#\s*브랜드 카드\s*[—-]\s*(.+)$", md, re.M)
    name = title.group(1).strip() if title else path.stem
    snap = re.search(r"^\|\s*스냅샷 일자\s*\|\s*([^|]*)\|", md, re.M)
    snap = snap.group(1).strip() if snap else ""
    t = re.search(r"^\|\s*비즈니스 타입\s*\|\s*([^|]*)\|", md, re.M)
    btype = detect_type(t.group(1)) if t else None
    metrics = {}
    for r in _rows(md, "[정량 지표]"):
        if len(r) >= 2 and r[0]:
            metrics[r[0]] = {"raw": r[1], "basis": r[2] if len(r) > 2 else "",
                             "est": r[1].strip().startswith("~")}
    checks = {}
    for r in _rows(md, "[32항목 체크]"):
        if len(r) >= 3 and r[0].isdigit():
            checks[int(r[0])] = {"status": _yn(r[2]), "basis": r[3] if len(r) > 3 else ""}
    return name, snap, btype, metrics, checks


def detect_type(text: str):
    """'프랜차이즈 고객수' / '지역 로컬 고객수' 문자열 → 키. 양식 안내문(둘 다 포함)은 None."""
    t = (text or "").strip()
    has_f, has_l = "프랜차이즈" in t, ("로컬" in t or "지역" in t)
    if has_f and not has_l:
        return "프랜차이즈"
    if has_l and not has_f:
        return "로컬"
    return None


# ---------------------------------------------------------------------------
# 판정
# ---------------------------------------------------------------------------

def quant_gap(metrics, btype):
    BENCH = BENCH_BY_TYPE[btype]
    BENCH_TOP = {k: max(v[0], v[1]) for k, v in BENCH.items()}
    out = []
    for key, (a, b, kind, grade) in BENCH.items():
        raw = metrics.get(key, {}).get("raw", "")
        v = _num(raw)
        if v is None:
            out.append((key, a, b, "미입력", "", "", "확인 필요"))
            continue
        gap = v - a
        rate = v / a * 100 if a else 0
        top = BENCH_TOP[key]
        if key == "평점":
            verdict = "강점" if v >= a else ("주의 — 서비스 문제로 별도 취급" if v < 4.8 else "보완")
        elif v >= top:
            verdict = "유지 (상위 수준 이상)"
        elif v >= a:
            verdict = f"개선점 — 상위값 {top:,.0f} 대비 격차 (P2)"
        else:
            if kind == "축적형":
                verdict = f"보완점 — 볼륨 GAP ({grade} 축적 과제)"
            elif rate >= 70:
                verdict = f"보완점 — 단기 충전 가능 ({grade})"
            else:
                verdict = f"보완점 — 즉시 보완 ({grade})"
        out.append((key, a, b, v, gap, rate, verdict))
    return out


def funnel_gap(metrics):
    out = []
    for key, grade in FUNNEL.items():
        st = _yn(metrics.get(key, {}).get("raw", "")) or "미입력"
        basis = metrics.get(key, {}).get("basis", "")
        if st == "Y":
            verdict = "충족"
        elif st == "부분":
            verdict = f"보완 ({'P1' if grade == 'P0' else grade})"
        elif st == "N":
            verdict = f"시급 ({grade})" if grade == "P0" else f"보완 ({grade})"
        else:
            verdict = "확인 필요"
        out.append((key.replace("쿠폰 ", ""), st, basis, verdict))
    return out


def price_diag(metrics):
    g = lambda k: _num(metrics.get(k, {}).get("raw", ""))
    badge, anchor, lo, hi = g("대표배지 가격"), g("주력 앵커 노출가"), g("최저 시술가"), g("최고 시술가")
    lines = []
    if badge is not None:
        ok = ANCHOR_LO <= badge <= ANCHOR_HI
        lines.append(("① 앵커 — 대표 배지 가격", f"{badge:,.0f}원",
                      "목표 구간 안 (앵커 완성)" if ok else f"목표 구간({ANCHOR_LO:,}~{ANCHOR_HI:,}) 밖 → 미끼가 대표 독점 의심, 시급 (P0)"))
    if anchor is not None:
        ok = ANCHOR_LO <= anchor <= ANCHOR_HI
        lines.append(("① 앵커 — 주력 노출가", f"{anchor:,.0f}원",
                      "목표 구간 안. 라벨·대표 배지만 확인" if ok else "목표 구간 밖 → 정상가·할인율 역산 재설계 (P0)"))
    if lo is not None and hi is not None:
        line = (lo + hi) / 2
        lines.append(("③ 검증선 — (최저+최고)÷2", f"{line:,.0f}원",
                      "가중평균과 대조. 격차 1.5만원 이상이면 미끼 과다 또는 업셀 공백 의심"))
    lines.append(("② 가중평균 객단가", "POS 구성비 필요", "워크시트 [1_가격설계]에 실구성비 입력 후 확정 (확인 필요 데이터)"))
    return lines


def area_verdicts(checks):
    res = {}
    for area in AREAS:
        nums = [n for n, (a, _, _) in ITEMS.items() if a == area]
        if not nums:  # ⑨ 재방문 장치
            st = checks.get(21, {}).get("status")
            res[area] = ("양호·유지" if st == "Y" else "보완" if st else "확인 필요",
                         "월 한정 쿠폰(#21) + 카드 '재방문 장치' 절로 판정")
            continue
        sts = {n: checks.get(n, {}).get("status") for n in nums}
        missing = [n for n, s in sts.items() if s is None]
        bad = [n for n, s in sts.items() if s in ("N", "부분")]
        p0_bad = [n for n in bad if ITEMS[n][2] == "P0" and sts[n] == "N"]
        if missing and len(missing) == len(nums):
            v = "확인 필요"
        elif p0_bad:
            v = "시급"
        elif bad:
            v = "보완"
        else:
            v = "양호·유지"
        why = ", ".join(f"#{n} {'미충족' if sts[n]=='N' else '부분'}" for n in bad) or "전 항목 충족"
        if missing:
            why += f" (미입력 #{', #'.join(map(str, missing))})"
        res[area] = (v, why)
    return res


def action_lists(checks, quant, btype):
    """보완점(P0/P1/P2 그룹) · 개선점 · 유지 목록."""
    BENCH = BENCH_BY_TYPE[btype]
    BENCH_TOP = {k: max(v[0], v[1]) for k, v in BENCH.items()}
    fix = {"P0": [], "P1": [], "P2": []}
    keep = []
    for n, (area, item, grade) in ITEMS.items():
        st = checks.get(n, {}).get("status")
        basis = checks.get(n, {}).get("basis", "")
        if st == "N":
            fix[grade].append((n, area, item, "미충족", basis))
        elif st == "부분":
            g = "P1" if grade == "P0" else grade  # 장치는 있으나 불완전 → 한 단계 완화
            fix[g].append((n, area, item, "부분", basis))
        elif st == "Y":
            keep.append((n, area, item, basis))
    improve = [(k, v, top) for (k, a, b, v, gap, rate, verdict) in quant
               if isinstance(v, float) and verdict.startswith("개선점") for top in [BENCH_TOP[k]]]
    return fix, improve, keep


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------

def render(name, snap, btype, metrics, checks):
    tlabel, tbase, ttop = TYPE_LABEL[btype]
    quant = quant_gap(metrics, btype)
    funnel = funnel_gap(metrics)
    price = price_diag(metrics)
    areas = area_verdicts(checks)
    fix, improve, keep = action_lists(checks, quant, btype)
    n_p0 = len(fix["P0"]); n_p1 = len(fix["P1"]); n_p2 = len(fix["P2"])
    filled = sum(1 for c in checks.values() if c["status"] is not None)
    ok = sum(1 for c in checks.values() if c["status"] == "Y")

    L = []
    w = L.append
    w(f"# 비교분석 보고서 — {name}")
    w("")
    w(f"| 항목 | 내용 |")
    w(f"| --- | --- |")
    w(f"| 스냅샷 일자 | {snap or '(카드에 미기재)'} |")
    w(f"| 비즈니스 타입 | **{tlabel}** — 기준 {tbase} · 상위 {ttop} (기준 문서 §0·§2) |")
    w(f"| 기준 문서 | `00-정의-및-최적화-기준.md` v1.2 |")
    w(f"| 32항목 충족 | {ok} / 32 (입력 {filled}) — P0 {n_p0} · P1 {n_p1} · P2 {n_p2} 건 보완 필요 |")
    w(f"| 한 줄 결론 | _(9영역 판정을 보고 매장 유형을 한 줄로 쓴다 — 기준 문서 §1-5)_ |")
    w("")
    w("## 0. 우선순위 5 (Executive)")
    w("")
    w("_(P0 목록에서 5개를 고르고 '왜 먼저 하는가'와 '완료 기준'을 붙인다)_")
    w("")
    w("| # | 액션 | 왜 먼저 | 완료 기준 |")
    w("| --- | --- | --- | --- |")
    for i, (n, area, item, st, basis) in enumerate(fix["P0"][:5], 1):
        w(f"| {i} | #{n} {item} | {basis or '_'} | _ |")
    w("")
    w("## 1. 정량 GAP (7지표)")
    w("")
    w(f"| 지표 | 기준값 ({tbase.split()[0]}) | 상위값 ({ttop.split()[0]}) | 진단값 | GAP | 달성률 | 판정 |")
    w("| --- | --- | --- | --- | --- | --- | --- |")
    for (k, a, b, v, gap, rate, verdict) in quant:
        fa = f"{a:,.2f}" if k == "평점" else f"{a:,.0f}"
        fb = f"{b:,.2f}" if k == "평점" else f"{b:,.0f}"
        if isinstance(v, float):
            fv = f"{v:,.2f}" if k == "평점" else f"{v:,.0f}"
            fg = f"{gap:+,.2f}" if k == "평점" else f"{gap:+,.0f}"
            fr = f"{rate:.1f}%"
        else:
            fv, fg, fr = v, "", ""
        est = " (추정)" if metrics.get(k, {}).get("est") else ""
        w(f"| {k} | {fa} | {fb} | {fv}{est} | {fg} | {fr} | {verdict} |")
    # 예약 구조
    d = metrics.get("예약상품 디자이너", {}).get("raw", "")
    g_ = metrics.get("예약상품 안내형", {}).get("raw", "")
    e = metrics.get("예약상품 이벤트형", {}).get("raw", "")
    w(f"| 예약 구조 | {RESERVE_STRUCT[btype]} | {RESERVE_TOP[btype]} | 디자이너 {d or '?'} + 안내형 {g_ or '?'} + 이벤트형 {e or '?'} | | | "
      f"{'구조 충족' if all(_num(x) and _num(x) >= 1 for x in (d, g_, e)) else '부분 충족 — 빠진 유형 보완 (P0 표준화 / P1 추가)'} |")
    w("")
    w("### 쿠폰 퍼널 4축")
    w("")
    w("| 퍼널 단계 | 현황 | 근거 | 판정 |")
    w("| --- | --- | --- | --- |")
    for (k, st, basis, verdict) in funnel:
        w(f"| {k} | {st} | {basis} | {verdict} |")
    w("")
    w("### 가격 3단 구조")
    w("")
    w("| 단계 | 값 | 판정·처방 |")
    w("| --- | --- | --- |")
    for (k, v, verdict) in price:
        w(f"| {k} | {v} | {verdict} |")
    disc = metrics.get("첫방문 할인율", {}).get("raw", "")
    if disc:
        w("")
        w(f"- 첫방문 할인율: {disc} — 기준 30%(A 이가자) / 50%(B 로한) / 로컬 1차 목표 30% 매장 통일. {'범위 표기 → 디자이너별 상이 → 매장 통일 필요 (P0)' if '~' in disc else ''}")
    w("")
    w("## 2. 9개 영역 판정")
    w("")
    w("| 영역 | 판정 | 사유 (체크 항목) |")
    w("| --- | --- | --- |")
    for area in AREAS:
        v, why = areas[area]
        w(f"| {area} | **{v}** | {why} |")
    w("")
    w("## 3. 보완점 — 기준 미달 (기준까지 채운다)")
    w("")
    for grade in ("P0", "P1", "P2"):
        w(f"### {grade} · {DEADLINE[grade]} 이내 — {len(fix[grade])}건")
        w("")
        if not fix[grade]:
            w("- 없음")
            w("")
            continue
        w("| # | 영역 | 항목 | 현재 | 근거 | 처방 (기준 문서 §3·§9 문형으로 작성) |")
        w("| --- | --- | --- | --- | --- | --- |")
        for (n, area, item, st, basis) in fix[grade]:
            w(f"| {n} | {area} | {item} | {st} | {basis} | _ |")
        w("")
    w("## 4. 개선점 — 기준 충족, 상위 수준과 격차 (더 잘한다)")
    w("")
    w(f"_(상위 수준 = {ttop})_")
    w("")
    if improve:
        w("| 지표 | 진단값 | 상위값 | 방향 |")
        w("| --- | --- | --- | --- |")
        for (k, v, top) in improve:
            w(f"| {k} | {v:,.0f} | {top:,.0f} | _ |")
    else:
        w("- 정량 지표에서 '기준 이상·상위 미만' 구간 없음. 체크 Y 항목 중 벤치마크 최상급 패턴과 차이 나는 것을 아래에 적는다.")
    w("")
    w("| 항목 | 현재 (Y) | 벤치마크 최상급 패턴 | 방향 |")
    w("| --- | --- | --- | --- |")
    w("| _ | _ | _ | _ |")
    w("")
    w("## 5. 강점 — 유지·표준화 대상")
    w("")
    for (n, area, item, basis) in keep:
        w(f"- #{n} {item}" + (f" — {basis}" if basis else ""))
    if not keep:
        w("- (충족 항목 없음)")
    w("")
    w("## 6. 로드맵")
    w("")
    w("### 14일 Quick Wins (P0)")
    w("")
    w("| 기한 | 액션 | 담당 | 산출물 | 완료 기준 |")
    w("| --- | --- | --- | --- | --- |")
    for (n, area, item, st, basis) in fix["P0"]:
        w(f"| D_ | #{n} {item} | _ | _ | _ |")
    w("")
    w("### 90일 플랜")
    w("")
    w("| 기간 | 목표 | 핵심 액션 | Exit KPI |")
    w("| --- | --- | --- | --- |")
    w("| 0~14일 | 전환 기반 복구 | P0 전부 | 설정 누락 0 · 대표 6~7만원 · 월간 이벤트 1건 |")
    w("| 15~30일 | 콘텐츠 슬롯 최대화 | P1 전부 | 스타일 300 · 블로그 8/월 · 클립 8/월 |")
    w("| 31~60일 | 퍼널 실험 | 앵커/쿠폰 카피 2주 단위 비교 | 방문→예약 5% |")
    w("| 61~90일 | 객단가·재방문 최적화 | P2 · 프리미엄 케어 2단계 · 컷 비중 관리 | 가중평균 6~7만 · 컷 <40% · 2회차 35% |")
    w("")
    w("## 7. KPI 계기판 기준선")
    w("")
    w("| KPI | 목표 | 현재 기준선 | 경고선 |")
    w("| --- | --- | --- | --- |")
    w("| 신규 예약/월 | 450 | 확인 필요 | 2주 연속 일 10 미만 |")
    w("| 플레이스→예약 전환율 | 5%+ | 확인 필요 | 4% 미만 |")
    w("| 월 신규 리뷰 | 300 또는 신규의 65% | 확인 필요 | — |")
    w("| 답글률 | 100% / 24h | " + (metrics.get("답글률", {}).get("raw") or "확인 필요") + " | 미답글 당일 배정 |")
    w("| 가중평균 객단가 | 6~7만 | 확인 필요 (POS) | 6만 미만 |")
    w("| 컷 비중 | <40% | 확인 필요 (POS) | 40%+ |")
    w("| 2회차 재방문 | 35%+ | 확인 필요 | — |")
    w("")
    w("## 8. 확인 필요 데이터 (공개 자료로 확인 불가)")
    w("")
    w("- 네이버 예약 파트너센터 최근 90일 신규 예약 수")
    w("- 스마트플레이스 유입/예약 통계")
    w("- POS 최근 30일: 시술군 구성비 · 첫방문 실결제가 · 할인액 · 기장추가 · 공헌이익")
    w("- 리뷰 답글 전체 집계")
    w("- 90일 내 2회차 예약 데이터")
    w("- 시술별 마진 (30%/50% 혜택 지속 가능성)")
    w("")
    w("## 9. 기준 문서에 반영할 것")
    w("")
    w("- _(이 브랜드를 보며 기준에 빠져 있다고 느낀 항목, 기준값이 틀렸다고 보이는 항목)_")
    w("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card", type=Path, help="브랜드 카드 .md")
    ap.add_argument("-o", "--out", type=Path, help="출력 파일 (기본: 표준출력)")
    ap.add_argument("--type", choices=list(BENCH_BY_TYPE), help="비즈니스 타입 강제 지정 (프랜차이즈 / 로컬)")
    a = ap.parse_args()
    name, snap, btype, metrics, checks = parse_card(a.card)
    btype = a.type or btype
    if btype is None:
        sys.exit("비즈니스 타입을 정할 수 없습니다. 카드의 '| 비즈니스 타입 |' 행에 '프랜차이즈 고객수' 또는 '지역 로컬 고객수'를 적거나 --type 을 주세요.")
    if not checks:
        sys.exit("[32항목 체크] 표에서 항목을 읽지 못했습니다. 번호 열이 숫자인지 확인하세요.")
    md = render(name, snap, btype, metrics, checks)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(md, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
