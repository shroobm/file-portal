/**
 * voyage.js — the honest model of ONE voyage.
 *
 * Damodaran, "Investment Valuation" 4e · 1377 pages · dropped 2026-08-31T21:30:12Z ·
 * HELD 2026-09-01T04:56:33Z. 7h 26m 21s wall. Two convert legs, two audits, one power
 * cut, one unattended reboot, and 6h 20m 08s of total silence.
 *
 * QUARANTINE: prototypes/. Nothing here is imported, spawned, watched or shipped by the
 * live system. This module READS NOTHING AT RUNTIME — the fixture is inlined below.
 *
 * USAGE
 *   <script type="module">
 *     import VOYAGE, { TIMELINE, FIELDS, ALARMS, dishonest, fmtDuration } from './voyage.js';
 *     document.title = VOYAGE.title;
 *     for (const f of dishonest()) console.log(f.id, '->', f.display, '(naive:', f.naive + ')');
 *   </script>
 *
 * THE ONE RULE THIS MODULE EXISTS TO ENFORCE
 *   Every numeric field is a `measure` record: { value, num, den, conditions, honest, display }.
 *   `value` is the RAW number as the pipeline wrote it. `display` is the only string safe to
 *   put on glass. When `honest === false`, rendering `value` is a lie — render `display`.
 *   `naive` is preserved deliberately: it is what a careless panel WOULD have printed, and it
 *   is the negative control. If a panel's output ever equals `naive`, that panel is lying.
 *
 * PROVENANCE OF EVERY NUMBER (tag `evidence`)
 *   'event'     — read from voyage-events.jsonl (34 events, inlined verbatim below)
 *   'manifest'  — read from voyage-manifest.json (inlined verbatim below)
 *   'source'    — read from the live pipeline source, READ-ONLY, for thresholds and for the
 *                 definitions of numerator/denominator that the fixture does not carry:
 *                 windows-converter/fidelity_audit.py, windows-converter/convert_and_ship.py
 *   'derived'   — arithmetic over the above, computed in this file, shown in `conditions`
 *   'testimony' — the operator told us; NO event and NO manifest field attests it
 *   'absence'   — measured by the ABSENCE of events between two timestamps
 *
 * `testimony` and `absence` are not lesser truths, but they are different truths, and a panel
 * that draws them with the same ink as `event` is lying about how much the machine knows.
 */

/* ==========================================================================================
 * 0 · THE FIXTURE, INLINED VERBATIM
 * The only transform: the `source` field, byte-identical across all 34 events (verified),
 * is factored out to SOURCE_PDF. Nothing else is altered, rounded, filtered or reordered.
 * ========================================================================================== */

export const SOURCE_PDF = "Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Fourth Edition, 2023 -- Wiley & Sons, Incorporated, John.pdf";

/** All 34 events, in file order, `source` stripped (see SOURCE_PDF). */
export const EVENTS = Object.freeze([
  {"ts":"2026-08-31T21:30:12+00:00","pid":21748,"stage":"intake","event":"detected","analyst_mode":"local"},
  {"ts":"2026-08-31T21:30:19+00:00","pid":10408,"stage":"convert","event":"probe","chars_per_page":2102.1,"pages":1377,"lane":"clean","lane_reason":"text_layer_present","ocr_invisible_ratio":0,"ocr_invisible_spans":0,"ocr_total_spans":157924},
  {"ts":"2026-08-31T21:30:19+00:00","pid":10408,"stage":"convert","event":"estimate","eta_s":4343,"s_per_page":3.154,"basis":"similar","samples":3,"pages_this_run":1377,"resumed_pages_assumed":0},
  {"ts":"2026-08-31T21:30:19+00:00","pid":10408,"stage":"convert","event":"chunking","pages":1377,"slices":7,"slice_size":200,"batch":8},
  {"ts":"2026-08-31T21:37:28+00:00","pid":10408,"stage":"convert","event":"slice","slice":1,"slices":7,"page_range":"0-199","wall_s":428.8,"batch":8,"resumed":false},
  {"ts":"2026-08-31T21:43:53+00:00","pid":10408,"stage":"convert","event":"slice","slice":2,"slices":7,"page_range":"200-399","wall_s":385.6,"batch":8,"resumed":false},
  {"ts":"2026-08-31T21:56:46+00:00","pid":10408,"stage":"convert","event":"slice","slice":3,"slices":7,"page_range":"400-599","wall_s":772.2,"batch":8,"resumed":false},
  {"ts":"2026-08-31T22:10:15+00:00","pid":10408,"stage":"convert","event":"slice","slice":4,"slices":7,"page_range":"600-799","wall_s":809.2,"batch":8,"resumed":false},
  {"ts":"2026-08-31T22:22:38+00:00","pid":10408,"stage":"convert","event":"slice","slice":5,"slices":7,"page_range":"800-999","wall_s":742.3,"batch":8,"resumed":false},
  {"ts":"2026-08-31T22:31:31+00:00","pid":10408,"stage":"convert","event":"slice","slice":6,"slices":7,"page_range":"1000-1199","wall_s":533.1,"batch":8,"resumed":false},
  {"ts":"2026-08-31T22:34:14+00:00","pid":10408,"stage":"convert","event":"slice","slice":7,"slices":7,"page_range":"1200-1376","wall_s":163,"batch":8,"resumed":false},
  {"ts":"2026-08-31T22:34:14+00:00","pid":10408,"stage":"convert","event":"converted","wall_s":3834.2,"s_per_page":2.78,"pages":1377,"pages_converted_this_run":1377,"s_per_page_this_run":2.78,"retry_wall_s":0,"resumed_slices":0,"cost_s":3834.2,"slices":7,"peak_vram_mib":9395,"promised_s_per_page":3.154,"promised_eta_s":4343,"estimate_basis":"similar","estimate_samples":3},
  {"ts":"2026-08-31T22:34:15+00:00","pid":10408,"stage":"audit","event":"supersede","from_verdict":"fail","sha":"14c66834bdfeaa2e"},
  {"ts":"2026-08-31T22:35:15+00:00","pid":10408,"stage":"audit","event":"scored","phase":"convert","kind":"fidelity","doc_survival":0.9334,"runs":25,"runs_total":531,"degeneration":true,"verdict":"fail"},
  {"ts":"2026-08-31T22:35:15+00:00","pid":10408,"stage":"audit","event":"flagged","phase":"convert","verdict":"fail"},
  {"ts":"2026-09-01T03:37:28+00:00","pid":10784,"stage":"intake","event":"stale-lock-reaped"},
  {"ts":"2026-09-01T03:37:29+00:00","pid":10784,"stage":"intake","event":"detected","analyst_mode":"local"},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"probe","chars_per_page":2102.1,"pages":1377,"lane":"clean","lane_reason":"text_layer_present","ocr_invisible_ratio":0,"ocr_invisible_spans":0,"ocr_total_spans":157924},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"estimate","eta_s":0,"s_per_page":3.154,"basis":"similar","samples":3,"pages_this_run":0,"resumed_pages_assumed":1377},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"chunking","pages":1377,"slices":7,"slice_size":200,"batch":8},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"slice","slice":1,"slices":7,"page_range":"0-199","resumed":true},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"slice","slice":2,"slices":7,"page_range":"200-399","resumed":true},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"slice","slice":3,"slices":7,"page_range":"400-599","resumed":true},
  {"ts":"2026-09-01T03:37:37+00:00","pid":13704,"stage":"convert","event":"slice","slice":4,"slices":7,"page_range":"600-799","resumed":true},
  {"ts":"2026-09-01T03:37:38+00:00","pid":13704,"stage":"convert","event":"slice","slice":5,"slices":7,"page_range":"800-999","resumed":true},
  {"ts":"2026-09-01T03:37:38+00:00","pid":13704,"stage":"convert","event":"slice","slice":6,"slices":7,"page_range":"1000-1199","resumed":true},
  {"ts":"2026-09-01T03:37:38+00:00","pid":13704,"stage":"convert","event":"slice","slice":7,"slices":7,"page_range":"1200-1376","resumed":true},
  {"ts":"2026-09-01T03:37:38+00:00","pid":13704,"stage":"convert","event":"converted","wall_s":0,"s_per_page":0,"pages":1377,"pages_converted_this_run":0,"s_per_page_this_run":0,"retry_wall_s":0,"resumed_slices":7,"cost_s":3834.2,"slices":7,"peak_vram_mib":null,"promised_s_per_page":3.154,"promised_eta_s":0,"estimate_basis":"similar","estimate_samples":3},
  {"ts":"2026-09-01T03:38:37+00:00","pid":13704,"stage":"audit","event":"scored","phase":"convert","kind":"fidelity","doc_survival":0.9334,"runs":25,"runs_total":531,"degeneration":true,"verdict":"fail"},
  {"ts":"2026-09-01T03:38:37+00:00","pid":13704,"stage":"audit","event":"flagged","phase":"convert","verdict":"fail"},
  {"ts":"2026-09-01T04:56:32+00:00","pid":13704,"stage":"audit","event":"scored","phase":"analyst","doc_survival":0.9402,"runs":25,"runs_total":404,"verdict":"fail"},
  {"ts":"2026-09-01T04:56:32+00:00","pid":13704,"stage":"audit","event":"flagged","phase":"analyst","verdict":"fail"},
  {"ts":"2026-09-01T04:56:32+00:00","pid":13704,"stage":"audit","event":"verdict_fail","bundle":"Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four","verdict":"fail"},
  {"ts":"2026-09-01T04:56:33+00:00","pid":13704,"stage":"audit","event":"held","bundle":"Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four","verdict":"fail"}
]);

/** voyage-manifest.json → .analyst (the held bundle's analyst block). */
export const MANIFEST_ANALYST = Object.freeze({
  "model": "qwen3:8b",
  "backend": "local",
  "program": "readability",
  "chunks_passed": 928,
  "chunks_rejected": 29,
  "chunks_failed": 0,
  "chunks_resumed": 641,
  "chunks_generated": 316,
  "duration_s": 4634.4,
  "tokens_prompt_total": 314311,
  "tokens_prompt_counted_calls": 316,
  "tokens_output_total": 279174,
  "tokens_counted_calls": 316,
  "tokens_accepted_output": 275162,
  "goodput_accepted_tok_s": 59.37,
  "goodput_conditions": "THIS-run accepted-output tokens / whole-phase wall seconds (wall includes resumed-chunk skips, API pacing, and the terminal model unload; prompt totals are partial sums over tokens_prompt_counted_calls — cached prefills report none)"
});

