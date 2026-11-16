import { useEffect, useState } from 'react'
import type { AppApiClient } from '@kirocrew/app-sdk'
import { errorText, gitInstall, saveSettings, type Settings, type State } from './api'

export function SettingsPanel({ api, state, open, onToggle, onSaved }: {
  api: AppApiClient; state: State; open: boolean; onToggle: (o: boolean) => void; onSaved: () => void
}) {
  const s = state.settings
  const [checkout, setCheckout] = useState(s?.hauntlet_checkout ?? '')
  const [ws, setWs] = useState(s?.watched_workspace ?? '')
  const [rooms, setRooms] = useState<string[]>(s?.rooms ?? state.known_rooms)
  const [repeat, setRepeat] = useState(s?.repeat ?? 3)
  const [source, setSource] = useState<Settings['hauntlet_source']>(s?.hauntlet_source ?? 'checkout')
  const [errors, setErrors] = useState<string[]>([])
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [approve, setApprove] = useState(false)
  const [installMsg, setInstallMsg] = useState('')

  useEffect(() => {
    if (!s) return
    setCheckout(s.hauntlet_checkout); setWs(s.watched_workspace); setRooms(s.rooms); setRepeat(s.repeat); setSource(s.hauntlet_source)
  }, [s?.hauntlet_checkout, s?.watched_workspace, s?.repeat, s?.hauntlet_source, (s?.rooms ?? []).join(',')])

  const gitInstalled = !!s?.git_install?.approved && !!s?.git_install?.tool_path

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setSaved(false); setErrors([])
    try {
      await saveSettings(api, {
        hauntlet_source: source, hauntlet_checkout: checkout.trim(), watched_workspace: ws.trim(),
        rooms: state.known_rooms.filter((r) => rooms.includes(r)), repeat: Number(repeat),
        uv_path: s?.uv_path ?? '', command_timeout_secs: s?.command_timeout_secs ?? 150,
      })
      setSaved(true); onSaved()
    } catch (err) {
      setErrors(errorText(err).split('; '))
    } finally {
      setBusy(false)
    }
  }

  async function install() {
    setBusy(true); setInstallMsg('')
    try {
      const r = await gitInstall(api)
      setInstallMsg(`Installed: ${r.tool_path}`); onSaved()
    } catch (err) {
      setInstallMsg(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  const toggle = (room: string) => setRooms((rs) => (rs.includes(room) ? rs.filter((r) => r !== room) : [...rs, room]))

  return (
    <details className="hw-card" open={open} onToggle={(e) => onToggle((e.target as HTMLDetailsElement).open)}>
      <summary className="hw-card-head" style={{ cursor: 'pointer', listStyle: 'none' }}>
        <div><h2>Settings</h2><p>{s ? (state.settings_errors.length ? state.settings_errors[0] : 'Saved. Runs use these on the next start.') : 'Not configured yet.'}</p></div>
        <span className="hw-help">{open ? 'Hide' : 'Show'}</span>
      </summary>
      <form className="hw-card-body hw-form" onSubmit={save}>
        <div className="hw-field wide">
          <span className="lab">Hauntlet source</span>
          <div className="hw-checks" role="radiogroup">
            <label className={`hw-check ${source === 'checkout' ? 'on' : ''}`}>
              <input type="radio" name="src" checked={source === 'checkout'} onChange={() => setSource('checkout')} />local checkout
            </label>
            <label className={`hw-check ${source === 'git' ? 'on' : ''}`} title={gitInstalled ? '' : 'Install from GitHub first'}>
              <input type="radio" name="src" checked={source === 'git'} disabled={!gitInstalled} onChange={() => setSource('git')} />installed from GitHub
            </label>
          </div>
        </div>
        <div className="hw-field">
          <label htmlFor="hw-co">Hauntlet checkout</label>
          <input id="hw-co" className="hw-input" value={checkout} onChange={(e) => setCheckout(e.target.value)} placeholder="/Users/you/src/hauntlet" spellCheck={false} />
          <span className="hw-help">Run as <code>uv run --offline --project &lt;path&gt; hauntlet …</code> from Warden’s own range directory. Run <code>uv sync</code> in the checkout first.</span>
        </div>
        <div className="hw-field">
          <label htmlFor="hw-ws">Watched workspace (optional)</label>
          <input id="hw-ws" className="hw-input" value={ws} onChange={(e) => setWs(e.target.value)} placeholder="/Users/you/src/my-project" spellCheck={false} />
          <span className="hw-help">Read-only. Warden reads its .kiro/ and never writes there.</span>
        </div>
        <div className="hw-field wide">
          <span className="lab">Rooms</span>
          <div className="hw-checks">
            {state.known_rooms.map((r) => (
              <label key={r} className={`hw-check ${rooms.includes(r) ? 'on' : ''}`}>
                <input type="checkbox" checked={rooms.includes(r)} onChange={() => toggle(r)} />{r}
              </label>
            ))}
          </div>
        </div>
        <div className="hw-field">
          <label htmlFor="hw-k">Repeats per agent (k)</label>
          <input id="hw-k" className="hw-input num" type="number" min={1} max={10} value={repeat} onChange={(e) => setRepeat(Number(e.target.value))} />
          <span className="hw-help">Hauntlet prints pass^k for k in 1, 2, 4, 8 up to this number. At 3 the headline is pass^2.</span>
        </div>
        <div className="hw-sub-card">
          <strong style={{ fontSize: 13 }}>Install Hauntlet from GitHub</strong>
          <span className="hw-help">One-time, only when you approve it: <code>uv tool install</code> from github.com/kuberaplutus224/hauntlet into Warden’s data dir. After that every run is offline. The local checkout stays the default.</span>
          <div className="row">
            <label className="hw-check"><input type="checkbox" checked={approve} onChange={(e) => setApprove(e.target.checked)} />I approve this one-time download</label>
            <button type="button" className="hw-btn small" disabled={!approve || busy} onClick={install}>{gitInstalled ? 'Reinstall' : 'Install'}</button>
            {installMsg && <span>{installMsg}</span>}
          </div>
        </div>
        {errors.length > 0 && <ul className="hw-errors">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
        <div className="hw-formfoot">
          <button className="hw-btn primary" type="submit" disabled={busy}>Save settings</button>
          {saved && <span className="hw-saved">Saved</span>}
          <span className="hw-help">The schedule (03:00 local) is edited on the Schedule page. Disabling and re-enabling the app resets it to 03:00.</span>
        </div>
      </form>
    </details>
  )
}
