const fs = require('fs');
const D = require(process.env.DOCX_LIB || 'docx');
const {Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
       BorderStyle, ShadingType, AlignmentType, HeadingLevel, PageNumber,
       Header, Footer, LevelFormat, convertMillimetersToTwip} = D;

const SERIF = '바탕', SANS = '맑은 고딕', MONO = 'Consolas';
const INK = '1A1A1A', MUTED = '4A4A4A', RULE = 'BFBFBF', HEADBG = 'EFEFEF', BOXBG = 'F7F7F7';

// A4, 좌우 25mm / 상하 25mm
const PAGE_W = 11906, MARGIN = convertMillimetersToTwip(25);
const CONTENT = PAGE_W - MARGIN * 2;          // 9070

function colWidths(n) {
  const pct = n === 2 ? [0.30, 0.70]
            : n === 3 ? [0.22, 0.39, 0.39]
            : n === 4 ? [0.16, 0.28, 0.28, 0.28]
            : Array(n).fill(1 / n);
  const w = pct.map(p => Math.floor(CONTENT * p));
  w[n - 1] = CONTENT - w.slice(0, n - 1).reduce((a, b) => a + b, 0);
  return w;
}

function mkRuns(rs, o = {}) {
  return (rs || [{t: ''}]).map(r => new TextRun({
    text: r.t,
    bold: !!r.b || !!o.bold,
    italics: !!r.i,
    font: r.c ? MONO : (o.font || SERIF),
    size: o.size || 21,                        // half-points → 10.5pt
    color: o.color || INK,
  }));
}

const border = (sz = 4, color = RULE) => ({style: BorderStyle.SINGLE, size: sz, color});
const CELL_BORDERS = {top: border(), bottom: border(), left: border(), right: border()};

function cellPara(rs, o) {
  return new Paragraph({
    children: mkRuns(rs, o),
    spacing: {line: 288, before: 40, after: 40},
  });
}

function mkTable(b) {
  const n = b.cols, w = colWidths(n);
  const rows = [];
  if (b.head) {
    const h = b.head.slice(); while (h.length < n) h.push([{t: ''}]);
    rows.push(new TableRow({
      tableHeader: true,
      children: h.map((c, j) => new TableCell({
        width: {size: w[j], type: WidthType.DXA},
        shading: {type: ShadingType.CLEAR, fill: HEADBG, color: 'auto'},
        borders: CELL_BORDERS,
        margins: {top: 60, bottom: 60, left: 100, right: 100},
        children: [cellPara(c, {bold: true, font: SANS, size: 19})],
      })),
    }));
  }
  for (const r0 of b.rows) {
    const r = r0.slice(); while (r.length < n) r.push([{t: ''}]);
    rows.push(new TableRow({
      children: r.slice(0, n).map((c, j) => new TableCell({
        width: {size: w[j], type: WidthType.DXA},
        borders: CELL_BORDERS,
        margins: {top: 60, bottom: 60, left: 100, right: 100},
        children: [cellPara(c, {size: 19})],
      })),
    }));
  }
  return new Table({columnWidths: w, width: {size: CONTENT, type: WidthType.DXA}, rows});
}

function mkPre(b) {
  const lines = b.lines.length ? b.lines : [''];
  return new Table({
    columnWidths: [CONTENT],
    width: {size: CONTENT, type: WidthType.DXA},
    rows: [new TableRow({children: [new TableCell({
      width: {size: CONTENT, type: WidthType.DXA},
      shading: {type: ShadingType.CLEAR, fill: BOXBG, color: 'auto'},
      borders: CELL_BORDERS,
      margins: {top: 140, bottom: 140, left: 160, right: 160},
      children: lines.map(l => new Paragraph({
        children: [new TextRun({text: l.replace(/\t/g, '    '), font: MONO, size: 17, color: MUTED})],
        spacing: {line: 260, before: 0, after: 0},
      })),
    })]})],
  });
}

