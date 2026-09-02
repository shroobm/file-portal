const fs = require('fs');
const rows = JSON.parse(fs.readFileSync('table5_clean.json', 'utf8'));

const LOWCONF = new Set(["Ruby", "RB", "RT", "RP", "Warichu", "WT", "WP", "content item"]);

function fmt(list) {
  // list: [type, occ, line]
  return list.map(([t, occ]) => {
    if (occ === "0..n") return t;
    return `${t}[${occ}]`;
  }).join(", ");
}

let out = [];
for (const r of rows) {
  const lc = LOWCONF.has(r.header) ? " ⚠LOW-CONFIDENCE PARSE" : "";
  out.push(`#### ${r.header}${lc}`);
  out.push(`- Children (${r.children.length}): ${r.children.length ? fmt(r.children) : "(none)"}`);
  out.push(`- Parents (${r.parents.length}): ${r.parents.length ? fmt(r.parents) : "(none)"}`);
  out.push("");
}

fs.writeFileSync('table5_markdown.md', out.join("\n"), 'utf8');
console.log("wrote table5_markdown.md, " + rows.length + " rows");
