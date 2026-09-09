# -*- coding: utf-8 -*-
"""권별 단행본 원고 한 파일로 조립.
   사용: python3 tools/build_manuscript.py <권번호> <출력경로>"""
import re, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOL = int(sys.argv[1]) if len(sys.argv) > 1 else 1
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    ROOT, 'build', '%d권' % VOL, '관리자론-%d.md' % VOL)

META = {1: ('관리자론 1 — 기준과 진단', '우리 살롱에 맞는 관리자 모델을 설계하다'),
        2: ('관리자론 2 — 권한과 운영', '관리자가 일하고 시스템이 돌아가는 매장을 만들다'),
        3: ('관리자론 3 — 확장과 양성', '사람이 바뀌어도 이어지는 운영을 설계하다')}

files = sorted(glob.glob(os.path.join(ROOT, '원고', '%d권' % VOL, '*.md')),
               key=lambda p: os.path.basename(p))

secs = []
for f in files:
    lines = open(f, encoding='utf-8').read().split('\n')
    title = next(l[2:].strip() for l in lines if l.startswith('# '))
    part = ''
    for l in lines[:8]:
        m = re.search(r'섹션\s*([A-C])\.\s*([^*]+)', l)
        if m:
            part = '섹션 %s · %s' % (m.group(1), m.group(2).strip()); break
    body, i, seen = [], 0, False
    while i < len(lines):
        if not seen:
            if lines[i].startswith('# '):
                seen = True; i += 1
                while i < len(lines) and (not lines[i].strip()
                        or lines[i].strip().startswith('>')
                        or re.fullmatch(r'-{3,}', lines[i].strip())):
                    i += 1
                continue
            i += 1; continue
        body.append(lines[i]); i += 1
    secs.append(dict(title=title, part=part, body='\n'.join(body).strip()))

t, sub = META[VOL]
out = ['# %s\n' % t, '## %s\n' % sub,
       '관리자론 — 헤어살롱 편 · 전 3권 중 %d권\n' % VOL,
       '적용 범위 · 중대형 살롱(40평 이상 · 8인 이상) · 다점포(2개 지점 이상)\n', '\n---\n',
       '# 목차\n']
seen = None
for s in secs:
    if s['part'] and s['part'] != seen:
        seen = s['part']; out.append('\n**%s**\n' % s['part'])
    out.append('- %s' % s['title'])
out.append('\n---\n')

seen = None
for s in secs:
    if s['part'] and s['part'] != seen:
        seen = s['part']
        out += ['\n---\n', '# %s\n' % s['part'].split(' · ')[0],
                '## %s\n' % s['part'].split(' · ', 1)[1], '\n---\n']
    out.append('\n# %s\n' % s['title'])
    out.append(s['body']); out.append('\n')

doc = '\n'.join(out)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(doc)
print('%d권: %s  %d자 / %d개 절' % (VOL, os.path.basename(OUT), len(doc), len(secs)))