/** voyage-manifest.json → .fidelity.convert */
export const MANIFEST_FIDELITY_CONVERT = Object.freeze({
  "kind": "fidelity",
  "doc_survival": 0.9334,
  "pages_scored": 1372,
  "pages_flagged": [
    3,
    9,
    10,
    30,
    60,
    62,
    63,
    65,
    78,
    82,
    104,
    108,
    110,
    119,
    127,
    131,
    134,
    145,
    153,
    164,
    165,
    167,
    169,
    171,
    172,
    174,
    177,
    178,
    180,
    185,
    195,
    249,
    251,
    258,
    271,
    288,
    291,
    303,
    308,
    309,
    314,
    318,
    319,
    329,
    330,
    332,
    335,
    346,
    351,
    353,
    355,
    373,
    375,
    376,
    377,
    382,
    383,
    394,
    399,
    400,
    401,
    403,
    413,
    417,
    420,
    431,
    435,
    439,
    440,
    442,
    455,
    456,
    457,
    462,
    489,
    490,
    505,
    507,
    510,
    511,
    512,
    514,
    517,
    521,
    522,
    524,
    525,
    530,
    531,
    533,
    536,
    537,
    538,
    539,
    541,
    542,
    543,
    556,
    557,
    561,
    562,
    563,
    567,
    568,
    570,
    580,
    585,
    596,
    602,
    608,
    609,
    610,
    618,
    622,
    638,
    639,
    654,
    655,
    656,
    657,
    676,
    678,
    679,
    692,
    694,
    695,
    696,
    702,
    708,
    709,
    710,
    711,
    712,
    713,
    714,
    721,
    732,
    742,
    743,
    744,
    746,
    748,
    749,
    750,
    751,
    752,
    754,
    755,
    757,
    766,
    767,
    773,
    774,
    791,
    794,
    795,
    796,
    799,
    800,
    807,
    828,
    834,
    836,
    837,
    841,
    842,
    843,
    844,
    847,
    850,
    855,
    856,
    861,
    873,
    878,
    879,
    880,
    892,
    896,
    901,
    902,
    903,
    909,
    911,
    913,
    916,
    917,
    922,
    938,
    943,
    944,
    946,
    952,
    960,
    971,
    975,
    992,
    995,
    996,
    997,
    999,
    1002,
    1015,
    1023,
    1048,
    1061,
    1063,
    1064,
    1068,
    1071,
    1074,
    1078,
    1083,
    1084,
    1093,
    1099,
    1102,
    1106,
    1110,
    1113,
    1119,
    1122,
    1124,
    1134,
    1146,
    1152,
    1157,
    1158,
    1159,
    1160,
    1161,
    1162,
    1163,
    1170,
    1172,
    1180,
    1185,
    1196,
    1197,
    1207,
    1209
  ],
  "runs": [
    {
      "page": 757,
      "words": 154,
      "excerpt": "year. valuing famous using these inputs, you can estimate the"
    },
    {
      "page": 946,
      "words": 120,
      "excerpt": "firm (no synergy) cost of equity = 8.93% 9.37% 9.12%"
    },
    {
      "page": 3,
      "words": 116,
      "excerpt": "measuring earnings and profitability measuring risk other issues in analyzing"
    },
    {
      "page": 10,
      "words": 108,
      "excerpt": "cash-flow-producing assets collectibles trophy assets conclusion questions and short problems"
    },
    {
      "page": 746,
      "words": 108,
      "excerpt": "growth by using a two-stage firm valuation model: ev forward"
    },
    {
      "page": 1134,
      "words": 108,
      "excerpt": "revenues) = (40/200)(200 × . 03) = $1.2million expected free"
    },
    {
      "page": 9,
      "words": 106,
      "excerpt": "what makes private firms different? estimating valuation inputs at private"
    },
    {
      "page": 375,
      "words": 96,
      "excerpt": "$ 0 0.00% 1 $ 292 −$125 $266 $ 0"
    },
    {
      "page": 561,
      "words": 96,
      "excerpt": "are estimated in the following calculations: reinvestmentrate = adjustedebit(1 −t)"
    },
    {
      "page": 654,
      "words": 96,
      "excerpt": "trailing pe = payout ratio(1 + g)(1 − (1 +"
    },
    {
      "page": 556,
      "words": 93,
      "excerpt": "of 2010 yields a value for the equity: reinvestment ="
    },
    {
      "page": 174,
      "words": 84,
      "excerpt": "1/12, σ2 = 0.05, r = 0.04 the value from"
    },
    {
      "page": 710,
      "words": 84,
      "excerpt": "per share0 = eps1 × payout ratio × [1 −"
    },
    {
      "page": 799,
      "words": 84,
      "excerpt": "years-deutsche bank in 2009 current 1 2 3 4 5"
    },
    {
      "page": 892,
      "words": 84,
      "excerpt": "is σj, and that the standard deviation in the market"
    },
    {
      "page": 909,
      "words": 84,
      "excerpt": "the inputs to valuation for different valuation motives. illiquidity discountbase"
    },
    {
      "page": 916,
      "words": 84,
      "excerpt": "in table 24.6: table 24.6 expected cash flows and present"
    },
    {
      "page": 1068,
      "words": 84,
      "excerpt": "15% 1 $150.00 $120.00 $ 30.00 $ 26.09 2 $180.00"
    },
    {
      "page": 1159,
      "words": 84,
      "excerpt": "year ebit(1 − t) from assets in place $ 0.00"
    },
    {
      "page": 1161,
      "words": 83,
      "excerpt": "next 10 years: terminal value = ebit10(1 −tax rate)(1 +"
    },
    {
      "page": 742,
      "words": 80,
      "excerpt": "firm can be extracted from a stable growth dividend discount"
    },
    {
      "page": 580,
      "words": 72,
      "excerpt": "divisions, with other assets added in: table 15.10 value of"
    },
    {
      "page": 609,
      "words": 72,
      "excerpt": "from segovia's consolidated assets = $300 million valueofseville'soperatingassets = ebit"
    },
    {
      "page": 750,
      "words": 72,
      "excerpt": "sales do not increase proportionately. expectedgrowthnetincome = retentionratio × returnonequity"
    },
    {
      "page": 754,
      "words": 72,
      "excerpt": "equity per share is $10. the cost of capital for"
    }
  ],
  "runs_total": 531,
  "runs_capped_at": 25,
  "tripwires": {
    "degeneration": true,
    "degeneration_detail": {
      "flagged": true,
      "repeated_lines": 0,
      "md_lines": 29696,
      "worst": [
        {
          "line": 5524,
          "chars": 34523,
          "zlib": 0.023,
          "max_trigram": 129,
          "excerpt": "| Betas and Operating Leverage—Shoe Companies<br>Company Name<br>Beta<br>Market D/E<br>Fixed/Variable<br>Barry"
        },
        {
          "line": 7068,
          "chars": 4799,
          "zlib": 0.041,
          "max_trigram": 42,
          "excerpt": "| 11<br>This will happen only if the marketable"
        },
        {
          "line": 12456,
          "chars": 1886,
          "zlib": 0.045,
          "max_trigram": 139,
          "excerpt": "| holdings in other publicly traded firms. |"
        },
        {
          "line": 18584,
          "chars": 873,
          "zlib": 0.052,
          "max_trigram": 180,
          "excerpt": "| standing. | | | | |-----------|--|--|--| |"
        },
        {
          "line": 18065,
          "chars": 2111,
          "zlib": 0.064,
          "max_trigram": 40,
          "excerpt": "| that the growth rate in stable growth"
        },
        {
          "line": 11339,
          "chars": 2413,
          "zlib": 0.067,
          "max_trigram": 43,
          "excerpt": "| negative consequences. In fact, we count the"
        },
        {
          "line": 8795,
          "chars": 3005,
          "zlib": 0.074,
          "max_trigram": 62,
          "excerpt": "<span id=\"page-439-6\"></span> $\\begin{array}{lll} {\\rm ROC} + {\\rm D/E}"
        },
        {
          "line": 20481,
          "chars": 4799,
          "zlib": 0.09,
          "max_trigram": 57,
          "excerpt": "| Inbev | SAB Miller | Combined firm"
        },
        {
          "line": 19370,
          "chars": 1259,
          "zlib": 0.108,
          "max_trigram": 136,
          "excerpt": "| Interest Coverage Ratios and Bond Ratings |"
        },
        {
          "line": 602,
          "chars": 4724,
          "zlib": 0.143,
          "max_trigram": 165,
          "excerpt": "| | Table 14.2 Expected dividends and Present"
        }
      ],
      "blocks_total": 24,
      "worst_capped_at": 10
    },
    "page_coverage": {
      "with_text": 1372,
      "surviving": 1369
    },
    "asset_delta": 76,
    "embedded_images": 232,
    "reverse_sample": 0.765,
    "dict_hit": null,
    "garbage_rate": null
  }
});

/** voyage-manifest.json → .fidelity.analyst */
export const MANIFEST_FIDELITY_ANALYST = Object.freeze({
  "doc_survival": 0.9402,
  "runs": [
    {
      "page": null,
      "words": 576,
      "excerpt": "{1 - t} \\right)/{\\rm e}} \\\\ & - & {\\rm"
    },
    {
      "page": null,
      "words": 372,
      "excerpt": "evokes strong positive and negative reactions. can you avoid being"
    },
    {
      "page": null,
      "words": 312,
      "excerpt": "assumed to be diversified? the argument that diversification reduces an"
    },
    {
      "page": null,
      "words": 240,
      "excerpt": "valuing a private equity stake assume that you work for"
    },
    {
      "page": null,
      "words": 192,
      "excerpt": "1997 sales \\$10,346 \\$10,696 \\$ 9,881 service and rentals \\$"
    },
    {
      "page": null,
      "words": 156,
      "excerpt": "a brand name using the enterprise value to sales ratio"
    },
    {
      "page": null,
      "words": 144,
      "excerpt": "following information about these investments (in \\$millions) in table 16.2:"
    },
    {
      "page": null,
      "words": 132,
      "excerpt": "there are many academics as well as practitioners, who suggest"
    },
    {
      "page": null,
      "words": 132,
      "excerpt": "regression is undervalued (overvalued) relative to the market. the first"
    },
    {
      "page": null,
      "words": 132,
      "excerpt": "sachs 1 2 3 4 5 net income \\$ 9,118"
    },
    {
      "page": null,
      "words": 132,
      "excerpt": "deal is: cost of takeover buy-back stock: \\$38 × 12.2"
    },
    {
      "page": null,
      "words": 120,
      "excerpt": "roic in 2017 roic: 2013- 2017 cost of capital power"
    },
    {
      "page": null,
      "words": 120,
      "excerpt": "noncash and cash assets: betaofthefirm = betaoperatingassets × weightoperatingassets+ betacashassets"
    },
    {
      "page": null,
      "words": 120,
      "excerpt": "dividend discount model: $value of equity = \\frac{dividends1}{\\left(cost of equity"
    },
    {
      "page": null,
      "words": 120,
      "excerpt": "wacc pv 1 \\$ 358,394 \\$ 62,719 35.00% 10.50% \\$"
    },
    {
      "page": null,
      "words": 120,
      "excerpt": "undervalued % time value lowest value highest value a \\$"
    },
    {
      "page": null,
      "words": 108,
      "excerpt": "changes suggested: 1999 1998 1997 net income from continuing operations"
    },
    {
      "page": null,
      "words": 108,
      "excerpt": "capital maintenance fcff wacc4 cumulated wacc5 pv 6 \\$45.53 \\$5.20"
    },
    {
      "page": null,
      "words": 108,
      "excerpt": "year \\$ 3,626 (\\$ 818) 1 \\$ 4,692 \\$1,066 (\\$"
    },
    {
      "page": null,
      "words": 108,
      "excerpt": "improving the odds if the message that you have received"
    },
    {
      "page": null,
      "words": 108,
      "excerpt": "in place \\$ 100.00 + eva from assets in place"
    },
    {
      "page": null,
      "words": 96,
      "excerpt": "to valuation and the business. business stories: spanning the spectrum"
    },
    {
      "page": null,
      "words": 96,
      "excerpt": "telstra adr 21.70 27.66 -21.55% based on the predicted pe"
    },
    {
      "page": null,
      "words": 96,
      "excerpt": "is \\$1,529 million, and the consolidated debt outstanding at the"
    },
    {
      "page": null,
      "words": 96,
      "excerpt": "corporate bonds gold real estate 1930- 39 −1.92% 0.07% 4.27%"
    }
  ],
  "runs_total": 404,
  "runs_capped_at": 25
});

/** voyage-manifest.json → .fidelity.verdict */
export const MANIFEST_VERDICT = 'fail';

/**
 * Thresholds and definitions read from the live source, READ-ONLY.
 * These are NOT in the fixture. Without them a panel cannot say WHY a verdict fired, and
 * "FAIL" with no reason violates the error-structure protocol.
 */
