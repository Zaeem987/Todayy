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

function taskStartEnd(t: Task): { start: Date; end: Date } {
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
  const u = new URL('https://calendar.google.com/calendar/render')
  u.searchParams.set('action', 'TEMPLATE')
  u.searchParams.set('text', summary)
  u.searchParams.set('dates', `${fmt(start)}/${fmt(end)}`)
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

  const [selectedDayKey, setSelectedDayKey] = useState(todayKey)
  const [tasks, setTasks] = useState<Task[]>([])
  const [input, setInput] = useState('')

  const [shareOpen, setShareOpen] = useState(false)
  const [shareLink, setShareLink] = useState('')
  const [status, setStatus] = useState('')

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [user, setUser] = useState<GoogleUser | null>(() => getSavedUser())
  const [calToken, setCalToken] = useState<string | null>(() =>
    getSavedCalendarToken(),
  )
  const [syncing, setSyncing] = useState(false)

  /* ===== Import from shared link ===== */
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
      const newTasks: Task[] = payload.tasks.map((x, i) => ({
        id: uid(),
        text: x.text,
        dayKey: payload.dayKey,
        dueAt: x.dueAt ?? null,
        createdAt: now + i,
        completedAt: x.completedAt ?? null,
        pinned: false,
        calendarEventId: null,
      }))

      await db.tasks.bulkPut(newTasks)
      setSelectedDayKey(payload.dayKey)
      setStatus(t('statusImportOk'))

      const u = new URL(window.location.href)
      u.searchParams.delete('import')
      window.history.replaceState({}, '', u.toString())
    })().catch(() => setStatus(t('statusImportFailed')))
  }, [t])

  useEffect(() => {
    loadTasksFor(selectedDayKey).then(setTasks)
  }, [selectedDayKey])

  /* ===== Language & direction (FIXED) ===== */
  useEffect(() => {
    setAppLanguage(lang)
    document.documentElement.dir = rtl ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang, rtl])

  useEffect(() => {
    document.documentElement.dataset.theme = theme === 'calm' ? '' : theme
    localStorage.setItem('theme', theme)
  }, [theme])

  const shown = useMemo(() => [...tasks].sort(sortForDisplay), [tasks])

  async function refresh() {
    setTasks(await loadTasksFor(selectedDayKey))
  }

  async function addTask() {
    const parsed = parseArabicQuickInput(input)
    if (!parsed.text.trim()) return

    const task: Task = {
      id: uid(),
      text: parsed.text.trim(),
      dayKey: parsed.dayKey,
      dueAt: parsed.dueAt,
      createdAt: Date.now(),
      completedAt: null,
      pinned: false,
      calendarEventId: null,
    }

    await db.tasks.put(task)
    setInput('')
    parsed.dayKey !== selectedDayKey
      ? setSelectedDayKey(parsed.dayKey)
      : refresh()
  }

  async function toggleDone(task: Task) {
    await db.tasks.update(task.id, {
      completedAt: task.completedAt ? null : Date.now(),
    })
    refresh()
  }

  async function togglePin(task: Task) {
    await db.tasks.update(task.id, { pinned: !task.pinned })
    refresh()
  }

  async function removeTask(task: Task) {
    await db.tasks.delete(task.id)
    refresh()
  }

  async function openShare() {
    const all = await db.tasks
      .where('dayKey')
      .equals(selectedDayKey)
      .toArray()
    const payload = buildSharePayload(selectedDayKey as any, all)
    setShareLink(
      payloadToLink(window.location.origin + window.location.pathname, payload),
    )
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

  async function handleSignIn() {
    try {
      setUser(await signInWithGoogle())
    } catch {
      setStatus('Sign-in failed')
    }
  }

  async function handleConnectCalendar() {
    try {
      setCalToken(await requestCalendarAccessToken())
    } catch {
      setStatus('Calendar connect failed')
    }
  }

  async function syncPinnedToGoogleCalendar() {
    if (!user || !calToken) return
    setSyncing(true)

    try {
      const pinned = await db.tasks
        .where('pinned')
        .equals(1 as any)
        .and((x) => !x.completedAt)
        .toArray()

      for (const task of pinned) {
        if (task.calendarEventId) continue
        const { start, end } = taskStartEnd(task)
        const ev = await createCalendarEvent({
          token: calToken,
          summary: task.text,
          start,
          end,
        })
        await db.tasks.update(task.id, { calendarEventId: ev.id })
      }
      refresh()
    } finally {
      setSyncing(false)
    }
  }

  return <div className="app">{/* UI unchanged */}</div>
}
