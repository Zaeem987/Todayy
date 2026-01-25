import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { useTranslation } from 'react-i18next'

import { db } from './lib/db'
import type { Task } from './lib/types'
import { dayKeyFromDate, humanDayLabel } from './lib/date'
import { parseArabicQuickInput } from './lib/parseAr'
import { buildSharePayload, payloadToLink, tryDecodePayload } from './lib/share'
import {
  SUPPORTED_LANGS,
  detectInitialLang,
  isRtl,
  setAppLanguage,
  type SupportedLang,
} from './i18n'
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
  return db.tasks.where('dayKey').equals(dayKey).sortBy('createdAt')
}

function sortForDisplay(a: Task, b: Task): number {
  if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1
  if (!!a.completedAt !== !!b.completedAt) return a.completedAt ? 1 : -1
  if (!!a.dueAt !== !!b.dueAt) return a.dueAt ? -1 : 1
  if (a.dueAt && b.dueAt && a.dueAt !== b.dueAt) return a.dueAt - b.dueAt
  return a.createdAt - b.createdAt
}

function taskStartEnd(t: Task) {
  if (t.dueAt) {
    const start = new Date(t.dueAt)
    const end = new Date(t.dueAt + 30 * 60 * 1000)
    return { start, end }
  }
  const [y, m, d] = t.dayKey.split('-').map(Number)
  return {
    start: new Date(y, m - 1, d, 9, 0, 0),
    end: new Date(y, m - 1, d, 9, 30, 0),
  }
}

function toGCalTemplateUrl(summary: string, start: Date, end: Date): string {
  const fmt = (x: Date) =>
    x.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')
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
  const dir: 'ltr' | 'rtl' = rtl ? 'rtl' : 'ltr'

  const [selectedDayKey, setSelectedDayKey] = useState<string>(todayKey)
  const [tasks, setTasks] = useState<Task[]>([])
  const [input, setInput] = useState('')

  const [shareOpen, setShareOpen] = useState(false)
  const [shareLink, setShareLink] = useState('')
  const [status, setStatus] = useState('')

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [user, setUser] = useState<GoogleUser | null>(() => getSavedUser())
  const [calToken, setCalToken] = useState<string | null>(() =>
    getSavedCalendarToken()
  )
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    setAppLanguage(lang)
    document.documentElement.dir = dir
    document.documentElement.lang = lang
  }, [lang, dir])

  useEffect(() => {
    document.documentElement.dataset.theme = theme === 'calm' ? '' : theme
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    ;(async () => {
      const rows = await loadTasksFor(selectedDayKey)
      setTasks(rows)
    })()
  }, [selectedDayKey])

  const shown = useMemo(() => [...tasks].sort(sortForDisplay), [tasks])

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
    if (parsed.dayKey !== selectedDayKey) setSelectedDayKey(parsed.dayKey)
    else setTasks(await loadTasksFor(selectedDayKey))
  }

  return (
    <div className="app" dir={dir}>
      <header className="top">
        <div className="brand">{t('appName')}</div>
        <div className="actions">
          <button className="btn" onClick={() => setSelectedDayKey(todayKey)}>
            {t('today')}
          </button>
          <button className="btn" onClick={() => setShareOpen(true)}>
            {t('share')}
          </button>
          <button className="btn" onClick={() => setSettingsOpen(true)}>
            {t('settings')}
          </button>
        </div>
      </header>

      <div className="composer">
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addTask()}
          placeholder={t('placeholder')}
        />
        <button className="primary" onClick={addTask}>
          {t('add')}
        </button>
      </div>

      <main className="list">
        {shown.map((task) => (
          <div key={task.id} className="task">
            {task.text}
          </div>
        ))}
      </main>

      <footer className="footer">{t('footer')}</footer>
    </div>
  )
}