export const AUDIT_LAW = Object.freeze({
  source: 'windows-converter/fidelity_audit.py',
  WINDOW_WORDS: 12,          // :41 — doc_survival's denominator unit is a 12-word window
  WINDOW_MIN_WORDS: 6,       // :42
  CLEAN_PAGE_FLAG: 0.85,     // :63 — page below this joins pages_flagged
  CLEAN_DOC_FLAG: 0.97,      // :64 — convert doc_survival below this → "flag", NEVER "fail"
  CLEAN_RUN_WORDS: 50,       // :65 — convert omission run at/above this → "flag"
  ANALYST_DOC_FAIL: 0.995,   // :68 — analyst doc_survival below this → "fail"
  ANALYST_RUN_WORDS: 25,     // :69 — ANY analyst run at/above this → "fail"
  DEGEN_ZLIB_MAX: 0.20,      // :57
  DEGEN_TRIGRAM_MAX: 40,     // :58
  DEGEN_BLOCK_MIN_CHARS: 200,// :59
  DEGEN_LINE_REPEAT: 20,     // :60 — repeated_lines is 0 unless a run EXCEEDS this
  REVERSE_SAMPLE_N: 200,     // :49
  REVERSE_SEED: 20260720,    // :50 — deterministic
  RUNS_CAP: 25,              // :383 — the shown list is sorted by words desc and sliced [:25]
  // compute_verdict (:422-465): only TWO signals reach "fail" — the degeneration tripwire,
  // and the analyst near-exact gate. Everything else LOCALIZES and reaches at most "flag".
  FAIL_SIGNALS: ['convert.tripwires.degeneration', 'analyst.doc_survival', 'analyst.runs[].words'],
});

/* ==========================================================================================
 * 1 · PRIMITIVES
 * ========================================================================================== */

/** The sentinel for a quantity nobody reported. docs/34: renders UNREAD, never 0.0. */
export const UNREAD = 'UNREAD';

/** The sentinel for a rate whose denominator is zero or whose denominator is not this run's. */
export const UNDEFINED = 'UNDEFINED';

const T = (iso) => Date.parse(iso);

/** Seconds → "5h 02m 13s" / "1h 17m 55s" / "428.8s". Never returns a bare number. */
export function fmtDuration(s) {
  if (s === null || s === undefined) return UNREAD;
  if (s < 60) return `${Number(s.toFixed(1))}s`;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.round(s % 60);
  return h ? `${h}h ${String(m).padStart(2, '0')}m ${String(sec).padStart(2, '0')}s`
           : `${m}m ${String(sec).padStart(2, '0')}s`;
}

/** ISO → "21:30:12Z" (the operator reads UTC; the machine writes UTC). */
export function fmtClock(iso) { return iso.slice(11, 19) + 'Z'; }

/** A percentage ALWAYS prints its base. docs/34. */
export function pct(n, d, label) {
  if (n === null || d === null || !d) return UNREAD;
  return `${((n / d) * 100).toFixed(1)}% (${n} of ${d}${label ? ' ' + label : ''})`;
}

/**
 * measure() — the only way a number enters this model.
 * Required: id, label, value, evidence, conditions.
 * `honest` defaults TRUE only when a numerator and denominator are both named, or the field
 * is a plain count with a named population. Anything else must declare itself.
 */
function measure(spec) {
  const m = {
    id: spec.id,
    label: spec.label,
    value: spec.value,                       // RAW, as the pipeline wrote it. Never render alone.
    unit: spec.unit ?? null,
    num: spec.num ?? null,                   // { label, value, unit }
    den: spec.den ?? null,                   // { label, value, unit }
    conditions: spec.conditions,             // docs/34: the third mandatory part
    population: spec.population ?? 'n/a',    // 'whole-book' | 'this-run' | 'prior-run' | 'mixed'
    evidence: spec.evidence,
    origin: spec.origin ?? null,             // file + key it came from
    honest: spec.honest !== false,
    display: spec.display,                   // THE ONLY STRING SAFE TO PUT ON GLASS
    naive: spec.naive ?? String(spec.value), // the negative control: what a lying panel prints
    census: spec.census ?? [],               // docs/51 row ids that bite this field
    defect: spec.defect ?? null,             // { reason, highlight, solution } — error structure
  };
  if (!m.honest && !m.defect) {
    throw new Error(`voyage.js: dishonest field ${m.id} has no error-structure record`);
  }
  return Object.freeze(m);
}

/* ==========================================================================================
 * 2 · POPULATIONS — the distinction that every lie in this voyage is made of
 * ========================================================================================== */

export const POPULATIONS = Object.freeze({
  'whole-book': {
    id: 'whole-book',
    label: 'whole book (both runs)',
    note: '957 analyst chunks / 1377 pages, accumulated across the crash. Correct for totals; ' +
          'NEVER a valid numerator over a this-run denominator.',
  },
  'this-run': {
    id: 'this-run',
    label: 'this run only (run 2, after the reboot)',
    note: '316 analyst chunks generated / 0 pages converted. The only population with a ' +
          'measured wall clock.',
  },
  'prior-run': {
    id: 'prior-run',
    label: 'run 1, before the power cut',
    note: '641 analyst chunks + 1377 pages converted. Its analyst wall clock, token counts and ' +
          'VRAM peak were never written to any file. Permanently UNREAD.',
  },
  mixed: {
    id: 'mixed',
    label: 'MIXED — numerator and denominator drawn from different runs',
    note: 'A number in this population is a defect, not a measurement.',
  },
});

/* ==========================================================================================
 * 3 · THE TIMELINE — work, dark, and dead, all first-class
 * ========================================================================================== */

const t_intake1   = '2026-08-31T21:30:12+00:00';
const t_chunk1    = '2026-08-31T21:30:19+00:00';
const t_conv1     = '2026-08-31T22:34:14+00:00';
const t_audit1    = '2026-08-31T22:35:15+00:00';
const t_reap      = '2026-09-01T03:37:28+00:00';
const t_conv2     = '2026-09-01T03:37:38+00:00';
const t_audit2    = '2026-09-01T03:38:37+00:00';
const t_audit3    = '2026-09-01T04:56:32+00:00';
const t_held      = '2026-09-01T04:56:33+00:00';

// Operator testimony. NO event and NO manifest field attests these three instants.
const t_powercut  = '2026-09-01T01:38:00+00:00';  // "~01:38Z", approximate
const t_reboot    = '2026-09-01T01:48:17+00:00';  // Windows event log, not this fixture
const t_humanback = '2026-09-01T03:34:00+00:00';  // "~03:34Z", approximate

const span = (a, b) => (T(b) - T(a)) / 1000;

/**
 * Every interval of the voyage, contiguous and exhaustive: they tile 21:30:12Z → 04:56:33Z
 * with no overlap and no hole. `kind` drives the ink:
 *   'work'  — the machine was measurably doing the thing
 *   'audit' — scoring, bracketed by two events
 *   'dark'  — ZERO events. The pipeline was alive (probably) and told us nothing.
 *   'dead'  — ZERO events because there was no process at all
 *   'gap'   — a boundary the record does not explain
 */
export const TIMELINE = Object.freeze([
  {
    id: 'intake-1', kind: 'work', label: 'intake · detect + probe + chunk plan',
    start: t_intake1, end: t_chunk1, seconds: span(t_intake1, t_chunk1),
    evidence: 'event', instrumented: true,
    note: 'lane=clean, lane_reason=text_layer_present, 0 of 157,924 spans invisible.',
  },
  {
    id: 'convert-leg-1', kind: 'work', label: 'convert leg 1 · 7 slices, 1377 pages',
    start: t_chunk1, end: t_conv1, seconds: span(t_chunk1, t_conv1),
    evidence: 'event', instrumented: true,
    note: 'Seven slice events sum to 3834.2s — exactly the reported wall_s. No gaps between ' +
          'slices. Beat its own 4343s promise by 508.8s.',
  },
  {
    id: 'audit-convert-1', kind: 'audit', label: 'convert audit (scored → flagged)',
    start: t_conv1, end: t_audit1, seconds: span(t_conv1, t_audit1),
    evidence: 'event', instrumented: true,
    note: 'Also carries an audit/supersede at 22:34:15Z, from_verdict "fail", sha 14c66834bdfeaa2e ' +
          '— a PRIOR failed bundle for this same book was being replaced.',
  },
  {
    id: 'dark-1', kind: 'dark', label: 'DARK ZONE 1 — no events of any kind',
    start: t_audit1, end: t_reap, seconds: span(t_audit1, t_reap),
    evidence: 'absence', instrumented: false,
    note: '5h 02m 13s. The analyst ran 641 chunks inside here and emitted NOTHING: the inline ' +
          'analyst code path has no analyst/start and no analyst/done — those exist only on the ' +
          '--resume path. The sole liveness signal was .analyst-progress.json, overwritten in ' +
          'place, keeping no history. Then the power failed. This interval is measured by the ' +
          'ABSENCE of records, which is the only thing it contains.',
    testimony: [
      {
        id: 'analyst-run-1', kind: 'dark', label: 'analyst run 1 working (641 chunks)',
        start: t_audit1, end: t_powercut, seconds: span(t_audit1, t_powercut),
        evidence: 'testimony', approximate: true,
        note: 'Duration UNREAD. The 641 is measured (manifest chunks_resumed); the end instant ' +
              'is the operator\u2019s "~01:38Z" and is approximate.',
      },
      {
        id: 'power-cut', kind: 'dead', label: 'power cut → machine off',
        start: t_powercut, end: t_reboot, seconds: span(t_powercut, t_reboot),
        evidence: 'testimony', approximate: true,
        note: 'Hard cut. No shutdown event, no crash record in this fixture.',
      },
      {
        id: 'dead-idle', kind: 'dead', label: 'DEAD MACHINE — powered, healthy, idle',
        start: t_reboot, end: t_humanback, seconds: span(t_reboot, t_humanback),
        evidence: 'testimony', approximate: true,
        note: '1h 45m 43s of a working computer doing nothing. The widget has no autostart and ' +
              'the watcher is the widget\u2019s child, so nothing could restart the pipeline. ' +
              'Recovery required a human to come home and log in.',
      },
      {
        id: 'operator-recovery', kind: 'gap', label: 'human logs in → first event',
        start: t_humanback, end: t_reap, seconds: span(t_humanback, t_reap),
        evidence: 'testimony', approximate: true,
        note: '3m 28s between the operator\u2019s testified return and the first machine record.',
      },
    ],
  },
  {
    id: 'convert-leg-2', kind: 'work', label: 'convert leg 2 · resumed 7/7 from cache',
    start: t_reap, end: t_conv2, seconds: span(t_reap, t_conv2),
    evidence: 'event', instrumented: true,
    note: 'stale-lock-reaped → re-detect → probe → estimate(eta 0s) → 7 resumed slices → ' +
          'converted. 10 seconds of clock, ZERO pages converted. Every rate field it emitted is ' +
          'a zero that means "nothing happened", not "it was instant".',
  },
  {
    id: 'audit-convert-2', kind: 'audit', label: 'convert audit re-scored (identical result)',
    start: t_conv2, end: t_audit2, seconds: span(t_conv2, t_audit2),
    evidence: 'event', instrumented: true,
    note: 'Byte-identical scores to 22:35:15Z — same doc_survival 0.9334, same 25-of-531 runs, ' +
          'same degeneration true. The audit re-ran on the same cached markdown.',
  },
  {
    id: 'dark-2', kind: 'dark', label: 'DARK ZONE 2 — the analyst\u2019s entire second run',
    start: t_audit2, end: t_audit3, seconds: span(t_audit2, t_audit3),
    evidence: 'absence', instrumented: false,
    note: '1h 17m 55s (4675s) with zero events, containing a 4634.4s analyst phase that we only ' +
          'know about because the manifest was written afterward. 40.6s of that window is ' +
          'unaccounted for even by the manifest. During this hour the glass had nothing to show.',
  },
  {
    id: 'verdict', kind: 'audit', label: 'analyst audit → verdict_fail → HELD',
    start: t_audit3, end: t_held, seconds: span(t_audit3, t_held),
    evidence: 'event', instrumented: true,
    note: 'No analyst/done event ever fired for this book, in either run.',
  },
]);

