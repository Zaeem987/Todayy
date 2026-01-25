import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { useTranslation } from 'react-i18next'

import { db } from './lib/db'
import type { Task } from './lib/types'
import { dayKeyFromDate, humanDayLabel } from './lib/date'
import { parseArabicQuickInput } from './lib/parseAr'
import { buildSharePayload, payloadToLink, tryDecodePayload } from './lib/share'
import { SUPPORTED_LANGS, detectInitialLang, isRtl, setAppLanguage, type SupportedLang } from './i18n'
import { buildIcsEvent, downloadTextFile } from './lib/ics'
import {
  createCalendarEvent,
  getSavedCalendarToken,
  getSavedUser,
  requestCalendarAccessToken,
  signInWithGoogle,
  signOutGoogle,
  type GoogleUser,
} from './lib/google'

function uid(): string {
  return crypto.randomUUID()
}

async function loadTasksFor(dayKey: string): Promise<Task[]> {
  const rows = await db.tasks.where('dayKey').equals(dayKey).sortBy('createdAt')
  return rows
}

function sortForDisplay(a: Task, b: Task): number {
  // pinned first
  if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1
  // incomplete first
  if (!!a.completedAt !== !!b.completedAt) return a.completedAt ? 1 : -1
  // tasks with dueAt first
  if (!!a.dueAt !== !!b.dueAt) return a.dueAt ? -1 : 1
  if (a.dueAt && b.dueAt && a.dueAt !== b.dueAt) return a.dueAt - b.dueAt
  return a.createdAt - b.createdAt
}

function taskStartEnd(t: Task): { start: Date; end: Date } {
  if (t.dueAt) {
    const start = new Date(t.dueAt)
    const end = new Date(t.dueAt + 30 * 60 * 1000)
    return { start, end }
  }
  // default 09:00 local
  const [y, m, d] = t.dayKey.split('-').map(Number)
  const start = new Date(y, m - 1, d, 9, 0, 0)
  const end = new Date(y, m - 1, d, 9, 30, 0)
  return { start, end }
}

function toGCalTemplateUrl(summary: string, start: Date, end: Date): string {
  const fmt = (x: Date) => x.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')
  const dates = `${fmt(start)}/${fmt(end)}`
  const u = new URL('https://calendar.google.com/calendar/render')
  u.searchParams.set('action', 'TEMPLATE')
  u.searchParams.set('text', summary)
  u.searchParams.set('dates', dates)
  return u.toString()
}

