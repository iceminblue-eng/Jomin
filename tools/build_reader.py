#!/usr/bin/env python3
"""원고/*.md → 읽기용 HTML 아티팩트 빌드.

마크다운 서브셋(이 책이 쓰는 문법)만 처리한다.
☐ 는 실제 체크박스로, ____ 는 입력칸으로 바꿔 워크북으로 만든다.
"""
import re, glob, os, html, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "reader.html")

# ---------- 인라인 ----------
def inline(t, ids):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*(?!\s)([^*]+?)(?<!\s)\*(?!\*)', r'<em>\1</em>', t)
    # 빈칸 → 입력
    def blank(m):
        ids[0] += 1
        return f'<input class="fill" type="text" data-k="{ids[1]}-{ids[0]}">'
    t = re.sub(r'_{3,}', blank, t)
    # 체크박스
    def box(m):
        ids[0] += 1
        return f'<input class="tick" type="checkbox" data-k="{ids[1]}-{ids[0]}">'
    t = t.replace('☐', '\x00')
    t = re.sub('\x00', box, t)
    return t

def fence_fill(t, ids):
    """코드펜스(진단 시트) 안의 ☐ / ____ 도 워크북 입력으로 바꾼다."""
    t = html.escape(t)
    def blank(m):
        ids[0] += 1
        w = min(max(len(m.group(0)), 4), 40)
        return (f'<input class="fill mono" type="text" style="width:{w}ch" '
                f'data-k="{ids[1]}-{ids[0]}">')
    t = re.sub(r'_{3,}', blank, t)
    def box(m):
        ids[0] += 1
        return f'<input class="tick" type="checkbox" data-k="{ids[1]}-{ids[0]}">'
    t = t.replace('\u2610', '\x00')
    t = re.sub('\x00', box, t)
    return t

def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