/** Roll-ups over the timeline. All 'derived'. */
const _voyageSeconds = span(t_intake1, t_held);
const _darkSeconds = TIMELINE.filter(s => s.kind === 'dark').reduce((a, s) => a + s.seconds, 0);
const _deadSeconds = (TIMELINE.find(s => s.id === 'dark-1').testimony || [])
  .filter(s => s.kind === 'dead').reduce((a, s) => a + s.seconds, 0);
// convert leg 1 + analyst run 2. Nothing else in this voyage is timed at all.
const _measuredWork = Number((3834.2 + 4634.4).toFixed(1));

export const SPANS = Object.freeze({
  voyage: measure({
    id: 'span.voyage', label: 'voyage wall clock', value: _voyageSeconds, unit: 's',
    num: { label: 'seconds from intake/detected to audit/held', value: _voyageSeconds, unit: 's' },
    den: null, evidence: 'derived', population: 'whole-book',
    conditions: 'First event 2026-08-31T21:30:12Z to last event 2026-09-01T04:56:33Z, one book, ' +
                'one machine, spanning one power failure and one unattended reboot.',
    display: `${fmtDuration(_voyageSeconds)} wall (21:30:12Z → 04:56:33Z, next day)`,
  }),
  measuredWork: measure({
    id: 'span.measured_work', label: 'seconds any stage actually reported', value: _measuredWork,
    unit: 's',
    num: { label: 'convert leg 1 wall_s + analyst run 2 duration_s', value: _measuredWork, unit: 's' },
    den: { label: 'voyage wall seconds', value: _voyageSeconds, unit: 's' },
    evidence: 'derived', population: 'mixed',
    conditions: 'Only two durations exist in the whole record: convert leg 1 (3834.2s, event) and ' +
                'the analyst second run (4634.4s, manifest). Convert leg 2 measured 0s of work. ' +
                'The analyst FIRST run — 641 chunks — reported no duration at all. This ratio ' +
                'therefore understates the work done and overstates the idleness.',
    display: `${fmtDuration(_measuredWork)} of ${fmtDuration(_voyageSeconds)} instrumented ` +
             `(${((_measuredWork / _voyageSeconds) * 100).toFixed(1)}%) — the rest is unmeasured, ` +
             'not necessarily idle',
    naive: '31.6% utilisation',
    honest: false,
    census: ['N-013'],
    defect: {
      reason: 'A "utilisation" or "idle" reading built on this ratio is wrong: the analyst\u2019s ' +
              'first run did 641 chunks of real GPU work whose duration was never recorded.',
      highlight: 'dark-1 (18133s): work happened here and is absent from the numerator.',
      solution: 'Label the remainder "UNMEASURED", split into dark (22808s, no events) and dead ' +
                '(6343s, testimony). Never print a utilisation percentage from this pair.',
    },
  }),
  dark: measure({
    id: 'span.dark', label: 'seconds with zero events', value: _darkSeconds, unit: 's',
    num: { label: 'dark-1 + dark-2 seconds', value: _darkSeconds, unit: 's' },
    den: { label: 'voyage wall seconds', value: _voyageSeconds, unit: 's' },
    evidence: 'absence', population: 'whole-book',
    conditions: 'Contiguous stretches between consecutive events where no event of any stage was ' +
                'emitted. Measured by absence. 18133s + 4675s.',
    display: `${fmtDuration(_darkSeconds)} of ${fmtDuration(_voyageSeconds)} with ZERO events ` +
             `(${((_darkSeconds / _voyageSeconds) * 100).toFixed(1)}% of the voyage)`,
  }),
  dead: measure({
    id: 'span.dead', label: 'seconds the machine was off or idle-after-reboot', value: _deadSeconds,
    unit: 's',
    num: { label: 'power-cut + dead-idle seconds', value: _deadSeconds, unit: 's' },
    den: { label: 'voyage wall seconds', value: _voyageSeconds, unit: 's' },
    evidence: 'testimony', population: 'whole-book',
    conditions: 'OPERATOR TESTIMONY, approximate at both ends. Neither the power cut nor the ' +
                '01:48:17Z reboot appears in the event stream; the pipeline cannot see its own ' +
                'death. 6960s total, of which 6343s was a powered, healthy, idle machine.',
    display: `${fmtDuration(_deadSeconds)} machine down or idle (testimony, \u00b1minutes) — ` +
             `${fmtDuration(6343)} of it powered and doing nothing`,
  }),
});

/* ==========================================================================================
 * 4 · THE CONVERT LEGS — two legs, and only one of them converted anything
 * ========================================================================================== */

const LEG1_SLICES = Object.freeze([
  { slice: 1, page_range: '0-199',     wall_s: 428.8, batch: 8, resumed: false, ts: '2026-08-31T21:37:28+00:00' },
  { slice: 2, page_range: '200-399',   wall_s: 385.6, batch: 8, resumed: false, ts: '2026-08-31T21:43:53+00:00' },
  { slice: 3, page_range: '400-599',   wall_s: 772.2, batch: 8, resumed: false, ts: '2026-08-31T21:56:46+00:00' },
  { slice: 4, page_range: '600-799',   wall_s: 809.2, batch: 8, resumed: false, ts: '2026-08-31T22:10:15+00:00' },
  { slice: 5, page_range: '800-999',   wall_s: 742.3, batch: 8, resumed: false, ts: '2026-08-31T22:22:38+00:00' },
  { slice: 6, page_range: '1000-1199', wall_s: 533.1, batch: 8, resumed: false, ts: '2026-08-31T22:31:31+00:00' },
  { slice: 7, page_range: '1200-1376', wall_s: 163.0, batch: 8, resumed: false, ts: '2026-08-31T22:34:14+00:00' },
]);

const LEG2_SLICES = Object.freeze([1, 2, 3, 4, 5, 6, 7].map((n, i) => ({
  slice: n,
  page_range: LEG1_SLICES[i].page_range,
  wall_s: null,                 // the resumed slice event carries NO wall_s. Not zero — absent.
  resumed: true,
  ts: n <= 4 ? '2026-09-01T03:37:37+00:00' : '2026-09-01T03:37:38+00:00',
})));

const _sliceSum = LEG1_SLICES.reduce((a, s) => a + s.wall_s, 0);

export const CONVERT_LEG_1 = Object.freeze({
  id: 'convert.leg1',
  label: 'Convert leg 1 — the run that did the work',
  start: t_chunk1, end: t_conv1,
  slices: LEG1_SLICES,
  didWork: true,
  fields: Object.freeze({
    wall_s: measure({
      id: 'convert.leg1.wall_s', label: 'GPU wall seconds', value: 3834.2, unit: 's',
      num: { label: 'sum of 7 slice wall_s', value: Number(_sliceSum.toFixed(1)), unit: 's' },
      den: null, evidence: 'event', population: 'this-run',
      origin: 'events[12].wall_s',
      conditions: 'Marker, clean lane, batch 8 at every slice, 1377 pages in 7 slices of 200. ' +
                  'The seven slice events sum to exactly 3834.2s and run back-to-back with no ' +
                  'idle between them (slice 1 ended 21:37:28Z, 428.8s after chunking at 21:30:19Z).',
      display: '3834.2s GPU wall over 7 slices (slice sum reconciles exactly)',
    }),
    s_per_page: measure({
      id: 'convert.leg1.s_per_page', label: 'seconds per page', value: 2.78, unit: 's/pp',
      num: { label: 'GPU wall seconds this run', value: 3834.2, unit: 's' },
      den: { label: 'pages converted this run', value: 1377, unit: 'pp' },
      evidence: 'event', population: 'this-run',
      origin: 'events[12].s_per_page',
      conditions: 'Numerator and denominator are BOTH this run — on leg 1 nothing was resumed ' +
                  '(resumed_slices 0), so s_per_page and s_per_page_this_run agree at 2.78. ' +
                  'Clean lane, text layer present, Marker batch 8, one RTX-class card.',
      display: '2.78 s/pp (3834.2s \u00f7 1377 pp converted this run)',
    }),
    pages: measure({
      id: 'convert.leg1.pages', label: 'pages converted', value: 1377, unit: 'pp',
      num: { label: 'pages_converted_this_run', value: 1377, unit: 'pp' },
      den: { label: 'pages in the source PDF', value: 1377, unit: 'pp' },
      evidence: 'event', population: 'this-run',
      conditions: 'pages_converted_this_run equals pages: the whole book was converted here.',
      display: '1377 of 1377 pages converted this run',
    }),
    peak_vram_mib: measure({
      id: 'convert.leg1.peak_vram_mib', label: 'peak VRAM', value: 9395, unit: 'MiB',
      num: { label: 'largest VRAM reading seen', value: 9395, unit: 'MiB' },
      den: { label: 'samples taken', value: null, unit: '30s samples' },
      evidence: 'event', population: 'this-run',
      origin: 'events[12].peak_vram_mib',
      conditions: 'A 30-second-sampled MAXIMUM, not a true peak: the sample count is not recorded ' +
                  'and any spike between samples is invisible. Over 3834.2s that is at most ~128 ' +
                  'samples.',
      display: '9395 MiB, highest of ~128 samples at 30s (a sampled max, not a peak)',
      naive: 'peak VRAM 9395 MiB',
      honest: false,
      census: ['N-066'],
      defect: {
        reason: 'The field is named "peak" but is a coarse sampled maximum; the spike that ' +
                'causes a stall lives between samples.',
        highlight: 'events[12].peak_vram_mib = 9395, sample count unrecorded.',
        solution: 'Render as "sampled max @30s". Never use it to claim headroom.',
      },
    }),
    retry_wall_s: measure({
      id: 'convert.leg1.retry_wall_s', label: 'seconds lost to retries', value: 0.0, unit: 's',
      num: { label: 'retry seconds', value: 0.0, unit: 's' },
      den: null, evidence: 'event', population: 'this-run',
      conditions: 'A genuine measured zero: no slice event carries `attempts` or `recovered`, so ' +
                  'the recovery ladder never engaged. Zero stalls. This is the one 0.0 on this ' +
                  'voyage that means what it says.',
      display: '0.0s — zero retries, zero stalls (7 of 7 slices first-attempt)',
    }),
    promise_delta: measure({
      id: 'convert.leg1.promise_delta', label: 'promise vs outcome', value: -508.8, unit: 's',
      num: { label: 'actual wall_s minus promised eta_s', value: -508.8, unit: 's' },
      den: { label: 'promised eta_s', value: 4343, unit: 's' },
      evidence: 'derived', population: 'this-run',
      conditions: 'Promise filed 21:30:19Z: eta 4343s at 3.154 s/pp, basis "similar", n=3 samples. ' +
                  'Outcome 3834.2s at 2.78 s/pp. An n=3 estimate, so the beat is within sampling ' +
                  'noise and is not evidence the machine got faster.',
      display: 'beat its promise by 508.8s (3834.2s actual vs 4343s promised, 11.7% under; ' +
               'estimate basis "similar", n=3)',
    }),
  }),
});

