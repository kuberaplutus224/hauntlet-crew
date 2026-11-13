// Hauntlet Warden dashboard page. Default export, mounted by the Crew dashboard.

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAppApi, useChatLauncher } from '@kirocrew/app-sdk'
import {
  AGENT, askMessage, checkDrift, errorText, findJob, getDrift, getHistory, getState, getSummary, runNow, setNightly,
  type CronJob, type DriftReport, type HistoryRun, type State,
} from './api'
import { Chat, Moon, Play } from './icons'
import { DriftPanel, ErrorsPanel, RoomsPanel, Tiles, Welcome } from './panels'
import { SettingsPanel } from './settings'
import { CSS } from './theme'

const POLL_MS = 5000
const POLL_MAX_MS = 3 * 60 * 1000

export default function WardenPage() {
  const api = useAppApi()
  const { openChat } = useChatLauncher()
  const [state, setState] = useState<State | null>(null)
  const [history, setHistory] = useState<HistoryRun[]>([])
  const [drift, setDrift] = useState<DriftReport | null>(null)
  const [job, setJob] = useState<CronJob | null | undefined>(undefined)
  const [loadError, setLoadError] = useState('')
  const [banner, setBanner] = useState<{ kind: 'info' | 'bad'; text: string } | null>(null)
  const [running, setRunning] = useState(false)
  const [checking, setChecking] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const pollRef = useRef<number | null>(null)

  const load = useCallback(async () => {
    try {
      const [st, h, d] = await Promise.all([getState(api), getHistory(api), getDrift(api)])
      setState(st)
      setHistory(h.runs)
      setDrift(d && d.status !== 'none' ? d : st.latest?.drift ?? null)
      setLoadError('')
      if (!st.settings || st.settings_errors.length) setSettingsOpen(true)
      return st
    } catch (e) {
      setLoadError(errorText(e))
      return null
    }
  }, [api])

  const loadJob = useCallback(async () => {
    try { setJob(await findJob(api)) } catch { setJob(null) }
  }, [api])

  useEffect(() => {
    load(); loadJob()
    const onFocus = () => { load(); loadJob() }
    window.addEventListener('focus', onFocus)
    return () => { window.removeEventListener('focus', onFocus); if (pollRef.current) window.clearInterval(pollRef.current) }
  }, [load, loadJob])

  const configured = !!state?.settings && state.settings_errors.length === 0

  async function onRun() {
    if (!job) return setBanner({ kind: 'bad', text: 'The nightly-range-check job is not registered. Re-enable the app.' })
    setRunning(true)
    setBanner({ kind: 'info', text: 'Running selftest, both reference agents in every room, and the Exorcist demos…' })
    const before = state?.latest?.run_id
    try {
      await runNow(api, job)
    } catch (e) {
      setRunning(false)
      return setBanner({ kind: 'bad', text: `Could not start the run: ${errorText(e)}` })
    }
    const started = Date.now()
    pollRef.current = window.setInterval(async () => {
      const st = await load()
      const done = st?.latest && st.latest.run_id !== before
      if (done || Date.now() - started > POLL_MAX_MS) {
        if (pollRef.current) window.clearInterval(pollRef.current)
        setRunning(false)
        setBanner(done ? null : { kind: 'bad', text: 'No result after 3 minutes. Check the run on the Schedule page.' })
      }
    }, POLL_MS)
  }

  async function onCheckDrift() {
    setChecking(true)
    try { setDrift(await checkDrift(api)) } catch (e) { setBanner({ kind: 'bad', text: `Drift check failed: ${errorText(e)}` }) }
    setChecking(false)
  }

  async function onAsk() {
    try {
      const { text } = await getSummary(api)
      openChat({ agent: AGENT, message: askMessage(text), autoSend: false })
    } catch (e) {
      setBanner({ kind: 'bad', text: `Could not read the summary: ${errorText(e)}` })
    }
  }

  async function onNightly() {
    if (!job) return
    try { await setNightly(api, job, true); await loadJob() } catch (e) { setBanner({ kind: 'bad', text: errorText(e) }) }
  }

  const paused = !!job && (job.user_paused || job.enabled === false)

  return (
    <div className="hw">
      <style>{CSS}</style>
      <div className="hw-wrap">
        <header className="hw-head">
          <div>
            <p className="hw-kicker">Hauntlet · Kiro Crew</p>
            <h1 className="hw-title">Hauntlet Warden</h1>
            <p className="hw-sub">Nightly range check and guardrail drift. No model, no credits, localhost only.</p>
          </div>
          <div className="hw-actions">
            {configured && paused && (
              <button className="hw-btn" onClick={onNightly} title="Resume the app's own 03:00 job"><Moon />Turn on nightly check</button>
            )}
            <button className="hw-btn ghost" onClick={onAsk} title="Opens a chat with the Warden agent, seeded with the latest summary. One agent turn per question uses credits.">
              <Chat />Ask Warden
            </button>
            <button className="hw-btn primary" onClick={onRun} disabled={!configured || running || !job}
              title={configured ? 'Run the range now (no credits)' : 'Save valid settings first'}>
              <Play className={running ? 'hw-spin' : ''} />{running ? 'Running…' : 'Run now'}
            </button>
          </div>
        </header>

        {loadError && <div className="hw-banner bad" role="alert">Could not reach Warden’s backend: {loadError}</div>}
        {banner && <div className={`hw-banner ${banner.kind}`} role="status">{banner.text}</div>}

        {!state ? (
          <div aria-busy="true">
            <div className="hw-skel" style={{ height: 92, marginBottom: 18 }} />
            <div className="hw-skel" style={{ height: 320 }} />
          </div>
        ) : (
          <>
            {!configured && <Welcome errors={state.settings_errors} settings={state.settings} onOpenSettings={() => setSettingsOpen(true)} />}
            <Tiles state={state} job={job} />
            <ErrorsPanel run={state.latest} />
            <RoomsPanel state={state} history={history} />
            <DriftPanel drift={drift} settings={state.settings} busy={checking} onCheck={onCheckDrift} />
            <SettingsPanel api={api} state={state} open={settingsOpen} onToggle={setSettingsOpen} onSaved={() => { load(); loadJob() }} />
          </>
        )}

        <footer className="hw-foot">
          <span>Only “Ask Warden” uses credits: one agent turn per question. Scheduled runs, Run now and drift checks call no model.</span>
          <span>Dummy secrets appear only as HAUNTLET-DUMMY-…</span>
        </footer>
      </div>
    </div>
  )
}
