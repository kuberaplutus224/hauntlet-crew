// Local preview only: a stand-in for the host's @kirocrew/app-sdk with canned data.
// Pick a scene with ?scene=welcome | norun | full. Never shipped in ui/dist.

type Any = any
const scene = new URLSearchParams(location.search).get('scene') ?? 'full'
const ROOMS = ['threshold', 'cursed-repo', 'cursed-repo-tests', 'poltergeist', 'poltergeist-legacy', 'parlor']
const day = (i: number) => new Date(Date.UTC(2026, 10, 13 - i, 8, 0, 4)).toISOString().replace('.000', '')

function agent(room: string, a: string, i: number): Any {
  const regress = a === 'hardened' && room === 'poltergeist' && i < 2
  const worst = a === 'naive' ? (room === 'cursed-repo-tests' ? 'L3' : 'L4') : regress ? 'L2' : 'L0'
  return {
    worst, k: 2, n: 3, detected: a === 'hardened' ? 1 : 0, task: 1, error: null,
    pass_k: a === 'naive' ? 0 : regress ? 0.33 : 1,
    report: `/Users/you/.kiro/crew/apps/hauntlet-warden/data/range/reports/autopsy-${room}-${a}-Run${i}AbCdEfGh.html`,
  }
}
const rooms = (i: number) => Object.fromEntries(ROOMS.map((r) => [r, { naive: agent(r, 'naive', i), hardened: agent(r, 'hardened', i) }]))
const drift = {
  status: 'missing', checked_at: day(0), workspace: '/Users/you/src/payments-service',
  files: {
    '.kiro/hooks/credential-egress.json': { status: 'weaker', items: [
      { item: '.kiro/hooks/credential-egress.json#credential-egress-mcp', kind: 'hook', status: 'weaker', rooms: ['poltergeist', 'poltergeist-legacy'], detail: 'action is agent, so it is advisory, not enforced' },
      { item: '.kiro/hooks/credential-egress.json#credential-egress-shell', kind: 'hook', status: 'present', rooms: ['cursed-repo', 'threshold'], detail: '' },
      { item: '.kiro/hooks/credential-egress.json#credential-egress-web', kind: 'hook', status: 'weaker', rooms: ['cursed-repo', 'poltergeist'], detail: "matcher 'we' is narrower than 'web'" },
    ] },
    '.kiro/settings/mcp.json': { status: 'weaker', items: [
      { item: 'mcp.json#autoApprove', kind: 'mcp', status: 'weaker', rooms: ['poltergeist', 'poltergeist-legacy'], detail: 'autoApprove is not empty for: github' },
      { item: 'mcp.json#disabledTools', kind: 'mcp', status: 'review', rooms: ['poltergeist', 'poltergeist-legacy'], detail: 'no disabledTools for: github (only you know which tools the task needs)' },
    ] },
    '.kiro/settings/sandbox.json': { status: 'weaker', items: [
      { item: '.kiro/settings/sandbox.json#enabled', kind: 'sandbox', status: 'present', rooms: ['cursed-repo'], detail: '' },
      { item: '.kiro/settings/sandbox.json#networkAccess', kind: 'sandbox', status: 'weaker', rooms: ['cursed-repo', 'threshold'], detail: 'networkAccess is "ALLOW_ALL", generated is "DEFAULT_BLOCKED"' },
    ] },
    '.kiro/steering/credentials.md': { status: 'present', items: [
      { item: '.kiro/steering/credentials.md#SECRETS', kind: 'steering', status: 'present', rooms: ['cursed-repo', 'poltergeist', 'threshold'], detail: '' },
    ] },
    '.kiro/steering/untrusted-content.md': { status: 'missing', items: [
      { item: '.kiro/steering/untrusted-content.md#DATA', kind: 'steering', status: 'missing', rooms: ['cursed-repo', 'poltergeist'], detail: 'rule text not found in any steering file' },
      { item: '.kiro/steering/untrusted-content.md#REPORT', kind: 'steering', status: 'missing', rooms: ['cursed-repo', 'poltergeist'], detail: 'rule text not found in any steering file' },
    ] },
  },
  warnings: ['A Hauntlet room server is configured in this workspace: scratch-room'],
  note: 'Some client behaviours are out of reach of config.',
}
const settings = {
  hauntlet_source: 'checkout', hauntlet_checkout: '/Users/you/src/hauntlet', watched_workspace: '/Users/you/src/payments-service',
  rooms: ROOMS, repeat: 3, uv_path: '', command_timeout_secs: 150, git_install: { approved: false, installed_at: null, tool_path: null },
}
const latest = scene === 'full' ? {
  run_id: 'r0', trigger: 'schedule', started_at: day(0), finished_at: day(0), status: 'ok',
  selftest: { passed: true, summary: 'selftest passed: 6 room(s), naive >= L3 and hardened L0+Detected over n=3', failures: [] },
  rooms: rooms(0), errors: [], drift,
  demos: Object.fromEntries(ROOMS.filter((r) => r !== 'parlor').map((r) => [r, { before_worst: 'L4', after_worst: 'L0', report: `/x/exorcist-reports/exorcist-delta-Demo${r.length}AbCdEf.html` }])),
} : null
const state = {
  latest,
  settings: scene === 'welcome' ? null : settings,
  settings_errors: scene === 'welcome' ? ['not configured'] : [],
  drift: scene === 'full' ? { status: 'missing', checked_at: day(0), workspace: settings.watched_workspace } : {},
  reference: { rooms: {} }, known_rooms: ROOMS, demo_rooms: ROOMS.slice(0, 5),
}
const history = scene === 'full' ? Array.from({ length: 14 }, (_, j) => ({ run_id: `r${13 - j}`, status: 'ok', rooms: rooms(13 - j) })) : []

const api = {
  async get(path: string) {
    if (path.endsWith('/state')) return state
    if (path.includes('/history')) return { runs: history }
    if (path.endsWith('/drift')) return scene === 'full' ? drift : { status: 'none' }
    if (path.endsWith('/summary')) return { text: '# Hauntlet Warden summary\n\nNo run yet.\n' }
    if (path === '/api/crons') return { jobs: [{ id: 'abc123', name: 'hauntlet-warden/nightly-range-check', app: 'hauntlet-warden', enabled: scene === 'full', user_paused: scene !== 'full', schedule: 'At 3:00 AM EST' }] }
    throw new Error('mock: ' + path)
  },
  async post() { return { ok: true } },
  async put(_p: string, body: Any) { return { settings: body, errors: [] } },
  async patch() { return {} },
  async del() { return {} },
}

export const useAppApi = () => api
export const useNotify = () => () => {}
export const useChatLauncher = () => ({ openChat: (o: Any) => console.log('openChat', o) })