export const CONVERT_LEG_2 = Object.freeze({
  id: 'convert.leg2',
  label: 'Convert leg 2 — resumed 7/7 from cache; converted NOTHING',
  start: t_reap, end: t_conv2,
  slices: LEG2_SLICES,
  didWork: false,
  headline: 'This leg converted 0 pages. Every rate it reported is undefined.',
  fields: Object.freeze({
    wall_s: measure({
      id: 'convert.leg2.wall_s', label: 'GPU wall seconds', value: 0.0, unit: 's',
      num: { label: 'sum of slice wall_s for slices executed', value: 0.0, unit: 's' },
      den: { label: 'slices executed', value: 0, unit: 'slices' },
      evidence: 'event', population: 'this-run',
      origin: 'events[27].wall_s',
      conditions: 'An empty sum. Seven slices were admitted from cache (resumed: true, and the ' +
                  'resumed slice events carry NO wall_s field at all); none ran. Observed elapsed ' +
                  'between chunking and converted was \u22641s of clock.',
      display: 'NO WORK THIS RUN — 0 of 7 slices executed; the book\u2019s cost stands at 3834.2s',
      naive: 'converted in 0.0s',
      honest: false,
      census: ['N-064'],
      defect: {
        reason: 'A zero-length sum over an empty set reads as "the book converted instantly".',
        highlight: 'events[27]: wall_s 0.0, pages_converted_this_run 0, resumed_slices 7.',
        solution: 'Suppress the number. Print "resumed 7/7, no new work" and show cost_s 3834.2 ' +
                  'as the book\u2019s figure.',
      },
    }),
    s_per_page: measure({
      id: 'convert.leg2.s_per_page', label: 'seconds per page', value: 0.0, unit: 's/pp',
      num: { label: 'GPU wall seconds this run', value: 0.0, unit: 's' },
      den: { label: 'pages in the whole book (NOT pages converted)', value: 1377, unit: 'pp' },
      evidence: 'event', population: 'mixed',
      origin: 'events[27].s_per_page',
      conditions: 'THE CENSUS ROW N-059 IN THE FLESH: this-run numerator over whole-book ' +
                  'denominator. 0 pages were converted, so the rate has no denominator at all.',
      display: `${UNDEFINED} — 0 pages converted this run (book average from leg 1: 2.78 s/pp)`,
      naive: '0.00 s/pp',
      honest: false,
      census: ['N-059'],
      defect: {
        reason: 'A rate whose true denominator is zero, published as 0.00 by dividing this ' +
                'run\u2019s zero seconds by the whole book\u2019s 1377 pages.',
        highlight: 'convert_and_ship.py:1305 — s_per_page=round(wall / pages, 2) with wall=0.0.',
        solution: 'When pages_converted_this_run == 0, render UNDEFINED and show cost_s instead. ' +
                  'Downstream medians (line.rs collects s_per_page from every converted event) ' +
                  'must exclude any event with pages_converted_this_run == 0.',
      },
    }),
    s_per_page_this_run: measure({
      id: 'convert.leg2.s_per_page_this_run', label: 'seconds per page, this run', value: 0.0,
      unit: 's/pp',
      num: { label: 'GPU wall seconds this run', value: 0.0, unit: 's' },
      den: { label: 'pages_converted_this_run, SUBSTITUTED to 1377 by a divide-guard', value: 1377,
             unit: 'pp' },
      evidence: 'event', population: 'mixed',
      origin: 'events[27].s_per_page_this_run',
      conditions: 'The REPAIRED field is also wrong here. convert_and_ship.py:1303 does ' +
                  '`run_pages = true_run_pages or pages`, so an all-resumed run silently swaps ' +
                  'the whole book in as the denominator to avoid a divide-by-zero. The emitted ' +
                  'COUNT stays honest (pages_converted_this_run: 0); the RATE does not.',
      display: `${UNDEFINED} — 0/0, guarded to 0\u00f71377`,
      naive: '0.00 s/pp (this run)',
      honest: false,
      census: ['N-059'],
      defect: {
        reason: 'The N-059 repair guards the division, not the publication: 0/0 becomes 0.00.',
        highlight: 'convert_and_ship.py:1302-1307, the `or pages` guard.',
        solution: 'Guard the RENDER, not just the divide: pages_converted_this_run == 0 ⇒ UNDEFINED.',
      },
    }),
    pages_converted_this_run: measure({
      id: 'convert.leg2.pages_converted_this_run', label: 'pages converted this run', value: 0,
      unit: 'pp',
      num: { label: 'pages converted', value: 0, unit: 'pp' },
      den: { label: 'pages in the book', value: 1377, unit: 'pp' },
      evidence: 'event', population: 'this-run',
      conditions: 'Honest and load-bearing: this is the field that proves the two rates above are ' +
                  'undefined. It was added after an all-resumed run emitted 1377 for a 1-second ' +
                  'resume (caught live 2026-08-31 07:40:59).',
      display: '0 of 1377 pages converted this run (7 slices admitted from cache)',
    }),
    peak_vram_mib: measure({
      id: 'convert.leg2.peak_vram_mib', label: 'peak VRAM', value: null, unit: 'MiB',
      num: null, den: null, evidence: 'event', population: 'this-run',
      origin: 'events[27].peak_vram_mib = null',
      conditions: 'null, not zero. Nothing sampled because nothing ran. docs/34: a duration or ' +
                  'reading nobody reported renders UNREAD.',
      display: `${UNREAD} — nothing ran, so nothing was sampled`,
      naive: '0 MiB',
      honest: false,
      census: ['N-066'],
      defect: {
        reason: 'A null VRAM reading rendered as 0 would claim the GPU was idle-and-measured.',
        highlight: 'events[27].peak_vram_mib === null.',
        solution: 'Render UNREAD. Carry leg 1\u2019s 9395 MiB forward only if labelled "leg 1".',
      },
    }),
    cost_s: measure({
      id: 'convert.leg2.cost_s', label: 'total GPU cost of this book', value: 3834.2, unit: 's',
      num: { label: 'sum of wall_s across all slices, all runs', value: 3834.2, unit: 's' },
      den: { label: 'pages in the book', value: 1377, unit: 'pp' },
      evidence: 'event', population: 'whole-book',
      origin: 'events[27].cost_s',
      conditions: 'THE HONEST FIGURE FOR THIS LEG. Accumulated from each resumed slice\u2019s .done ' +
                  'file. It structurally omits retry_wall_s from resumed slices (census N-064) — ' +
                  'but on THIS book leg 1 recorded retry_wall_s 0.0 and no slice was ever retried, ' +
                  'so the understatement here is exactly zero. Verified, not assumed.',
      display: '3834.2s total GPU cost for 1377 pp (2.78 s/pp book average) — carried from leg 1',
    }),
    promised_eta_s: measure({
      id: 'convert.leg2.promised_eta_s', label: 'ETA filed before the resume', value: 0, unit: 's',
      num: { label: 'pages_this_run', value: 0, unit: 'pp' },
      den: { label: 'resumed_pages_assumed', value: 1377, unit: 'pp' },
      evidence: 'event', population: 'this-run',
      origin: 'events[18]: eta_s 0, pages_this_run 0, resumed_pages_assumed 1377',
      conditions: 'DEVIATION FROM THE BRIEF, IN THE PIPELINE\u2019S FAVOUR. Census N-055 says the ' +
                  'pre-work ETA always promises the whole book on a resume. On THIS voyage it did ' +
                  'not: the estimate event correctly declared eta 0s, 0 pages this run, 1377 ' +
                  'pages assumed resumed. N-055 did not fire here.',
      display: '0s promised, 0 pages this run, 1377 assumed already done — correct',
    }),
  }),
});

/* ==========================================================================================
 * 5 · THE AUDITS — three scorings, two phases, and the REASONS the verdicts fired
 * ========================================================================================== */

const runsMeasure = (id, shown, total, phase) => measure({
  id, label: 'omission runs found', value: shown, unit: 'runs',
  num: { label: 'runs SHOWN (display cap)', value: shown, unit: 'runs' },
  den: { label: 'runs_total (the real count)', value: total, unit: 'runs' },
  evidence: 'event', population: 'whole-book',
  origin: `audit/scored (${phase}): runs=${shown}, runs_total=${total}`,
  conditions: `The event's \`runs\` field is len(block["runs"]) — the length of a list already ` +
              `sliced [:25] and sorted by words descending. It is the CAP, not the count. ` +
              `runs_total rides beside it because SYM-066 was repaired at the source (NUM-3, ` +
              `signed 2026-08-31); the fixture proves the repair reached production.`,
  display: `${shown} shown of ${total} omission runs (display cap ${AUDIT_LAW.RUNS_CAP}, ` +
           `longest first)`,
  naive: `${shown} omission runs`,
  honest: false,
  census: ['N-028'],
  defect: {
    reason: 'A display cap rendered as a count. 25 is the ceiling; the truth is ' + total + '.',
    highlight: `fidelity_audit.py:383 (\`[:25]\`) and convert_and_ship.py:54/80 ` +
               `(\`runs=len(conv["runs"])\`).`,
    solution: 'Always render "N shown of runs_total". runs_total is present in the event — there ' +
              'is no excuse. If runs_total is absent (null), say so; never fall back to the cap.',
  },
});

