#!/usr/bin/env node
/**
 * 네이버 플레이스 리포트/카드/기준 문서(마크다운) → Word(.docx)
 *
 * 사용법:
 *   node tools/naver_place_docx.js 입력.md 출력.docx
 *   node tools/naver_place_docx.js 입력.md 출력.docx --landscape   # 표가 넓은 리포트용
 *
 * 지원 문법: # ~ #### 제목, 표(| a | b |), 목록(- / 1.), 인용(>), 코드 블록(```), 구분선(---),
 *           **굵게**, `코드`, _기울임_.  이 폴더의 문서만 대상으로 하므로 범용 변환기는 아니다.
 * 출력 후 tools/fix_opc.py 로 OPC 순서를 교정해야 LibreOffice에서도 열린다.
 */
const fs = require("fs");
const path = require("path");
const docx = require(path.join(__dirname, "node_modules", "docx", "build", "index.cjs"));
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, HeadingLevel, BorderStyle, ShadingType, LevelFormat, PageOrientation,
  Header, Footer, PageNumber, TabStopType, ImageRun,
} = docx;

const [,, inPath, outPath, ...flags] = process.argv;
if (!inPath || !outPath) {
  console.error("사용법: node tools/naver_place_docx.js 입력.md 출력.docx [--landscape]");
  process.exit(1);
}
const landscape = flags.includes("--landscape");
const FONT = "맑은 고딕";
const MONO = "Consolas";
const BODY = 20;        // half-points (10pt)
const TABLE = 17;       // 8.5pt
const A4 = { width: 11906, height: 16838 };
const MARGIN = 1134;    // 2cm
const pageW = (landscape ? A4.height : A4.width) - MARGIN * 2;

// ---------------------------------------------------------------- inline
function inline(text, base = {}) {
  // **bold**, `code`, _italic_ (단어 경계) 처리
  const runs = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|(?<![\w가-힣])_[^_]+_(?![\w가-힣]))/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) runs.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) runs.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) runs.push(new TextRun({ text: t.slice(1, -1), font: MONO, ...base, size: (base.size || BODY) - 1 }));
    else runs.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) runs.push(new TextRun({ text: text.slice(last), ...base }));
  return runs.length ? runs : [new TextRun({ text: "", ...base })];
}

// ---------------------------------------------------------------- block parse
function parse(md) {
  const lines = md.replace(/\r/g, "").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; blocks.push({ t: "code", lines: buf }); continue;
    }
    if (/^\s*\|/.test(l)) {
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) {
        const cells = lines[i].trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, "|"));
        if (!cells.every(c => /^:?-{2,}:?$/.test(c) || c === "")) rows.push(cells);
        i++;
      }
      blocks.push({ t: "table", rows }); continue;
    }
    if (/^#{1,6}\s/.test(l)) { const m = l.match(/^(#+)\s+(.*)$/); blocks.push({ t: "h", level: m[1].length, text: m[2].trim() }); i++; continue; }
    if (/^\s*>/.test(l)) {
      const buf = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) { buf.push(lines[i].replace(/^\s*>\s?/, "")); i++; }
      // 인용 안 표는 지원하지 않음 — 줄 그대로
      blocks.push({ t: "quote", text: buf.join(" ").trim() });
      continue;
    }
    if (/^\s*[-*]\s+/.test(l)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        const indent = lines[i].match(/^(\s*)/)[1].length;
        items.push({ level: indent >= 2 ? 1 : 0, text: lines[i].replace(/^\s*[-*]\s+/, "") });
        i++;
      }
      blocks.push({ t: "ul", items }); continue;
    }
    if (/^\s*\d+\.\s+/.test(l)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*\d+\.\s+/, "")); i++; }
      blocks.push({ t: "ol", items }); continue;
    }
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(l)) { blocks.push({ t: "hr" }); i++; continue; }
    if (/^\s*!\[.*\]\([^()]+\)\s*$/.test(l)) {
      const m = l.match(/^\s*!\[(.*)\]\(([^()]+)\)\s*$/);   // 캡션 안의 [ ] 허용, 경로에는 괄호 없음
      blocks.push({ t: "img", caption: m[1], src: m[2] }); i++; continue;
    }
    if (l.trim() === "") { i++; continue; }
    const buf = [l.trim()];
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !/^(\s*\||#{1,6}\s|\s*>|\s*[-*]\s|\s*\d+\.\s|```|\s*-{3,}\s*$|\s*!\[)/.test(lines[i])) buf.push(lines[i++].trim());
    blocks.push({ t: "p", text: buf.join(" ") });
  }
  return blocks;
}

// ---------------------------------------------------------------- render
const GREY = "F2F2F2", HEAD = "DDE5F0", LINE = "BFBFBF";
const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };

