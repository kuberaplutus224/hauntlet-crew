import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  CLIENT_NOTE, localTime, relTime, reportHref,
  type DriftReport, type HistoryRun, type RunRecord, type Settings, type State, type CronJob,
} from './api'
import { LevelChip, LevelTrend, PassTrend } from './charts'
import { Caret, External, Folder, Ghost, Moon, Refresh, Shield } from './icons'
import { DRIFT_COLOR, LEVELS, RUN_STATUS, T } from './theme'

export function Empty({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="hw-empty">
      <div className="glyph">{icon}</div>
      <div><h3>{title}</h3>{children}</div>
    </div>
  )
}

function Tile({ title, colour, big, small }: { title: string; colour?: string; big: ReactNode; small?: ReactNode }) {
  return (
    <div className="hw-tile" style={{ ['--tile' as string]: colour ?? T.border }}>
      <h3>{title}</h3>
      <div className="big">{big}</div>
      {small && <div className="small">{small}</div>}
    </div>
  )
}

export function Tiles({ state, job }: { state: State; job: CronJob | null | undefined }) {
  const r = state.latest
  const st = r ? RUN_STATUS[r.status] ?? { label: r.status, color: T.muted } : null
  const passed = r?.selftest?.passed
  const drift = r?.drift ?? null
  const driftStatus = drift?.status ?? state.drift.status
  const nightly = job === undefined ? 'checking…' : job === null ? 'not registered' : job.user_paused || job.enabled === false ? 'paused' : 'on'
  return (
    <div className="hw-tiles">
      <Tile title="Last run" colour={st?.color}
        big={r ? relTime(r.finished_at || r.started_at) : 'No run yet'}
        small={r ? `${localTime(r.finished_at || r.started_at)} · ${r.trigger === 'manual' ? 'Run now' : 'scheduled'}` : `Nightly check: ${nightly}`} />
      <Tile title="Status" colour={st?.color}
        big={<span style={{ color: st?.color ?? T.muted }}>{st ? st.label : '—'}</span>}
        small={r?.reason ?? (r ? `Nightly check: ${nightly}${job?.schedule ? ` · ${job.schedule}` : ''}` : 'Nothing has run yet')} />
      <Tile title="Selftest" colour={passed === true ? LEVELS[0].color : passed === false ? LEVELS[4].color : undefined}
        big={passed === true ? 'Passed' : passed === false ? 'Failed' : '—'}
        small={passed === false ? `${r?.selftest?.failures?.length ?? 0} failure(s)` : r?.selftest?.summary?.replace(/^selftest passed: /, '') || 'naive ≥ L3, hardened L0 + Detected'} />
      <Tile title="Guardrail drift" colour={driftStatus ? DRIFT_COLOR[driftStatus] : undefined}
        big={<span style={{ color: driftStatus ? DRIFT_COLOR[driftStatus] ?? T.text : T.muted }}>{driftLabel(driftStatus)}</span>}
        small={drift?.workspace || state.drift.workspace || state.settings?.watched_workspace || 'No workspace watched'} />
    </div>
  )
}

function driftLabel(s?: string) {
  switch (s) {
    case 'present': return 'All guardrails present'
    case 'review': return 'Needs review'
    case 'weaker': return 'Weaker than generated'
    case 'missing': return 'Guardrails missing'
    case 'n/a': return 'Nothing to compare'
    case 'no reference yet': return 'No reference yet'
    case 'not configured': return 'Not configured'
    case 'error': return 'Could not check'
    default: return '—'
  }
}

export function Legend() {
  return (
    <div className="hw-legend" aria-label="Level colours">
      {LEVELS.map((l) => <span key={l.id} className="hw-chip line" style={{ color: l.color }}><span className="dot" />{l.id} {l.name}</span>)}
    </div>
  )
}

function AgentCell({ now, series }: { now?: { worst?: string; pass_k?: number | null; k?: number | null; error?: string | null }; series: any[] }) {
  if (now?.error) {
    return <div className="hw-cell"><span className="hw-chip line" style={{ color: LEVELS[3].color }}>error</span><span className="hw-help">{now.error.split(':')[0]}</span></div>
  }
  const k = now?.k
  return (
    <div className="hw-cell">
      <div className="hw-stack">
        <LevelChip id={now?.worst} />
        <span className="hw-num" title={k ? `pass^${k}: the chance that ${k} runs in a row are all clean` : 'no pass^k printed'}>
          {typeof now?.pass_k === 'number' ? <>pass^{k} <b>{now.pass_k.toFixed(2)}</b></> : <span className="k">pass^k n/a</span>}
        </span>
      </div>
      <div className="hw-stack" style={{ gap: 2 }}>
        <LevelTrend points={series} />
        <PassTrend points={series} />
      </div>
    </div>
  )
}

