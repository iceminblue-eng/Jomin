# -*- coding: utf-8 -*-
"""단행본 원고 마크다운 → 조판용 JSON 블록 스트림."""
import re, json, sys

def runs(t):
    """**굵게** · *기울임* · `코드` 를 런 배열로."""
    out, i = [], 0
    pat = re.compile(r'\*\*(.+?)\*\*|(?<!\*)\*(?!\s)([^*]+?)(?<!\s)\*(?!\*)|`([^`]+)`')
    for m in pat.finditer(t):
        if m.start() > i:
            out.append({'t': t[i:m.start()]})
        if m.group(1) is not None:
            out.append({'t': m.group(1), 'b': True})
        elif m.group(2) is not None:
            out.append({'t': m.group(2), 'i': True})
        else:
            out.append({'t': m.group(3), 'c': True})
        i = m.end()
    if i < len(t):
        out.append({'t': t[i:]})
    return out or [{'t': ''}]

def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

def parse(md):
    L = md.split('\n')
    blocks, i, n = [], 0, len(L)
    while i < n:
        s = L[i].strip()
        if not s:
            i += 1; continue

        if s.startswith('```'):
            i += 1; buf = []
            while i < n and not L[i].strip().startswith('```'):
                buf.append(L[i]); i += 1
            i += 1
            blocks.append({'k': 'pre', 'lines': buf})
            continue

        if re.fullmatch(r'-{3,}', s):
            blocks.append({'k': 'hr'}); i += 1; continue

        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            blocks.append({'k': 'h', 'lvl': len(m.group(1)), 'runs': runs(m.group(2).strip())})
            i += 1; continue

        if s.startswith('|'):
            rows = []
            while i < n and L[i].strip().startswith('|'):
                rows.append(cells(L[i])); i += 1
            if len(rows) < 2:
                continue
            head = rows[0]
            has_head = any(c for c in head)
            body = [[runs(c) for c in r] for r in rows[2:]]
            blocks.append({'k': 'table',
                           'head': [runs(c) for c in head] if has_head else None,
                           'rows': body,
                           'cols': max([len(head)] + [len(r) for r in rows[2:]] or [1])})
            continue

        if s.startswith('>'):
            buf = []
            while i < n and L[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', L[i])); i += 1
            txt = '\n'.join(buf).strip()
            big = txt.startswith('###')
            txt = re.sub(r'^#{1,4}\s*', '', txt, flags=re.M)
            paras = [p.strip() for p in txt.split('\n') if p.strip()]
            blocks.append({'k': 'quote', 'big': big, 'paras': [runs(p) for p in paras]})
            continue

        if re.match(r'^[-*]\s+', s):
            items = []
            while i < n and re.match(r'^[-*]\s+', L[i].strip()):
                items.append(runs(re.sub(r'^[-*]\s+', '', L[i].strip()))); i += 1
            blocks.append({'k': 'ul', 'items': items})
            continue

        if re.match(r'^\d+\.\s+', s):
            items = []
            while i < n and re.match(r'^\d+\.\s+', L[i].strip()):
                cur = re.sub(r'^\d+\.\s+', '', L[i].strip()); i += 1
                while i < n and L[i].startswith('   ') and L[i].strip() \
                        and not re.match(r'^\d+\.', L[i].strip()):
                    cur += ' ' + L[i].strip(); i += 1
                items.append(runs(cur))
            blocks.append({'k': 'ol', 'items': items})
            continue

        buf = [s]; i += 1
        while i < n and L[i].strip() and not re.match(
                r'^(#{1,4}\s|\||>|[-*]\s|\d+\.\s|```|-{3,}$)', L[i].strip()):
            buf.append(L[i].strip()); i += 1
        blocks.append({'k': 'p', 'runs': runs(' '.join(buf))})

    return blocks

if __name__ == '__main__':
    md = open(sys.argv[1], encoding='utf-8').read()
    b = parse(md)
    json.dump(b, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
    from collections import Counter
    print('%d blocks' % len(b), dict(Counter(x['k'] for x in b)))
