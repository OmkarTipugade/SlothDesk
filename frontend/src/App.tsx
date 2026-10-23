import { useCallback, useEffect, useState, type ReactNode } from 'react'
import {
  Archive, ArrowRight, Check, CheckCircle2, ChevronDown, CircleAlert, ClipboardList,
  Clock3, FileArchive, FileImage, FileText, FolderOpen, LayoutDashboard, LoaderCircle,
  Menu, Moon, MoreHorizontal, RefreshCw, Search, Settings, ShieldCheck, Sparkles,
  Sun, X, XCircle,
} from 'lucide-react'
import { api, baseUrl } from './lib/api'
import type { ApplyResult, FileRecord, Health, PlanAction } from './types'

type Page = 'overview' | 'organize' | 'explorer' | 'history' | 'settings'
type Toast = { type: 'success' | 'error'; message: string }

const navItems: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'organize', label: 'Organize Files', icon: Sparkles },
  { id: 'explorer', label: 'File Explorer', icon: FolderOpen },
  { id: 'history', label: 'Activity History', icon: Clock3 },
  { id: 'settings', label: 'Settings', icon: Settings },
]

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const fileIcon = (extension: string) => {
  if (['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(extension.toLowerCase())) return FileImage
  if (['.zip', '.tar', '.gz'].includes(extension.toLowerCase())) return FileArchive
  return FileText
}

function App() {
  const [page, setPage] = useState<Page>('overview')
  const [files, setFiles] = useState<FileRecord[]>([])
  const [actions, setActions] = useState<PlanAction[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState<'health' | 'scan' | 'plan' | 'apply' | null>(null)
  const [error, setError] = useState('')
  const [toast, setToast] = useState<Toast | null>(null)
  const [dark, setDark] = useState(() => localStorage.getItem('slothdesk-theme') === 'dark')
  const [confirming, setConfirming] = useState(false)
  const [result, setResult] = useState<ApplyResult | null>(null)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')
  const [mobileNav, setMobileNav] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('slothdesk-theme', dark ? 'dark' : 'light')
  }, [dark])

  const checkHealth = useCallback(async () => {
    setLoading('health')
    try { setHealth(await api.health()); setError('') } catch (e) { setHealth(null); setError(e instanceof Error ? e.message : 'Backend unavailable.') } finally { setLoading(null) }
  }, [])

  const scan = useCallback(async () => {
    setLoading('scan')
    try { setFiles(await api.scan()); setError(''); setToast({ type: 'success', message: 'Folder inventory refreshed.' }) } catch (e) { setError(e instanceof Error ? e.message : 'Unable to scan the folder.') } finally { setLoading(null) }
  }, [])

  useEffect(() => { void checkHealth() }, [checkHealth])
  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(null), 4000); return () => window.clearTimeout(timer) }, [toast])

  const generatePlan = async () => {
    setLoading('plan')
    try {
      const next = await api.plan()
      setActions(next); setSelected(new Set(next.map((_, index) => index))); setPage('organize'); setError('')
      setToast({ type: 'success', message: next.length ? `${next.length} suggestions ready for review.` : 'No organization suggestions found.' })
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to generate a plan.') } finally { setLoading(null) }
  }

  const applyPlan = async () => {
    const chosen = actions.filter((_, index) => selected.has(index))
    if (!chosen.length) return
    setLoading('apply')
    try {
      const applied = await api.apply(chosen)
      setResult(applied); setConfirming(false); setActions([]); setSelected(new Set())
      setToast({ type: 'success', message: `${applied.moved.length} file${applied.moved.length === 1 ? '' : 's'} organized.` })
      await scan()
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to apply the selected actions.') } finally { setLoading(null) }
  }

  const title = navItems.find((item) => item.id === page)?.label ?? 'Overview'
  const selectedCount = selected.size

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand"><span className="brand-mark">S</span><span>sloth<span className="brand-accent">desk</span></span><button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Close menu"><X size={18} /></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>{navItems.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); setMobileNav(false) }}><Icon size={18} />{label}{id === 'organize' && actions.length > 0 && <span className="nav-count">{actions.length}</span>}</button>)}</nav>
        <div className="sidebar-bottom">
          <div className={`local-status ${health ? 'online' : ''}`}><span className="status-dot" /><div><strong>Local AI</strong><small>{health ? 'Connected' : 'Not connected'}</small></div></div>
          <div className="sidebar-footer"><span>v0.1.0</span><span>Hacktoberfest 2026</span></div>
        </div>
      </aside>
      {mobileNav && <button className="mobile-overlay" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
      <main className="main-content">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open menu"><Menu size={20} /></button><div className="breadcrumbs"><span>SlothDesk</span><span>/</span><strong>{title}</strong></div><div className="topbar-actions"><span className={`connection-pill ${health ? 'connected' : ''}`}><span className="status-dot" />{health ? 'Backend connected' : 'Backend offline'}</span><button className="icon-button" onClick={() => setDark(!dark)} aria-label="Toggle theme">{dark ? <Sun size={18} /> : <Moon size={18} />}</button><button className="icon-button" onClick={() => void checkHealth()} disabled={loading === 'health'} aria-label="Refresh connection"><RefreshCw size={17} className={loading === 'health' ? 'spin' : ''} /></button></div></header>
        {error && <div className="error-banner"><CircleAlert size={18} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={16} /></button></div>}
        {page === 'overview' && <Dashboard files={files} actions={actions} health={health} loading={loading} onScan={scan} onPlan={generatePlan} onNavigate={setPage} />}
        {page === 'organize' && <Organize actions={actions} selected={selected} setSelected={setSelected} query={query} setQuery={setQuery} category={category} setCategory={setCategory} loading={loading} onPlan={generatePlan} onApply={() => setConfirming(true)} />}
        {page === 'explorer' && <Explorer files={files} query={query} setQuery={setQuery} loading={loading} onScan={scan} />}
        {page === 'history' && <History result={result} />}
        {page === 'settings' && <SettingsPage health={health} loading={loading} onRefresh={checkHealth} />}
      </main>
      {confirming && <ConfirmDialog actions={actions.filter((_, index) => selected.has(index))} loading={loading === 'apply'} onCancel={() => setConfirming(false)} onConfirm={() => void applyPlan()} />}
      {toast && <div className={`toast ${toast.type}`}><CheckCircle2 size={18} />{toast.message}</div>}
    </div>
  )
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>
}

