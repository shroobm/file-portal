const fs = require('fs');

const rawLines = fs.readFileSync('table5_raw.txt', 'utf8').split(/\r?\n/);

const BOM = String.fromCharCode(0xFEFF);
const BS = String.fromCharCode(0x08);

const NOISE_EXACT = new Set([
  "Structure Type", "Children", "Parents", "Occ.",
  "Table 5 (continued)",
  "Table 5 — Parent-child relationships between the PDF 1.7 elements and PDF 2.0 elements",
  "© ISO 2023 – All rights reserved\t",
  "© ISO 2023 – All rights reserved",
  "ISO/TS 32005:2023(E)",
  "Sold by the PDF Association to Rabiullah Lotfullah  20978 | September 2, 2026 |",
  "Single user only, copying and networking prohibited.",
  BOM,
  "c",
]);

const OCC_SET = new Set(["0..n", "1..n", "0..1", "1", "∅*", "‡", "[a]", "[b]"]);

const ctrlOnlyRe = new RegExp("^[" + BOM + BS + "]*$");

const tokens = [];
const tokenSrcLine = [];
const droppedDigits = [];

rawLines.forEach((l, idx) => {
  const lineNo = idx + 1;
  const s = l.trim();
  if (s === "") return;
  if (ctrlOnlyRe.test(s)) return; // BOM / stray backspace control-char artifacts
  if (/^-{5,} PAGE \d+ -{5,}$/.test(s)) return;
  if (NOISE_EXACT.has(s)) return;
  if (/^\d+$/.test(s) && s !== "1") {
    droppedDigits.push([lineNo, s]);
    return;
  }
  tokens.push(s);
  tokenSrcLine.push(lineNo);
});

console.error(`Total data tokens after noise filtering: ${tokens.length}`);
console.error(`Dropped bare page-number digit lines: ${droppedDigits.length}`);

const rows = [];
let pos = 0;
const n_tok = tokens.length;
const errors = [];

while (pos < n_tok) {
  const header = tokens[pos];
  const headerLine = tokenSrcLine[pos];
  if (OCC_SET.has(header)) {
    errors.push([pos, tokenSrcLine[pos], `Expected row header, got OCC token ${header}`]);
    pos += 1;
    continue;
  }
  pos += 1;

  const childrenOcc = [];
  while (pos < n_tok && OCC_SET.has(tokens[pos])) {
    childrenOcc.push(tokens[pos]);
    pos += 1;
  }
  const n = childrenOcc.length;
  const childrenTypes = tokens.slice(pos, pos + n);
  const childLines = tokenSrcLine.slice(pos, pos + n);
  pos += n;

  const parentsOcc = [];
  while (pos < n_tok && OCC_SET.has(tokens[pos])) {
    parentsOcc.push(tokens[pos]);
    pos += 1;
  }
  const m = parentsOcc.length;
  const parentsTypes = tokens.slice(pos, pos + m);
  const parentLines = tokenSrcLine.slice(pos, pos + m);
  pos += m;

  rows.push({
    header, headerLine,
    children: childrenTypes.map((t, i) => [t, childrenOcc[i], childLines[i]]),
    parents: parentsTypes.map((t, i) => [t, parentsOcc[i], parentLines[i]]),
  });
}

console.error(`Parsed ${rows.length} row-blocks`);
console.error(`Parse errors: ${errors.length}`);
errors.forEach(e => console.error("  ERROR:", JSON.stringify(e)));

rows.forEach(r => {
  console.log(`L${String(r.headerLine).padStart(5)}  ${r.header.padEnd(16)} children=${String(r.children.length).padStart(3)} parents=${String(r.parents.length).padStart(3)}`);
});

fs.writeFileSync('table5_parsed.json', JSON.stringify(rows, null, 1), 'utf8');
