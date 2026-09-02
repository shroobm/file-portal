const fs = require('fs');
const rows = JSON.parse(fs.readFileSync('table5_parsed.json', 'utf8'));

// Drop known noise/duplicate rows: the table-title row (0 children/0 parents at very start)
// and the orphaned empty "Artifact" row created by a page-break widow at line 4975
// (its real, full data row follows at line 5147 after the intervening "Formula" row).
const clean = rows.filter((r, i) => {
  if (r.children.length === 0 && r.parents.length === 0) return false;
  return true;
});

console.error(`clean rows: ${clean.length}`);
const byHeader = {};
for (const r of clean) {
  if (byHeader[r.header]) {
    console.error(`DUPLICATE HEADER: ${r.header} at lines ${byHeader[r.header].headerLine} and ${r.headerLine}`);
  }
  byHeader[r.header] = r;
}
console.error(`unique headers: ${Object.keys(byHeader).length}`);

fs.writeFileSync('table5_clean.json', JSON.stringify(clean, null, 1), 'utf8');

// Bidirectional consistency check
let mismatches = 0, checks = 0, missingRow = 0;
for (const r of clean) {
  for (const [childType, occ, line] of r.children) {
    checks++;
    const childRow = byHeader[childType];
    if (!childRow) { missingRow++; console.error(`No row for child type ${childType} (referenced from ${r.header} L${line})`); continue; }
    const back = childRow.parents.find(p => p[0] === r.header);
    if (!back) {
      mismatches++;
      console.error(`ASYMMETRY: ${r.header} -> child ${childType} (${occ}) @L${line}, but ${childType}'s parent list has no entry for ${r.header}`);
    } else if (back[1] !== occ) {
      mismatches++;
      console.error(`VALUE MISMATCH: ${r.header}->${childType} child-side occ=${occ} @L${line}, but ${childType}'s parent-side occ for ${r.header} = ${back[1]} @L${back[2]}`);
    }
  }
}
console.error(`checks=${checks} mismatches=${mismatches} missingRow=${missingRow}`);
