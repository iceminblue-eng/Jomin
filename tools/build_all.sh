#!/usr/bin/env bash
# 원고 → 전체 산출물 빌드
set -e
cd "$(dirname "$0")/.."
SP="${SCRATCH:-/tmp/gwanrijaron}"
mkdir -p "$SP" build

echo "[1/6] 읽기용 HTML (워크북 리더)"
python3 tools/build_reader.py build/reader.html

echo "[2/6] 단행본 원고 (단일 마크다운)"
python3 tools/build_manuscript.py "build/관리자론-헤어살롱편-원고.md"

echo "[3/6] 인쇄용 HTML"
python3 tools/build_print.py

echo "[4/6] Word 원고 (.docx)"
python3 tools/md_to_json.py "build/관리자론-헤어살롱편-원고.md" "$SP/book.json"
node "$SP/make_docx.js" "$SP/book.json" "build/관리자론-헤어살롱편.docx"
python3 tools/fix_opc.py "build/관리자론-헤어살롱편.docx"   # OPC 파트 순서 교정

echo "[5/6] PDF"
node "$SP/pdf.js"

echo "[6/6] 배포용 묶음"
python3 tools/make_bundle.py

ls -la build/
