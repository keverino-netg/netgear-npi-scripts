// Zenith ENG Schedule - 4-slide Orbi-branded deck.
// Follows the netgear-slides L2/L3 content-slide anatomy and netgear-brand palette.

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const PptxGenJS = require('pptxgenjs');
const AdmZip = require('adm-zip');

const HERE = __dirname;
const BUILD = process.env.ZENITH_BUILD_DIR || path.join(HERE, 'build');
const MEASURE = path.join(HERE, 'measure.py');
const C = require(path.join(HERE, 'content.js'));

const A = JSON.parse(fs.readFileSync(path.join(BUILD, 'assets.json'), 'utf8'));
const OUT = path.join(BUILD, 'Zenith_ENG_Schedule.pptx');

// ---------- canvas constants (LAYOUT_WIDE) ----------
const SLIDE_W = 13.333, SLIDE_H = 7.5;
const BAR_W = 0.444, BAR_X = SLIDE_W - BAR_W, BAR_H = SLIDE_H;
const MARGIN_X = 0.436;
const CONTENT_W = 12.154;
const CONTENT_R = MARGIN_X + CONTENT_W;      // 12.590
const CONTENT_FLOOR = 6.86;                  // lowest y any content may reach

// ---------- brand (Orbi) ----------
const ORBI = '1E96FC';
const NG = { white: 'FFFFFF', gray1: 'F1F5F9', gray2: 'E2E8F0', gray4: '94A3B8',
             gray5: '64748B', gray6: '2B3749', blue: '002FFF' };
const FONT = 'Outfit';

// ---------- type scale ----------
const PTS = 72, LS = 1.2;
const EYEBROW_FZ = 13, TITLE_FZ = 32;
const EYEBROW_Y = 0.193, TITLE_Y = 0.580, TITLE_W = 11.467;
const HBAR_W = 1.1145, HBAR_H = 0.0575, HBAR_GAP = 0.08;

// PowerPoint's lineSpacingMultiple scales the FONT'S NATURAL line height, not the
// point size. Outfit reports ascent 1000 / descent -260 / gap 0 per 1000 em, so one
// single-spaced line occupies 1.26 em. Every height calculation must use this.
const NAT_LH = 1.26;
// Small extra allowance for renderer cell insets when growing table rows.
const TABLE_CALIB = 1.02;

// ---------- accurate text measurement via real Outfit metrics ----------
const _mcache = new Map();
function measure(jobs) {
  const todo = jobs.filter((j) => !_mcache.has(JSON.stringify(j)));
  if (todo.length) {
    const res = JSON.parse(execSync(`python3 ${JSON.stringify(MEASURE)}`,
      { input: JSON.stringify(todo), encoding: 'utf8', maxBuffer: 1 << 24,
        env: { ...process.env, ZENITH_BUILD_DIR: BUILD } }));
    todo.forEach((j, i) => _mcache.set(JSON.stringify(j), res[i]));
  }
  return jobs.map((j) => _mcache.get(JSON.stringify(j)));
}
const lines = (text, pt, w_in, bold = false, safety) =>
  measure([{ op: 'lines', text, pt, w_in, bold, safety }])[0];
const textW = (text, pt, bold = false) =>
  measure([{ op: 'width', text, pt, bold }])[0];

const lineH = (pt, mult = 1.0) => (mult * NAT_LH * pt) / PTS;
// Tight box height: exactly lineH x lineCount, no buffer (Step 9 rule).
const boxH = (pt, n, mult = 1.0) => lineH(pt, mult) * n;

