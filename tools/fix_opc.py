# -*- coding: utf-8 -*-
"""docx-js 출력의 OPC 패키지 순서를 바로잡는다.
   [Content_Types].xml 을 첫 항목으로 두고 빈 디렉터리 엔트리를 제거한다."""
import zipfile, shutil, sys, os

def fix(path):
    src = zipfile.ZipFile(path)
    names = [n for n in src.namelist() if not n.endswith('/')]
    if '[Content_Types].xml' not in names:
        raise SystemExit('[Content_Types].xml 없음: ' + path)
    order = ['[Content_Types].xml'] + [n for n in names if n != '[Content_Types].xml']
    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as out:
        for n in order:
            out.writestr(src.getinfo(n), src.read(n))
    src.close()
    shutil.move(tmp, path)
    print('repacked %s  %d parts  %.2fMB'
          % (os.path.basename(path), len(order), os.path.getsize(path) / 1048576))

if __name__ == '__main__':
    for p in sys.argv[1:]:
        fix(p)
