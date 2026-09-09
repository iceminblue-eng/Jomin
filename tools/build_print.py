# -*- coding: utf-8 -*-
"""권별 단행본 원고 → 인쇄용 HTML (Chromium PDF 출력용)."""
import sys, os, html as H
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md_to_json import parse

SRC = sys.argv[1]
OUT = sys.argv[2]

def runs(rs):
    o = []
    for r in rs:
        t = H.escape(r.get('t', ''))
        if r.get('b'): t = '<strong>%s</strong>' % t
        if r.get('i'): t = '<em>%s</em>' % t
        if r.get('c'): t = '<code>%s</code>' % t
        o.append(t)
    return ''.join(o)

def render(blocks):
    out, first = [], True
    for idx, b in enumerate(blocks):
        k = b['k']
        if k == 'h':
            lv = b['lvl']
            if lv == 1:
                out.append('<h1%s>%s</h1>' % ('' if first else ' class="brk"', runs(b['runs'])))
                first = False
            else:
                out.append('<h%d>%s</h%d>' % (lv, runs(b['runs']), lv))
        elif k == 'p':   out.append('<p>%s</p>' % runs(b['runs']))
        elif k == 'quote':
            out.append('<blockquote class="%s">%s</blockquote>'
                       % ('q big' if b['big'] else 'q',
                          ''.join('<p>%s</p>' % runs(p) for p in b['paras'])))
        elif k == 'ul':  out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % runs(x) for x in b['items']))
        elif k == 'ol':  out.append('<ol>%s</ol>' % ''.join('<li>%s</li>' % runs(x) for x in b['items']))
        elif k == 'pre': out.append('<pre>%s</pre>' % H.escape('\n'.join(b['lines'])))
        elif k == 'table':
            n = b['cols']; t = ['<table>']
            if b['head']:
                h = b['head'] + [[{'t': ''}]] * (n - len(b['head']))
                t.append('<thead><tr>%s</tr></thead>' % ''.join('<th>%s</th>' % runs(c) for c in h[:n]))
            t.append('<tbody>')
            for r0 in b['rows']:
                r = r0 + [[{'t': ''}]] * (n - len(r0))
                t.append('<tr>%s</tr>' % ''.join('<td>%s</td>' % runs(c) for c in r[:n]))
            t.append('</tbody></table>'); out.append(''.join(t))
        elif k == 'hr':
            pv, nx = blocks[idx-1] if idx else None, blocks[idx+1] if idx+1 < len(blocks) else None
            if pv and nx and pv['k'] != 'h' and nx['k'] != 'h': out.append('<hr>')
    return ''.join(out)

CSS = """
@page { size: A4; margin: 22mm 20mm 20mm; }
*{box-sizing:border-box}
body{font-family:'Gowun Batang',serif;font-size:10.2pt;line-height:1.78;color:#1a1a1a;margin:0}
h1,h2,h3,h4{font-family:'IBM Plex Sans KR',sans-serif;line-height:1.4;text-wrap:balance;
  page-break-after:avoid;break-after:avoid}
h1{font-size:20pt;font-weight:700;margin:0 0 16mm;letter-spacing:-.02em;
   padding-bottom:5mm;border-bottom:2px solid #12483a;color:#12483a}
h1.brk{page-break-before:always;break-before:page}
h2{font-size:13.5pt;font-weight:700;margin:9mm 0 3mm;color:#12483a}
h3{font-size:11.2pt;font-weight:600;margin:6mm 0 2mm}
h4{font-size:10.4pt;font-weight:600;margin:4mm 0 1.5mm;font-family:'Gowun Batang',serif}
p{margin:0 0 2.6mm;text-align:justify;word-break:keep-all}
strong{font-weight:700}
code{font-family:Consolas,monospace;font-size:.92em;background:#f0f2f1;padding:0 2px;border-radius:2px}
blockquote.q{margin:3mm 0 3.6mm;padding:0 0 0 4mm;border-left:2px solid #9fc2b3;color:#3d4a45}
blockquote.q p{margin:0 0 1.2mm}
blockquote.q.big p{font-size:11.4pt;font-weight:700;color:#12483a;line-height:1.6}
ul,ol{margin:2.5mm 0 3.5mm;padding-left:6mm}
li{margin:0 0 1.4mm}
table{border-collapse:collapse;width:100%;margin:3mm 0 4.5mm;font-size:9.1pt;line-height:1.6;
  page-break-inside:avoid;break-inside:avoid}
th,td{border:.4pt solid #b9c6c0;padding:1.6mm 2.2mm;vertical-align:top;text-align:left;word-break:keep-all}
th{background:#eaf0ed;font-family:'IBM Plex Sans KR',sans-serif;font-weight:600;font-size:8.9pt}
pre{font-family:Consolas,'IBM Plex Sans KR',monospace;font-size:8.4pt;line-height:1.55;
  background:#f7f8f8;border:.4pt solid #ccd6d1;padding:3.4mm 4mm;margin:3mm 0 4.5mm;
  white-space:pre-wrap;page-break-inside:avoid;break-inside:avoid;color:#33403a}
hr{border:0;border-top:.4pt solid #cfd8d4;margin:5mm 0}
"""

blocks = parse(open(SRC, encoding='utf-8').read())
doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
       '<title>관리자론 — 헤어살롱 편</title><style>%s</style></head><body>%s</body></html>'
       % (CSS, render(blocks)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(doc)
print('  인쇄용 HTML: %d blocks' % len(blocks))