export function RoomsPanel({ state, history }: { state: State; history: HistoryRun[] }) {
  const r = state.latest
  const rooms = r?.rooms && Object.keys(r.rooms).length ? Object.keys(r.rooms) : []
  const ks = new Set<number>()
  rooms.forEach((room) => ['naive', 'hardened'].forEach((a) => { const k = r?.rooms?.[room]?.[a]?.k; if (k) ks.add(k) }))
  const kLabel = ks.size === 1 ? `pass^${[...ks][0]}` : 'pass^k'
  return (
    <section className="hw-card" aria-labelledby="hw-rooms">
      <div className="hw-card-head">
        <div>
          <h2 id="hw-rooms">Range, room by room</h2>
          <p>Worst level and {kLabel} for the two reference agents, over the last {history.length || 0} runs.{ks.size === 1 ? ` k = ${[...ks][0]}: Hauntlet prints pass^k for k in 1, 2, 4, 8 up to the number of runs.` : ''}</p>
        </div>
        <Legend />
      </div>
      <div className="hw-card-body">
        {rooms.length === 0 ? (
          <Empty icon={<Moon />} title={r ? 'This run has no room results' : 'No range results yet'}>
            <p>{r?.reason ? r.reason : 'The first nightly run fills this table: selftest, then naive and hardened in every room. Press Run now to fill it right away; it takes a few seconds and uses no credits.'}</p>
          </Empty>
        ) : (
          <table className="hw-table">
            <thead><tr><th>Room</th><th>naive · expected high</th><th>hardened · expected L0</th><th>Scorecards</th></tr></thead>
            <tbody>
              {rooms.map((room) => {
                const series = (a: string) => history.map((h) => h.rooms?.[room]?.[a])
                const naive = r?.rooms?.[room]?.naive
                const hard = r?.rooms?.[room]?.hardened
                const demo = r?.demos?.[room]
                return (
                  <tr key={room}>
                    <td className="hw-room">{room}<small>{demo?.after_worst ? `Exorcist demo ${demo.before_worst} → ${demo.after_worst}` : room === 'parlor' ? 'no Exorcist demo for this room' : ''}</small></td>
                    <td><AgentCell now={naive} series={series('naive')} /></td>
                    <td><AgentCell now={hard} series={series('hardened')} /></td>
                    <td>
                      <div className="hw-links">
                        <ReportLink path={naive?.report} label="naive" />
                        <ReportLink path={hard?.report} label="hardened" />
                        {demo?.report && <ReportLink path={demo.report} label="exorcism" />}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}

function ReportLink({ path, label }: { path?: string; label: string }) {
  const href = reportHref(path)
  if (!href || !path) return null
  return (
    <span className="hw-rep">
      <a className="hw-link" href={href} target="_blank" rel="noopener noreferrer" title={`Open ${label} scorecard`}>{label}<External /></a>
      <span className="hw-path" title={path}>{path.split('/').pop()}</span>
    </span>
  )
}

export function ErrorsPanel({ run }: { run: RunRecord | null }) {
  const errs = run?.errors ?? []
  if (!errs.length) return null
  return (
    <section className="hw-card" aria-labelledby="hw-errs">
      <div className="hw-card-head"><div><h2 id="hw-errs">What did not complete</h2><p>Later commands still ran. Fix the first one and press Run now.</p></div></div>
      <div className="hw-card-body hw-errlist" style={{ paddingTop: 14 }}>
        {errs.map((e, i) => (
          <div className="hw-err" key={i}><div className="cmd">{e.command} · {e.kind}</div><div className="msg">{e.detail}</div></div>
        ))}
      </div>
    </section>
  )
}

export function DriftPanel({ drift, settings, busy, onCheck }: {
  drift: DriftReport | null; settings: Settings | null; busy: boolean; onCheck: () => void
}) {
  const files = drift?.files ? Object.entries(drift.files) : []
  const ws = drift?.workspace || settings?.watched_workspace
  return (
    <section className="hw-card" aria-labelledby="hw-drift">
      <div className="hw-card-head">
        <div>
          <h2 id="hw-drift">Guardrail drift</h2>
          <p>{ws ? <>Read-only comparison of <span className="hw-path">{ws}/.kiro</span> with what the Exorcist generates{drift?.checked_at ? `, checked ${relTime(drift.checked_at)}` : ''}.</> : 'Compares one workspace’s .kiro/ with the guardrails the Exorcist generates. Warden never writes to it.'}</p>
        </div>
        <button className="hw-btn small" onClick={onCheck} disabled={busy || !settings?.watched_workspace}>
          <Refresh className={busy ? 'hw-spin' : ''} />Check drift now
        </button>
      </div>
      <div className="hw-card-body">
        {!settings?.watched_workspace ? (
          <Empty icon={<Folder />} title="No workspace watched">
            <p>Set a workspace path in Settings below. Warden reads its .kiro/ steering, hooks, mcp.json and sandbox.json, and reports what is missing or weaker, file by file.</p>
          </Empty>
        ) : drift?.status === 'no reference yet' || (!files.length && !drift?.error && drift?.status !== 'n/a') ? (
          <Empty icon={<Shield />} title="No reference yet">
            <p>The reference comes from the Exorcist demo bundles that each nightly run generates. Run the range once, then drift appears here.</p>
          </Empty>
        ) : drift?.status === 'error' ? (
          <Empty icon={<Shield />} title="Could not check this workspace"><p>{drift.error || 'Unknown error'}</p></Empty>
        ) : (
          <div className="hw-files">
            {files.map(([file, info]) => {
              const bad = info.items.filter((i) => i.status !== 'present' && i.status !== 'n/a').length
              return (
                <details className="hw-file" key={file} open={info.status === 'missing' || info.status === 'weaker'}>
                  <summary>
                    <Caret className="hw-caret" />
                    <span className="name">{file}</span>
                    <span className="count">{bad ? `${bad} of ${info.items.length} need attention` : `${info.items.length} checked`}</span>
                    <StatusChip status={info.status} />
                  </summary>
                  <div className="hw-items">
                    {info.items.map((it) => (
                      <div className="hw-item" key={it.item}>
                        <span className="rule">{it.item.includes('#') ? it.item.split('#').pop() : it.item.split('/').pop()}</span>
                        <span><StatusChip status={it.status} /></span>
                        <div><div className="detail">{it.detail || defaultDetail(it.status)}</div><div className="rooms">generated for {it.rooms.join(', ')}</div></div>
                      </div>
                    ))}
                  </div>
                </details>
              )
            })}
          </div>
        )}
        {!!drift?.warnings?.length && (
          <div className="hw-warn" role="note">{drift.warnings.map((w) => <span key={w}>⚠ {w}</span>)}</div>
        )}
        <p className="hw-note">{CLIENT_NOTE}</p>
      </div>
    </section>
  )
}

function defaultDetail(s: string) {
  return s === 'present' ? 'Matches the generated guardrail.' : s === 'n/a' ? 'Nothing here to compare.' : ''
}

export function StatusChip({ status }: { status: string }) {
  const c = DRIFT_COLOR[status] ?? T.muted
  return status === 'n/a' ? <span className="hw-chip line" style={{ color: c }}>n/a</span> : <span className="hw-chip fill" style={{ background: c }}>{status}</span>
}

export function Welcome({ errors, settings, onOpenSettings }: { errors: string[]; settings: Settings | null; onOpenSettings: () => void }) {
  const hasCheckout = !!settings?.hauntlet_checkout && !errors.some((e) => /checkout/i.test(e))
  return (
    <div className="hw-hero">
      <Empty icon={<Ghost />} title="Point Warden at your Hauntlet checkout">
        <p>Warden runs Hauntlet’s model-free checks every night at 03:00 and watches one workspace’s guardrails. Nothing it runs uses a model or credits.</p>
        <ol className="hw-steps">
          <li className={hasCheckout ? 'done' : ''}>Set the path to your local Hauntlet checkout (run <code>uv sync</code> there first).</li>
          <li className={settings?.watched_workspace ? 'done' : ''}>Optionally, set a workspace whose .kiro/ guardrails Warden should watch.</li>
          <li>Save, then press Run now or turn on the nightly check.</li>
        </ol>
        <div style={{ marginTop: 14 }}><button className="hw-btn primary small" onClick={onOpenSettings}>Open settings</button></div>
      </Empty>
    </div>
  )
}
