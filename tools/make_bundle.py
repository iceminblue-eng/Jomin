# -*- coding: utf-8 -*-
"""배포용 묶음(zip) — 권별 완성본 + 장별 원고 + 작업 문서."""
import zipfile, os, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
Z = sys.argv[1] if len(sys.argv) > 1 else 'build/관리자론-3부작.zip'
VN = {1: '1권 기준과 진단', 2: '2권 권한과 운영', 3: '3권 확장과 양성'}

if os.path.exists(Z): os.remove(Z)
with zipfile.ZipFile(Z, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for v in (1, 2, 3):
        for ext in ('pdf', 'docx', 'md'):
            p = 'build/%d권/관리자론-%d.%s' % (v, v, ext)
            if os.path.exists(p):
                z.write(p, '%s/관리자론-%d.%s' % (VN[v], v, ext))
    z.write('build/reader.html', '워크북-리더(세 권 통합).html')
    import os.path
    for ext in ('pdf', 'docx', 'md', 'html'):
        p2 = 'build/편집자/관리자론-재구성-대조표.%s' % ext
        if os.path.exists(p2):
            z.write(p2, '편집자 인수인계/관리자론-재구성-대조표.%s' % ext)
    for f in sorted(glob.glob('원고/[123]권/*.md')):
        z.write(f, '원고(절별)/' + f.split('/', 1)[1])
    for f in ['docs/책-구성안.md', 'docs/집필-가이드.md']:
        if os.path.exists(f): z.write(f, '작업문서/' + os.path.basename(f))
print('wrote %s  %d개 파일  %.1fMB'
      % (Z, len(zipfile.ZipFile(Z).namelist()), os.path.getsize(Z) / 1048576))
