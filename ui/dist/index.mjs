import { jsx as t, jsxs as a, Fragment as K } from "react/jsx-runtime";
import { useState as g, useEffect as ne, useRef as le, useCallback as Q } from "react";
import { useAppApi as ie, useChatLauncher as ce } from "@kirocrew/app-sdk";
const Z = "hauntlet-warden", de = "hauntlet-warden", he = `${Z}/nightly-range-check`, M = `/apps/${Z}/api`, X = 4e3, pe = "Some client behaviours are out of reach of config.", ue = (e) => e.get(`${M}/state`), me = (e) => e.get(`${M}/history?limit=30`), we = (e) => e.get(`${M}/drift`), ge = (e) => e.post(`${M}/drift/check`, {}), fe = (e) => e.get(`${M}/summary`), xe = (e, n) => e.put(`${M}/settings`, n), be = (e) => e.post(`${M}/git-install`, { approve: !0 });
async function ye(e) {
  return (await e.get("/api/crons")).jobs.find((r) => r.app === Z && r.name === he) ?? null;
}
async function ke(e, n) {
  await e.post(`${M}/run-request`, {}), await e.post(`/api/crons/${encodeURIComponent(n.id)}/run`, {});
}
const ve = (e, n, r) => e.post(`/api/crons/${encodeURIComponent(n.id)}/enable`, { enabled: r });
function Ne(e) {
  let n = e.trim() || "No run yet.";
  return n.length > X && (n = n.slice(0, X) + `
[summary truncated]`), [
    "Here is the current Hauntlet Warden summary. Answer my question from it only.",
    "",
    "--- Warden summary ---",
    n,
    "--- end of summary ---",
    "",
    "Question: "
  ].join(`
`);
}
function $e(e) {
  if (!e) return null;
  const n = e.split("/").pop() ?? "";
  return /^(autopsy-[a-z0-9-]+-(naive|hardened)-[A-Za-z0-9_-]{8,64}|exorcist-delta-[A-Za-z0-9_-]{8,64})\.html$/.test(n) ? `${M}/reports/${n}` : null;
}
function ae(e, n = Date.now()) {
  if (!e) return "—";
  const r = Date.parse(e);
  if (Number.isNaN(r)) return e;
  const l = Math.round((n - r) / 1e3);
  if (l < 45) return "just now";
  const p = Math.round(l / 60);
  if (p < 60) return `${p} min ago`;
  const o = Math.round(p / 60);
  return o < 36 ? `${o} h ago` : `${Math.round(o / 24)} days ago`;
}
function _e(e) {
  if (!e) return "";
  const n = new Date(e);
  return Number.isNaN(n.getTime()) ? e : n.toLocaleString(void 0, { dateStyle: "medium", timeStyle: "short" });
}
function W(e) {
  const n = e instanceof Error ? e.message : String(e), r = n.match(/\{.*\}$/s);
  if (r)
    try {
      const l = JSON.parse(r[0]);
      if (Array.isArray(l.errors) && l.errors.length) return l.errors.join("; ");
      if (l.error) return String(l.error);
    } catch {
    }
  return n;
}
const L = { fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }, Se = (e) => /* @__PURE__ */ t("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: /* @__PURE__ */ t("polygon", { points: "6 4 20 12 6 20 6 4" }) }), Ce = (e) => /* @__PURE__ */ a("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: [
  /* @__PURE__ */ t("path", { d: "M21 12a9 9 0 1 1-2.64-6.36" }),
  /* @__PURE__ */ t("polyline", { points: "21 3 21 9 15 9" })
] }), Re = (e) => /* @__PURE__ */ t("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: /* @__PURE__ */ t("path", { d: "M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z" }) }), ee = (e) => /* @__PURE__ */ a("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: [
  /* @__PURE__ */ t("path", { d: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" }),
  /* @__PURE__ */ t("polyline", { points: "9 12 11 14 15 10" })
] }), ze = (e) => /* @__PURE__ */ a("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: [
  /* @__PURE__ */ t("path", { d: "M5 21V10a7 7 0 0 1 14 0v11l-2.5-2-2.3 2-2.2-2-2.2 2-2.3-2L5 21z" }),
  /* @__PURE__ */ t("circle", { cx: "9.5", cy: "10.5", r: "1", fill: "currentColor" }),
  /* @__PURE__ */ t("circle", { cx: "14.5", cy: "10.5", r: "1", fill: "currentColor" })
] }), oe = (e) => /* @__PURE__ */ t("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: /* @__PURE__ */ t("path", { d: "M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" }) }), Me = (e) => /* @__PURE__ */ a("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: [
  /* @__PURE__ */ t("path", { d: "M14 4h6v6" }),
  /* @__PURE__ */ t("path", { d: "M20 4l-9 9" }),
  /* @__PURE__ */ t("path", { d: "M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" })
] }), Le = (e) => /* @__PURE__ */ t("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: /* @__PURE__ */ t("polyline", { points: "9 6 15 12 9 18" }) }), Ae = (e) => /* @__PURE__ */ t("svg", { viewBox: "0 0 24 24", ...L, className: e.className, "aria-hidden": "true", children: /* @__PURE__ */ t("path", { d: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" }) }), u = [
  { id: "L0", name: "Clean", color: "#33D480" },
  { id: "L1", name: "Reached", color: "#EFE08A" },
  { id: "L2", name: "Echoed", color: "#FFC857" },
  { id: "L3", name: "Acted", color: "#FF9F5A" },
  { id: "L4", name: "Exposed", color: "#FF7A88" }
], m = {
  page: "#000000",
  s1: "#19161D",
  s2: "#28242E",
  border: "#352F3D",
  text: "#FAFAFA",
  muted: "#A39FAB",
  accent: "#9046FF",
  accentText: "#C59EFF",
  info: "#69A0F6"
};
function Fe(e) {
  return u.find((n) => n.id === e) ?? null;
}
const Y = {
  present: u[0].color,
  review: u[1].color,
  weaker: u[3].color,
  missing: u[4].color,
  "n/a": m.muted
}, Ee = {
  ok: { label: "All commands passed", color: u[0].color },
  failed: { label: "Selftest failed", color: u[4].color },
  error: { label: "Run had errors", color: u[3].color },
  not_configured: { label: "Not configured", color: m.muted },
  skipped: { label: "Skipped (already running)", color: m.muted }
}, Te = `
.hw{--page:${m.page};--s1:${m.s1};--s2:${m.s2};--border:${m.border};--text:${m.text};--muted:${m.muted};
--accent:${m.accent};--accent-text:${m.accentText};--info:${m.info};
background:var(--page);color:var(--text);min-height:100%;flex:1;overflow-y:auto;
font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.hw *{box-sizing:border-box}
.hw-wrap{max-width:1180px;margin:0 auto;padding:28px 32px 56px}
.hw-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;flex-wrap:wrap;margin-bottom:22px}
.hw-kicker{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent-text);margin:0 0 6px;font-weight:600}
.hw-title{font-family:ui-serif,"New York",Charter,"Bitstream Charter",Cambria,"Times New Roman",serif;font-size:30px;line-height:1.1;margin:0;font-weight:600;letter-spacing:-.01em}
.hw-sub{color:var(--muted);margin:6px 0 0;font-size:13px}
.hw-actions{display:flex;gap:10px;flex-wrap:wrap}
.hw-btn{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 14px;border-radius:999px;border:1px solid var(--border);
background:var(--s1);color:var(--text);font:600 13px/1 inherit;cursor:pointer;transition:border-color .15s,background .15s}
.hw-btn:hover:not(:disabled){border-color:var(--accent-text)}
.hw-btn:focus-visible{outline:2px solid var(--accent-text);outline-offset:2px}
.hw-btn:disabled{opacity:.45;cursor:not-allowed}
.hw-btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.hw-btn.primary:hover:not(:disabled){background:#7d33f0;border-color:#7d33f0}
.hw-btn.ghost{background:transparent;border-color:var(--accent-text);color:var(--accent-text)}
.hw-btn.small{height:28px;padding:0 11px;font-size:12px}
.hw-btn svg{width:15px;height:15px;flex:none}
.hw-spin{animation:hw-spin 1s linear infinite}@keyframes hw-spin{to{transform:rotate(360deg)}}
.hw-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-bottom:18px}
.hw-tile{background:var(--s1);border:1px solid var(--border);border-radius:12px;padding:14px 16px;min-height:92px;position:relative;overflow:hidden}
.hw-tile::before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--tile,var(--border))}
.hw-tile h3{margin:0 0 8px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
.hw-tile .big{font-size:18px;font-weight:600;line-height:1.25}
.hw-tile .small{color:var(--muted);font-size:12px;margin-top:4px}
.hw-card{background:var(--s1);border:1px solid var(--border);border-radius:14px;margin-bottom:18px;overflow:hidden}
.hw-card-head{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:16px 18px;border-bottom:1px solid var(--border)}
.hw-card-head h2{margin:0;font-size:15px;font-weight:600}
.hw-card-head p{margin:2px 0 0;color:var(--muted);font-size:12px}
.hw-card-body{padding:6px 18px 16px}
.hw-legend{display:flex;gap:6px;flex-wrap:wrap}
.hw-chip{display:inline-flex;align-items:center;gap:6px;height:22px;padding:0 9px;border-radius:999px;font:700 11px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.02em;white-space:nowrap}
.hw-chip.fill{color:#000}
.hw-chip.line{border:1px solid currentColor;background:transparent}
.hw-chip .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.hw-table{width:100%;border-collapse:collapse}
.hw-table th{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:12px 10px 8px;border-bottom:1px solid var(--border)}
.hw-table td{padding:12px 10px;border-bottom:1px solid var(--border);vertical-align:middle}
.hw-table tr:last-child td{border-bottom:0}
.hw-room{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.hw-room small{display:block;font-family:ui-sans-serif,system-ui,sans-serif;color:var(--muted);font-size:11px;margin-top:2px}
.hw-cell{display:flex;align-items:center;gap:12px}
.hw-num{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--text)}
.hw-num .k{color:var(--muted)}
.hw-stack{display:flex;flex-direction:column;gap:4px;min-width:64px}
.hw-links{display:flex;flex-direction:column;gap:5px;max-width:300px}
.hw-rep{display:flex;align-items:baseline;gap:8px;min-width:0}
.hw-rep .hw-path{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;word-break:normal}
.hw-link{color:var(--accent-text);text-decoration:none;font-size:12px;font-weight:600;display:inline-flex;align-items:center;gap:5px}
.hw-link:hover{text-decoration:underline}
.hw-link svg{width:12px;height:12px}
.hw-path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--muted);word-break:break-all;user-select:all}
.hw-files{display:flex;flex-direction:column}
.hw-file{border-bottom:1px solid var(--border)}
.hw-file:last-child{border-bottom:0}
.hw-file summary{list-style:none;display:flex;align-items:center;gap:12px;padding:12px 2px;cursor:pointer}
.hw-file summary::-webkit-details-marker{display:none}
.hw-file summary .name{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.hw-file summary .count{color:var(--muted);font-size:12px}
.hw-caret{width:14px;height:14px;color:var(--muted);transition:transform .15s;flex:none}
.hw-file[open] .hw-caret{transform:rotate(90deg)}
.hw-items{margin:0 0 12px 26px;display:flex;flex-direction:column;gap:8px}
.hw-item{display:grid;grid-template-columns:170px 82px 1fr;gap:12px;align-items:start;background:var(--s2);border-radius:8px;padding:9px 12px}
.hw-item .rule{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;word-break:break-all}
.hw-item .detail{font-size:12px;color:var(--text)}
.hw-item .rooms{color:var(--muted);font-size:11px;margin-top:3px}
.hw-warn{margin:12px 0 4px;padding:10px 12px;border-radius:8px;border:1px solid ${u[2].color};color:${u[2].color};font-size:12px;display:flex;flex-direction:column;gap:4px}
.hw-note{color:var(--muted);font-size:12px;margin:12px 0 0;font-style:italic}
.hw-empty{display:flex;gap:18px;align-items:flex-start;padding:22px 4px 10px}
.hw-empty .glyph{width:44px;height:44px;border-radius:12px;background:var(--s2);display:grid;place-items:center;color:var(--accent-text);flex:none}
.hw-empty .glyph svg{width:22px;height:22px}
.hw-empty h3{margin:0 0 4px;font-size:15px}
.hw-empty p{margin:0;color:var(--muted);font-size:13px;max-width:620px}
.hw-steps{margin:12px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;counter-reset:s}
.hw-steps li{counter-increment:s;display:flex;gap:10px;color:var(--text);font-size:13px}
.hw-steps li::before{content:counter(s);width:20px;height:20px;border-radius:50%;background:var(--s2);color:var(--accent-text);font:700 11px/20px ui-sans-serif,system-ui;text-align:center;flex:none}
.hw-steps li.done::before{content:"✓";background:${u[0].color};color:#000}
.hw-hero{background:linear-gradient(135deg,#1d1426 0%,var(--s1) 60%);border:1px solid var(--border);border-radius:14px;padding:22px 24px;margin-bottom:18px}
.hw-form{display:grid;grid-template-columns:1fr 1fr;gap:14px 18px;padding-top:10px}
.hw-field{display:flex;flex-direction:column;gap:6px}
.hw-field.wide{grid-column:1/-1}
.hw-field label,.hw-field .lab{font-size:12px;font-weight:600;color:var(--muted)}
.hw-input{height:36px;border-radius:8px;border:1px solid var(--border);background:var(--page);color:var(--text);padding:0 11px;
font:13px ui-monospace,SFMono-Regular,Menlo,monospace}
.hw-input:focus{outline:2px solid var(--accent-text);outline-offset:0;border-color:transparent}
.hw-input.num{width:90px}
.hw-help{font-size:11px;color:var(--muted)}
.hw-checks{display:flex;flex-wrap:wrap;gap:8px}
.hw-check{display:inline-flex;align-items:center;gap:7px;height:30px;padding:0 11px;border-radius:999px;border:1px solid var(--border);
font:12px ui-monospace,SFMono-Regular,Menlo,monospace;cursor:pointer;user-select:none}
.hw-check input{accent-color:var(--accent);margin:0}
.hw-check.on{border-color:var(--accent-text);color:var(--text);background:rgba(144,70,255,.12)}
.hw-errors{grid-column:1/-1;margin:0;padding:10px 14px;border-radius:8px;border:1px solid ${u[4].color};color:${u[4].color};font-size:12px;list-style:none;display:flex;flex-direction:column;gap:3px}
.hw-formfoot{grid-column:1/-1;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-top:4px}
.hw-saved{color:${u[0].color};font-size:12px;font-weight:600}
.hw-sub-card{grid-column:1/-1;background:var(--s2);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
.hw-sub-card .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.hw-errlist{display:flex;flex-direction:column;gap:8px}
.hw-err{background:var(--s2);border-left:3px solid ${u[3].color};border-radius:8px;padding:10px 12px}
.hw-err .cmd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.hw-err .msg{font-size:12px;color:var(--muted);margin-top:2px}
.hw-banner{display:flex;gap:10px;align-items:center;padding:10px 14px;border-radius:10px;background:var(--s2);border:1px solid var(--border);font-size:13px;margin-bottom:14px}
.hw-banner.bad{border-color:${u[4].color};color:${u[4].color}}
.hw-banner.info{border-color:var(--info);color:var(--info)}
.hw-foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-top:24px;padding-top:16px;border-top:1px solid var(--border)}
.hw-skel{background:linear-gradient(90deg,var(--s1),var(--s2),var(--s1));background-size:200% 100%;animation:hw-sk 1.4s ease infinite;border-radius:12px}
@keyframes hw-sk{to{background-position:-200% 0}}
.hw-spark{display:block}
@media (max-width:820px){.hw-form{grid-template-columns:1fr}.hw-item{grid-template-columns:1fr}.hw-wrap{padding:20px 16px 40px}
.hw-table thead{display:none}.hw-table tr{display:grid;grid-template-columns:1fr;padding:8px 0;border-bottom:1px solid var(--border)}.hw-table td{border:0;padding:6px 4px}}
`, z = 132, R = 34, N = 4;
function B(e, n) {
  return n <= 1 ? z / 2 : N + e * (z - 2 * N) / (n - 1);
}
function We({ points: e }) {
  const n = e.length, r = (s) => R - N - s * (R - 2 * N) / 4, l = e.map((s) => s != null && s.worst ? Number(s.worst.slice(1)) : null);
  let p = "";
  l.forEach((s, i) => {
    if (s === null) return;
    const c = l.slice(0, i).reverse().find((w) => w !== null);
    p += c == null ? `M${B(i, n)},${r(s)}` : ` H${B(i, n)} V${r(s)}`;
  });
  const o = l.filter((s) => s !== null).map((s) => `L${s}`).join(", ");
  return /* @__PURE__ */ a("svg", { className: "hw-spark", width: z, height: R, viewBox: `0 0 ${z} ${R}`, role: "img", "aria-label": `Worst level over the last ${n} runs: ${o || "none"}`, children: [
    [0, 1, 2, 3, 4].map((s) => /* @__PURE__ */ t("line", { x1: N, x2: z - N, y1: r(s), y2: r(s), stroke: m.border, strokeWidth: s === 0 || s === 4 ? 1 : 0.5, strokeDasharray: s === 0 || s === 4 ? "" : "2 3" }, s)),
    /* @__PURE__ */ t("path", { d: p, fill: "none", stroke: m.muted, strokeWidth: 1.25 }),
    l.map(
      (s, i) => s === null ? /* @__PURE__ */ t("circle", { cx: B(i, n), cy: R / 2, r: 2, fill: "none", stroke: m.muted, strokeWidth: 1 }, i) : /* @__PURE__ */ t("circle", { cx: B(i, n), cy: r(s), r: i === n - 1 ? 3.4 : 2.3, fill: u[s].color, children: /* @__PURE__ */ t("title", { children: `L${s} ${u[s].name}` }) }, i)
    )
  ] });
}
function De({ points: e }) {
  const n = e.length, r = (i) => R - N - i * (R - 2 * N), l = e.map((i) => typeof (i == null ? void 0 : i.pass_k) == "number" ? i.pass_k : null), p = l.map((i, c) => i === null ? null : `${B(c, n)},${r(i)}`).filter(Boolean), o = l[l.length - 1], s = o == null ? m.muted : o >= 0.999 ? u[0].color : o > 0 ? u[2].color : u[4].color;
  return /* @__PURE__ */ a("svg", { className: "hw-spark", width: z, height: R, viewBox: `0 0 ${z} ${R}`, role: "img", "aria-label": `pass^k over the last ${n} runs`, children: [
    /* @__PURE__ */ t("line", { x1: N, x2: z - N, y1: r(1), y2: r(1), stroke: m.border, strokeWidth: 1 }),
    /* @__PURE__ */ t("line", { x1: N, x2: z - N, y1: r(0), y2: r(0), stroke: m.border, strokeWidth: 1 }),
    p.length > 1 && /* @__PURE__ */ t("polyline", { points: p.join(" "), fill: "none", stroke: s, strokeWidth: 1.5 }),
    l.map((i, c) => i === null ? null : /* @__PURE__ */ t("circle", { cx: B(c, n), cy: r(i), r: c === n - 1 ? 3 : 1.6, fill: s }, c))
  ] });
}
function He({ id: e, outline: n }) {
  const r = Fe(e);
  return r ? n ? /* @__PURE__ */ a("span", { className: "hw-chip line", style: { color: r.color }, children: [
    /* @__PURE__ */ t("span", { className: "dot" }),
    r.id,
    " ",
    r.name
  ] }) : /* @__PURE__ */ a("span", { className: "hw-chip fill", style: { background: r.color }, title: `${r.id} ${r.name}`, children: [
    r.id,
    " ",
    r.name
  ] }) : /* @__PURE__ */ t("span", { className: "hw-chip line", style: { color: m.muted }, children: "no result" });
}
function j({ icon: e, title: n, children: r }) {
  return /* @__PURE__ */ a("div", { className: "hw-empty", children: [
    /* @__PURE__ */ t("div", { className: "glyph", children: e }),
    /* @__PURE__ */ a("div", { children: [
      /* @__PURE__ */ t("h3", { children: n }),
      r
    ] })
  ] });
}
function G({ title: e, colour: n, big: r, small: l }) {
  return /* @__PURE__ */ a("div", { className: "hw-tile", style: { "--tile": n ?? m.border }, children: [
    /* @__PURE__ */ t("h3", { children: e }),
    /* @__PURE__ */ t("div", { className: "big", children: r }),
    l && /* @__PURE__ */ t("div", { className: "small", children: l })
  ] });
}
function Oe({ state: e, job: n }) {
  var c, w, h, b, y, x;
  const r = e.latest, l = r ? Ee[r.status] ?? { label: r.status, color: m.muted } : null, p = (c = r == null ? void 0 : r.selftest) == null ? void 0 : c.passed, o = (r == null ? void 0 : r.drift) ?? null, s = (o == null ? void 0 : o.status) ?? e.drift.status, i = n === void 0 ? "checking…" : n === null ? "not registered" : n.user_paused || n.enabled === !1 ? "paused" : "on";
  return /* @__PURE__ */ a("div", { className: "hw-tiles", children: [
    /* @__PURE__ */ t(
      G,
      {
        title: "Last run",
        colour: l == null ? void 0 : l.color,
        big: r ? ae(r.finished_at || r.started_at) : "No run yet",
        small: r ? `${_e(r.finished_at || r.started_at)} · ${r.trigger === "manual" ? "Run now" : "scheduled"}` : `Nightly check: ${i}`
      }
    ),
    /* @__PURE__ */ t(
      G,
      {
        title: "Status",
        colour: l == null ? void 0 : l.color,
        big: /* @__PURE__ */ t("span", { style: { color: (l == null ? void 0 : l.color) ?? m.muted }, children: l ? l.label : "—" }),
        small: (r == null ? void 0 : r.reason) ?? (r ? `Nightly check: ${i}${n != null && n.schedule ? ` · ${n.schedule}` : ""}` : "Nothing has run yet")
      }
    ),
    /* @__PURE__ */ t(
      G,
      {
        title: "Selftest",
        colour: p === !0 ? u[0].color : p === !1 ? u[4].color : void 0,
        big: p === !0 ? "Passed" : p === !1 ? "Failed" : "—",
        small: p === !1 ? `${((h = (w = r == null ? void 0 : r.selftest) == null ? void 0 : w.failures) == null ? void 0 : h.length) ?? 0} failure(s)` : ((y = (b = r == null ? void 0 : r.selftest) == null ? void 0 : b.summary) == null ? void 0 : y.replace(/^selftest passed: /, "")) || "naive ≥ L3, hardened L0 + Detected"
      }
    ),
    /* @__PURE__ */ t(
      G,
      {
        title: "Guardrail drift",
        colour: s ? Y[s] : void 0,
        big: /* @__PURE__ */ t("span", { style: { color: s ? Y[s] ?? m.text : m.muted }, children: Be(s) }),
        small: (o == null ? void 0 : o.workspace) || e.drift.workspace || ((x = e.settings) == null ? void 0 : x.watched_workspace) || "No workspace watched"
      }
    )
  ] });
}
function Be(e) {
  switch (e) {
    case "present":
      return "All guardrails present";
    case "review":
      return "Needs review";
    case "weaker":
      return "Weaker than generated";
    case "missing":
      return "Guardrails missing";
    case "n/a":
      return "Nothing to compare";
    case "no reference yet":
      return "No reference yet";
    case "not configured":
      return "Not configured";
    case "error":
      return "Could not check";
    default:
      return "—";
  }
}
function Ie() {
  return /* @__PURE__ */ t("div", { className: "hw-legend", "aria-label": "Level colours", children: u.map((e) => /* @__PURE__ */ a("span", { className: "hw-chip line", style: { color: e.color }, children: [
    /* @__PURE__ */ t("span", { className: "dot" }),
    e.id,
    " ",
    e.name
  ] }, e.id)) });
}
function te({ now: e, series: n }) {
  if (e != null && e.error)
    return /* @__PURE__ */ a("div", { className: "hw-cell", children: [
      /* @__PURE__ */ t("span", { className: "hw-chip line", style: { color: u[3].color }, children: "error" }),
      /* @__PURE__ */ t("span", { className: "hw-help", children: e.error.split(":")[0] })
    ] });
  const r = e == null ? void 0 : e.k;
  return /* @__PURE__ */ a("div", { className: "hw-cell", children: [
    /* @__PURE__ */ a("div", { className: "hw-stack", children: [
      /* @__PURE__ */ t(He, { id: e == null ? void 0 : e.worst }),
      /* @__PURE__ */ t("span", { className: "hw-num", title: r ? `pass^${r}: the chance that ${r} runs in a row are all clean` : "no pass^k printed", children: typeof (e == null ? void 0 : e.pass_k) == "number" ? /* @__PURE__ */ a(K, { children: [
        "pass^",
        r,
        " ",
        /* @__PURE__ */ t("b", { children: e.pass_k.toFixed(2) })
      ] }) : /* @__PURE__ */ t("span", { className: "k", children: "pass^k n/a" }) })
    ] }),
    /* @__PURE__ */ a("div", { className: "hw-stack", style: { gap: 2 }, children: [
      /* @__PURE__ */ t(We, { points: n }),
      /* @__PURE__ */ t(De, { points: n })
    ] })
  ] });
}
function Pe({ state: e, history: n }) {
  const r = e.latest, l = r != null && r.rooms && Object.keys(r.rooms).length ? Object.keys(r.rooms) : [], p = /* @__PURE__ */ new Set();
  l.forEach((s) => ["naive", "hardened"].forEach((i) => {
    var w, h, b;
    const c = (b = (h = (w = r == null ? void 0 : r.rooms) == null ? void 0 : w[s]) == null ? void 0 : h[i]) == null ? void 0 : b.k;
    c && p.add(c);
  }));
  const o = p.size === 1 ? `pass^${[...p][0]}` : "pass^k";
  return /* @__PURE__ */ a("section", { className: "hw-card", "aria-labelledby": "hw-rooms", children: [
    /* @__PURE__ */ a("div", { className: "hw-card-head", children: [
      /* @__PURE__ */ a("div", { children: [
        /* @__PURE__ */ t("h2", { id: "hw-rooms", children: "Range, room by room" }),
        /* @__PURE__ */ a("p", { children: [
          "Worst level and ",
          o,
          " for the two reference agents, over the last ",
          n.length || 0,
          " runs.",
          p.size === 1 ? ` k = ${[...p][0]}: Hauntlet prints pass^k for k in 1, 2, 4, 8 up to the number of runs.` : ""
        ] })
      ] }),
      /* @__PURE__ */ t(Ie, {})
    ] }),
    /* @__PURE__ */ t("div", { className: "hw-card-body", children: l.length === 0 ? /* @__PURE__ */ t(j, { icon: /* @__PURE__ */ t(oe, {}), title: r ? "This run has no room results" : "No range results yet", children: /* @__PURE__ */ t("p", { children: r != null && r.reason ? r.reason : "The first nightly run fills this table: selftest, then naive and hardened in every room. Press Run now to fill it right away; it takes a few seconds and uses no credits." }) }) : /* @__PURE__ */ a("table", { className: "hw-table", children: [
      /* @__PURE__ */ t("thead", { children: /* @__PURE__ */ a("tr", { children: [
        /* @__PURE__ */ t("th", { children: "Room" }),
        /* @__PURE__ */ t("th", { children: "naive · expected high" }),
        /* @__PURE__ */ t("th", { children: "hardened · expected L0" }),
        /* @__PURE__ */ t("th", { children: "Scorecards" })
      ] }) }),
      /* @__PURE__ */ t("tbody", { children: l.map((s) => {
        var b, y, x, k, $;
        const i = (D) => n.map((E) => {
          var H, C;
          return (C = (H = E.rooms) == null ? void 0 : H[s]) == null ? void 0 : C[D];
        }), c = (y = (b = r == null ? void 0 : r.rooms) == null ? void 0 : b[s]) == null ? void 0 : y.naive, w = (k = (x = r == null ? void 0 : r.rooms) == null ? void 0 : x[s]) == null ? void 0 : k.hardened, h = ($ = r == null ? void 0 : r.demos) == null ? void 0 : $[s];
        return /* @__PURE__ */ a("tr", { children: [
          /* @__PURE__ */ a("td", { className: "hw-room", children: [
            s,
            /* @__PURE__ */ t("small", { children: h != null && h.after_worst ? `Exorcist demo ${h.before_worst} → ${h.after_worst}` : s === "parlor" ? "no Exorcist demo for this room" : "" })
          ] }),
          /* @__PURE__ */ t("td", { children: /* @__PURE__ */ t(te, { now: c, series: i("naive") }) }),
          /* @__PURE__ */ t("td", { children: /* @__PURE__ */ t(te, { now: w, series: i("hardened") }) }),
          /* @__PURE__ */ t("td", { children: /* @__PURE__ */ a("div", { className: "hw-links", children: [
            /* @__PURE__ */ t(J, { path: c == null ? void 0 : c.report, label: "naive" }),
            /* @__PURE__ */ t(J, { path: w == null ? void 0 : w.report, label: "hardened" }),
            (h == null ? void 0 : h.report) && /* @__PURE__ */ t(J, { path: h.report, label: "exorcism" })
          ] }) })
        ] }, s);
      }) })
    ] }) })
  ] });
}
function J({ path: e, label: n }) {
  const r = $e(e);
  return !r || !e ? null : /* @__PURE__ */ a("span", { className: "hw-rep", children: [
    /* @__PURE__ */ a("a", { className: "hw-link", href: r, target: "_blank", rel: "noopener noreferrer", title: `Open ${n} scorecard`, children: [
      n,
      /* @__PURE__ */ t(Me, {})
    ] }),
    /* @__PURE__ */ t("span", { className: "hw-path", title: e, children: e.split("/").pop() })
  ] });
}
function je({ run: e }) {
  const n = (e == null ? void 0 : e.errors) ?? [];
  return n.length ? /* @__PURE__ */ a("section", { className: "hw-card", "aria-labelledby": "hw-errs", children: [
    /* @__PURE__ */ t("div", { className: "hw-card-head", children: /* @__PURE__ */ a("div", { children: [
      /* @__PURE__ */ t("h2", { id: "hw-errs", children: "What did not complete" }),
      /* @__PURE__ */ t("p", { children: "Later commands still ran. Fix the first one and press Run now." })
    ] }) }),
    /* @__PURE__ */ t("div", { className: "hw-card-body hw-errlist", style: { paddingTop: 14 }, children: n.map((r, l) => /* @__PURE__ */ a("div", { className: "hw-err", children: [
      /* @__PURE__ */ a("div", { className: "cmd", children: [
        r.command,
        " · ",
        r.kind
      ] }),
      /* @__PURE__ */ t("div", { className: "msg", children: r.detail })
    ] }, l)) })
  ] }) : null;
}
function Ue({ drift: e, settings: n, busy: r, onCheck: l }) {
  var s;
  const p = e != null && e.files ? Object.entries(e.files) : [], o = (e == null ? void 0 : e.workspace) || (n == null ? void 0 : n.watched_workspace);
  return /* @__PURE__ */ a("section", { className: "hw-card", "aria-labelledby": "hw-drift", children: [
    /* @__PURE__ */ a("div", { className: "hw-card-head", children: [
      /* @__PURE__ */ a("div", { children: [
        /* @__PURE__ */ t("h2", { id: "hw-drift", children: "Guardrail drift" }),
        /* @__PURE__ */ t("p", { children: o ? /* @__PURE__ */ a(K, { children: [
          "Read-only comparison of ",
          /* @__PURE__ */ a("span", { className: "hw-path", children: [
            o,
            "/.kiro"
          ] }),
          " with what the Exorcist generates",
          e != null && e.checked_at ? `, checked ${ae(e.checked_at)}` : "",
          "."
        ] }) : "Compares one workspace’s .kiro/ with the guardrails the Exorcist generates. Warden never writes to it." })
      ] }),
      /* @__PURE__ */ a("button", { className: "hw-btn small", onClick: l, disabled: r || !(n != null && n.watched_workspace), children: [
        /* @__PURE__ */ t(Ce, { className: r ? "hw-spin" : "" }),
        "Check drift now"
      ] })
    ] }),
    /* @__PURE__ */ a("div", { className: "hw-card-body", children: [
      n != null && n.watched_workspace ? (e == null ? void 0 : e.status) === "no reference yet" || !p.length && !(e != null && e.error) && (e == null ? void 0 : e.status) !== "n/a" ? /* @__PURE__ */ t(j, { icon: /* @__PURE__ */ t(ee, {}), title: "No reference yet", children: /* @__PURE__ */ t("p", { children: "The reference comes from the Exorcist demo bundles that each nightly run generates. Run the range once, then drift appears here." }) }) : (e == null ? void 0 : e.status) === "error" ? /* @__PURE__ */ t(j, { icon: /* @__PURE__ */ t(ee, {}), title: "Could not check this workspace", children: /* @__PURE__ */ t("p", { children: e.error || "Unknown error" }) }) : /* @__PURE__ */ t("div", { className: "hw-files", children: p.map(([i, c]) => {
        const w = c.items.filter((h) => h.status !== "present" && h.status !== "n/a").length;
        return /* @__PURE__ */ a("details", { className: "hw-file", open: c.status === "missing" || c.status === "weaker", children: [
          /* @__PURE__ */ a("summary", { children: [
            /* @__PURE__ */ t(Le, { className: "hw-caret" }),
            /* @__PURE__ */ t("span", { className: "name", children: i }),
            /* @__PURE__ */ t("span", { className: "count", children: w ? `${w} of ${c.items.length} need attention` : `${c.items.length} checked` }),
            /* @__PURE__ */ t(re, { status: c.status })
          ] }),
          /* @__PURE__ */ t("div", { className: "hw-items", children: c.items.map((h) => /* @__PURE__ */ a("div", { className: "hw-item", children: [
            /* @__PURE__ */ t("span", { className: "rule", children: h.item.includes("#") ? h.item.split("#").pop() : h.item.split("/").pop() }),
            /* @__PURE__ */ t("span", { children: /* @__PURE__ */ t(re, { status: h.status }) }),
            /* @__PURE__ */ a("div", { children: [
              /* @__PURE__ */ t("div", { className: "detail", children: h.detail || Ge(h.status) }),
              /* @__PURE__ */ a("div", { className: "rooms", children: [
                "generated for ",
                h.rooms.join(", ")
              ] })
            ] })
          ] }, h.item)) })
        ] }, i);
      }) }) : /* @__PURE__ */ t(j, { icon: /* @__PURE__ */ t(Ae, {}), title: "No workspace watched", children: /* @__PURE__ */ t("p", { children: "Set a workspace path in Settings below. Warden reads its .kiro/ steering, hooks, mcp.json and sandbox.json, and reports what is missing or weaker, file by file." }) }),
      !!((s = e == null ? void 0 : e.warnings) != null && s.length) && /* @__PURE__ */ t("div", { className: "hw-warn", role: "note", children: e.warnings.map((i) => /* @__PURE__ */ a("span", { children: [
        "⚠ ",
        i
      ] }, i)) }),
      /* @__PURE__ */ t("p", { className: "hw-note", children: pe })
    ] })
  ] });
}
function Ge(e) {
  return e === "present" ? "Matches the generated guardrail." : e === "n/a" ? "Nothing here to compare." : "";
}
function re({ status: e }) {
  const n = Y[e] ?? m.muted;
  return e === "n/a" ? /* @__PURE__ */ t("span", { className: "hw-chip line", style: { color: n }, children: "n/a" }) : /* @__PURE__ */ t("span", { className: "hw-chip fill", style: { background: n }, children: e });
}
function Ve({ errors: e, settings: n, onOpenSettings: r }) {
  const l = !!(n != null && n.hauntlet_checkout) && !e.some((p) => /checkout/i.test(p));
  return /* @__PURE__ */ t("div", { className: "hw-hero", children: /* @__PURE__ */ a(j, { icon: /* @__PURE__ */ t(ze, {}), title: "Point Warden at your Hauntlet checkout", children: [
    /* @__PURE__ */ t("p", { children: "Warden runs Hauntlet’s model-free checks every night at 03:00 and watches one workspace’s guardrails. Nothing it runs uses a model or credits." }),
    /* @__PURE__ */ a("ol", { className: "hw-steps", children: [
      /* @__PURE__ */ a("li", { className: l ? "done" : "", children: [
        "Set the path to your local Hauntlet checkout (run ",
        /* @__PURE__ */ t("code", { children: "uv sync" }),
        " there first)."
      ] }),
      /* @__PURE__ */ t("li", { className: n != null && n.watched_workspace ? "done" : "", children: "Optionally, set a workspace whose .kiro/ guardrails Warden should watch." }),
      /* @__PURE__ */ t("li", { children: "Save, then press Run now or turn on the nightly check." })
    ] }),
    /* @__PURE__ */ t("div", { style: { marginTop: 14 }, children: /* @__PURE__ */ t("button", { className: "hw-btn primary small", onClick: r, children: "Open settings" }) })
  ] }) });
}
function qe({ api: e, state: n, open: r, onToggle: l, onSaved: p }) {
  var v, T;
  const o = n.settings, [s, i] = g((o == null ? void 0 : o.hauntlet_checkout) ?? ""), [c, w] = g((o == null ? void 0 : o.watched_workspace) ?? ""), [h, b] = g((o == null ? void 0 : o.rooms) ?? n.known_rooms), [y, x] = g((o == null ? void 0 : o.repeat) ?? 3), [k, $] = g((o == null ? void 0 : o.hauntlet_source) ?? "checkout"), [D, E] = g([]), [H, C] = g(!1), [A, _] = g(!1), [F, O] = g(!1), [U, I] = g("");
  ne(() => {
    o && (i(o.hauntlet_checkout), w(o.watched_workspace), b(o.rooms), x(o.repeat), $(o.hauntlet_source));
  }, [o == null ? void 0 : o.hauntlet_checkout, o == null ? void 0 : o.watched_workspace, o == null ? void 0 : o.repeat, o == null ? void 0 : o.hauntlet_source, ((o == null ? void 0 : o.rooms) ?? []).join(",")]);
  const P = !!((v = o == null ? void 0 : o.git_install) != null && v.approved) && !!((T = o == null ? void 0 : o.git_install) != null && T.tool_path);
  async function V(d) {
    d.preventDefault(), _(!0), C(!1), E([]);
    try {
      await xe(e, {
        hauntlet_source: k,
        hauntlet_checkout: s.trim(),
        watched_workspace: c.trim(),
        rooms: n.known_rooms.filter((S) => h.includes(S)),
        repeat: Number(y),
        uv_path: (o == null ? void 0 : o.uv_path) ?? "",
        command_timeout_secs: (o == null ? void 0 : o.command_timeout_secs) ?? 150
      }), C(!0), p();
    } catch (S) {
      E(W(S).split("; "));
    } finally {
      _(!1);
    }
  }
  async function q() {
    _(!0), I("");
    try {
      const d = await be(e);
      I(`Installed: ${d.tool_path}`), p();
    } catch (d) {
      I(W(d));
    } finally {
      _(!1);
    }
  }
  const f = (d) => b((S) => S.includes(d) ? S.filter((se) => se !== d) : [...S, d]);
  return /* @__PURE__ */ a("details", { className: "hw-card", open: r, onToggle: (d) => l(d.target.open), children: [
    /* @__PURE__ */ a("summary", { className: "hw-card-head", style: { cursor: "pointer", listStyle: "none" }, children: [
      /* @__PURE__ */ a("div", { children: [
        /* @__PURE__ */ t("h2", { children: "Settings" }),
        /* @__PURE__ */ t("p", { children: o ? n.settings_errors.length ? n.settings_errors[0] : "Saved. Runs use these on the next start." : "Not configured yet." })
      ] }),
      /* @__PURE__ */ t("span", { className: "hw-help", children: r ? "Hide" : "Show" })
    ] }),
    /* @__PURE__ */ a("form", { className: "hw-card-body hw-form", onSubmit: V, children: [
      /* @__PURE__ */ a("div", { className: "hw-field wide", children: [
        /* @__PURE__ */ t("span", { className: "lab", children: "Hauntlet source" }),
        /* @__PURE__ */ a("div", { className: "hw-checks", role: "radiogroup", children: [
          /* @__PURE__ */ a("label", { className: `hw-check ${k === "checkout" ? "on" : ""}`, children: [
            /* @__PURE__ */ t("input", { type: "radio", name: "src", checked: k === "checkout", onChange: () => $("checkout") }),
            "local checkout"
          ] }),
          /* @__PURE__ */ a("label", { className: `hw-check ${k === "git" ? "on" : ""}`, title: P ? "" : "Install from GitHub first", children: [
            /* @__PURE__ */ t("input", { type: "radio", name: "src", checked: k === "git", disabled: !P, onChange: () => $("git") }),
            "installed from GitHub"
          ] })
        ] })
      ] }),
      /* @__PURE__ */ a("div", { className: "hw-field", children: [
        /* @__PURE__ */ t("label", { htmlFor: "hw-co", children: "Hauntlet checkout" }),
        /* @__PURE__ */ t("input", { id: "hw-co", className: "hw-input", value: s, onChange: (d) => i(d.target.value), placeholder: "/Users/you/src/hauntlet", spellCheck: !1 }),
        /* @__PURE__ */ a("span", { className: "hw-help", children: [
          "Run as ",
          /* @__PURE__ */ t("code", { children: "uv run --offline --project <path> hauntlet …" }),
          " from Warden’s own range directory. Run ",
          /* @__PURE__ */ t("code", { children: "uv sync" }),
          " in the checkout first."
        ] })
      ] }),
      /* @__PURE__ */ a("div", { className: "hw-field", children: [
        /* @__PURE__ */ t("label", { htmlFor: "hw-ws", children: "Watched workspace (optional)" }),
        /* @__PURE__ */ t("input", { id: "hw-ws", className: "hw-input", value: c, onChange: (d) => w(d.target.value), placeholder: "/Users/you/src/my-project", spellCheck: !1 }),
        /* @__PURE__ */ t("span", { className: "hw-help", children: "Read-only. Warden reads its .kiro/ and never writes there." })
      ] }),
      /* @__PURE__ */ a("div", { className: "hw-field wide", children: [
        /* @__PURE__ */ t("span", { className: "lab", children: "Rooms" }),
        /* @__PURE__ */ t("div", { className: "hw-checks", children: n.known_rooms.map((d) => /* @__PURE__ */ a("label", { className: `hw-check ${h.includes(d) ? "on" : ""}`, children: [
          /* @__PURE__ */ t("input", { type: "checkbox", checked: h.includes(d), onChange: () => f(d) }),
          d
        ] }, d)) })
      ] }),
      /* @__PURE__ */ a("div", { className: "hw-field", children: [
        /* @__PURE__ */ t("label", { htmlFor: "hw-k", children: "Repeats per agent (k)" }),
        /* @__PURE__ */ t("input", { id: "hw-k", className: "hw-input num", type: "number", min: 1, max: 10, value: y, onChange: (d) => x(Number(d.target.value)) }),
        /* @__PURE__ */ t("span", { className: "hw-help", children: "Hauntlet prints pass^k for k in 1, 2, 4, 8 up to this number. At 3 the headline is pass^2." })
      ] }),
      /* @__PURE__ */ a("div", { className: "hw-sub-card", children: [
        /* @__PURE__ */ t("strong", { style: { fontSize: 13 }, children: "Install Hauntlet from GitHub" }),
        /* @__PURE__ */ a("span", { className: "hw-help", children: [
          "One-time, only when you approve it: ",
          /* @__PURE__ */ t("code", { children: "uv tool install" }),
          " from github.com/kuberaplutus224/hauntlet into Warden’s data dir. After that every run is offline. The local checkout stays the default."
        ] }),
        /* @__PURE__ */ a("div", { className: "row", children: [
          /* @__PURE__ */ a("label", { className: "hw-check", children: [
            /* @__PURE__ */ t("input", { type: "checkbox", checked: F, onChange: (d) => O(d.target.checked) }),
            "I approve this one-time download"
          ] }),
          /* @__PURE__ */ t("button", { type: "button", className: "hw-btn small", disabled: !F || A, onClick: q, children: P ? "Reinstall" : "Install" }),
          U && /* @__PURE__ */ t("span", { children: U })
        ] })
      ] }),
      D.length > 0 && /* @__PURE__ */ t("ul", { className: "hw-errors", children: D.map((d) => /* @__PURE__ */ t("li", { children: d }, d)) }),
      /* @__PURE__ */ a("div", { className: "hw-formfoot", children: [
        /* @__PURE__ */ t("button", { className: "hw-btn primary", type: "submit", disabled: A, children: "Save settings" }),
        H && /* @__PURE__ */ t("span", { className: "hw-saved", children: "Saved" }),
        /* @__PURE__ */ t("span", { className: "hw-help", children: "The schedule (03:00 local) is edited on the Schedule page. Disabling and re-enabling the app resets it to 03:00." })
      ] })
    ] })
  ] });
}
const Je = 5e3, Ye = 180 * 1e3;
function Xe() {
  const e = ie(), { openChat: n } = ce(), [r, l] = g(null), [p, o] = g([]), [s, i] = g(null), [c, w] = g(void 0), [h, b] = g(""), [y, x] = g(null), [k, $] = g(!1), [D, E] = g(!1), [H, C] = g(!1), A = le(null), _ = Q(async () => {
    var f;
    try {
      const [v, T, d] = await Promise.all([ue(e), me(e), we(e)]);
      return l(v), o(T.runs), i(d && d.status !== "none" ? d : ((f = v.latest) == null ? void 0 : f.drift) ?? null), b(""), (!v.settings || v.settings_errors.length) && C(!0), v;
    } catch (v) {
      return b(W(v)), null;
    }
  }, [e]), F = Q(async () => {
    try {
      w(await ye(e));
    } catch {
      w(null);
    }
  }, [e]);
  ne(() => {
    _(), F();
    const f = () => {
      _(), F();
    };
    return window.addEventListener("focus", f), () => {
      window.removeEventListener("focus", f), A.current && window.clearInterval(A.current);
    };
  }, [_, F]);
  const O = !!(r != null && r.settings) && r.settings_errors.length === 0;
  async function U() {
    var T;
    if (!c) return x({ kind: "bad", text: "The nightly-range-check job is not registered. Re-enable the app." });
    $(!0), x({ kind: "info", text: "Running selftest, both reference agents in every room, and the Exorcist demos…" });
    const f = (T = r == null ? void 0 : r.latest) == null ? void 0 : T.run_id;
    try {
      await ke(e, c);
    } catch (d) {
      return $(!1), x({ kind: "bad", text: `Could not start the run: ${W(d)}` });
    }
    const v = Date.now();
    A.current = window.setInterval(async () => {
      const d = await _(), S = (d == null ? void 0 : d.latest) && d.latest.run_id !== f;
      (S || Date.now() - v > Ye) && (A.current && window.clearInterval(A.current), $(!1), x(S ? null : { kind: "bad", text: "No result after 3 minutes. Check the run on the Schedule page." }));
    }, Je);
  }
  async function I() {
    E(!0);
    try {
      i(await ge(e));
    } catch (f) {
      x({ kind: "bad", text: `Drift check failed: ${W(f)}` });
    }
    E(!1);
  }
  async function P() {
    try {
      const { text: f } = await fe(e);
      n({ agent: de, message: Ne(f), autoSend: !1 });
    } catch (f) {
      x({ kind: "bad", text: `Could not read the summary: ${W(f)}` });
    }
  }
  async function V() {
    if (c)
      try {
        await ve(e, c, !0), await F();
      } catch (f) {
        x({ kind: "bad", text: W(f) });
      }
  }
  const q = !!c && (c.user_paused || c.enabled === !1);
  return /* @__PURE__ */ a("div", { className: "hw", children: [
    /* @__PURE__ */ t("style", { children: Te }),
    /* @__PURE__ */ a("div", { className: "hw-wrap", children: [
      /* @__PURE__ */ a("header", { className: "hw-head", children: [
        /* @__PURE__ */ a("div", { children: [
          /* @__PURE__ */ t("p", { className: "hw-kicker", children: "Hauntlet · Kiro Crew" }),
          /* @__PURE__ */ t("h1", { className: "hw-title", children: "Hauntlet Warden" }),
          /* @__PURE__ */ t("p", { className: "hw-sub", children: "Nightly range check and guardrail drift. No model, no credits, localhost only." })
        ] }),
        /* @__PURE__ */ a("div", { className: "hw-actions", children: [
          O && q && /* @__PURE__ */ a("button", { className: "hw-btn", onClick: V, title: "Resume the app's own 03:00 job", children: [
            /* @__PURE__ */ t(oe, {}),
            "Turn on nightly check"
          ] }),
          /* @__PURE__ */ a("button", { className: "hw-btn ghost", onClick: P, title: "Opens a chat with the Warden agent, seeded with the latest summary. One agent turn per question uses credits.", children: [
            /* @__PURE__ */ t(Re, {}),
            "Ask Warden"
          ] }),
          /* @__PURE__ */ a(
            "button",
            {
              className: "hw-btn primary",
              onClick: U,
              disabled: !O || k || !c,
              title: O ? "Run the range now (no credits)" : "Save valid settings first",
              children: [
                /* @__PURE__ */ t(Se, { className: k ? "hw-spin" : "" }),
                k ? "Running…" : "Run now"
              ]
            }
          )
        ] })
      ] }),
      h && /* @__PURE__ */ a("div", { className: "hw-banner bad", role: "alert", children: [
        "Could not reach Warden’s backend: ",
        h
      ] }),
      y && /* @__PURE__ */ t("div", { className: `hw-banner ${y.kind}`, role: "status", children: y.text }),
      r ? /* @__PURE__ */ a(K, { children: [
        !O && /* @__PURE__ */ t(Ve, { errors: r.settings_errors, settings: r.settings, onOpenSettings: () => C(!0) }),
        /* @__PURE__ */ t(Oe, { state: r, job: c }),
        /* @__PURE__ */ t(je, { run: r.latest }),
        /* @__PURE__ */ t(Pe, { state: r, history: p }),
        /* @__PURE__ */ t(Ue, { drift: s, settings: r.settings, busy: D, onCheck: I }),
        /* @__PURE__ */ t(qe, { api: e, state: r, open: H, onToggle: C, onSaved: () => {
          _(), F();
        } })
      ] }) : /* @__PURE__ */ a("div", { "aria-busy": "true", children: [
        /* @__PURE__ */ t("div", { className: "hw-skel", style: { height: 92, marginBottom: 18 } }),
        /* @__PURE__ */ t("div", { className: "hw-skel", style: { height: 320 } })
      ] }),
      /* @__PURE__ */ a("footer", { className: "hw-foot", children: [
        /* @__PURE__ */ t("span", { children: "Only “Ask Warden” uses credits: one agent turn per question. Scheduled runs, Run now and drift checks call no model." }),
        /* @__PURE__ */ t("span", { children: "Dummy secrets appear only as HAUNTLET-DUMMY-…" })
      ] })
    ] })
  ] });
}
export {
  Xe as default
};
