// Data access for the Warden page. All calls go through the host's permission-scoped
// client (useAppApi), to the gateway's /api/crons and to Warden's own backend proxy.

import type { AppApiClient } from '@kirocrew/app-sdk'

export const APP = 'hauntlet-warden'
export const AGENT = 'hauntlet-warden'
export const CRON_NAME = `${APP}/nightly-range-check`
export const BACKEND = `/apps/${APP}/api`
export const SUMMARY_LIMIT = 4000
export const CLIENT_NOTE = 'Some client behaviours are out of reach of config.'

export type Level = 'L0' | 'L1' | 'L2' | 'L3' | 'L4'

export interface AgentResult {
  worst?: Level
  pass_k?: number | null
  k?: number | null
  detected?: number
  task?: number
  error?: string | null
  report?: string
  n?: number
}

export interface DriftItem {
  item: string
  kind: string
  status: string
  rooms: string[]
  detail: string
}

export interface DriftReport {
  status: string
  checked_at?: string
  workspace?: string
  files?: Record<string, { status: string; items: DriftItem[] }>
  warnings?: string[]
  error?: string
  note?: string
}

export interface RunRecord {
  run_id: string
  trigger?: string
  started_at?: string
  finished_at?: string | null
  status: string
  reason?: string
  selftest?: { passed?: boolean | null; summary?: string; failures?: string[]; error?: string | null }
  rooms?: Record<string, Record<string, AgentResult>>
  demos?: Record<string, { report?: string; before_worst?: Level; after_worst?: Level; error?: string | null }>
  errors?: { command: string; kind: string; detail: string }[]
  drift?: DriftReport | null
}

export interface Settings {
  hauntlet_source: 'checkout' | 'git'
  hauntlet_checkout: string
  watched_workspace: string
  rooms: string[]
  repeat: number
  uv_path: string
  command_timeout_secs: number
  git_install: { approved: boolean; installed_at: string | null; tool_path: string | null }
}

export interface State {
  latest: RunRecord | null
  settings: Settings | null
  settings_errors: string[]
  drift: { status?: string; checked_at?: string; workspace?: string }
  reference: { rooms: Record<string, string> }
  known_rooms: string[]
  demo_rooms: string[]
}

export interface HistoryRun {
  run_id: string
  finished_at?: string
  status: string
  rooms: Record<string, Record<string, AgentResult>>
}

export interface CronJob {
  id: string
  name: string
  app?: string
  enabled?: boolean
  user_paused?: boolean
  schedule?: string
  next_run?: number | string | null
}

export const getState = (api: AppApiClient) => api.get<State>(`${BACKEND}/state`)
export const getHistory = (api: AppApiClient) => api.get<{ runs: HistoryRun[] }>(`${BACKEND}/history?limit=30`)
export const getDrift = (api: AppApiClient) => api.get<DriftReport>(`${BACKEND}/drift`)
export const checkDrift = (api: AppApiClient) => api.post<DriftReport>(`${BACKEND}/drift/check`, {})
export const getSummary = (api: AppApiClient) => api.get<{ text: string }>(`${BACKEND}/summary`)
export const saveSettings = (api: AppApiClient, s: Partial<Settings>) =>
  api.put<{ settings: Settings; errors: string[] }>(`${BACKEND}/settings`, s)
export const gitInstall = (api: AppApiClient) =>
  api.post<{ ok: boolean; tool_path: string }>(`${BACKEND}/git-install`, { approve: true })

export async function findJob(api: AppApiClient): Promise<CronJob | null> {
  const d = await api.get<{ jobs: CronJob[] }>('/api/crons')
  return d.jobs.find((j) => j.app === APP && j.name === CRON_NAME) ?? null
}

/** "Run now": mark the run as manual, then trigger the app's own cron job (spike 1.5). */
export async function runNow(api: AppApiClient, job: CronJob) {
  await api.post(`${BACKEND}/run-request`, {})
  await api.post(`/api/crons/${encodeURIComponent(job.id)}/run`, {})
}

export const setNightly = (api: AppApiClient, job: CronJob, enabled: boolean) =>
  api.post(`/api/crons/${encodeURIComponent(job.id)}/enable`, { enabled })

/** The message "Ask Warden" puts in the chat composer (option A: the agent has no tools). */
export function askMessage(summary: string): string {
  let text = summary.trim() || 'No run yet.'
  if (text.length > SUMMARY_LIMIT) text = text.slice(0, SUMMARY_LIMIT) + '\n[summary truncated]'
  return [
    'Here is the current Hauntlet Warden summary. Answer my question from it only.',
    '',
    '--- Warden summary ---',
    text,
    '--- end of summary ---',
    '',
    'Question: ',
  ].join('\n')
}

export function reportHref(path: string | undefined): string | null {
  if (!path) return null
  const name = path.split('/').pop() ?? ''
  if (!/^(autopsy-[a-z0-9-]+-(naive|hardened)-[A-Za-z0-9_-]{8,64}|exorcist-delta-[A-Za-z0-9_-]{8,64})\.html$/.test(name)) return null
  return `${BACKEND}/reports/${name}`
}

export function relTime(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return iso
  const s = Math.round((now - t) / 1000)
  if (s < 45) return 'just now'
  const m = Math.round(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.round(m / 60)
  if (h < 36) return `${h} h ago`
  return `${Math.round(h / 24)} days ago`
}

export function localTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function errorText(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e)
  const m = msg.match(/\{.*\}$/s)
  if (m) {
    try {
      const j = JSON.parse(m[0])
      if (Array.isArray(j.errors) && j.errors.length) return j.errors.join('; ')
      if (j.error) return String(j.error)
    } catch {
      /* fall through */
    }
  }
  return msg
}
