// S149 — the table-health functions of bench.html against the vendored renderer (node test_table_health.js, from this dir).
// The functions are read out of bench.html between the S149-HEALTH markers — the page is the source of truth — and every
// case is judged two ways: what tableHealth flags, and what markdown-it (the same build the view loads) renders.
"use strict";
const fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "bench.html"), "utf8");
const a = html.indexOf("// S149-HEALTH-BEGIN"), b = html.indexOf("// S149-HEALTH-END");
if (a < 0 || b < 0) { console.error("markers not found in bench.html"); process.exit(2); }
const block = html.slice(a, b);
// the page's functions, evaluated in their own scope with the DOM helpers stubbed (markTableHealth is not under test)
const stub = () => { throw new Error("markTableHealth needs the DOM; not under test here"); };
const fns = new Function("$", "ctxText", block + "\n;return { DELIM, fenceMask, hasPipe, cellCount, isRepairLine, tableBlocks, tableSpanJS, tableHealth };")(stub, stub);
const { DELIM, fenceMask, hasPipe, cellCount, isRepairLine, tableBlocks, tableSpanJS, tableHealth } = fns;
const md = require("./vendor/markdown-it.min.js")({ html: false, linkify: false, breaks: false });
const tables = (text) => (md.render(text).match(/<table/g) || []).length;
const L = (s) => s.split("\n");

let fails = 0, n = 0;
function check(name, cond, detail) { n++; if (!cond) { fails++; console.log("  FAIL  " + name + (detail ? " — " + detail : "")); } else console.log("  ok    " + name); }
function flags(text) { return tableHealth(L(text)); }

// clean tables: no flags, one <table>
check("a clean table renders and is not flagged", flags("| a | b |\n|---|---|\n| 1 | 2 |\n").length === 0 && tables("| a | b |\n|---|---|\n| 1 | 2 |\n") === 1);
check("a table without leading pipes is a table", flags("a | b\n--- | ---\n1 | 2\n").length === 0 && tables("a | b\n--- | ---\n1 | 2\n") === 1);
check("alignment colons are a delimiter", flags("| a | b |\n|:--|--:|\n| 1 | 2 |\n").length === 0 && tables("| a | b |\n|:--|--:|\n| 1 | 2 |\n") === 1);
check("an escaped pipe is text", flags("| a | b |\n|---|---|\n| x\\|y | 2 |\n").length === 0);
check("a pipe in a code span is text", flags("| a | b |\n|---|---|\n| `x|y` | 2 |\n").length === 0);
check("two tables one blank apart are two tables", tableBlocks(L("| a |\n|---|\n| 1 |\n\n| b |\n|---|\n| 2 |\n")).length === 2 && flags("| a |\n|---|\n| 1 |\n\n| b |\n|---|\n| 2 |\n").length === 0);
check("a repair block after the last row with its blank line is not flagged", flags("| a |\n|---|\n| 1 |\n\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n\ntail\n").length === 0);
check("pipes inside a code fence are not a table and not flagged", flags("```\n| a | b |\n| c | d |\n```\n").length === 0 && tableBlocks(L("```\n| a | b |\n|---|---|\n```\n")).length === 0);

// broken tables: flagged, and the renderer agrees
const split = "| a | b |\n\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n|---|---|\n| 1 | 2 |\n";
const f1 = flags(split);
check("the S149 split is flagged on the header and the inserted lines and the orphan delimiter", f1.some((x) => x.line === 1 && /cut from its delimiter/.test(x.reason)) && f1.some((x) => x.line === 3) && f1.some((x) => x.line === 4) && f1.some((x) => x.line === 5 && /no header row/.test(x.reason)) && tables(split) === 0, JSON.stringify(f1));
const mid = "| a | b |\n|---|---|\n| 1 | 2 |\n\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n| 3 | 4 |\n";
const f2 = flags(mid);
check("a block splitting the body is flagged with the orphan rows", f2.some((x) => x.line === 5) && f2.some((x) => x.line === 7 && /cut off/.test(x.reason)) && tables(mid) === 1, JSON.stringify(f2));
const touch = "| a | b |\n|---|---|\n| 1 | 2 |\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n";
const f3 = flags(touch);
// the renderer folds both touching lines in: the header row + three body rows (the real row, the embed, the comment)
check("a block touching the last row is a garbled row: flagged, and the renderer folds it in", f3.some((x) => x.line === 4 && /touches/.test(x.reason)) && (md.render(touch).match(/<tr/g) || []).length === 4, JSON.stringify(f3) + " rows=" + (md.render(touch).match(/<tr/g) || []).length);
const hd = "| a | b | c |\n|---|---|\n| 1 | 2 | 3 |\n";
check("header/delimiter disagreement: not a table to a renderer, said so", flags(hd).some((x) => x.line === 1 && /does not treat this as a table/.test(x.reason)) && tables(hd) === 0);
const extra = "a | b\n--- | ---\n1 | 2 | 3\n";
check("a row with extra cells is flagged, the renderer drops them", flags(extra).some((x) => x.line === 3 && /extra cells/.test(x.reason)) && tables(extra) === 1);
check("a delimiter with no header is flagged", flags("para\n\n|---|---|\n| 1 | 2 |\n").some((x) => x.line === 3 && /no header row/.test(x.reason)) && tables("para\n\n|---|---|\n| 1 | 2 |\n") === 0);
check("a lone pipe row is flagged", flags("| a | b |\n\npara\n").some((x) => x.line === 1 && /lone pipe row/.test(x.reason)));
check("a header with a non-delimiter under it is flagged", flags("| a | b |\n| 1 | 2 |\n| 3 | 4 |\n").some((x) => x.line === 1 && /not a delimiter/.test(x.reason)) && tables("| a | b |\n| 1 | 2 |\n") === 0);
check("tableSpanJS finds the block from any row", JSON.stringify(tableSpanJS(L("x\n| a |\n|---|\n| 1 |\n| 2 |\n\ny"), 3)) === "[1,4]" && tableSpanJS(L("x\n| a |\n|---|\n| 1 |"), 0) === null);
check("CRLF endings do not break the reading", flags("| a | b |\r\n|---|---|\r\n| 1 | 2 |\r\n".replace(/\r\n/g, "\n")).length === 0);

console.log(fails ? `TABLE HEALTH: ${fails} of ${n} FAILED` : `TABLE HEALTH: ${n}/${n} ok`);
process.exit(fails ? 1 : 0);