function table(rows) {
  const ncol = Math.max(...rows.map(r => r.length));
  // 열 너비: 각 열 최대 글자수(상한 40)에 비례
  const lens = Array.from({ length: ncol }, (_, c) => Math.min(40, Math.max(4, ...rows.map(r => (r[c] || "").replace(/\*\*|`/g, "").length))));
  const sum = lens.reduce((a, b) => a + b, 0);
  const widths = lens.map(x => Math.floor(pageW * x / sum));
  widths[ncol - 1] += pageW - widths.reduce((a, b) => a + b, 0);
  const trs = rows.map((r, ri) => new TableRow({
    tableHeader: ri === 0,
    cantSplit: true,
    children: Array.from({ length: ncol }, (_, c) => new TableCell({
      width: { size: widths[c], type: WidthType.DXA },
      borders,
      shading: ri === 0 ? { type: ShadingType.CLEAR, fill: HEAD, color: "auto" } : undefined,
      margins: { top: 40, bottom: 40, left: 70, right: 70 },
      children: [new Paragraph({ spacing: { before: 0, after: 0 }, children: inline(r[c] || "", { size: TABLE, bold: ri === 0 || undefined }) })],
    })),
  }));
  return new Table({ width: { size: pageW, type: WidthType.DXA }, columnWidths: widths, rows: trs });
}

function pngSize(buf) {
  // PNG IHDR: width/height at byte 16/20 (big-endian)
  if (buf.length > 24 && buf.toString("ascii", 1, 4) === "PNG") return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  return { w: 800, h: 600 };
}

function render(blocks) {
  const out = [];
  let firstH1 = true;
  for (const b of blocks) {
    switch (b.t) {
      case "h": {
        const text = b.text.replace(/\*\*/g, "");
        if (b.level === 1 && firstH1) { firstH1 = false; out.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text, bold: true, size: 36 })], spacing: { after: 200 } })); break; }
        const lvl = b.level <= 2 ? HeadingLevel.HEADING_1 : b.level === 3 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3;
        out.push(new Paragraph({ heading: lvl, children: inline(text, { bold: true, size: b.level <= 2 ? 26 : b.level === 3 ? 23 : 21 }), spacing: { before: b.level <= 2 ? 320 : 220, after: 100 } }));
        break;
      }
      case "p": out.push(new Paragraph({ children: inline(b.text, { size: BODY }), spacing: { after: 120 } })); break;
      case "quote": out.push(new Paragraph({
        children: inline(b.text, { size: BODY - 1, color: "444444" }),
        indent: { left: 360 }, spacing: { after: 140 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: "9AA8B8", space: 8 } },
        shading: { type: ShadingType.CLEAR, fill: "F7F9FB", color: "auto" },
      })); break;
      case "ul": for (const it of b.items) out.push(new Paragraph({ children: inline(it.text, { size: BODY }), numbering: { reference: "bul", level: it.level }, spacing: { after: 60 } })); break;
      case "ol": for (const it of b.items) out.push(new Paragraph({ children: inline(it, { size: BODY }), numbering: { reference: "num", level: 0 }, spacing: { after: 60 } })); break;
      case "code": for (const l of b.lines) out.push(new Paragraph({ children: [new TextRun({ text: l || " ", font: MONO, size: BODY - 2 })], shading: { type: ShadingType.CLEAR, fill: GREY, color: "auto" }, spacing: { after: 0 }, indent: { left: 200 } })); out.push(new Paragraph({ spacing: { after: 100 } })); break;
      case "hr": out.push(new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE } }, spacing: { before: 120, after: 200 } })); break;
      case "table": out.push(table(b.rows)); out.push(new Paragraph({ spacing: { after: 120 } })); break;
      case "img": {
        const file = path.resolve(path.dirname(inPath), b.src);
        if (!fs.existsSync(file)) { out.push(new Paragraph({ children: [new TextRun({ text: `[이미지 없음: ${b.src}]`, color: "C00000", size: BODY })] })); break; }
        const data = fs.readFileSync(file);
        const dim = pngSize(data);
        const maxW = Math.floor(pageW / 15), maxH = 560;       // DXA → px (96dpi)
        let w = dim.w, h = dim.h;
        const k = Math.min(maxW / w, maxH / h, 1);
        w = Math.round(w * k); h = Math.round(h * k);
        out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
          children: [new ImageRun({ type: "png", data, transformation: { width: w, height: h } })] }));
        if (b.caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: inline(b.caption, { size: BODY - 2, color: "595959", italics: true }) }));
        break;
      }
    }
  }
  return out;
}

const md = fs.readFileSync(inPath, "utf8");
const blocks = parse(md);
const title = (blocks.find(b => b.t === "h" && b.level === 1) || { text: path.basename(inPath, ".md") }).text.replace(/\*\*/g, "");

const doc = new Document({
  creator: "네이버 플레이스 전략 기획 시스템",
  title,
  styles: {
    default: { document: { run: { font: FONT, size: BODY }, paragraph: { spacing: { line: 300 } } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 36, bold: true, color: "1F3864" }, paragraph: { spacing: { after: 200 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 26, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 320, after: 100 }, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "1F3864", space: 2 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 23, bold: true, color: "2E5496" }, paragraph: { spacing: { before: 220, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 21, bold: true }, paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bul", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 900, hanging: 240 } } } },
      ] },
      { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 300 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: landscape ? { width: A4.width, height: A4.height, orientation: PageOrientation.LANDSCAPE } : { width: A4.width, height: A4.height },
        margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      },
    },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: `네이버 플레이스 전략 기획 시스템 · ${title}`, size: 16, color: "808080" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "808080" })] })] }) },
    children: render(blocks),
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  console.log(`wrote ${outPath} (${(buf.length / 1024).toFixed(0)} KB, ${blocks.length} blocks)`);
});