// ---------- shared slide chrome ----------
function chrome(slide, pageNo, titleThin, titleBold) {
  slide.addImage({ data: A.texture, x: 0, y: 0, w: SLIDE_W, h: SLIDE_H,
    sizing: { type: 'cover', w: SLIDE_W, h: SLIDE_H } });

  slide.addText(C.eyebrow, {
    x: MARGIN_X, y: EYEBROW_Y, w: 7.115, h: boxH(EYEBROW_FZ, 1, 1.0),
    fontSize: EYEBROW_FZ, bold: true, color: ORBI, fontFace: FONT,
    charSpacing: 1.33, valign: 'middle', margin: 0,
  });

  // The title box is bottom-anchored so the last line hugs the horizontal bar.
  // That means any under-estimate of the line height overflows UPWARDS into the
  // eyebrow, so the box carries a little headroom above the text.
  // Titles are a single regular weight - Kevin asked for no bold tail.
  const title = titleThin + titleBold;
  const tLines = lines(title, TITLE_FZ, TITLE_W, true);
  const titleH = boxH(TITLE_FZ, tLines) * 1.10;
  slide.addText(title,
    { x: MARGIN_X, y: TITLE_Y, w: TITLE_W, h: titleH,
      fontSize: TITLE_FZ, bold: false, color: NG.gray6,
      fontFace: FONT, valign: 'bottom',
      lineSpacingMultiple: 1.0, margin: 0 });

  const hBarY = TITLE_Y + titleH + HBAR_GAP;
  slide.addImage({ data: A.hbar, x: MARGIN_X, y: hBarY, w: HBAR_W, h: HBAR_H });

  slide.addImage({ data: A.vbar, x: BAR_X, y: 0, w: BAR_W, h: BAR_H });

  const CONF_W = 2.0;
  slide.addText('NETGEAR Confidential', {
    x: BAR_X - CONF_W - 0.47, y: 7.047, w: CONF_W, h: 0.333,
    fontSize: 10, color: NG.gray4, fontFace: FONT,
    align: 'right', valign: 'middle', margin: 0 });

  slide.addText(String(pageNo), {
    x: BAR_X, y: 7.067, w: BAR_W, h: 0.333,
    fontSize: 8, color: NG.gray6, fontFace: FONT,
    align: 'center', valign: 'middle', margin: 0 });

  return hBarY + HBAR_H;          // bottom of the header block
}

// ---------- column auto-sizing ----------
// Columns marked {fit:true} are widened to hold their widest single line, so
// short data like "Duration" or "10/16/2026" never wraps - not even by one
// character. Remaining width is shared between the flexible text columns in
// proportion to their weight.
const CELL_PAD = 0.10;
// Generous slack on fitted columns. PowerPoint's own text layout differs
// slightly from the measured advance widths, and a single character dropping to
// a second line is far more visible than a slightly wide column.
const FIT_SLACK = 0.24;
function sizeColumns(cols, rows, fz, hfz, totalW) {
  const sized = cols.map((c, ci) => {
    if (!c.fit) return { ...c };
    // Measure both weights so the column is safe regardless of row emphasis.
    const cand = [textW(c.label, hfz, true), textW(c.label, hfz, false)];
    rows.forEach((r) => {
      cand.push(textW(r[ci], fz, true), textW(r[ci], fz, false));
    });
    return { ...c, w: Math.max(...cand) + CELL_PAD * 2 + FIT_SLACK };
  });
  const fixed = sized.filter((c) => c.fit).reduce((s, c) => s + c.w, 0);
  const flex = sized.filter((c) => !c.fit);
  const weightSum = flex.reduce((s, c) => s + (c.weight || 1), 0);
  flex.forEach((c) => { c.w = (totalW - fixed) * ((c.weight || 1) / weightSum); });
  return sized.map((c) => ({ ...c, w: +c.w.toFixed(4) }));
}

