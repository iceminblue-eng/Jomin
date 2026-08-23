# -*- coding: utf-8 -*-
"""원고/ 의 장 파일을 읽어 단행본 원고 한 파일로 조립한다.
   사용: python3 tools/build_manuscript.py build/관리자론-헤어살롱편-원고.md"""
import re, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'build', '관리자론-헤어살롱편-원고.md')

PART_TITLE = {
    '제1부': '규모가 커지면 관계가 아니라 구조로',
    '제2부': '상수와 변수로 우리 살롱의 좌표를 찾아라',
    '제3부': '선수형인가, 오피스형인가',
    '제4부': '중간에 선 사람의 리더십',
    '제5부': '운영 관리자가 실제로 돌려야 할 시스템',
    '제6부': '두 번째 지점부터는 복제가 아니라 운영 체계',
    '제7부': '운영 관리자를 선발하고 성장시켜라',
    '제8부': '매트릭스를 현장에 적용하라',
}

files = sorted(glob.glob(os.path.join(ROOT, '원고', '*', '*.md')),
               key=lambda p: os.path.basename(p))

secs = []
for f in files:
    md = open(f, encoding='utf-8').read()
    lines = md.split('\n')
    title = next(l[2:].strip() for l in lines if l.startswith('# '))
    part = ''
    for l in lines[:8]:
        m = re.search(r'\*\*(제\d부)', l)
        if m:
            part = m.group(1); break
    # 머리말 인용(부 표시·적용 범위)은 단행본에서 제거하고 부 간지로 대체
    body, i = [], 0
    seen_h1 = False
    while i < len(lines):
        ln = lines[i]
        if not seen_h1:
            if ln.startswith('# '):
                seen_h1 = True; i += 1
                # 이어지는 인용 블록과 구분선 건너뛰기
                while i < len(lines) and (not lines[i].strip()
                       or lines[i].strip().startswith('>')
                       or re.fullmatch(r'-{3,}', lines[i].strip())):
                    i += 1
                continue
            i += 1; continue
        body.append(ln); i += 1
    secs.append(dict(title=title, part=part, body='\n'.join(body).strip()))

out = []
out.append('# 관리자론 — 헤어살롱 편\n')
out.append('## 미용 시장 관리자 운용 바이블\n')
out.append('원본 「운영 관리자 · 매트릭스 대입 수업」 강의안 (전 30회차)\n')
out.append('적용 범위 · 중대형 살롱(40평 이상 · 8인 이상) · 다점포(2개 지점 이상)\n')
out.append('\n---\n')

# 목차
out.append('# 목차\n')
seen = None
for s in secs:
    if s['part'] and s['part'] != seen:
        seen = s['part']
        out.append('\n**%s · %s**\n' % (s['part'], PART_TITLE.get(s['part'], '')))
    out.append('- %s' % s['title'])
out.append('\n---\n')

# 본문
seen = None
for s in secs:
    if s['part'] and s['part'] != seen:
        seen = s['part']
        out.append('\n---\n')
        out.append('# %s\n' % s['part'])
        out.append('## %s\n' % PART_TITLE.get(s['part'], ''))
        out.append('\n---\n')
    out.append('\n# %s\n' % s['title'])
    out.append(s['body'])
    out.append('\n')

doc = '\n'.join(out)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(doc)
print('wrote %s  %d자 / %d개 절' % (OUT, len(doc), len(secs)))