export const AUDITS = Object.freeze([
  {
    id: 'audit.convert.1', phase: 'convert', at: t_audit1, verdict: 'fail',
    label: 'Convert audit — first scoring',
    fields: {
      doc_survival: measure({
        id: 'audit.convert.doc_survival', label: 'document survival', value: 0.9334, unit: 'ratio',
        num: { label: 'window-weighted surviving score (weighted_sum)', value: null, unit: 'windows' },
        den: { label: 'total witness windows (total_windows)', value: null, unit: 'windows' },
        evidence: 'event', population: 'whole-book',
        origin: 'events[13].doc_survival; definition fidelity_audit.py:371',
        conditions: 'weighted_sum \u00f7 total_windows, where a window is 12 words ' +
                    '(WINDOW_MIN_WORDS 6 for a short tail) of the pymupdf witness, matched ' +
                    'FUZZILY into the Marker markdown. It is NOT a page ratio and NOT a character ' +
                    'ratio. BOTH SIDES OF THIS RATIO ARE ABSENT FROM THE RECORD: neither ' +
                    'weighted_sum nor total_windows is written to the event or the manifest. ' +
                    'Scored over 1372 pages; 5 of the book\u2019s 1377 pages produced no ' +
                    'scoreable witness text and were dropped from the denominator silently.',
        display: '0.9334 window-survival (12-word fuzzy windows, pymupdf witness; both sides of ' +
                 'the ratio UNREAD; 1372 of 1377 pages scored)',
        naive: '93.3% of the document survived',
        honest: false,
        census: ['N-088'],
        defect: {
          reason: 'docs/34 requires a ratio to print both its sides; this one cannot, because ' +
                  'the pipeline discards weighted_sum and total_windows at the moment of ' +
                  'computation. It is also routinely misread as a page or character percentage.',
          highlight: 'fidelity_audit.py:371 computes and immediately drops both operands.',
          solution: 'Render the unit ("window-survival"), name the witness, and state the ' +
                    'denominator as UNREAD. Do not print it as a plain percentage beside ' +
                    'page_coverage, which is a different ratio (0.9978).',
        },
      }),
      runs: runsMeasure('audit.convert.runs', 25, 531, 'convert'),
      degeneration: measure({
        id: 'audit.convert.degeneration', label: 'degeneration tripwire', value: true, unit: 'bool',
        evidence: 'event', population: 'whole-book',
        conditions: 'True if any block \u2265200 chars has zlib ratio \u22640.20 or max trigram ' +
                    'repeat \u226540, or any normalized line repeats more than 20 times. This is ' +
                    'ONE OF ONLY TWO SIGNALS IN THE SYSTEM THAT CAN REACH "fail". It fired.',
        display: 'TRIPPED \u2014 24 degenerate blocks, worst at line 5524 (34,523 chars, zlib 0.023)',
      }),
      verdict: 'fail',
      verdictReason: {
        fired: 'convert.tripwires.degeneration',
        text: 'FAIL because the degeneration tripwire fired \u2014 NOT because survival was 0.9334.',
        detail: 'compute_verdict (fidelity_audit.py:422-465): survival below CLEAN_DOC_FLAG 0.97 ' +
                'and 241 flagged pages are LOCALIZERS and reach at most "flag". Only degeneration ' +
                'and the analyst near-exact gate reach "fail". Acceptable books measure 0.76-0.96 ' +
                'survival from legitimate reflow, so gating on survival would false-fail good work.',
      },
    },
  },
  {
    id: 'audit.convert.2', phase: 'convert', at: t_audit2, verdict: 'fail',
    label: 'Convert audit — re-scored after the resume (identical)',
    identicalTo: 'audit.convert.1',
    note: 'Every field byte-identical to the 22:35:15Z scoring: doc_survival 0.9334, runs 25 of ' +
          '531, degeneration true. The audit re-ran over the same cached markdown, so this is a ' +
          'repetition, not a second opinion. A panel that stacks these as two data points is ' +
          'double-counting one measurement.',
    fields: null,
  },
  {
    id: 'audit.analyst', phase: 'analyst', at: t_audit3, verdict: 'fail',
    label: 'Analyst audit — the scoring that held the bundle',
    fields: {
      doc_survival: measure({
        id: 'audit.analyst.doc_survival', label: 'analyst near-exact containment', value: 0.9402,
        unit: 'ratio',
        num: { label: 'Marker windows found VERBATIM in the analyst output', value: null,
               unit: 'windows' },
        den: { label: 'total Marker windows (len(windows))', value: null, unit: 'windows' },
        evidence: 'event', population: 'whole-book',
        origin: 'events[30].doc_survival; definition fidelity_audit.py:414',
        conditions: 'failed.count(False) \u00f7 len(windows). EXACT containment, no fuzzy match: ' +
                    'the Marker document IS the reference, so any rewording counts as loss. ' +
                    'A DIFFERENT MEASUREMENT FROM THE CONVERT doc_survival ABOVE despite the ' +
                    'identical field name. Both sides absent from the record.',
        display: '0.9402 verbatim-window containment vs the Marker doc (exact match, no fuzzy; ' +
                 'both sides of the ratio UNREAD)',
        naive: '94.0% survived (better than convert\u2019s 93.3%)',
        honest: false,
        census: ['N-088'],
        defect: {
          reason: 'Same name, different measurement, different matcher, different reference. ' +
                  'Placed beside the convert figure it invites a comparison that is meaningless.',
          highlight: 'fidelity_audit.py:414 (exact) vs :371 (fuzzy, weighted).',
          solution: 'Never place the two doc_survival numbers on one axis. Label this one ' +
                    '"verbatim containment vs Marker".',
        },
      }),
      runs: runsMeasure('audit.analyst.runs', 25, 404, 'analyst'),
      runLocation: measure({
        id: 'audit.analyst.run_page', label: 'where the analyst runs are', value: null, unit: 'page',
        evidence: 'manifest', population: 'whole-book',
        origin: 'manifest.fidelity.analyst.runs[*].page — all 25 are null',
        conditions: 'audit_analyst calls _merge_runs(..., page=None) by construction: the analyst ' +
                    'audit compares two markdown strings and has no page index at all. All 25 ' +
                    'shown runs carry page: null.',
        display: `${UNREAD} \u2014 the analyst audit has no page index; runs are locatable only ` +
                 `by their excerpt text`,
        naive: 'page 0',
        honest: false,
        census: [],
        defect: {
          reason: 'The error-structure protocol demands a HIGHLIGHT ("where, exactly"). For the ' +
                  'analyst phase the pipeline cannot supply one.',
          highlight: 'All 25 runs: page null. Worst is 576 words, excerpt begins ' +
                     '"{1 - t} \\right)/{\\rm e}}".',
          solution: 'Surface the excerpt as the locator and say the page is unavailable. Do not ' +
                    'render a zero or blank page number.',
        },
      }),
      verdict: 'fail',
      verdictReason: {
        fired: 'BOTH analyst fail gates',
        text: 'FAIL on two independent triggers, either of which alone is sufficient.',
        detail: 'Gate 1: doc_survival 0.9402 < ANALYST_DOC_FAIL 0.995. Gate 2: the longest ' +
                'omission run is 576 words \u2265 ANALYST_RUN_WORDS 25 (23\u00d7 the threshold) ' +
                '\u2014 and 404 runs exist, of which 25 are shown. The convert degeneration ' +
                'tripwire is ALSO still true, so this bundle fails three ways.',
      },
    },
  },
]);

/* ==========================================================================================
 * 6 · THE ANALYST PHASE — the counters that exist nowhere in the event stream
 * ========================================================================================== */

export const ANALYST = Object.freeze({
  id: 'analyst',
  label: 'Analyst phase (qwen3:8b, local, program "readability")',
  model: MANIFEST_ANALYST.model,
  backend: MANIFEST_ANALYST.backend,
  program: MANIFEST_ANALYST.program,
  emittedEvents: 0,
  note: 'ZERO events across both runs. No analyst/start, no analyst/done, no heartbeat in the ' +
        'stream. Every number below reached us ONLY because the manifest was written at the end. ' +
        'chunks_generated and goodput_accepted_tok_s are recorded here for the first time ever.',
  fields: Object.freeze({
    chunks_total: measure({
      id: 'analyst.chunks_total', label: 'chunks in the book', value: 957, unit: 'chunks',
      num: { label: 'chunks_resumed + chunks_generated', value: 957, unit: 'chunks' },
      den: null, evidence: 'derived', population: 'whole-book',
      conditions: '641 resumed + 316 generated = 957. Independently: 928 passed + 29 rejected + ' +
                  '0 failed = 957. Both identities check exactly, which is the only reason we can ' +
                  'trust the split at all.',
      display: '957 chunks (641 resumed + 316 generated; 928 passed + 29 rejected + 0 failed)',
    }),
    chunks_resumed: measure({
      id: 'analyst.chunks_resumed', label: 'chunks admitted from run 1', value: 641, unit: 'chunks',
      num: { label: 'chunks_resumed', value: 641, unit: 'chunks' },
      den: { label: 'chunks in the book', value: 957, unit: 'chunks' },
      evidence: 'manifest', population: 'prior-run',
      origin: 'manifest.analyst.chunks_resumed',
      conditions: 'THE FIELD THE OPERATOR IS NEVER SHOWN. It is stripped by the frontmatter ' +
                  'writer\u2019s whitelist and by the analyst/done event\u2019s whitelist (which ' +
                  'did not fire here anyway), and the widget never projects the progress file\u2019s ' +
                  'own `resumed` field. It is also the only evidence of how far run 1 got before ' +
                  'the power cut. Its cost in seconds and tokens is UNREAD forever.',
      display: '641 of 957 chunks (67.0%) carried over from run 1 \u2014 their seconds and tokens ' +
               'are UNREAD',
      naive: '(not shown at all)',
      honest: false,
      census: ['N-005'],
      defect: {
        reason: 'Silenced on every human channel, which is what makes every other analyst number ' +
                'on the glass unreadable — you cannot judge 928 passed or 4634.4s without it.',
        highlight: 'observability/acceptance.py:41; convert_and_ship.py:1264-1273, :1338-1347.',
        solution: 'MANDATORY on any surface that shows chunks_passed or duration_s. If it is ' +
                  'absent from the source record, that surface must print "resume state UNKNOWN".',
      },
    }),
    chunks_generated: measure({
      id: 'analyst.chunks_generated', label: 'chunks generated this run', value: 316, unit: 'chunks',
      num: { label: 'chunks_generated', value: 316, unit: 'chunks' },
      den: { label: 'chunks in the book', value: 957, unit: 'chunks' },
      evidence: 'manifest', population: 'this-run',
      conditions: 'The honest this-run numerator, and the only correct partner for duration_s and ' +
                  'for every token counter (tokens_counted_calls is also 316). First voyage on ' +
                  'which this field was ever recorded.',
      display: '316 of 957 chunks (33.0%) generated this run \u2014 the denominator for every ' +
               'this-run rate below',
    }),
    chunks_passed: measure({
      id: 'analyst.chunks_passed', label: 'chunks passed the fence', value: 928, unit: 'chunks',
      num: { label: 'chunks_passed', value: 928, unit: 'chunks' },
      den: { label: 'chunks in the book', value: 957, unit: 'chunks' },
      evidence: 'manifest', population: 'whole-book',
      conditions: 'A WHOLE-BOOK count. It includes all 641 resumed chunks. Arithmetically correct ' +
                  'and catastrophically misleading the moment it is placed beside duration_s, ' +
                  'which covers only 316 of these chunks.',
      display: '928 of 957 chunks passed (whole book, both runs \u2014 includes the 641 resumed)',
      naive: '928\u2713 in 4634.4s',
      honest: false,
      census: ['N-007'],
      defect: {
        reason: 'Denominator trap: a book-sized numerator paired with a run-sized wall clock ' +
                'implies a throughput the GPU never achieved (928 \u00f7 4634.4s = 0.20 chunks/s ' +
                'vs the true this-run 316 \u00f7 4634.4s = 0.068).',
        highlight: 'manifest.analyst.chunks_passed 928 vs duration_s 4634.4 (316 chunks).',
        solution: 'Print the population in the same breath: "928 of 957, whole book". Any rate ' +
                  'must use chunks_generated 316.',
      },
    }),
    chunks_rejected: measure({
      id: 'analyst.chunks_rejected', label: 'chunks rejected by the link fence', value: 29,
      unit: 'chunks',
      num: { label: 'chunks_rejected', value: 29, unit: 'chunks' },
      den: { label: 'chunks in the book', value: 957, unit: 'chunks' },
      evidence: 'manifest', population: 'whole-book',
      conditions: 'Whole-book. How many of the 29 occurred in run 2 is UNREAD, so the 4012-token ' +
                  'gap between tokens_output_total and tokens_accepted_output cannot be divided ' +
                  'by a known rejection count.',
      display: '29 of 957 chunks rejected (3.0%, whole book) \u2014 run-2 share UNREAD',
      naive: '29 rejected this run',
      honest: false,
      census: ['N-008'],
      defect: {
        reason: 'Whole-book count read as a this-run count; also double-counted downstream when ' +
                'a book is resumed twice.',
        highlight: 'manifest.analyst.chunks_rejected 29; tokens gap 279174 - 275162 = 4012.',
        solution: 'Label as whole-book and mark the run-2 share UNREAD.',
      },
    }),
    chunks_failed: measure({
      id: 'analyst.chunks_failed', label: 'chunks failed (backend/API errors)', value: 0,
      unit: 'chunks',
      num: { label: 'chunks_failed recorded', value: 0, unit: 'chunks' },
      den: { label: 'chunks in the book', value: 957, unit: 'chunks' },
      evidence: 'manifest', population: 'mixed',
      conditions: 'Failures are deliberately NOT journalled, so a resumed run cannot replay run ' +
                  '1\u2019s failures into this counter. 0 means "none recorded", not "none ' +
                  'occurred". For the 641 resumed chunks this number carries no information at all.',
      display: '0 recorded \u2014 run-1 failures are UNREAD by construction (failures are not ' +
               'journalled)',
      naive: '0 failed',
      honest: false,
      census: ['N-009'],
      defect: {
        reason: 'A reset masquerading as a count, and suppressed on the Dock even when non-zero.',
        highlight: 'analyst.py:344-350 (failures never journalled); the Dock prints ' +
                   '"938\u2713 0\ud83d\udee1" and omits the failure count entirely.',
        solution: 'Print "0 recorded (run 1 UNREAD)". Never render a bare 0 as an all-clear.',
      },
    }),
    duration_s: measure({
      id: 'analyst.duration_s', label: 'analyst wall clock', value: 4634.4, unit: 's',
      num: { label: 'wall seconds of the analyst phase', value: 4634.4, unit: 's' },
      den: { label: 'chunks GENERATED in that wall time', value: 316, unit: 'chunks' },
      evidence: 'manifest', population: 'this-run',
      origin: 'manifest.analyst.duration_s',
      conditions: 'RUN 2 ONLY. Covers the 316 generated chunks and includes the skip-time for the ' +
                  '641 resumed ones, API pacing, and the terminal model unload. Sits inside dark ' +
                  'zone 2 (4675s of silence), leaving 40.6s of that window unexplained. Run 1\u2019s ' +
                  'analyst seconds \u2014 the 641 chunks across 4h40m \u2014 were never written ' +
                  'anywhere and are permanently UNREAD.',
      display: '4634.4s covering 316 generated chunks (14.7 s/chunk); run 1\u2019s analyst seconds ' +
               'UNREAD',
      naive: 'analysis done in 4634.4s',
      honest: false,
      census: ['N-013', 'N-007'],
      defect: {
        reason: 'Self-poisoning denominator: it is paired everywhere with whole-book chunk counts, ' +
                'and it is fed back into the throughput estimator alongside whole-book character ' +
                'counts, so every resumed run permanently raises the learned rate.',
        highlight: 'manifest.analyst.duration_s 4634.4 beside chunks_passed 928.',
        solution: 'Never render it beside a whole-book count without the resumed count between ' +
                  'them. Label it "run 2". State that the book\u2019s total analyst time is UNREAD.',
      },
    }),
    goodput_accepted_tok_s: measure({
      id: 'analyst.goodput_accepted_tok_s', label: 'accepted-output goodput', value: 59.37,
      unit: 'tok/s',
      num: { label: 'tokens_accepted_output, this run', value: 275162, unit: 'tok' },
      den: { label: 'duration_s, this run', value: 4634.4, unit: 's' },
      evidence: 'manifest', population: 'this-run',
      origin: 'manifest.analyst.goodput_accepted_tok_s',
      conditions: MANIFEST_ANALYST.goodput_conditions,
      display: '59.37 accepted-output tok/s (275,162 tok \u00f7 4634.4s, run 2 only, 316 calls; ' +
               'wall includes resumed-chunk skips, pacing and the terminal model unload)',
      // HONEST: both sides are drawn from the same population, and the field ships its own
      // conditions string. It is NOT the book's throughput and NOT a decode rate.
      honest: true,
    }),
    tokens_prompt_total: measure({
      id: 'analyst.tokens_prompt_total', label: 'prompt tokens', value: 314311, unit: 'tok',
      num: { label: 'summed prompt tokens', value: 314311, unit: 'tok' },
      den: { label: 'calls that reported a count', value: 316, unit: 'calls' },
      evidence: 'manifest', population: 'this-run',
      conditions: 'A PARTIAL SUM. The manifest\u2019s own conditions line says cached prefills ' +
                  'report none, so calls served from cache contribute zero and are ' +
                  'indistinguishable from calls with no prompt.',
      display: '\u2265314,311 prompt tok over 316 counted calls (lower bound \u2014 cached ' +
               'prefills report none)',
      naive: '314,311 prompt tokens',
      honest: false,
      census: [],
      defect: {
        reason: 'A lower bound presented as a total; a cached prefill is not a measured prefill.',
        highlight: 'manifest.analyst.tokens_prompt_total 314311 / tokens_prompt_counted_calls 316.',
        solution: 'Render with a \u2265 and name the counted-call denominator. Never derive a ' +
                  'prefill rate from it.',
      },
    }),
    tokens_output_total: measure({
      id: 'analyst.tokens_output_total', label: 'output tokens generated', value: 279174,
      unit: 'tok',
      num: { label: 'output tokens', value: 279174, unit: 'tok' },
      den: { label: 'counted calls', value: 316, unit: 'calls' },
      evidence: 'manifest', population: 'this-run',
      conditions: 'Run 2 only, 316 counted calls. 279,174 generated of which 275,162 were ' +
                  'accepted: 4,012 tokens (1.44%) were produced and thrown away by fence ' +
                  'rejections.',
      display: '279,174 tok generated over 316 calls; 275,162 accepted, 4,012 discarded (1.4%)',
    }),
  }),
});