// ---------- schedule table ----------
function tableMetrics({ cols, rows, bold, fz, hfz, vpad, ls, uniform = false,
                        safety }) {
  const lh = lineH(fz, ls);
  const jobs = [];
  rows.forEach((r, ri) => r.forEach((cell, ci) =>
    jobs.push({ op: 'lines', text: cell, pt: fz, w_in: cols[ci].w - CELL_PAD * 2,
                bold: bold[ri], safety })));
  const counts = measure(jobs);
  let perRow = rows.map((r, ri) =>
    Math.max(...r.map((_, ci) => counts[ri * cols.length + ci])));
  // Brand rule: every row in a table is the same height. Only a dense table
  // where uniformity would not fit the slide uses per-row heights.
  if (uniform) {
    const maxN = Math.max(...perRow);
    perRow = perRow.map(() => maxN);
  }
  const rowH = perRow.map((n) => +(lh * n + vpad).toFixed(4));
  const headerH = +(lineH(hfz, ls) + vpad).toFixed(4);
  const raw = headerH + rowH.reduce((s, h) => s + h, 0);
  return { rowH, headerH, raw, drawnH: raw * TABLE_CALIB };
}

function scheduleTable(slide, opts) {
  const { x, y, cols, rows, bold, fz, hfz, ls } = opts;
  const { rowH, headerH, drawnH } = tableMetrics(opts);

  const headerRow = cols.map((c) => ({
    text: c.label,
    options: { fill: { color: ORBI }, color: NG.white, bold: true, fontSize: hfz,
               fontFace: FONT, valign: 'middle', align: c.align || 'left',
               margin: [0, CELL_PAD, 0, CELL_PAD] },
  }));

  const body = rows.map((r, ri) => r.map((cell, ci) => ({
    text: cell,
    options: {
      fill: { color: ri % 2 === 0 ? NG.white : NG.gray1 },
      color: NG.gray6, bold: !!bold[ri], fontSize: fz, fontFace: FONT,
      valign: 'middle', align: cols[ci].align || 'left',
      lineSpacingMultiple: ls,
      margin: [0, CELL_PAD, 0, CELL_PAD],
      border: { type: 'solid', color: NG.gray2, pt: 0.75 },
    },
  })));

  slide.addTable([headerRow, ...body], {
    x, y, w: cols.reduce((s, c) => s + c.w, 0),
    colW: cols.map((c) => c.w),
    rowH: [headerH, ...rowH],
    border: { type: 'solid', color: NG.gray2, pt: 0.75 },
    fontFace: FONT,
  });

  return drawnH;
}

// ---------- callout card (Step 7b style) ----------
const CARD_ICON = 0.26, CARD_ICON_GAP = 0.10, CARD_LAB_GAP = 0.12;

function calloutMetrics(o) {
  const { w, label, text, labelFz = 13, bodyFz = 12, icon = true,
          pad = 0.20, bodyLS = 1.32 } = o;
  const txtW = w - pad * 2;
  const labW = icon ? txtW - CARD_ICON - CARD_ICON_GAP : txtW;
  const hasLabel = !!label;
  const labH = hasLabel ? boxH(labelFz, lines(label, labelFz, labW, true), 1.1) : 0;
  const gap = hasLabel ? CARD_LAB_GAP : 0;
  const bodyH = boxH(bodyFz, lines(text, bodyFz, txtW), bodyLS);
  return { pad, txtW, labW, labH, gap, hasLabel, bodyH, bodyLS,
           cardH: pad + labH + gap + bodyH + pad };
}

function calloutCard(slide, o) {
  const { x, y, w, label, text, labelFz = 13, bodyFz = 12, icon = true } = o;
  const m = calloutMetrics(o);
  const txtX = x + m.pad;

  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h: m.cardH,
    fill: { color: NG.white }, line: { color: NG.gray2, width: 0.75 }, rectRadius: 0.1,
  });

  let cy = y + m.pad;
  if (m.hasLabel) {
    if (icon) {
      slide.addImage({ data: A.icon_list, x: txtX, y: cy + (m.labH - CARD_ICON) / 2,
                       w: CARD_ICON, h: CARD_ICON });
    }
    slide.addText(label, {
      x: icon ? txtX + CARD_ICON + CARD_ICON_GAP : txtX, y: cy, w: m.labW, h: m.labH,
      fontSize: labelFz, bold: true, color: ORBI, fontFace: FONT,
      valign: 'middle', lineSpacingMultiple: 1.1, margin: 0 });
  }

  cy += m.labH + m.gap;
  slide.addText(text, {
    x: txtX, y: cy, w: m.txtW, h: m.bodyH,
    fontSize: bodyFz, color: NG.gray6, fontFace: FONT,
    valign: 'top', lineSpacingMultiple: m.bodyLS, margin: 0 });

  return m.cardH;
}