function Dashboard({ files, actions, health, loading, onScan, onPlan, onNavigate }: { files: FileRecord[]; actions: PlanAction[]; health: Health | null; loading: string | null; onScan: () => void; onPlan: () => void; onNavigate: (page: Page) => void }) {
  return <div className="page"><PageHeader eyebrow="YOUR WORKSPACE" title="Good morning." description="A calmer way to keep your files in order." action={<button className="primary-button" onClick={onScan} disabled={loading === 'scan'}>{loading === 'scan' ? <LoaderCircle className="spin" size={17} /> : <FolderOpen size={17} />} Scan folder <ArrowRight size={16} /></button>} /><section className="hero-card"><div><div className="hero-icon"><Sparkles size={20} /></div><h2>Ready to make space?</h2><p>Scan your workspace and let your local AI suggest a thoughtful home for every file.</p><button className="dark-button" onClick={onPlan} disabled={loading === 'plan'}>{loading === 'plan' ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />} Generate AI plan</button></div><div className="hero-orbit"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><Archive size={25} /></div></div></section><div className="stat-grid"><Stat icon={FileText} label="Files scanned" value={files.length ? files.length.toString() : '—'} note={files.length ? 'Latest inventory' : 'Scan to get started'} /><Stat icon={Sparkles} label="Suggestions" value={actions.length ? actions.length.toString() : '—'} note={actions.length ? 'Waiting for review' : 'No plan generated'} /><Stat icon={CheckCircle2} label="Files organized" value="—" note="No history available yet" /><Stat icon={MoreHorizontal} label="Duplicates" value="—" note="Not supported by API" /></div><div className="dashboard-grid"><div className="card activity-card"><div className="card-heading"><div><div className="eyebrow">WORKFLOW</div><h3>Recent activity</h3></div><button className="text-button" onClick={() => onNavigate('history')}>View history <ArrowRight size={14} /></button></div>{actions.length ? actions.slice(0, 3).map((action) => <div className="activity-row" key={`${action.source}-${action.destination}`}><span className="activity-check"><Sparkles size={14} /></span><div><strong>Plan suggestion</strong><small>{action.source} → {action.destination}</small></div><span className="muted">Pending</span></div>) : <Empty icon={Clock3} title="Nothing here yet" text="Your completed organization activity will appear here." />}</div><AiCard health={health} /></div></div>
}

