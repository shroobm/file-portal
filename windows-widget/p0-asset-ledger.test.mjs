// Extract the two P-0 render functions from the real source files and exercise them on the
// REAL corpus shapes. Tests logic, not layout: nulls, sign, both-sides, and Room/Dock parity.
import { readFileSync } from "fs";
const grab = (file, name) => {
  const src = readFileSync(file, "utf8");
  const i = src.indexOf(`function ${name}(`);
  if (i < 0) throw new Error(`${name} not found in ${file}`);
  let d = 0, j = src.indexOf("{", i);
  for (let k = j; k < src.length; k++) {
    if (src[k] === "{") d++;
    else if (src[k] === "}" && --d === 0) return src.slice(i, k + 1);
  }
  throw new Error("unbalanced");
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const escHtml = esc;
const room = eval(`(${grab("windows-widget/src/room.js", "assetLedger")})`);
const dock = eval(`(${grab("windows-widget/src/main.js", "assetLedgerLine")})`);

const cases = [
  { n: "scan (OCR worked, delta lies)", d: { assets_out: 49,  embedded_images: 465, asset_delta: -416 }, want: ["49", "465", "Δ-416", "count only"] },
  { n: "vector figures (blind spot)",   d: { assets_out: 92,  embedded_images: 0,   asset_delta: 92   }, want: ["92", "Δ+92"] },
  { n: "born-digital",                  d: { assets_out: 313, embedded_images: 232, asset_delta: 81   }, want: ["313", "232", "Δ+81"] },
  { n: "absent ledger → BLANK",         d: { assets_out: null, embedded_images: null, asset_delta: null }, blank: true },
  { n: "partial (delta only) → BLANK",  d: { assets_out: null, embedded_images: null, asset_delta: -5 }, blank: true },
];
let pass = 0, total = 0;
for (const c of cases) {
  for (const [label, fn] of [["Room", room], ["Dock", dock]]) {
    total++;
    const out = fn(c.d);
    let ok;
    if (c.blank) ok = out === "";
    else ok = c.want.every((w) => out.includes(w)) && !out.includes("undefined") && !out.includes("NaN");
    if (ok) { pass++; console.log(`PASS ${label.padEnd(4)} — ${c.n}`); }
    else console.log(`FAIL ${label.padEnd(4)} — ${c.n}\n      got: ${out}`);
  }
}
// parity: both surfaces must say the same thing about the same book
total++;
const a = room(cases[0].d), b = dock(cases[0].d);
const words = (s) => (s.match(/figures|out|in source|count only/g) || []).join(",");
if (words(a) === words(b)) { pass++; console.log("PASS both — Room and Dock wording agree"); }
else console.log(`FAIL both — wording diverges\n  room:${words(a)}\n  dock:${words(b)}`);
console.log(`════ P-0 frontend: ${pass}/${total} ════`);
process.exit(pass === total ? 0 : 1);