// ================= build =================
const pres = new PptxGenJS();
pres.layout = 'LAYOUT_WIDE';
const fits = [];

// Kevin asked for no bold anywhere in the table body, so the source's own row
// emphasis (section rows, Feature Complete, Launch) is not carried through.
const ROW_BOLD = false;

// Body-copy size ladder for callout cards, most generous first. The largest
// option that fits the available band wins - copy is never cut to fit (Rule 2).
const CARD_LADDER = [[13, 1.30], [13, 1.20], [12, 1.28], [12, 1.18], [12, 1.10],
                     [11, 1.22], [11, 1.12], [10, 1.20], [10, 1.10]];

// Two-column slide: schedule table on the left, callout card(s) on the right.
function splitSlide(pageNo, spec) {
  const s = pres.addSlide();
  const headBottom = chrome(s, pageNo, spec.titleThin, spec.titleBold);
  const bandTop = headBottom + 0.20;
  const bandH = CONTENT_FLOOR - bandTop;

  const GAP = 0.36, CARD_GAP = 0.22;
  const tableRows = spec.rows.map((r) => r.slice(0, 4));
  const tableBold = spec.rows.map(() => ROW_BOLD);

  // Size every column to its own content rather than forcing a fixed table
  // width. That keeps Duration and the dates on one line without stealing the
  // width Task Name needs, and the callout column takes whatever is left.
  const fitW = (label, ci) => {
    const cand = [textW(label, spec.fz, true), textW(label, spec.fz, false)];
    tableRows.forEach((r) => {
      cand.push(textW(r[ci], spec.fz, true), textW(r[ci], spec.fz, false));
    });
    return Math.max(...cand) + CELL_PAD * 2 + FIT_SLACK;
  };
  const wDur = fitW('Duration', 1), wStart = fitW('Start', 2), wFin = fitW('Finish', 3);
  const TBL_W = Math.min(spec.maxTableW || 7.6,
                         fitW('Task Name', 0) + wDur + wStart + wFin);
  const cols = [
    { label: 'Task Name', w: +(TBL_W - wDur - wStart - wFin).toFixed(4) },
    { label: 'Duration',  w: +wDur.toFixed(4),   align: 'center' },
    { label: 'Start',     w: +wStart.toFixed(4), align: 'left' },
    { label: 'Finish',    w: +wFin.toFixed(4),   align: 'left' },
  ];
  const cx = MARGIN_X + TBL_W + GAP, cw = CONTENT_R - cx;

  // Pick the largest card type size whose stack fits the band.
  let cardFz, cardLS, cardHs, cardsH;
  for (const [fz, ls] of CARD_LADDER) {
    cardHs = spec.callouts.map((co) => calloutMetrics({
      w: cw, label: co.label, text: co.text,
      labelFz: spec.labelFz, bodyFz: fz, bodyLS: ls }).cardH);
    cardsH = cardHs.reduce((a, b) => a + b, 0) + CARD_GAP * (cardHs.length - 1);
    cardFz = fz; cardLS = ls;
    if (cardsH <= bandH) break;
  }

  // Grow row padding so the table matches the card stack and fills the band,
  // rather than leaving a block of dead space underneath it.
  const VPAD_MIN = 0.10, VPAD_MAX = 0.26;
  const TBL_COMMON = { cols, rows: tableRows, bold: tableBold, fz: spec.fz,
                       hfz: spec.fz, ls: 1.12, uniform: true, safety: 0.995 };
  const base = tableMetrics({ ...TBL_COMMON, vpad: VPAD_MIN });
  // Aim to fill the band so the slide does not end in a block of dead space.
  const targetH = Math.min(bandH, Math.max(base.drawnH, cardsH, bandH * 0.94));
  const nRows = tableRows.length + 1;
  const vpad = Math.min(VPAD_MAX,
    VPAD_MIN + Math.max(0, (targetH / TABLE_CALIB - base.raw) / nRows));

  const tOpts = { ...TBL_COMMON, vpad };
  const tblH = tableMetrics(tOpts).drawnH;

  const blockH = Math.max(tblH, cardsH);
  const top = bandTop + Math.max(0, (bandH - blockH) / 2);

  // Centre each column within the block so leftover space reads as whitespace
  // rather than as a gap hanging off the bottom of the shorter column.
  scheduleTable(s, { ...tOpts, x: MARGIN_X, y: top + Math.max(0, (blockH - tblH) / 2) });

  let cy = top + Math.max(0, (blockH - cardsH) / 2);
  spec.callouts.forEach((co, i) => {
    calloutCard(s, { x: cx, y: cy, w: cw, label: co.label, text: co.text,
                     labelFz: spec.labelFz, bodyFz: cardFz, bodyLS: cardLS });
    cy += cardHs[i] + CARD_GAP;
  });

  fits.push({ slide: pageNo, bandTop, bandH, tblH, cardsH,
              bottom: top + blockH, floor: CONTENT_FLOOR,
              note: `card ${cardFz}pt/${cardLS} vpad ${vpad.toFixed(3)}` });
}

