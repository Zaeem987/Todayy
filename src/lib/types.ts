export type { DayKey } from './date'

export type Task = {
  id: string
  text: string
  dayKey: import('./date').DayKey
  dueAt: number | null
  createdAt: number
  completedAt: number | null
  pinned: boolean
  calendarEventId: string | null
}

/**
 * Share payload format used by src/lib/share.ts
 */
export type SharePayload = {
  v: 1
  exportedAt: number
  dayKey: import('./date').DayKey
  tasks: Array<{
    text: string
    dueAt: number | null
    completedAt: number | null
  }>
}