function Stat({ icon: Icon, label, value, note }: { icon: typeof FileText; label: string; value: string; note: string }) { return <div className="stat-card"><div className="stat-icon"><Icon size={17} /></div><span>{label}</span><strong>{value}</strong><small>{note}</small></div> }
function AiCard({ health }: { health: Health | null }) { return <div className="card ai-card"><div className={`ai-badge ${health ? 'online' : ''}`}><ShieldCheck size={20} /></div><div className="eyebrow">LOCAL AI STATUS</div><h3>{health ? 'Your AI is ready.' : 'Connect your local AI'}</h3><p>{health ? 'Inference stays on this machine. Your files are never sent to a third-party AI service.' : 'Start the FastAPI backend to enable local scanning and private suggestions.'}</p><div className="ai-foot"><span className={`status-dot ${health ? 'green' : ''}`} />{health ? health.model ?? 'Backend reachable' : `Waiting at ${baseUrl}`}</div></div> }

function Organize({ actions, selected, setSelected, query, setQuery, category, setCategory, loading, onPlan, onApply }: { actions: PlanAction[]; selected: Set<number>; setSelected: (value: Set<number>) => void; query: string; setQuery: (value: string) => void; category: string; setCategory: (value: string) => void; loading: string | null; onPlan: () => void; onApply: () => void }) {
  const categories = ['All', ...new Set(actions.map((action) => action.category))]
  const visible = actions.map((action, index) => ({ action, index })).filter(({ action }) => (category === 'All' || action.category === category) && `${action.source} ${action.destination} ${action.reason}`.toLowerCase().includes(query.toLowerCase()))
  const toggle = (index: number) => { const next = new Set(selected); if (next.has(index)) next.delete(index); else next.add(index); setSelected(next) }
  return <div className="page"><PageHeader eyebrow="ORGANIZATION PLAN" title="Review suggestions." description="Nothing moves until you approve it." action={<button className="secondary-button" onClick={onPlan} disabled={loading === 'plan'}><RefreshCw size={16} className={loading === 'plan' ? 'spin' : ''} /> Refresh plan</button>} /><div className="toolbar"><div className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search suggestions..." /></div><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category">{categories.map((item) => <option key={item}>{item}</option>)}</select>{actions.length > 0 && <button className="select-button" onClick={() => setSelected(selected.size === actions.length ? new Set() : new Set(actions.map((_, index) => index)))}>{selected.size === actions.length ? 'Deselect all' : 'Select all'}</button>}</div>{actions.length === 0 ? <div className="empty-panel"><Sparkles size={28} /><h2>No suggestions to review</h2><p>Scan your folder, then ask the local AI to create an organization plan.</p><button className="primary-button" onClick={onPlan} disabled={loading === 'plan'}><Sparkles size={17} /> Generate a plan</button></div> : <div className="plan-list">{visible.map(({ action, index }) => <div className={`plan-row ${selected.has(index) ? 'selected' : ''}`} key={`${action.source}-${index}`}><button className={`checkbox ${selected.has(index) ? 'checked' : ''}`} onClick={() => toggle(index)} aria-label={`${selected.has(index) ? 'Deselect' : 'Select'} ${action.source}`}>{selected.has(index) && <Check size={14} />}</button><div className="plan-files"><div><span className="file-path">{action.source}</span><ArrowRight size={15} /><span className="file-path destination">{action.destination}</span></div><small>{action.reason}</small></div><span className="category-badge">{action.category}</span></div>)}<div className="plan-footer"><span>{selected.size} of {actions.length} selected</span><button className="primary-button" disabled={!selected.size || loading === 'apply'} onClick={onApply}><Check size={16} /> Approve and organize</button></div></div>}</div>
}

