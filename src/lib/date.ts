export type DayKey = `${number}-${string}-${string}`

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

export function dayKeyFromDate(d: Date): DayKey {
  const y = d.getFullYear()
  const m = pad2(d.getMonth() + 1)
  const day = pad2(d.getDate())
  return `${y}-${m}-${day}` as DayKey
}

export function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0)
}

export function addDays(d: Date, days: number): Date {
  const x = new Date(d)
  x.setDate(x.getDate() + days)
  return x
}

export function formatTimeHM(d: Date): string {
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function humanDayLabel(dayKey: DayKey): string {
  const [y, m, d] = dayKey.split('-').map((x) => Number(x))
  const dt = new Date(y, (m ?? 1) - 1, d ?? 1)
  const today = new Date()
  if (isSameDay(dt, today)) return 'اليوم'
  if (isSameDay(dt, addDays(today, 1))) return 'بكرا'
  const weekday = dt.toLocaleDateString('ar', { weekday: 'short' })
  return `${weekday} ${d}/${m}`
}