export default function App() {
  const { t } = useTranslation()
  const todayKey = useMemo(() => dayKeyFromDate(new Date()), [])

  type Theme = 'calm' | 'minimal' | 'warm'
  const [theme, setTheme] = useState<Theme>(() => {
    const v = localStorage.getItem('theme') as Theme | null
    return v === 'minimal' || v === 'warm' || v === 'calm' ? v : 'calm'
  })

  const [lang, setLang] = useState<SupportedLang>(detectInitialLang())
  const rtl = isRtl(lang)

  const [selectedDayKey, setSelectedDayKey] = useState<string>(todayKey)
  const [tasks, setTasks] = useState<Task[]>([])
  const [input, setInput] = useState('')

  const [shareOpen, setShareOpen] = useState(false)
  const [shareLink, setShareLink] = useState<string>('')
  const [status, setStatus] = useState<string>('')

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [user, setUser] = useState<GoogleUser | null>(() => getSavedUser())
  const [calToken, setCalToken] = useState<string | null>(() => getSavedCalendarToken())
  const [syncing, setSyncing] = useState(false)

  // initial import from URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const encoded = params.get('import')
    if (!encoded) return
    const payload = tryDecodePayload(encoded)
    if (!payload) return

    ;(async () => {
      const ok = confirm(t('importConfirm', { dayKey: payload.dayKey }))
      if (!ok) return

      const now = Date.now()
      const newTasks: Task[] = payload.tasks.map((x, idx) => ({
        id: uid(),
        text: x.text,
        dayKey: payload.dayKey,
        dueAt: x.dueAt ?? null,
        createdAt: now + idx,
        completedAt: x.completedAt ?? null,
        pinned: false,
        calendarEventId: null,
      }))

      await db.tasks.bulkPut(newTasks)
      setStatus(t('statusImportOk'))
      setSelectedDayKey(payload.dayKey)

      const u = new URL(window.location.href)
      u.searchParams.delete('import')
      window.history.replaceState({}, '', u.toString())
    })().catch(() => {
      setStatus(t('statusImportFailed'))
    })
  }, [t])

  useEffect(() => {
    ;(async () => {
      const rows = await loadTasksFor(selectedDayKey)
      setTasks(rows)
    })()
  }, [selectedDayKey])

  useEffect(() => {
    setAppLanguage(lang)
    document.documentElement.dir = rtl ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang, rtl])

  useEffect(() => {
    document.documentElement.dataset.theme = theme === 'calm' ? '' : theme
    // store
    localStorage.setItem('theme', theme)
  }, [theme])

  const shown = useMemo(() => [...tasks].sort(sortForDisplay), [tasks])

  async function refresh() {
    const rows = await loadTasksFor(selectedDayKey)
    setTasks(rows)
  }

  async function addTask() {
    const parsed = parseArabicQuickInput(input)
    const text = parsed.text.trim()
    if (!text) return

    const task: Task = {
      id: uid(),
      text,
      dayKey: parsed.dayKey,
      dueAt: parsed.dueAt,
      createdAt: Date.now(),
      completedAt: null,
      pinned: false,
      calendarEventId: null,
    }
    await db.tasks.put(task)
    setInput('')
    setStatus('')

    if (parsed.dayKey !== selectedDayKey) setSelectedDayKey(parsed.dayKey)
    else await refresh()
  }

  async function toggleDone(task: Task) {
    await db.tasks.update(task.id, { completedAt: task.completedAt ? null : Date.now() })
    await refresh()
  }

  async function togglePin(task: Task) {
    await db.tasks.update(task.id, { pinned: !task.pinned })
    await refresh()
  }

  async function removeTask(task: Task) {
    await db.tasks.delete(task.id)
    await refresh()
  }

  async function openShare() {
    const all = await db.tasks.where('dayKey').equals(selectedDayKey).toArray()
    const payload = buildSharePayload(selectedDayKey as any, all)
    const link = payloadToLink(window.location.origin + window.location.pathname, payload)
    setShareLink(link)
    setShareOpen(true)
  }

  async function copyShareLink() {
    try {
      await navigator.clipboard.writeText(shareLink)
      setStatus(t('copied'))
    } catch {
      setStatus(t('copyFailed'))
    }
  }

  const dayChips = useMemo(() => {
    const base = new Date()
    const keys = [0, 1, 2, 3].map((d) => {
      const x = new Date(base)
      x.setDate(base.getDate() + d)
      return dayKeyFromDate(x)
    })
    return keys
  }, [])

  async function handleSignIn() {
    try {
      const u = await signInWithGoogle()
      setUser(u)
      setStatus('')
    } catch {
      setStatus('Sign-in failed')
    }
  }

  async function handleConnectCalendar() {
    try {
      const token = await requestCalendarAccessToken()
      setCalToken(token)
      setStatus('')
    } catch {
      setStatus('Calendar connect failed')
    }
  }

  async function syncPinnedToGoogleCalendar() {
    if (!user) {
      setStatus(t('needsSignIn'))
      return
    }
    if (!calToken) {
      setStatus(t('needsCalendar'))
      return
    }

    setSyncing(true)
    setStatus('')

    try {
      const pinned = await db.tasks.where('pinned').equals(1 as any).and((x) => !x.completedAt).toArray()
      for (const task of pinned) {
        if (task.calendarEventId) continue
        const { start, end } = taskStartEnd(task)
        const ev = await createCalendarEvent({ token: calToken, summary: task.text, start, end })
        await db.tasks.update(task.id, { calendarEventId: ev.id })
      }
      await refresh()
      setStatus('OK')
    } catch {
      setStatus('Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  function downloadTaskIcs(task: Task) {
    const { start, end } = taskStartEnd(task)
    const ics = buildIcsEvent({ uid: task.id, summary: task.text, start, end })
    downloadTextFile(`task-${task.id}.ics`, ics, 'text/calendar')
  }

  function openTaskGCal(task: Task) {
    const { start, end } = taskStartEnd(task)
    window.open(toGCalTemplateUrl(task.text, start, end), '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="app" dir={rtl ? 'rtl' : 'ltr'}>
      <header className="top">
        <div className="brand">{t('appName')}</div>
        <div className="actions">
          <button className="btn" onClick={() => setSelectedDayKey(todayKey)}>
            {t('today')}
          </button>
          <button className="btn" onClick={openShare}>
            {t('share')}
          </button>
          <button className="btn" onClick={() => setSettingsOpen(true)}>
            {t('settings')}
          </button>
        </div>
      </header>

      <div className="daybar">
        {dayChips.map((k) => (
          <button
            key={k}
            className={k === selectedDayKey ? 'chip chipActive' : 'chip'}
            onClick={() => setSelectedDayKey(k)}
          >
            {humanDayLabel(k)}
          </button>
        ))}
      </div>

      <div className="composer">
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') addTask().catch(() => setStatus('Error'))
          }}
          placeholder={t('placeholder')}
        />
        <button className="primary" onClick={() => addTask().catch(() => setStatus('Error'))}>
          {t('add')}
        </button>
      </div>

      {status ? <div className="status">{status}</div> : null}

      <main className="list">
        {shown.length === 0 ? (
          <div className="empty">{t('empty')}</div>
        ) : (
          shown.map((task) => {
            const due = task.dueAt ? new Date(task.dueAt).toLocaleTimeString(lang === 'ar' ? 'ar' : undefined, { hour: '2-digit', minute: '2-digit' }) : null
            return (
              <div key={task.id} className={task.completedAt ? 'task taskDone' : 'task'}>
                <button className={task.completedAt ? 'check checkDone' : 'check'} onClick={() => toggleDone(task)}>
                  ✓
                </button>

                <div className="taskBody">
                  <div className="taskRow">
                    <div className="taskText">{task.text}</div>
                    <button className={task.pinned ? 'pin pinActive' : 'pin'} onClick={() => togglePin(task)} title={task.pinned ? t('unpin') : t('pin')}>
                      ★
                    </button>
                  </div>
                  {due ? <div className="meta">{due}</div> : null}
                  <div className="miniActions">
                    <button className="mini" onClick={() => openTaskGCal(task)}>
                      {t('addToGoogleCalendar')}
                    </button>
                    <button className="mini" onClick={() => downloadTaskIcs(task)}>
                      {t('downloadIcs')}
                    </button>
                  </div>
                </div>

                <button className="delete" onClick={() => removeTask(task)} aria-label="delete">
                  ×
                </button>
              </div>
            )
          })
        )}
      </main>

      {shareOpen ? (
        <div className="modalBack" onClick={() => setShareOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modalTitle">{t('shareTitle', { dayLabel: humanDayLabel(selectedDayKey as any) })}</div>
            <div className="modalDesc">{t('shareDesc')}</div>
            <textarea className="textarea" value={shareLink} readOnly />
            <div className="modalActions">
              <button className="primary" onClick={copyShareLink}>
                {t('copyLink')}
              </button>
              <button className="btn" onClick={() => setShareOpen(false)}>
                {t('close')}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {settingsOpen ? (
        <div className="modalBack" onClick={() => setSettingsOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modalTitle">{t('settings')}</div>

            <div className="row">
              <div className="label">{t('language')}</div>
              <select
                className="select"
                value={lang}
                onChange={(e) => setLang(e.target.value as SupportedLang)}
              >
                {SUPPORTED_LANGS.map((l) => (
                  <option key={l} value={l}>
                    {l.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="row">
              <div className="label">{t('theme')}</div>
              <select className="select" value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
                <option value="calm">{t('themeCalm')}</option>
                <option value="minimal">{t('themeMinimal')}</option>
                <option value="warm">{t('themeWarm')}</option>
              </select>
            </div>

            <div className="row">
              <div className="label">Google</div>
              <div className="right">
                {user ? (
                  <div className="inline">
                    <span className="small">{t('connectedAs')} {user.email || user.name}</span>
                    <button
                      className="btn"
                      onClick={() => {
                        signOutGoogle()
                        setUser(null)
                        setCalToken(null)
                      }}
                    >
                      {t('signOut')}
                    </button>
                  </div>
                ) : (
                  <button className="primary" onClick={() => handleSignIn().catch(() => {})}>
                    {t('signIn')}
                  </button>
                )}
              </div>
            </div>

            <div className="row">
              <div className="label">Calendar</div>
              <div className="right">
                <button className="btn" onClick={() => handleConnectCalendar().catch(() => {})} disabled={!user}>
                  {t('connectGoogleCalendar')}
                </button>
              </div>
            </div>

            <div className="row">
              <div className="label">{t('syncPinned')}</div>
              <div className="right">
                <button className="primary" onClick={() => syncPinnedToGoogleCalendar().catch(() => {})} disabled={!user || !calToken || syncing}>
                  {syncing ? '...' : t('syncPinned')}
                </button>
              </div>
            </div>

            <div className="modalActions">
              <button className="btn" onClick={() => setSettingsOpen(false)}>
                {t('close')}
              </button>
            </div>

            {!user ? <div className="hint">{t('needsSignIn')}</div> : null}
          </div>
        </div>
      ) : null}

      <footer className="footer">
        <span>{t('footer')}</span>
      </footer>
    </div>
  )
}
