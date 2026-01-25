import type { DayKey } from './date'

export type Task = {
  id: string
  text: string
  dayKey: DayKey
  dueAt: number | null
  createdAt: number
  completedAt: number | null
  pinned: boolean
  calendarEventId?: string | null
}

export type SharePayload = {
  v: 1
  dayKey: DayKey
  exportedAt: number
  tasks: Array<Pick<Task, 'text' | 'dueAt' | 'completedAt'>>
}
