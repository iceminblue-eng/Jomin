#!/usr/bin/env bash
# 원고 → 전체 산출물 빌드 (3권 체제)
set -e
cd "$(dirname "$0")/.."
SP="${SCRATCH:-/tmp/gwanrijaron}"
mkdir -p "$SP" build

echo "[1/4] 워크북 리더 (세 권 통합)"
python3 tools/build_reader.py build/reader.html

echo "[2/4] 권별 단행본 원고"
for v in 1 2 3; do python3 tools/build_manuscript.py $v "build/${v}권/관리자론-${v}.md"; done

echo "[3/4] 권별 Word 원고"
for v in 1 2 3; do
  python3 tools/md_to_json.py "build/${v}권/관리자론-${v}.md" "$SP/book${v}.json" > /dev/null
  node tools/make_docx.js "$SP/book${v}.json" "build/${v}권/관리자론-${v}.docx"
  python3 tools/fix_opc.py "build/${v}권/관리자론-${v}.docx"   # OPC 파트 순서 교정
done

echo "[4/4] 권별 PDF"
for v in 1 2 3; do python3 tools/build_print.py "build/${v}권/관리자론-${v}.md" "build/${v}권/인쇄.html"; done
node tools/pdf.js

echo "[+] 편집자 인수인계 대조표"
python3 tools/build_print.py docs/재구성-대조표.md build/편집자/인쇄.html
python3 tools/md_to_json.py docs/재구성-대조표.md "$SP/report.json" > /dev/null
node tools/make_docx.js "$SP/report.json" "build/편집자/관리자론-재구성-대조표.docx"
python3 tools/fix_opc.py "build/편집자/관리자론-재구성-대조표.docx"
cp docs/재구성-대조표.md   build/편집자/관리자론-재구성-대조표.md
cp docs/재구성-대조표.html build/편집자/관리자론-재구성-대조표.html

python3 tools/make_bundle.py
ls -la build/*/