# ---------- 블록 ----------
def render(md, slug):
    ids = [0, slug]
    L = md.split('\n')
    out, i, n = [], 0, len(L)
    sec_open = False
    title = None
    meta = []
    preamble = True          # 첫 소제목 전까지가 머리말 구간

    def close_sec():
        nonlocal sec_open
        if sec_open:
            out.append('</section>')
            sec_open = False

    while i < n:
        ln = L[i]
        s = ln.strip()

        if not s:
            i += 1; continue

        # 코드펜스
        if s.startswith('```'):
            i += 1; buf = []
            while i < n and not L[i].strip().startswith('```'):
                buf.append(L[i]); i += 1
            i += 1
            out.append('<div class="scroll"><pre class="dia">'
                       + fence_fill('\n'.join(buf), ids) + '</pre></div>')
            continue

        # 구분선
        if re.fullmatch(r'-{3,}', s):
            i += 1; continue

        # 제목
        if s.startswith('# '):
            title = s[2:].strip()
            i += 1; continue

        if s.startswith('## '):
            close_sec()
            preamble = False
            h = s[3:].strip()
            m = re.match(r'^([0-9]+)\.\s+(.*)$', h)
            if m:
                num, txt = m.group(1), m.group(2)
            else:
                num, txt = '', h
            # STEP n · 제목  형태
            m2 = re.match(r'^(STEP\s*[0-9]+)\s*·\s*(.*)$', txt)
            if m2:
                num, txt = m2.group(1), m2.group(2)
            if not num:
                key = h.split('—')[0].strip()
                num = {'여는 질문':'여는 질문','장을 닫으며':'닫으며','과제':'과제',
                       '제2부 로드맵':'로드맵','제1부가 만든 것':'1부 총괄'}.get(key,'')
                if not num and h.startswith('다음 장 예고'): num='예고'
                if not num and h.startswith('다음 부 예고'): num='예고'
                if not num and h.startswith('이 장이 끝나면'): num='학습 목표'
            out.append('<section><div class="shead">'
                       + (f'<span class="snum">{inline(num,ids)}</span>' if num else '')
                       + f'<h2>{inline(txt,ids)}</h2></div>')
            sec_open = True
            i += 1; continue

        if s.startswith('#### '):
            out.append(f'<h4>{inline(s[5:],ids)}</h4>'); i += 1; continue

        if s.startswith('### '):
            preamble = False
            h = s[4:].strip()
            if re.fullmatch(r'이 (장|막간)의 좌표', h):
                # 다음 표를 좌표 박스로
                i += 1
                while i < n and not L[i].strip().startswith('|'): i += 1
                rows = []
                while i < n and L[i].strip().startswith('|'):
                    rows.append(cells(L[i])); i += 1
                body = ''.join(f'<dt>{inline(r[0],ids)}</dt><dd>{inline(r[1],ids)}</dd>'
                               for r in rows[2:] if len(r) >= 2)
                out.append(f'<div class="coord"><h2>{inline(h,ids)}</h2><dl>{body}</dl></div>')
                continue
            if h.endswith('요약 카드') or h.endswith('한 장 정리'):
                out.append(f'<h3 class="cardhead">{inline(h,ids)}</h3>'); i += 1; continue
            out.append(f'<h3>{inline(h,ids)}</h3>'); i += 1; continue

        # 표
        if s.startswith('|'):
            rows = []
            while i < n and L[i].strip().startswith('|'):
                rows.append(cells(L[i])); i += 1
            if len(rows) < 2: continue
            head = rows[0]
            has_head = any(c for c in head)
            t = ['<div class="scroll"><table>']
            start = 2
            if has_head:
                t.append('<thead><tr>' + ''.join(f'<th>{inline(c,ids)}</th>' for c in head) + '</tr></thead>')
            t.append('<tbody>')
            for r in rows[start:]:
                t.append('<tr>' + ''.join(f'<td>{inline(c,ids)}</td>' for c in r) + '</tr>')
            t.append('</tbody></table></div>')
            out.append(''.join(t))
            continue

        # 인용
        if s.startswith('>'):
            buf = []
            while i < n and L[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', L[i])); i += 1
            txt = '\n'.join(buf).strip()
            if preamble and not sec_open and ('적용 범위' in txt or re.search(r'제\d부', txt)):
                meta.append(txt); continue
            cls = 'callout'
            if txt.startswith('###'):
                cls = 'thesis big'
                txt = re.sub(r'^###\s*', '', txt, flags=re.M)
            elif txt.startswith('📌') or '📌' in txt[:8]:
                cls = 'aside'
            elif len(txt) < 120 and '\n' not in txt:
                cls = 'thesis'
            paras = [p for p in txt.split('\n') if p.strip()]
            inner = ''.join(f'<p>{inline(p,ids)}</p>' for p in paras)
            out.append(f'<div class="{cls}">{inner}</div>')
            continue

        # 목록
        if re.match(r'^[-*]\s+', s):
            items = []
            while i < n and re.match(r'^[-*]\s+', L[i].strip()):
                items.append(re.sub(r'^[-*]\s+', '', L[i].strip())); i += 1
            out.append('<ul class="bul">' + ''.join(f'<li>{inline(x,ids)}</li>' for x in items) + '</ul>')
            continue

        if re.match(r'^\d+\.\s+', s):
            items = []
            while i < n and re.match(r'^\d+\.\s+', L[i].strip()):
                cur = re.sub(r'^\d+\.\s+', '', L[i].strip()); i += 1
                while i < n and L[i].startswith('   ') and L[i].strip() and not re.match(r'^\d+\.', L[i].strip()):
                    cur += '<br>' + L[i].strip(); i += 1
                items.append(cur)
            out.append('<ol class="num">' + ''.join(f'<li>{inline(x,ids)}</li>' for x in items) + '</ol>')
            continue

        # 문단
        buf = [s]; i += 1
        while i < n and L[i].strip() and not re.match(r'^(#{1,4}\s|\||>|[-*]\s|\d+\.\s|```|-{3,}$)', L[i].strip()):
            buf.append(L[i].strip()); i += 1
        out.append(f'<p>{inline(" ".join(buf),ids)}</p>')

    close_sec()
    return title, meta, ''.join(out)

# ---------- 수집 ----------
files = sorted(glob.glob(os.path.join(ROOT, '원고', '*', '*.md')),
               key=lambda p: os.path.basename(p))
chapters = []
for f in files:
    md = open(f, encoding='utf-8').read()
    sm = re.match(r'(\d+)장?([A-Za-z])?', os.path.basename(f))
    slug = 'ch' + sm.group(1) + (sm.group(2) or '').lower()
    title, meta, body = render(md, slug)
    num = re.match(r'(\d+)장', title).group(1) if re.match(r'\d+장', title) else ''
    name = title.split('·', 1)[1].strip() if '·' in title else title
    # 번호 없는 막간은 제목 앞머리('막간')를 배지로 쓴다
    badge = num if num else title.split('·', 1)[0].strip()
    part = ''
    if meta:
        m = re.search(r'\*\*(제\d부[^*]*)\*\*', meta[0])
        if m: part = m.group(1).split('—')[0].strip()
    scope = ''
    if meta:
        m = re.search(r'\*\*적용 범위\*\*\s*(.*)', meta[0])
        if m: scope = re.sub(r'\*\*|·\s*$', '', m.group(1)).strip()
    chapters.append(dict(slug=slug, num=num, name=name, part=part,
                         scope=scope, badge=badge, body=body))

print(str(len(chapters)) + ' sections: '
      + ', '.join((c['num'] + '장' if c['num'] else c['badge']) for c in chapters))

# ---------- 템플릿 ----------
CSS = open(os.path.join(ROOT, 'tools', 'reader.css'), encoding='utf-8').read()

nav = ''.join(
    '<button class="tab" data-go="%s"><b>%s</b><span>%s</span></button>'
    % (c['slug'], c['badge'], c['name']) for c in chapters)

parts, seen = [], None
for c in chapters:
    pl = ''
    if c['part'] and c['part'] != seen:
        seen = c['part']
        pl = '<div class="partline"><i></i>%s</div>' % c['part']
    scope = ('<p class="scope"><b>적용 범위</b> &nbsp;%s</p>' % c['scope']) if c['scope'] else ''
    chno = (('<p class="chno">%02d<span>장</span></p>' % int(c['num'])) if c['num']
            else ('<p class="chno alt">%s</p>' % html.escape(c['badge'])))
    parts.append(
        '<article id="%s" class="chap"><header class="mast"><div class="wrap"><div class="col">'
        '%s%s<h1>%s</h1>%s'
        '</div></div></header><main class="wrap">%s</main></article>'
        % (c['slug'], pl, chno, c['name'], scope, c['body']))

SCRIPT = open(os.path.join(ROOT, 'tools', 'reader.js'), encoding='utf-8').read()

doc = (
'<title>관리자론 — 헤어살롱 편</title>\n'
'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700'
'&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">\n'
'<style>' + CSS + '</style>\n'
'<div id="bar"></div>\n'
'<nav id="nav"><div class="wrap navin">'
'<div class="brand"><b>관리자론</b><span>헤어살롱 편</span></div>'
'<div class="tabs">' + nav + '</div></div></nav>\n'
+ ''.join(parts) +
'\n<footer><div class="wrap">'
'<p><b>관리자론 — 헤어살롱 편</b><br>미용 시장 관리자 운용 바이블</p>'
'<p>원본 「운영 관리자 · 매트릭스 대입 수업」 강의안<br>단행본 원고 · 전 30장 초고 완료</p>'
'</div></footer>\n'
'<script>' + SCRIPT + '</script>\n')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(doc)
print('wrote ' + OUT + '  ' + str(len(doc)) + ' chars')
