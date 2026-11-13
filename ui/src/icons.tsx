// Small inline icons. Drawn here rather than imported from lucide-react, so the page
// does not depend on which icons the host's lucide build exports.

type P = { className?: string }
const base = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const

export const Play = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true"><polygon points="6 4 20 12 6 20 6 4" /></svg>
)
export const Refresh = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true">
    <path d="M21 12a9 9 0 1 1-2.64-6.36" /><polyline points="21 3 21 9 15 9" />
  </svg>
)
export const Chat = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true">
    <path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z" />
  </svg>
)
export const Shield = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true">
    <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" /><polyline points="9 12 11 14 15 10" />
  </svg>
)
export const Ghost = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true">
    <path d="M5 21V10a7 7 0 0 1 14 0v11l-2.5-2-2.3 2-2.2-2-2.2 2-2.3-2L5 21z" />
    <circle cx="9.5" cy="10.5" r="1" fill="currentColor" /><circle cx="14.5" cy="10.5" r="1" fill="currentColor" />
  </svg>
)
export const Moon = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" /></svg>
)
export const External = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true">
    <path d="M14 4h6v6" /><path d="M20 4l-9 9" /><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" />
  </svg>
)
export const Caret = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true"><polyline points="9 6 15 12 9 18" /></svg>
)
export const Folder = (p: P) => (
  <svg viewBox="0 0 24 24" {...base} className={p.className} aria-hidden="true">
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
  </svg>
)
