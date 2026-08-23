# -*- coding: utf-8 -*-
"""배포용 묶음(zip) 생성 — 완성본 + 장별 원고 + 작업 문서."""
import zipfile, os, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
Z = sys.argv[1] if len(sys.argv) > 1 else 'build/관리자론-헤어살롱편.zip'

TOP = [
    ('build/관리자론-헤어살롱편.pdf',     '관리자론-헤어살롱편.pdf'),
    ('build/관리자론-헤어살롱편.docx',    '관리자론-헤어살롱편.docx'),
    ('build/관리자론-헤어살롱편-원고.md', '관리자론-헤어살롱편-원고.md'),
    ('build/reader.html',                 '워크북-리더.html'),
]

if os.path.exists(Z):
    os.remove(Z)
with zipfile.ZipFile(Z, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for src, dst in TOP:
        z.write(src, dst)
    for f in sorted(glob.glob('원고/*/*.md')):
        z.write(f, '원고(장별)/' + f.split('/', 1)[1])
    for f in ['docs/책-구성안.md', 'docs/집필-가이드.md']:
        z.write(f, '작업문서/' + os.path.basename(f))

print('wrote %s  %d개 파일  %.1fMB'
      % (Z, len(zipfile.ZipFile(Z).namelist()), os.path.getsize(Z) / 1048576))