/* ==========================================================================================
 * 7 · THE LOCALIZERS — evidence the operator needs, none of which gates anything
 * ========================================================================================== */

const _fid = MANIFEST_FIDELITY_CONVERT;
const _degen = _fid.tripwires.degeneration_detail;

export const LOCALIZERS = Object.freeze({
  pages_flagged: measure({
    id: 'fidelity.pages_flagged', label: 'pages below the survival flag',
    value: _fid.pages_flagged.length, unit: 'pages',
    num: { label: 'pages scoring below CLEAN_PAGE_FLAG 0.85', value: _fid.pages_flagged.length,
           unit: 'pages' },
    den: { label: 'pages scored', value: _fid.pages_scored, unit: 'pages' },
    evidence: 'manifest', population: 'whole-book',
    conditions: 'Full page list is present in the manifest (all 241, not capped). Scored over ' +
                '1372 pages, not 1377. This signal LOCALIZES and can reach at most "flag" — it ' +
                'is not why the bundle was held.',
    display: `241 of 1372 scored pages below 0.85 survival (17.6%) \u2014 localizer, not a gate`,
  }),
  pages_scored: measure({
    id: 'fidelity.pages_scored', label: 'pages the audit could score', value: _fid.pages_scored,
    unit: 'pages',
    num: { label: 'pages scored', value: _fid.pages_scored, unit: 'pages' },
    den: { label: 'pages in the book', value: 1377, unit: 'pages' },
    evidence: 'manifest', population: 'whole-book',
    conditions: '5 of the book\u2019s 1377 pages yielded no scoreable witness text and were ' +
                'dropped from every audit denominator without any field announcing it.',
    display: '1372 of 1377 pages scored \u2014 5 pages silently excluded from every audit ratio',
    naive: '1372 pages',
    honest: false,
    census: [],
    defect: {
      reason: 'A silently shrinking denominator. Nothing in the record says which 5 pages, or why.',
      highlight: 'manifest pages_scored 1372 vs events probe pages 1377.',
      solution: 'Always render "N of 1377 scored" and mark the 5 as UNSCORED, not as surviving.',
    },
  }),
  page_coverage: measure({
    id: 'fidelity.page_coverage', label: 'pages with any surviving text', value: 0.9978,
    unit: 'ratio',
    num: { label: 'pages with score > 0 (surviving)', value: _fid.tripwires.page_coverage.surviving,
           unit: 'pages' },
    den: { label: 'pages with witness text (with_text)', value: _fid.tripwires.page_coverage.with_text,
           unit: 'pages' },
    evidence: 'manifest', population: 'whole-book',
    conditions: 'A COMPLETELY DIFFERENT RATIO FROM doc_survival, and the only one on this glass ' +
                'whose two sides are both recorded. 3 pages vanished entirely.',
    display: '1369 of 1372 pages retain some text (99.78%) \u2014 3 pages wholly lost',
  }),
  degeneration_blocks: measure({
    id: 'fidelity.degeneration.blocks', label: 'degenerate blocks', value: _degen.blocks_total,
    unit: 'blocks',
    num: { label: 'blocks shown in `worst`', value: _degen.worst.length, unit: 'blocks' },
    den: { label: 'blocks_total', value: _degen.blocks_total, unit: 'blocks' },
    evidence: 'manifest', population: 'whole-book',
    conditions: 'The NUM-3 repair is present and working here: blocks_total 24 and ' +
                'worst_capped_at 10 both ride beside the truncated list. The list length (10) ' +
                'must never be read as the count (24). Worst block: line 5524, 34,523 chars, ' +
                'zlib 0.023 (threshold \u22640.20), max trigram 129 (threshold \u226540).',
    display: '24 degenerate blocks, worst 10 shown (cap 10) \u2014 worst at line 5524, ' +
             '34,523 chars, zlib 0.023',
  }),
  repeated_lines: measure({
    id: 'fidelity.degeneration.repeated_lines', label: 'most-repeated line', value: 0,
    unit: 'repeats',
    num: null, den: null,
    evidence: 'manifest', population: 'whole-book',
    conditions: 'degeneration.py: `repeated_lines = max_run if max_run > DEGEN_LINE_REPEAT else 0`. ' +
                'The 0 means "no line repeated MORE THAN 20 times". A book whose worst run is ' +
                'exactly 20 identical lines publishes 0, byte-identical to a book with no ' +
                'repetition. The true maximum is discarded.',
    display: `${UNREAD} \u2014 no line-run exceeded 20 repeats; the actual maximum is suppressed ` +
             `(the tripwire fired on zlib/trigram, not on line repeats)`,
    naive: '0 repeated lines',
    honest: false,
    census: ['N-029'],
    defect: {
      reason: 'A threshold reset published as a count. 0 does not mean zero repetition.',
      highlight: 'manifest.fidelity.convert.tripwires.degeneration_detail.repeated_lines = 0, ' +
                 'beside flagged = true.',
      solution: 'Render UNREAD with the threshold named. Never draw it as a zero bar.',
    },
  }),
  reverse_sample: measure({
    id: 'fidelity.reverse_sample', label: 'anti-hallucination reverse check', value: 0.765,
    unit: 'ratio',
    num: { label: 'sampled output windows found in the witness', value: 153, unit: 'windows' },
    den: { label: 'output windows sampled (REVERSE_SAMPLE_N)', value: 200, unit: 'windows' },
    evidence: 'manifest', population: 'whole-book',
    conditions: 'Exact containment (no fuzzy) of 200 randomly sampled OUTPUT windows in the ' +
                'pymupdf witness, seed 20260720 so it is deterministic. Table restructuring and ' +
                'reflow legitimately break exact containment, so a miss is not proof of ' +
                'invention. This value gates NOTHING: compute_verdict never reads it.',
    display: '153 of 200 sampled output windows found verbatim in the source (76.5%, exact match, ' +
             'seed 20260720) \u2014 not a hallucination rate, and not a gate',
    naive: '23.5% hallucinated',
    honest: false,
    census: [],
    defect: {
      reason: 'Read as an invention rate it accuses the converter of fabricating a quarter of the ' +
              'book; the matcher is exact, so reflow alone produces misses.',
      highlight: 'fidelity_audit.py:328-337; n=200 of an unrecorded total window count.',
      solution: 'Label "verbatim containment, sampled n=200". Never call it hallucination.',
    },
  }),
  asset_delta: measure({
    id: 'fidelity.asset_delta', label: 'asset files vs embedded images', value: 76, unit: 'files',
    num: { label: 'asset files Marker wrote', value: 232 + 76, unit: 'files' },
    den: { label: 'images embedded in the PDF', value: _fid.tripwires.embedded_images,
           unit: 'images' },
    evidence: 'manifest', population: 'whole-book',
    conditions: 'A SIGNED DIFFERENCE (asset_count - embedded_images), not a loss count. Positive ' +
                'means Marker wrote MORE files than the PDF had embedded images \u2014 typically ' +
                'extra crops of figures and tables.',
    display: '308 asset files written vs 232 embedded images (+76 \u2014 a surplus, not a loss)',
    naive: '76 assets missing',
    honest: false,
    census: [],
    defect: {
      reason: 'A bare signed delta beside a fidelity audit reads as damage; here it is surplus.',
      highlight: 'asset_delta 76, embedded_images 232.',
      solution: 'Print both sides with the sign and the word "surplus"/"shortfall".',
    },
  }),
  dict_hit: measure({
    id: 'fidelity.dict_hit', label: 'dictionary hit rate', value: null, unit: 'ratio',
    evidence: 'manifest', population: 'n/a',
    conditions: 'null: the wordfreq dictionary is absent from this machine, so the check never ran.',
    display: `${UNREAD} \u2014 not measured (wordfreq absent)`,
    naive: '0.0',
    honest: false,
    census: [],
    defect: {
      reason: 'docs/34: a value nobody reported renders UNREAD, never 0.0.',
      highlight: 'tripwires.dict_hit = null.',
      solution: 'Render UNREAD and say why it was not measured.',
    },
  }),
  garbage_rate: measure({
    id: 'fidelity.garbage_rate', label: 'garbage token rate', value: null, unit: 'ratio',
    evidence: 'manifest', population: 'n/a',
    conditions: 'null BY DESIGN: garbage_rate is computed on the scan lane only, and this book ' +
                'ran the clean lane. Not a missing measurement \u2014 an inapplicable one.',
    display: `${UNREAD} \u2014 clean lane; this check applies to the scan lane only`,
    naive: '0.0',
    honest: false,
    census: [],
    defect: {
      reason: 'A null that means "not applicable" rendered as 0.0 claims a perfect score on a ' +
              'test that was never taken.',
      highlight: 'tripwires.garbage_rate = null, lane = clean.',
      solution: 'Render UNREAD with the reason "clean lane". Distinguish N/A from UNMEASURED.',
    },
  }),
});