splitSlide(1, { ...C.slide1, maxTableW: 7.6, fz: 13, labelFz: 14 });
splitSlide(2, { ...C.slide2, maxTableW: 7.6, fz: 13, labelFz: 14 });

// ---------- Prominent closing banner ----------
// Solid Orbi fill with reversed copy, so the "additional milestones" note reads
// as the standout element on the final slide rather than another quiet card.
function closingBanner(slide, { x, y, w, text, fz = 13 }) {
  const PAD = 0.22, ICON = 0.36, ICON_GAP = 0.20;
  const txtX = x + PAD + ICON + ICON_GAP;
  const txtW = w - PAD * 2 - ICON - ICON_GAP;
  const n = lines(text, fz, txtW);
  const bodyH = boxH(fz, n, 1.25);
  const h = PAD + bodyH + PAD;

  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, fill: { color: ORBI }, line: { color: ORBI, width: 0.75 },
    rectRadius: 0.1,
  });
  slide.addImage({ data: A.icon_list_white, x: x + PAD,
                   y: y + (h - ICON) / 2, w: ICON, h: ICON });
  slide.addText(text, {
    x: txtX, y: y + PAD, w: txtW, h: bodyH,
    fontSize: fz, color: NG.white, fontFace: FONT,
    valign: 'top', lineSpacingMultiple: 1.25, margin: 0 });
  return h;
}

