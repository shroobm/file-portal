// WHAT THIS FILE DOES
// Probe step 3 of 3 for ISO/TS 32005:2023 Table 5. Reads table5_clean.json (from verify_table5.js, run from the probes
// directory) and writes table5_markdown.md: one "####" section per structure type listing its children and parents,
// with occurrence codes shown in brackets (the default "0..n" is omitted) and a LOW-CONFIDENCE flag on types whose
// parse is marked unreliable. Prints one line naming the output and the row count.
// Top-level script; one helper, fmt().

// -- load cleaned rows and the list of low-confidence headers --
const fs = require('fs');
const rows = JSON.parse(fs.readFileSync('table5_clean.json', 'utf8'));

const LOWCONF = new Set(["Ruby", "RB", "RT", "RP", "Warichu", "WT", "WP", "content item"]);

/**
 * Formats a children/parents list as a comma-separated string: "Type" for occurrence 0..n, else "Type[occ]".
 * Input: list of [type, occ, line] triples. Returns the string. Pure; no side effects.
 */
function fmt(list) {
  // list: [type, occ, line]
  return list.map(([t, occ]) => {
    if (occ === "0..n") return t;
    return `${t}[${occ}]`;
  }).join(", ");
}

// -- build the markdown lines, one section per row --
let out = [];
for (const r of rows) {
  const lc = LOWCONF.has(r.header) ? " ⚠LOW-CONFIDENCE PARSE" : "";
  out.push(`#### ${r.header}${lc}`);
  out.push(`- Children (${r.children.length}): ${r.children.length ? fmt(r.children) : "(none)"}`);
  out.push(`- Parents (${r.parents.length}): ${r.parents.length ? fmt(r.parents) : "(none)"}`);
  out.push("");
}

// -- write the markdown file --
fs.writeFileSync('table5_markdown.md', out.join("\n"), 'utf8');
console.log("wrote table5_markdown.md, " + rows.length + " rows");
