// Hand-drawn SVG charts (Requirement 7.2: no chart library).

import { LEVELS, T, levelOf } from './theme'
import type { AgentResult } from './api'

const W = 132
const H = 34
const PAD = 4

function x(i: number, n: number) {
  return n <= 1 ? W / 2 : PAD + (i * (W - 2 * PAD)) / (n - 1)
}

/** Worst level over time: a step line, each run a dot in its level colour. L4 is at the top. */
export function LevelTrend({ points }: { points: (AgentResult | undefined)[] }) {
  const n = points.length
  const y = (lv: number) => H - PAD - (lv * (H - 2 * PAD)) / 4
  const vals = points.map((p) => (p?.worst ? Number(p.worst.slice(1)) : null))
  let d = ''
  vals.forEach((v, i) => {
    if (v === null) return
    const prev = vals.slice(0, i).reverse().find((p) => p !== null)
    d += prev === undefined || prev === null ? `M${x(i, n)},${y(v)}` : ` H${x(i, n)} V${y(v)}`
  })
  const label = vals.filter((v) => v !== null).map((v) => `L${v}`).join(', ')
  return (
    <svg className="hw-spark" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Worst level over the last ${n} runs: ${label || 'none'}`}>
      {[0, 1, 2, 3, 4].map((lv) => (
        <line key={lv} x1={PAD} x2={W - PAD} y1={y(lv)} y2={y(lv)} stroke={T.border} strokeWidth={lv === 0 || lv === 4 ? 1 : 0.5} strokeDasharray={lv === 0 || lv === 4 ? '' : '2 3'} />
      ))}
      <path d={d} fill="none" stroke={T.muted} strokeWidth={1.25} />
      {vals.map((v, i) =>
        v === null ? (
          <circle key={i} cx={x(i, n)} cy={H / 2} r={2} fill="none" stroke={T.muted} strokeWidth={1} />
        ) : (
          <circle key={i} cx={x(i, n)} cy={y(v)} r={i === n - 1 ? 3.4 : 2.3} fill={LEVELS[v].color}>
            <title>{`L${v} ${LEVELS[v].name}`}</title>
          </circle>
        ),
      )}
    </svg>
  )
}

/** pass^k over time, 0 at the bottom and 1 at the top. */
export function PassTrend({ points }: { points: (AgentResult | undefined)[] }) {
  const n = points.length
  const y = (v: number) => H - PAD - v * (H - 2 * PAD)
  const vals = points.map((p) => (typeof p?.pass_k === 'number' ? p.pass_k : null))
  const pts = vals.map((v, i) => (v === null ? null : `${x(i, n)},${y(v)}`)).filter(Boolean)
  const last = vals[vals.length - 1]
  const colour = last === null || last === undefined ? T.muted : last >= 0.999 ? LEVELS[0].color : last > 0 ? LEVELS[2].color : LEVELS[4].color
  return (
    <svg className="hw-spark" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`pass^k over the last ${n} runs`}>
      <line x1={PAD} x2={W - PAD} y1={y(1)} y2={y(1)} stroke={T.border} strokeWidth={1} />
      <line x1={PAD} x2={W - PAD} y1={y(0)} y2={y(0)} stroke={T.border} strokeWidth={1} />
      {pts.length > 1 && <polyline points={pts.join(' ')} fill="none" stroke={colour} strokeWidth={1.5} />}
      {vals.map((v, i) => (v === null ? null : <circle key={i} cx={x(i, n)} cy={y(v)} r={i === n - 1 ? 3 : 1.6} fill={colour} />))}
    </svg>
  )
}

export function LevelChip({ id, outline }: { id?: string | null; outline?: boolean }) {
  const lv = levelOf(id)
  if (!lv) return <span className="hw-chip line" style={{ color: T.muted }}>no result</span>
  return outline ? (
    <span className="hw-chip line" style={{ color: lv.color }}><span className="dot" />{lv.id} {lv.name}</span>
  ) : (
    <span className="hw-chip fill" style={{ background: lv.color }} title={`${lv.id} ${lv.name}`}>{lv.id} {lv.name}</span>
  )
}
