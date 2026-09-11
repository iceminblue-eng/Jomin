#!/usr/bin/env bash
# 네이버 플레이스 진단 산출물 일괄 생성: 리포트.md + 카드.md → Word + Excel
# 사용법: bash tools/naver_place_build.sh 네이버플레이스/03-분석보고서/브랜드-YYYYMMDD.md 네이버플레이스/02-비교브랜드/브랜드.md
set -euo pipefail
REPORT="$1"; CARD="$2"
DIR="$(dirname "$REPORT")/산출물"; BASE="$(basename "$REPORT" .md)"
NAME="${BASE%-*}"; DATE="${BASE##*-}"
mkdir -p "$DIR"
DOCX="$DIR/${NAME}-진단리포트-${DATE}.docx"
XLSX="$DIR/${NAME}-보완기입시트-${DATE}.xlsx"
node tools/naver_place_docx.js "$REPORT" "$DOCX"
python3 tools/fix_opc.py "$DOCX"
python3 - "$DOCX" <<'PY'
# docx-js 8 은 fontTable.xml 을 넣지만 document.xml.rels 에 관계를 쓰지 않는다 → 관계 추가
import sys, zipfile, shutil
p = sys.argv[1]; z = zipfile.ZipFile(p); tmp = p + ".tmp"
REL = '<Relationship Id="rIdFontTable" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>'
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
    for info in z.infolist():
        data = z.read(info.filename)
        if info.filename == "word/_rels/document.xml.rels" and b"fontTable" not in data and "word/fontTable.xml" in z.namelist():
            data = data.replace(b"</Relationships>", REL.encode() + b"</Relationships>")
        out.writestr(info, data)
z.close(); shutil.move(tmp, p)
PY
python3 tools/naver_place_xlsx.py "$REPORT" "$CARD" "$XLSX"
echo "→ $DOCX"; echo "→ $XLSX"
