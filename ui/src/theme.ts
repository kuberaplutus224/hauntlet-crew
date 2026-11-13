// Colour tokens from the Hauntlet scorecard (hauntlet/scorecard/theme.py), so a Warden
// page and a scorecard read as one product. The page carries its own scoped stylesheet
// (root class .hw) instead of following the dashboard theme.

export const LEVELS = [
  { id: 'L0', name: 'Clean', color: '#33D480' },
  { id: 'L1', name: 'Reached', color: '#EFE08A' },
  { id: 'L2', name: 'Echoed', color: '#FFC857' },
  { id: 'L3', name: 'Acted', color: '#FF9F5A' },
  { id: 'L4', name: 'Exposed', color: '#FF7A88' },
] as const

export const T = {
  page: '#000000',
  s1: '#19161D',
  s2: '#28242E',
  border: '#352F3D',
  text: '#FAFAFA',
  muted: '#A39FAB',
  accent: '#9046FF',
  accentText: '#C59EFF',
  info: '#69A0F6',
  l0Tint: '#0E2A1D',
}

export function levelOf(id: string | null | undefined) {
  return LEVELS.find((l) => l.id === id) ?? null
}

// drift statuses mapped onto the same scale: present is clean, missing is the worst
export const DRIFT_COLOR: Record<string, string> = {
  present: LEVELS[0].color,
  review: LEVELS[1].color,
  weaker: LEVELS[3].color,
  missing: LEVELS[4].color,
  'n/a': T.muted,
}

export const RUN_STATUS: Record<string, { label: string; color: string }> = {
  ok: { label: 'All commands passed', color: LEVELS[0].color },
  failed: { label: 'Selftest failed', color: LEVELS[4].color },
  error: { label: 'Run had errors', color: LEVELS[3].color },
  not_configured: { label: 'Not configured', color: T.muted },
  skipped: { label: 'Skipped (already running)', color: T.muted },
}

export const CSS = `
.hw{--page:${T.page};--s1:${T.s1};--s2:${T.s2};--border:${T.border};--text:${T.text};--muted:${T.muted};
--accent:${T.accent};--accent-text:${T.accentText};--info:${T.info};
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
.hw-warn{margin:12px 0 4px;padding:10px 12px;border-radius:8px;border:1px solid ${LEVELS[2].color};color:${LEVELS[2].color};font-size:12px;display:flex;flex-direction:column;gap:4px}
.hw-note{color:var(--muted);font-size:12px;margin:12px 0 0;font-style:italic}
.hw-empty{display:flex;gap:18px;align-items:flex-start;padding:22px 4px 10px}
.hw-empty .glyph{width:44px;height:44px;border-radius:12px;background:var(--s2);display:grid;place-items:center;color:var(--accent-text);flex:none}
.hw-empty .glyph svg{width:22px;height:22px}
.hw-empty h3{margin:0 0 4px;font-size:15px}
.hw-empty p{margin:0;color:var(--muted);font-size:13px;max-width:620px}
.hw-steps{margin:12px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;counter-reset:s}
.hw-steps li{counter-increment:s;display:flex;gap:10px;color:var(--text);font-size:13px}
.hw-steps li::before{content:counter(s);width:20px;height:20px;border-radius:50%;background:var(--s2);color:var(--accent-text);font:700 11px/20px ui-sans-serif,system-ui;text-align:center;flex:none}
.hw-steps li.done::before{content:"✓";background:${LEVELS[0].color};color:#000}
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
.hw-errors{grid-column:1/-1;margin:0;padding:10px 14px;border-radius:8px;border:1px solid ${LEVELS[4].color};color:${LEVELS[4].color};font-size:12px;list-style:none;display:flex;flex-direction:column;gap:3px}
.hw-formfoot{grid-column:1/-1;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-top:4px}
.hw-saved{color:${LEVELS[0].color};font-size:12px;font-weight:600}
.hw-sub-card{grid-column:1/-1;background:var(--s2);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
.hw-sub-card .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.hw-errlist{display:flex;flex-direction:column;gap:8px}
.hw-err{background:var(--s2);border-left:3px solid ${LEVELS[3].color};border-radius:8px;padding:10px 12px}
.hw-err .cmd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.hw-err .msg{font-size:12px;color:var(--muted);margin-top:2px}
.hw-banner{display:flex;gap:10px;align-items:center;padding:10px 14px;border-radius:10px;background:var(--s2);border:1px solid var(--border);font-size:13px;margin-bottom:14px}
.hw-banner.bad{border-color:${LEVELS[4].color};color:${LEVELS[4].color}}
.hw-banner.info{border-color:var(--info);color:var(--info)}
.hw-foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-top:24px;padding-top:16px;border-top:1px solid var(--border)}
.hw-skel{background:linear-gradient(90deg,var(--s1),var(--s2),var(--s1));background-size:200% 100%;animation:hw-sk 1.4s ease infinite;border-radius:12px}
@keyframes hw-sk{to{background-position:-200% 0}}
.hw-spark{display:block}
@media (max-width:820px){.hw-form{grid-template-columns:1fr}.hw-item{grid-template-columns:1fr}.hw-wrap{padding:20px 16px 40px}
.hw-table thead{display:none}.hw-table tr{display:grid;grid-template-columns:1fr;padding:8px 0;border-bottom:1px solid var(--border)}.hw-table td{border:0;padding:6px 4px}}
`