function Explorer({ files, query, setQuery, loading, onScan }: { files: FileRecord[]; query: string; setQuery: (value: string) => void; loading: string | null; onScan: () => void }) {
  const visible = files.filter((file) => `${file.name} ${file.relative_path} ${file.extension}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="page"><PageHeader eyebrow="FILE INVENTORY" title="Your files." description="A private view of the folder managed by SlothDesk." action={<button className="secondary-button" onClick={onScan} disabled={loading === 'scan'}><RefreshCw size={16} className={loading === 'scan' ? 'spin' : ''} /> Refresh</button>} /><div className="toolbar"><div className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search files..." /></div><span className="result-count">{files.length ? `${visible.length} files` : 'No inventory loaded'}</span></div>{files.length === 0 ? <div className="empty-panel"><FolderOpen size={28} /><h2>Your folder is waiting</h2><p>Scan the configured local directory to see its files here.</p><button className="primary-button" onClick={onScan} disabled={loading === 'scan'}><FolderOpen size={17} /> Scan folder</button></div> : <div className="table-card"><div className="table-head"><span>Name</span><span>Type</span><span>Size</span><span>Path</span></div>{visible.map((file) => { const Icon = fileIcon(file.extension); return <div className="file-row" key={file.relative_path}><div className="file-name"><span className="file-type-icon"><Icon size={16} /></span><strong>{file.name}</strong></div><span>{file.extension || '—'}</span><span>{formatBytes(file.size_bytes)}</span><span className="path-cell">{file.relative_path}</span></div> })}</div>}</div>
}

function History({ result }: { result: ApplyResult | null }) { return <div className="page"><PageHeader eyebrow="ACTIVITY HISTORY" title="What changed." description="A transparent record of work completed in this session." />{result ? <div className="card history-card"><div className="history-summary"><CheckCircle2 size={22} /><div><strong>Organization completed</strong><span>{result.moved.length} moved · {result.skipped.length} skipped</span></div></div>{result.moved.map((path) => <div className="history-row" key={path}><CheckCircle2 size={16} /><span>{path}</span><b>Moved</b></div>)}{result.skipped.map((path) => <div className="history-row skipped" key={path}><XCircle size={16} /><span>{path}</span><b>Skipped</b></div>)}</div> : <div className="empty-panel"><Clock3 size={28} /><h2>No activity recorded</h2><p>History is available for the current session after you apply an approved plan.</p></div>}</div> }

function SettingsPage({ health, loading, onRefresh }: { health: Health | null; loading: string | null; onRefresh: () => Promise<void> }) { return <div className="page"><PageHeader eyebrow="PREFERENCES" title="Settings." description="Understand how SlothDesk connects to your machine." /><div className="settings-grid"><div className="card settings-card"><div className="settings-title"><Settings size={18} /><h3>Connections</h3></div><SettingRow label="Backend API" value={health ? 'Connected' : 'Offline'} good={Boolean(health)} /><SettingRow label="Local AI model" value={health?.model ?? 'Not reported'} good={Boolean(health?.model)} /><SettingRow label="Root directory" value={health?.root_directory ?? 'Not reported by backend'} /><button className="secondary-button" onClick={() => void onRefresh()} disabled={loading === 'health'}><RefreshCw size={16} className={loading === 'health' ? 'spin' : ''} /> Refresh status</button></div><div className="card settings-card"><div className="settings-title"><ShieldCheck size={18} /><h3>Privacy & safety</h3></div><p className="settings-copy">SlothDesk is local-first. The browser only sends approved file actions to your local FastAPI backend, and the backend controls all filesystem access.</p><p className="settings-copy muted">No authentication, cloud AI, or unrestricted browser filesystem access is used.</p></div></div></div> }
function SettingRow({ label, value, good }: { label: string; value: string; good?: boolean }) { return <div className="setting-row"><span>{label}</span><strong className={good ? 'good-text' : ''}>{good && <span className="status-dot green" />}{value}</strong></div> }
function Empty({ icon: Icon, title, text }: { icon: typeof Clock3; title: string; text: string }) { return <div className="mini-empty"><Icon size={19} /><strong>{title}</strong><span>{text}</span></div> }
function ConfirmDialog({ actions, loading, onCancel, onConfirm }: { actions: PlanAction[]; loading: boolean; onCancel: () => void; onConfirm: () => void }) { return <div className="modal-backdrop" role="presentation"><div className="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><button className="dialog-close" onClick={onCancel} aria-label="Close dialog"><X size={18} /></button><div className="dialog-icon"><ShieldCheck size={22} /></div><h2 id="confirm-title">Organize {actions.length} file{actions.length === 1 ? '' : 's'}?</h2><p>These approved changes will affect files in the configured local directory. Review the destinations before continuing.</p><div className="dialog-list">{actions.slice(0, 4).map((action) => <div key={action.source}><span>{action.source}</span><ArrowRight size={13} /><strong>{action.destination}</strong></div>)}{actions.length > 4 && <small>+ {actions.length - 4} more selected</small>}</div><div className="dialog-note"><CircleAlert size={15} /> Undo is not available because the backend does not expose a rollback operation.</div><div className="dialog-actions"><button className="secondary-button" onClick={onCancel}>Keep reviewing</button><button className="primary-button" onClick={onConfirm} disabled={loading}>{loading ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />} Confirm and organize</button></div></div></div> }

export default App