/* ==========================================================================================
 * 8 · ALARMS — EEMUA 191 / ISA-18.2: every alarm names its consequence AND its operator response
 * Priority reflects consequence and TIME-TO-ACT. Six alarms across 7.5 hours is absorbable;
 * the 179 false-honesty rows of the census are NOT alarms and must never be raised as such.
 * ========================================================================================== */

export const ALARMS = Object.freeze([
  {
    id: 'ALM-LIVENESS', priority: 1, at: t_audit1, state: 'would-have-fired',
    title: 'LIVENESS LOST — no event for 5h 02m',
    consequence: 'The analyst died at chunk 641 and nobody knew for 5 hours. This is the alarm ' +
                 'that would have saved the night, and it does not exist.',
    timeToAct: 'minutes — a dead analyst holds the GPU and the book',
    reason: 'The inline analyst code path emits no events at all; analyst/start and analyst/done ' +
            'exist only on the --resume path. The only liveness signal was ' +
            '.analyst-progress.json, overwritten in place with no history.',
    highlight: 'dark-1: 2026-08-31T22:35:15Z → 2026-09-01T03:37:28Z, 18133s, zero events.',
    response: 'Watch .analyst-progress.json mtime. Stale > 300s while a book is in flight ⇒ the ' +
              'analyst is dead: kill the orphan, reap the GPU lock, re-run with --resume.',
    fired: false,
  },
  {
    id: 'ALM-IDLE-AFTER-REBOOT', priority: 1, at: t_reboot, state: 'would-have-fired',
    title: 'MACHINE IDLE AFTER UNATTENDED REBOOT — 1h 45m 43s',
    consequence: 'A powered, healthy machine did nothing for nearly two hours with a book in ' +
                 'staging. Pure lost throughput, and it recurs on every power event.',
    timeToAct: 'immediate — every second is unrecoverable',
    reason: 'The widget has no autostart and the watcher is the widget\u2019s child, so a reboot ' +
            'leaves nothing to restart the pipeline. Recovery required a human to log in.',
    highlight: 'dead-idle: 01:48:17Z → ~03:34:00Z (testimony). First machine record after the ' +
               'reboot is stale-lock-reaped at 03:37:28Z.',
    response: 'Autostart the widget at logon, or run the watcher as a service. Until then: after ' +
              'any reboot, open the widget first.',
    fired: false,
  },
  {
    id: 'ALM-HELD', priority: 1, at: t_held, state: 'fired',
    title: 'BUNDLE HELD — verdict fail (analyst gate)',
    consequence: 'The book will not reach the vault. It waits in staging indefinitely.',
    timeToAct: 'hours — the bundle is stable but blocks the book',
    reason: 'Analyst near-exact containment 0.9402 < 0.995, AND the longest omission run is 576 ' +
            'words \u2265 25. Either alone is a fail. The convert degeneration tripwire is also ' +
            'still true.',
    highlight: '404 analyst omission runs (25 shown), worst 576 words; 24 degenerate blocks, ' +
               'worst at line 5524.',
    response: 'Open the held bundle. Inspect the 25 shown runs by excerpt (no page index exists ' +
              'for the analyst phase). Repair or bless; a bless is the operator\u2019s signature, ' +
              'never the pipeline\u2019s.',
    fired: true,
  },
  {
    id: 'ALM-DEGENERATION', priority: 2, at: t_audit1, state: 'fired',
    title: 'DEGENERATION TRIPWIRE — 24 blocks',
    consequence: 'Repetition-loop corruption in the converted markdown. This is the signal that ' +
                 'failed the convert phase; survival 0.9334 was never the reason.',
    timeToAct: 'hours',
    reason: 'zlib ratio 0.023 (threshold \u22640.20) and max trigram 129 (threshold \u226540) on a ' +
            '34,523-char block.',
    highlight: 'line 5524 (34,523 chars) — a Betas/Operating-Leverage table collapsed into one ' +
               'line; 9 more blocks shown of 24.',
    response: 'Open the .md at line 5524. Apply the banked signature: column-wrap → <br> inside ' +
              'table cells. Re-convert the slice, not the book.',
    fired: true,
  },
  {
    id: 'ALM-PAGE-FLAGS', priority: 3, at: t_audit1, state: 'fired',
    title: '241 of 1372 pages below 0.85 survival',
    consequence: 'Localized suspicion only. Acceptable books measure 0.76-0.96 from legitimate ' +
                 'reflow; this gates nothing.',
    timeToAct: 'days — advisory',
    reason: 'Page survival below CLEAN_PAGE_FLAG 0.85.',
    highlight: 'Full page list in the manifest (241 entries, uncapped). Densest cluster: pages ' +
               '505-543 and 1157-1163.',
    response: 'Sample 3 pages from the densest cluster against the PDF before deciding whether ' +
              'this is reflow or loss. Do not act on the count alone.',
    fired: true,
  },
  {
    id: 'ALM-FENCE', priority: 3, at: t_audit3, state: 'fired',
    title: '29 of 957 chunks rejected by the link fence',
    consequence: '4,012 output tokens generated and discarded (1.4% of run 2\u2019s output).',
    timeToAct: 'days — advisory',
    reason: 'Fence violation: the analyst\u2019s output failed the image-token multiset check.',
    highlight: 'Whole-book count; the run-2 share is UNREAD. A context overflow is re-labelled as ' +
               'a fence rejection by the same path, so these 29 may not all be link violations.',
    response: 'If the count climbs across voyages, check NUM_CTX against the largest chunk before ' +
              'blaming the fence.',
    fired: true,
  },
]);

/* ==========================================================================================
 * 9 · FLAT INDEX + HELPERS
 * ========================================================================================== */

function collect() {
  const out = {};
  const add = (o) => { for (const k in o) { const v = o[k]; if (v && v.id && 'honest' in v) out[v.id] = v; } };
  add(SPANS);
  add(CONVERT_LEG_1.fields);
  add(CONVERT_LEG_2.fields);
  add(ANALYST.fields);
  add(LOCALIZERS);
  for (const a of AUDITS) if (a.fields) add(a.fields);
  return Object.freeze(out);
}

/** Every measure in the voyage, keyed by id. */
export const FIELDS = collect();

/** Every field whose raw value must never reach the glass unmodified. */
export function dishonest() {
  return Object.values(FIELDS).filter(f => !f.honest);
}

/** Every field a panel may render straight from `value`. */
export function honest() {
  return Object.values(FIELDS).filter(f => f.honest);
}

/**
 * The ONLY sanctioned way to put a number on glass.
 * Pass a field id or a measure. Returns the honest string. Never returns a bare number.
 */
export function render(idOrField) {
  const f = typeof idOrField === 'string' ? FIELDS[idOrField] : idOrField;
  if (!f) return UNREAD;
  return f.display;
}

/** Fields touched by a given census row, e.g. byCensus('N-059'). */
export function byCensus(rowId) {
  return Object.values(FIELDS).filter(f => f.census.includes(rowId));
}

/* ==========================================================================================
 * 10 · THE AGGREGATE
 * ========================================================================================== */

export const VOYAGE = Object.freeze({
  title: 'Damodaran · Investment Valuation 4e · HELD',
  source: SOURCE_PDF,
  pages: 1377,
  lane: 'clean',
  laneReason: 'text_layer_present',
  analystMode: 'local',
  start: t_intake1,
  end: t_held,
  outcome: 'HELD',
  outcomeReason: 'verdict fail on the analyst gate (0.9402 < 0.995 and a 576-word omission run), ' +
                 'with the convert degeneration tripwire also true',
  eventCount: EVENTS.length,
  analystEventCount: 0,
  timeline: TIMELINE,
  spans: SPANS,
  legs: [CONVERT_LEG_1, CONVERT_LEG_2],
  audits: AUDITS,
  analyst: ANALYST,
  localizers: LOCALIZERS,
  alarms: ALARMS,
  fields: FIELDS,
  populations: POPULATIONS,
  law: AUDIT_LAW,

  /** The one-paragraph macro reading, per Tufte: legible whole, inspectable at every point. */
  headline:
    '1377 pages. 7h 26m 21s wall. The convert leg beat its own promise by 508.8s and then the ' +
    'audit failed it on degeneration. The analyst ran 641 chunks into a five-hour silence, the ' +
    'power failed, the machine rebooted itself and sat idle for 1h 45m, a human restarted it, ' +
    'the convert resumed 7/7 slices and converted nothing, the analyst finished the remaining ' +
    '316 chunks into a second silence, and the bundle was HELD. Of 26,781 wall seconds, 8,468.6 ' +
    'were instrumented and 22,808 produced no event at all.',

  /**
   * NEGATIVE CONTROL — what this glass looks like if it is LYING.
   * If a panel prints any of these, it has failed:
   */
  negativeControl: Object.freeze([
    '"converted in 0.0s" or "0.00 s/pp" anywhere on leg 2 — the resume converted nothing',
    '"peak VRAM 0 MiB" on leg 2 — the reading is null, not zero',
    '"928 chunks in 4634.4s" — a whole-book numerator over a run-sized denominator',
    '"0 failed" as an all-clear — failures are not journalled, so 0 carries no information',
    '"0 repeated lines" beside a tripped degeneration flag — the value is a threshold reset',
    '"25 omission runs" — 25 is the display cap; the counts are 531 and 404',
    '"93.3% survived" beside "94.0% survived" on one axis — two different measurements',
    '"23.5% hallucinated" from reverse_sample — the matcher is exact; reflow breaks it',
    '"76 assets missing" — the delta is +76, a surplus',
    'a solid uninterrupted timeline bar from 21:30Z to 04:56Z — 85% of it had no events',
    'the dark zones drawn in the same ink as measured work',
    'the power cut, the reboot and the idle window drawn as if the machine recorded them',
    'any "utilisation %" built on measured-work ÷ wall — run 1\u2019s analyst work is unmeasured',
    'a FAIL badge with no reason beside it',
    'an alarm with no operator response',
  ]),
});

export default VOYAGE;