// ---------- Wide slide: full-width schedule table with a Description column ----------
function wideSlide(pageNo, spec) {
  const s = pres.addSlide();
  const headBottom = chrome(s, pageNo, spec.titleThin, spec.titleBold);
  const bandTop = headBottom + 0.22;
  const bandH = CONTENT_FLOOR - bandTop;

  const rows = spec.rows.map((r) => [r[0], r[1], r[2], r[3], r[5]]);
  const bold = spec.rows.map(() => ROW_BOLD);

  // Reserve space for the closing banner first, if this slide carries one.
  let bannerH = 0;
  if (spec.closingNote) {
    const PAD = 0.22, ICON = 0.36, ICON_GAP = 0.20;
    const txtW = CONTENT_W - PAD * 2 - ICON - ICON_GAP;
    bannerH = PAD * 2 + boxH(13, lines(spec.closingNote, 13, txtW), 1.25);
  }
  const BANNER_GAP = 0.26;
  const tableBandH = bandH - (bannerH ? bannerH + BANNER_GAP : 0);

  // Largest type size whose table fits, with padding grown to fill the band.
  const VPAD_FLOOR = 0.075, VPAD_MAX = 0.30;
  let FZ, cols, vpad;
  for (const fz of [15, 14, 13, 12, 11, 10]) {
    const c = sizeColumns([
      { label: 'Task Name',   weight: 1 },
      { label: 'Duration',    align: 'center', fit: true },
      { label: 'Start',       align: 'left',   fit: true },
      { label: 'Finish',      align: 'left',   fit: true },
      { label: 'Description', weight: 1.9 },
    ], rows, fz, fz + 1, CONTENT_W);
    const probe = tableMetrics({ cols: c, rows, bold, fz, hfz: fz + 1,
                                 vpad: 0, ls: 1.08 });
    const v = (tableBandH / TABLE_CALIB - probe.raw) / (rows.length + 1);
    FZ = fz; cols = c; vpad = Math.max(VPAD_FLOOR, Math.min(v, VPAD_MAX));
    if (v >= VPAD_FLOOR) break;
  }

  const tOpts = { cols, rows, bold, fz: FZ, hfz: FZ + 1, vpad, ls: 1.08 };
  const tblH = scheduleTable(s, { ...tOpts, x: MARGIN_X, y: bandTop });

  let bottom = bandTop + tblH;
  if (spec.closingNote) {
    // Pin the banner to the bottom of the band so it anchors the slide.
    const by = CONTENT_FLOOR - bannerH;
    closingBanner(s, { x: MARGIN_X, y: by, w: CONTENT_W, text: spec.closingNote });
    bottom = by + bannerH;
  }

  fits.push({ slide: pageNo, bandTop, bandH, tblH, cardsH: bannerH,
              bottom, floor: CONTENT_FLOOR,
              note: `table ${FZ}pt vpad ${vpad.toFixed(3)}` });
}

wideSlide(3, C.slide3);
wideSlide(4, C.slide4);

// ---------- fit report ----------
console.log('--- fit report (all bottoms must be <= floor) ---');
fits.forEach((f) => {
  const ok = f.bottom <= f.floor + 0.001 ? 'OK  ' : 'OVER';
  console.log(`${ok} slide ${f.slide}: band ${f.bandTop.toFixed(2)}-${f.floor.toFixed(2)} ` +
    `(${f.bandH.toFixed(2)}") table ${f.tblH.toFixed(2)}" cards ${f.cardsH.toFixed(2)}" ` +
    `bottom ${f.bottom.toFixed(2)}"  [${f.note}]`);
});
if (fits.some((f) => f.bottom > f.floor + 0.001)) {
  console.error('FIT CHECK FAILED');
  process.exitCode = 1;
}

// ---------- write + post-process ----------
pres.writeFile({ fileName: OUT }).then(() => {
  const zip = new AdmZip(OUT);
  zip.getEntries().forEach((e) => {
    if (!e.entryName.startsWith('ppt/slides/') || !e.entryName.endsWith('.xml')) return;
    let xml = zip.readAsText(e.entryName);
    xml = xml.replace(/<a:p>\s*<a:pPr[^/]*\/>\s*<a:endParaRPr[^/]*\/>\s*<\/a:p>/g, '');
    xml = xml.replace(/<a:p>\s*<a:endParaRPr[^/]*\/>\s*<\/a:p>/g, '');
    zip.updateFile(e.entryName, Buffer.from(xml, 'utf-8'));
  });
  // Embed Outfit so the deck renders correctly without a local install.
  ['Regular', 'Bold', 'Thin'].forEach((v) =>
    zip.addFile(`ppt/fonts/Outfit-${v}.ttf`,
                fs.readFileSync(path.join(BUILD, `Outfit-${v}.ttf`))));
  zip.writeZip(OUT);
  console.log('wrote ' + OUT);
});
