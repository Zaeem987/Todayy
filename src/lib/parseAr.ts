import { addDays, dayKeyFromDate, startOfDay } from './date'

export type ParsedInput = {
  text: string
  dayKey: string
  dueAt: number | null
}

function normalize(s: string): string {
  return s
    .trim()
    .replace(/[\u064B-\u0652]/g, '') // remove harakat
    .replace(/[إأآ]/g, 'ا')
    .replace(/ة/g, 'ه')
    .replace(/\s+/g, ' ')
}

function parseTime(token: string): { h: number; m: number } | null {
  // 10 or 10:30
  const m = token.match(/^([0-1]?\d|2[0-3])(?::([0-5]\d))?$/)
  if (!m) return null
  const h = Number(m[1])
  const mm = m[2] ? Number(m[2]) : 0
  return { h, m: mm }
}

export function parseArabicQuickInput(raw: string, now = new Date()): ParsedInput {
  const original = raw.trim()
  if (!original) {
    return { text: '', dayKey: dayKeyFromDate(now), dueAt: null }
  }

  const s = normalize(original)
  const tokens = s.split(' ')

  let dayOffset = 0
  let time: { h: number; m: number } | null = null
  let meridiem: 'am' | 'pm' | null = null

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i]

    if (t === 'اليوم') dayOffset = 0
    if (t === 'بكرا' || t === 'غدا') dayOffset = 1
    if (t === 'بعد' && tokens[i + 1] === 'بكرا') dayOffset = 2

    if (t === 'صباح' || t === 'صباحا') meridiem = 'am'
    if (t === 'مساء' || t === 'مساءا' || t === 'ليل' || t === 'ليلا') meridiem = 'pm'

    const tm = parseTime(t)
    if (tm) time = tm

    // patterns: الساعة 5
    if (t === 'الساعة' && tokens[i + 1]) {
      const tm2 = parseTime(tokens[i + 1])
      if (tm2) time = tm2
    }
  }

  const date = addDays(startOfDay(now), dayOffset)
  let dueAt: number | null = null

  if (time) {
    let h = time.h
    if (meridiem === 'pm' && h < 12) h += 12
    if (meridiem === 'am' && h === 12) h = 0
    const due = new Date(date.getFullYear(), date.getMonth(), date.getDate(), h, time.m, 0, 0)
    dueAt = due.getTime()
  }

  // remove date/time keywords from text (simple heuristic)
  const cleaned = tokens
    .filter((t, idx) => {
      if (t === 'اليوم' || t === 'بكرا' || t === 'غدا' || t === 'صباح' || t === 'صباحا' || t === 'مساء' || t === 'مساءا' || t === 'ليل' || t === 'ليلا') return false
      if (t === 'بعد' && tokens[idx + 1] === 'بكرا') return false
      if (tokens[idx - 1] === 'بعد' && t === 'بكرا') return false
      if (t === 'الساعة') return false
      if (parseTime(t)) return false
      if (tokens[idx - 1] === 'الساعة' && parseTime(t)) return false
      return true
    })
    .join(' ')
    .trim()

  return {
    text: cleaned || original,
    dayKey: dayKeyFromDate(date),
    dueAt,
  }
}