const H = {
  1: {size: 38, font: SANS, before: 0,   after: 360, level: HeadingLevel.HEADING_1},
  2: {size: 28, font: SANS, before: 440, after: 200, level: HeadingLevel.HEADING_2},
  3: {size: 24, font: SANS, before: 340, after: 150, level: HeadingLevel.HEADING_3},
  4: {size: 22, font: SERIF, before: 260, after: 120, level: HeadingLevel.HEADING_4},
};

function build(blocks) {
  const out = [];
  let firstH1 = true;
  blocks.forEach((b, idx) => {
    const prev = blocks[idx - 1], next = blocks[idx + 1];
    switch (b.k) {
      case 'h': {
        const c = H[b.lvl];
        out.push(new Paragraph({
          children: mkRuns(b.runs, {bold: true, font: c.font, size: c.size}),
          heading: c.level,
          pageBreakBefore: b.lvl === 1 && !firstH1,
          spacing: {before: c.before, after: c.after, line: 300},
          keepNext: true,
        }));
        if (b.lvl === 1) firstH1 = false;
        break;
      }
      case 'p':
        out.push(new Paragraph({
          children: mkRuns(b.runs),
          spacing: {line: 340, after: 140},
          alignment: AlignmentType.JUSTIFIED,
        }));
        break;
      case 'quote':
        b.paras.forEach((p, k) => out.push(new Paragraph({
          children: mkRuns(p, b.big ? {bold: true, size: 23} : {size: 21, color: MUTED}),
          indent: {left: 360},
          border: {left: {style: BorderStyle.SINGLE, size: 12, color: RULE, space: 12}},
          spacing: {line: 330, before: k === 0 ? 160 : 0,
                    after: k === b.paras.length - 1 ? 180 : 60},
        })));
        break;
      case 'ul':
        b.items.forEach(it => out.push(new Paragraph({
          children: mkRuns(it), bullet: {level: 0},
          spacing: {line: 330, after: 90},
        })));
        break;
      case 'ol':
        b.items.forEach(it => out.push(new Paragraph({
          children: mkRuns(it), numbering: {reference: 'num', level: 0},
          spacing: {line: 330, after: 90},
        })));
        break;
      case 'table':
        out.push(mkTable(b));
        out.push(new Paragraph({children: [], spacing: {after: 200}}));
        break;
      case 'pre':
        out.push(mkPre(b));
        out.push(new Paragraph({children: [], spacing: {after: 200}}));
        break;
      case 'hr':
        // 제목 앞뒤의 구분선은 생략 — 제목 간격이 이미 구분한다
        if (prev && next && prev.k !== 'h' && next.k !== 'h') {
          out.push(new Paragraph({
            children: [], spacing: {before: 120, after: 200},
            border: {bottom: {style: BorderStyle.SINGLE, size: 6, color: RULE, space: 6}},
          }));
        }
        break;
    }
  });
  return out;
}

const blocks = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const children = build(blocks);

const doc = new Document({
  creator: '조민',
  title: '관리자론 — 헤어살롱 편',
  description: '미용 시장 관리자 운용 바이블',
  numbering: {config: [{
    reference: 'num',
    levels: [{level: 0, format: LevelFormat.DECIMAL, text: '%1.',
              alignment: AlignmentType.START,
              style: {paragraph: {indent: {left: 480, hanging: 300}}}}],
  }]},
  styles: {default: {document: {run: {font: SERIF, size: 21, color: INK}}}},
  sections: [{
    properties: {page: {size: {width: PAGE_W, height: 16838},
                        margin: {top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN}}},
    headers: {default: new Header({children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: [new TextRun({text: '관리자론 — 헤어살롱 편', font: SANS, size: 16, color: '8A8A8A'})],
    })]})},
    footers: {default: new Footer({children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({children: [PageNumber.CURRENT], font: SANS, size: 17, color: '8A8A8A'})],
    })]})},
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(process.argv[3], buf);
  console.log('wrote', process.argv[3], (buf.length / 1024 / 1024).toFixed(2) + 'MB',
              '/', children.length, 'elements');
});
