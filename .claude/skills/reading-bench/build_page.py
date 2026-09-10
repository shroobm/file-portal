"""build_page.py <geometry.json> <out.html> — the Reading Bench's mechanical half, step 2.

Inlines the extracted dataset into the page. The page is self-contained (fonts from Google Fonts, the one host the
Artifact CSP admits; no other external resource), theme-aware, keyboard-operable, and draws the page to scale from the
geometry, with the real page rendered from the source PDF as a layer UNDER it when --pdf was given — see SKILL.md's three laws. The <title> is the artifact's name: The Reading Bench.
"""
import io
import json
import sys

HTML = r"""<meta charset="utf-8">
<title>The Reading Bench</title>
<meta name="description" content="What the converter reads, block by block, on real pages of a real book — the geometry it captures and the dials it scores.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root{
  --paper:#f6f3ec; --ink:#1f2320; --ink-2:#4f554f; --ink-3:#8a908a; --rule:#d9d4c7; --panel:#fffdf8; --well:#ece7db;
  --accent:#b9552a; --accent-ink:#ffffff;
  --t-text:#6b7a8f; --t-head:#2f4a7a; --t-table:#b9552a; --t-figure:#4e7d5b; --t-picture:#8a6d2f; --t-caption:#9a7bb0;
  --t-code:#3c6e71; --t-list:#5f6f9a; --t-footer:#a9a29a; --t-header:#a9a29a; --t-toc:#7a5f3a; --t-form:#a04f4f; --t-other:#7d7d7d;
  --good:#3d7a4a; --warn:#b98a2a; --bad:#a63d3d;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#1b1d1c; --ink:#ece8de; --ink-2:#b9b4a8; --ink-3:#7f7b72; --rule:#3a3d39; --panel:#232624; --well:#2c302d;
  --accent:#e08a5c; --accent-ink:#1b1d1c;
  --t-text:#8da0b8; --t-head:#8fb0e6; --t-table:#e08a5c; --t-figure:#7fb58c; --t-picture:#c9a65a; --t-caption:#bfa1d8;
  --t-code:#78b3b6; --t-list:#9aa9d6; --t-footer:#6e6a63; --t-header:#6e6a63; --t-toc:#b89670; --t-form:#d07a7a; --t-other:#9a9a9a;
  --good:#7fc08c; --warn:#d9b45a; --bad:#e07a7a;
}}
:root[data-theme="dark"]{
  --paper:#1b1d1c; --ink:#ece8de; --ink-2:#b9b4a8; --ink-3:#7f7b72; --rule:#3a3d39; --panel:#232624; --well:#2c302d;
  --accent:#e08a5c; --accent-ink:#1b1d1c;
  --t-text:#8da0b8; --t-head:#8fb0e6; --t-table:#e08a5c; --t-figure:#7fb58c; --t-picture:#c9a65a; --t-caption:#bfa1d8;
  --t-code:#78b3b6; --t-list:#9aa9d6; --t-footer:#6e6a63; --t-header:#6e6a63; --t-toc:#b89670; --t-form:#d07a7a; --t-other:#9a9a9a;
  --good:#7fc08c; --warn:#d9b45a; --bad:#e07a7a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"Source Sans 3",system-ui,Segoe UI,sans-serif;font-size:16px;line-height:1.45}
.wrap{max-width:1180px;margin:0 auto;padding:28px 22px 56px}
h1{font-family:Fraunces,Georgia,serif;font-weight:700;font-size:clamp(30px,4vw,44px);line-height:1.05;margin:0 0 6px;text-wrap:balance;letter-spacing:-.01em}
h2{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:22px;margin:34px 0 10px;text-wrap:balance}
p{max-width:68ch;margin:6px 0}
.lede{color:var(--ink-2);font-size:17px;max-width:74ch}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);font-weight:600;margin-bottom:8px}
.mono{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
.dials{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0 8px}
.dial{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.dial .k{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
.dial .v{font-family:"IBM Plex Mono",monospace;font-size:24px;font-weight:600;line-height:1.1;font-variant-numeric:tabular-nums}
.dial .d{font-size:12px;color:var(--ink-2)}
.dial .bar{height:6px;background:var(--well);border-radius:3px;overflow:hidden;margin-top:6px}
.dial .bar i{display:block;height:100%;background:var(--accent)}
.dial.good .bar i{background:var(--good)} .dial.warn .bar i{background:var(--warn)}
.bench{display:grid;grid-template-columns:minmax(300px,504fr) minmax(280px,460fr);gap:18px;margin-top:16px}
@media (max-width:820px){.bench{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px;display:flex;flex-direction:column;gap:10px;min-width:0}
.panel .hd{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}
.panel .hd .t{font-family:Fraunces,Georgia,serif;font-size:18px;font-weight:500}
.tabs{display:flex;flex-wrap:wrap;gap:6px}
.tab{border:1px solid var(--rule);background:transparent;color:var(--ink-2);border-radius:4px;padding:4px 9px;font:600 12px "IBM Plex Mono",monospace;cursor:pointer}
.tab[aria-selected="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.tab:focus-visible,.btn:focus-visible,.blk:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.sheet{background:var(--well);border-radius:4px;padding:10px;display:flex;justify-content:center}
svg.page{max-width:100%;height:auto;display:block}
.blk{cursor:pointer}
.blk rect{stroke-width:1.2;fill-opacity:.16}
.blk.cur rect{stroke:var(--accent);stroke-width:2.4;fill:var(--accent);fill-opacity:.32}
.blk:hover rect{fill-opacity:.3}
.head-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{border:1px solid var(--rule);background:var(--panel);color:var(--ink);border-radius:4px;padding:6px 11px;font:600 13px "Source Sans 3",sans-serif;cursor:pointer}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:12px;color:var(--ink-2)}
.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px;background:var(--c)}
.out{background:var(--well);border-radius:4px;padding:12px;min-height:150px;font-family:Fraunces,Georgia,serif;font-size:17px;line-height:1.45;overflow-wrap:anywhere}
.out .type{font:600 11px "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.rec{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:13px}
.rec dt{color:var(--ink-3);font:600 11px "IBM Plex Mono",monospace;letter-spacing:.06em;text-transform:uppercase;padding-top:2px}
.rec dd{margin:0;font-family:"IBM Plex Mono",monospace;font-size:13px;overflow-wrap:anywhere}
.rec dd.prose{font-family:"Source Sans 3",sans-serif;font-size:14px}
.pos{font-size:13px;color:var(--ink-2)}
.pos b{color:var(--ink)}
.explain{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:14px}
@media (max-width:820px){.explain{grid-template-columns:1fr}}
figure{margin:0;background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px}
figcaption{font-size:13px;color:var(--ink-2);margin-top:8px}
.census{display:grid;grid-template-columns:max-content 1fr max-content;gap:6px 12px;align-items:center;font-size:13px;margin-top:6px}
.census .b{height:10px;background:var(--well);border-radius:2px;overflow:hidden}
.census .b i{display:block;height:100%;background:var(--c)}
.notes{margin-top:22px;border-top:1px solid var(--rule);padding-top:14px}
.notes p{max-width:80ch}
.tag{display:inline-block;font:600 11px "IBM Plex Mono",monospace;letter-spacing:.06em;padding:1px 6px;border-radius:3px;border:1px solid var(--rule);color:var(--ink-2);vertical-align:1px}
@media (prefers-reduced-motion: reduce){ .blk rect{transition:none} }
</style>
<div class="wrap">
  <div class="eyebrow">File Portal · the assembly line, drawn from a real bundle</div>
  <h1>The Reading Bench</h1>
  <p class="lede" id="lede">Left: a real page as the converter saw it — every block it found, in the geometry it captured. Right: what the reading head is on right now, and the record behind it. The dials are the book's own numbers from its manifest. Press <b>Play</b> to watch it read.</p>

  <div class="dials" id="dials"></div>

  <div class="bench">
    <section class="panel" aria-label="The page the model reads">
      <div class="hd"><span class="t">What it reads</span><span class="pos mono" id="pagebox"></span></div>
      <div class="tabs" role="tablist" id="tabs"></div>
      <div class="head-controls" id="fadectl" hidden><label class="pos" for="fade">page render</label><input id="fade" type="range" min="0" max="100" value="85" aria-label="Opacity of the rendered page under the blocks"><span class="pos mono" id="fadev">85 %</span><span class="pos" id="rendermeta"></span></div>
      <div class="sheet"><svg class="page" id="sheet" role="img" aria-label="A page drawn to scale with every block the converter found"></svg></div>
      <div class="legend" id="legend"></div>
    </section>
    <section class="panel" aria-label="What the model writes">
      <div class="hd"><span class="t">What it writes</span><span class="pos" id="headpos"></span></div>
      <div class="head-controls">
        <button class="btn" id="prev" type="button">◀ Prev</button>
        <button class="btn primary" id="play" type="button">Play</button>
        <button class="btn" id="next" type="button">Next ▶</button>
        <span class="pos" id="speed"></span>
      </div>
      <div class="out" id="out"></div>
      <dl class="rec" id="rec"></dl>
    </section>
  </div>

  <h2>The numbers, in plain terms</h2>
  <div class="explain">
    <figure>
      <svg viewBox="0 0 520 300" role="img" aria-label="A page box in points with one block's polygon and bounding box drawn inside it, origin at the top-left">
        <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
        <g fill="none" stroke="currentColor" stroke-width="1.2">
          <rect x="30" y="20" width="200" height="262" rx="1"/>
          <line x1="30" y1="20" x2="90" y2="20" marker-end="url(#arr)"/>
          <line x1="30" y1="20" x2="30" y2="80" marker-end="url(#arr)"/>
        </g>
        <g fill="currentColor" font-family="IBM Plex Mono, monospace" font-size="11">
          <text x="94" y="24">x, points →</text>
          <text x="34" y="92">y ↓</text>
          <text x="30" y="296" id="figbox">page box</text>
          <text x="232" y="284" text-anchor="end" id="figin"></text>
        </g>
        <g id="figpoly" fill="var(--t-table)" fill-opacity=".22" stroke="var(--t-table)" stroke-width="1.6">
          <polygon id="figpolygon" points="59,48 201,48 201,94 59,94"/>
        </g>
        <g fill="currentColor" font-family="IBM Plex Mono, monospace" font-size="11">
          <text x="59" y="44" id="figtl"></text>
          <text x="201" y="107" text-anchor="end" id="figbr"></text>
        </g>
        <g fill="currentColor" font-family="Source Sans 3, sans-serif" font-size="12">
          <text x="262" y="60">polygon = the four corners, in order</text>
          <text x="262" y="78">bbox = left, top, right, bottom</text>
          <text x="262" y="96">(the same numbers when the block is square;</text>
          <text x="262" y="112">they differ on a skewed scan)</text>
          <text x="262" y="148" id="figl1"></text>
          <text x="262" y="166" id="figl2"></text>
          <text x="262" y="184" id="figl3"></text>
          <text x="262" y="220">The origin is the top-left corner;</text>
          <text x="262" y="238">y grows downward.</text>
        </g>
      </svg>
      <figcaption id="figcap"></figcaption>
    </figure>
    <figure>
      <div class="eyebrow">Block census · the whole book</div>
      <div class="census" id="census"></div>
      <figcaption id="censuscap"></figcaption>
    </figure>
  </div>

  <div class="notes" id="notes"></div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  const D = JSON.parse(document.getElementById('data').textContent);
  const COLOR = {Text:'--t-text',SectionHeader:'--t-head',Table:'--t-table',TableGroup:'--t-table',FigureGroup:'--t-figure',Picture:'--t-picture',PictureGroup:'--t-picture',Caption:'--t-caption',Code:'--t-code',ListGroup:'--t-list',ListItem:'--t-list',PageFooter:'--t-footer',PageHeader:'--t-header',TableOfContents:'--t-toc',Form:'--t-form'};
  const col = t => 'var(' + (COLOR[t] || '--t-other') + ')';
  const inch = pt => (pt/72).toFixed(2);
  const fmt = (n, d) => Number(n).toLocaleString(undefined, {maximumFractionDigits: d===undefined?0:d, minimumFractionDigits: d===undefined?0:d});
  const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  document.getElementById('lede').innerHTML = 'Left: a real page of <em>' + esc(String(D.book||'').split(' -- ')[0].split('_')[0]) + '</em> as the converter saw it — every block it found, in the geometry it captured. Right: what the reading head is on right now, and the record behind it. The dials are the book’s own numbers from its manifest. Press <b>Play</b> to watch it read.';

  // dials — the manifest's own numbers; a missing number is UNREAD, never 0
  const f = D.fidelity || {}, c = f.convert || {}, a = D.analyst || {}, fa = f.analyst || {};
  const dials = [];
  dials.push({k:'Fidelity · convert', v: c.doc_survival !== undefined ? fmt(c.doc_survival,4) : 'UNREAD', d: c.pages_scored ? ('document survival, ' + fmt(c.pages_scored) + ' pages scored, witness ' + (c.witness||'?')) : 'no convert score in the manifest', pct: c.doc_survival, cls: c.doc_survival >= 0.995 ? 'good' : 'warn'});
  dials.push({k:'Omissions · pages flagged', v: c.pages_flagged ? fmt(c.pages_flagged.length) : 'UNREAD', d: c.pages_scored ? ('of ' + fmt(c.pages_scored) + ' scored') : '', pct: (c.pages_flagged && c.pages_scored) ? 1 - c.pages_flagged.length/c.pages_scored : undefined, cls:'warn'});
  const fas = fa.doc_survival !== undefined ? fa.doc_survival : fa.score;
  if (fas !== undefined) dials.push({k:'Fidelity · analyst', v: fmt(fas, 4), d: 'verdict ' + (f.verdict || '?'), pct: fas, cls: fas >= 0.995 ? 'good':'warn'});
  else dials.push({k:'Verdict', v: (f.verdict || 'UNREAD'), d: 'the manifest’s fidelity verdict', pct: undefined, cls:'warn'});
  dials.push({k:'Chunks passed', v: a.chunks_passed !== undefined ? (fmt(a.chunks_passed) + ' / ' + fmt(a.chunks_generated)) : 'UNREAD', d: a.rejections ? ('rejected ' + fmt(a.chunks_rejected) + ': fence ' + a.rejections.fence + ', survival ' + a.rejections.survival) : '', pct: a.chunks_generated ? a.chunks_passed/a.chunks_generated : undefined, cls:'good'});
  dials.push({k:'Goodput', v: a.goodput_accepted_tok_s !== undefined ? (fmt(a.goodput_accepted_tok_s,1) + ' tok/s') : 'UNREAD', d: a.model ? (a.model + ' · ' + fmt(a.duration_s/60) + ' min for the analyst phase') : '', pct: undefined, cls:''});
  dials.push({k:'Layout pass', v: (D.timing_s && D.timing_s.build_document) ? (fmt(D.timing_s.build_document/60,1) + ' min') : 'UNREAD', d: D.totals ? (fmt(D.totals.blocks) + ' blocks over ' + fmt(D.totals.pages) + ' pages') : '', pct: undefined, cls:''});
  document.getElementById('dials').innerHTML = dials.map(x => '<div class="dial ' + x.cls + '"><span class="k">' + x.k + '</span><span class="v">' + x.v + '</span><span class="d">' + x.d + '</span>' + (x.pct !== undefined ? '<span class="bar"><i style="width:' + Math.max(0, Math.min(100, x.pct*100)).toFixed(1) + '%"></i></span>' : '') + '</div>').join('');

  const types = Array.from(new Set(D.pages.flatMap(p => p.blocks.map(b => b.type))));
  document.getElementById('legend').innerHTML = types.map(t => '<span style="--c:' + col(t) + '">' + esc(t) + '</span>').join('');

  const total = D.totals.blocks;
  const max = D.census.length ? D.census[0][1] : 1;
  document.getElementById('census').innerHTML = D.census.map(([t,n]) => '<span>' + esc(t) + '</span><span class="b"><i style="width:' + (100*n/max).toFixed(1) + '%;--c:' + col(t) + '"></i></span><span class="mono">' + fmt(n) + '</span>').join('');
  const tables = (D.census.find(x => x[0]==='Table')||[0,0])[1], tgroups = (D.census.find(x => x[0]==='TableGroup')||[0,0])[1];
  document.getElementById('censuscap').textContent = fmt(total) + ' blocks across ' + fmt(D.totals.pages) + ' pages. ' + fmt(tables) + ' Table and ' + fmt(tgroups) + ' TableGroup blocks in the whole book.';

  // the explainer figure, from the first Table on the chosen pages (or the first block)
  const P0 = D.pages[0]; const box0 = P0.box || [0,0,504,662];
  const ex = D.pages.flatMap(p => p.blocks.map(b => ({b, p}))).find(x => x.b.type === 'Table') || {b: P0.blocks[0], p: P0};
  const W0 = box0[2]-box0[0], H0 = box0[3]-box0[1];
  const sx = 200/W0, sy = 262/H0; const [ex0,ey0,ex1,ey1] = ex.b.bbox;
  document.getElementById('figpolygon').setAttribute('points', [30+ex0*sx,20+ey0*sy,30+ex1*sx,20+ey0*sy,30+ex1*sx,20+ey1*sy,30+ex0*sx,20+ey1*sy].map(v=>v.toFixed(1)).join(','));
  document.getElementById('figtl').setAttribute('x', (30+ex0*sx).toFixed(1)); document.getElementById('figtl').setAttribute('y', (20+ey0*sy-4).toFixed(1)); document.getElementById('figtl').textContent = ex0 + ', ' + ey0;
  document.getElementById('figbr').setAttribute('x', (30+ex1*sx).toFixed(1)); document.getElementById('figbr').setAttribute('y', (20+ey1*sy+13).toFixed(1)); document.getElementById('figbr').textContent = ex1 + ', ' + ey1;
  document.getElementById('figbox').textContent = 'page box: 0, 0 → ' + W0 + ', ' + H0 + ' pt';
  document.getElementById('figin').textContent = inch(W0) + ' in × ' + inch(H0) + ' in';
  document.getElementById('figl1').textContent = '72 points to the inch, so this ' + ex.b.type.toLowerCase() + ' is';
  document.getElementById('figl2').textContent = 'about ' + inch(ex0) + ' in from the left, ' + inch(ex1-ex0) + ' in wide,';
  document.getElementById('figl3').textContent = inch(ey0) + ' in from the top, ' + inch(ey1-ey0) + ' in tall.';
  document.getElementById('figcap').textContent = 'The ' + ex.b.type + ' on page ' + ex.p.page + ', placed on its page box. Every block carries these two shapes plus its page, its type and the headings it lives under.';

  // the bench
  let pi = 0, bi = 0, timer = null;
  const tabs = document.getElementById('tabs');
  D.pages.forEach((p, i) => {
    const b = document.createElement('button'); b.className='tab'; b.type='button'; b.setAttribute('role','tab'); b.textContent = 'p.' + p.page + ' · ' + p.blocks.length; b.setAttribute('aria-selected', i===0);
    b.addEventListener('click', () => { pi = i; bi = 0; stop(); render(); });
    tabs.appendChild(b);
  });
  function stop(){ if (timer){ clearInterval(timer); timer=null; document.getElementById('play').textContent='Play'; } }
  function row(k, v, prose){ return '<dt>' + k + '</dt><dd' + (prose?' class="prose"':'') + '>' + v + '</dd>'; }
  function render(){
    const P = D.pages[pi]; const box = P.box || [0,0,504,662];
    const W = box[2]-box[0], H = box[3]-box[1];
    Array.from(tabs.children).forEach((t,i)=>t.setAttribute('aria-selected', i===pi));
    document.getElementById('pagebox').textContent = 'page box ' + W + ' × ' + H + ' pt = ' + inch(W) + ' × ' + inch(H) + ' in';
    const svg = document.getElementById('sheet');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    let s = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--panel)" stroke="var(--rule)"/>';
    // the real page, rendered from the source PDF, UNDER the geometry (S129: "embed the real pages underneath … as an overlay")
    const fc = document.getElementById('fadectl');
    if (P.image && P.image.data_uri) {
      fc.hidden = false;
      const op = (+document.getElementById('fade').value) / 100;
      s += '<image href="' + P.image.data_uri + '" x="0" y="0" width="' + W + '" height="' + H + '" preserveAspectRatio="none" opacity="' + op + '"/>';
      document.getElementById('rendermeta').textContent = 'PDF page ' + P.image.pdf_page_index + ' at ' + P.image.dpi + ' dpi · PDF rect ' + P.image.pdf_rect.join(' × ') + ' pt' + (P.image.box_matches_pdf ? ' = the block page box' : ' ≠ the block page box (' + W + ' × ' + H + ')');
    } else {
      fc.hidden = true;
    }
    P.blocks.forEach((b, i) => {
      const [x0,y0,x1,y1] = b.bbox;
      s += '<g class="blk' + (i===bi?' cur':'') + '" data-i="' + i + '" tabindex="0" role="button" aria-label="' + esc(b.type) + ' block ' + (i+1) + '">' +
           '<rect x="' + x0 + '" y="' + y0 + '" width="' + (x1-x0) + '" height="' + (y1-y0) + '" fill="' + col(b.type) + '" stroke="' + col(b.type) + '"/>' +
           '<text x="' + (x0+3) + '" y="' + (y0+9) + '" font-size="7" font-family="IBM Plex Mono, monospace" fill="currentColor" opacity=".75">' + (i+1) + '</text></g>';
    });
    svg.innerHTML = s;
    svg.querySelectorAll('.blk').forEach(g => { g.addEventListener('click', () => { bi = +g.dataset.i; stop(); render(); }); g.addEventListener('keydown', e => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); bi = +g.dataset.i; stop(); render(); } }); });
    const b = P.blocks[bi];
    document.getElementById('headpos').textContent = 'reading block ' + (bi+1) + ' of ' + P.blocks.length + ' on page ' + P.page;
    document.getElementById('out').innerHTML = '<div class="type">' + esc(b.type) + '</div>' + (b.text ? esc(b.text) : '<span style="color:var(--ink-3)">(no text: this block’s html is empty — a Picture or Figure block ships its pixels as an asset; any other kind is what the layout stage wrote)</span>');
    const [x0,y0,x1,y1] = b.bbox;
    const hier = Object.entries(b.hier || {}).map(([lvl, id]) => 'L' + lvl + ': ' + esc(D.headers[id] || id)).join(' › ') || 'none';
    document.getElementById('rec').innerHTML =
      row('id', esc(b.id)) + row('polygon', b.polygon.map(p => '[' + p[0] + ', ' + p[1] + ']').join(' ')) + row('bbox', b.bbox.join(', ')) +
      row('size', (x1-x0).toFixed(1) + ' × ' + (y1-y0).toFixed(1) + ' pt = ' + inch(x1-x0) + ' × ' + inch(y1-y0) + ' in', true) +
      row('from left / top', inch(x0) + ' in / ' + inch(y0) + ' in', true) +
      row('section', hier, true) + row('page (marker said)', (b.page_raw === undefined || b.page_raw === null) ? '—' : (b.page_raw + ' — corrected to ' + P.page + ' from the id'), true);
  }
  document.getElementById('prev').addEventListener('click', () => { stop(); bi = (bi - 1 + D.pages[pi].blocks.length) % D.pages[pi].blocks.length; render(); });
  document.getElementById('next').addEventListener('click', () => { stop(); bi = (bi + 1) % D.pages[pi].blocks.length; render(); });
  const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById('speed').textContent = reduced ? 'step with Next (reduced motion)' : 'one block every 1.4 s';
  document.getElementById('play').addEventListener('click', () => {
    if (timer) { stop(); return; }
    if (reduced) { bi = (bi + 1) % D.pages[pi].blocks.length; render(); return; }
    document.getElementById('play').textContent = 'Pause';
    timer = setInterval(() => { const n = D.pages[pi].blocks.length; if (bi >= n-1) { if (pi < D.pages.length-1) { pi++; bi = 0; } else { stop(); return; } } else bi++; render(); }, 1400);
  });
  document.addEventListener('keydown', e => { if (e.target && e.target.tagName === 'BUTTON' && e.target.classList.contains('tab')) return; if (e.key === 'ArrowRight') document.getElementById('next').click(); if (e.key === 'ArrowLeft') document.getElementById('prev').click(); });

  document.getElementById('fade').addEventListener('input', e => { document.getElementById('fadev').textContent = e.target.value + ' %'; const im = document.querySelector('#sheet image'); if (im) im.setAttribute('opacity', (+e.target.value)/100); });

  const n = D.totals;
  const R = D.render || {};
  const renderNote = (D.pages.some(p => p.image && p.image.data_uri))
    ? '<p><span class="tag">Observed</span> The page renders under the blocks come from the source PDF <code>' + esc(R.pdf||'') + '</code> at ' + esc(String(R.dpi||'')) + ' dpi (PyMuPDF), page index = the block’s corrected page. A bundle ships figure crops, not page renders; the render is a layer under the geometry, never a substitute for it.</p>'
    : '<p><span class="tag">UNREAD</span> No page render: ' + esc(R.reason || 'the source PDF was not available') + '. The page is drawn from geometry alone.</p>';
  document.getElementById('notes').innerHTML = renderNote +
    '<p><span class="tag">Observed</span> Every number on this page was read from the bundle at <code>' + esc(D.bundle||'') + '</code>: <code>blocks.json</code> for the geometry, <code>manifest.json</code> for the dials. Nothing is mocked; a number the manifest does not carry reads UNREAD.</p>' +
    (n.page_raw_disagreements !== undefined && n.page_raw_disagreements !== null ? '<p><span class="tag">Observed</span> Marker’s own page field disagreed with the block’s id on ' + fmt(n.page_raw_disagreements) + ' of ' + fmt(n.blocks) + ' blocks (J24). The page shown here is the corrected one, read from the id. Geometry is only worth anything when its page is right.</p>' : '') +
    '<p><span class="tag">Inferred</span> The reading head steps through blocks in the order the layout stage emitted them, which is the order the text reaches the analyst. The analyst’s own per-chunk scores exist in its journal but are not yet joined to block ids — that join is the one piece of plumbing this bench needs to show a live score per block instead of the book-level dials above.</p>' +
    '<p><span class="tag">The vision</span> The crop tool writes the same record back: a polygon, a page, a label. So a human’s crop and a model’s block are one thing, and every correction is a labeled example.</p>';

  render();
})();
</script>
"""


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    data = json.load(io.open(sys.argv[1], encoding="utf-8"))
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = HTML.replace("__DATA__", blob)
    io.open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("written", len(out.encode("utf-8")), "bytes ->", sys.argv[2])


if __name__ == "__main__":
    main()
