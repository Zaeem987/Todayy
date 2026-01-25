import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from 'lz-string'
import type { SharePayload, Task } from './types'
import type { DayKey } from './date'

export function buildSharePayload(dayKey: DayKey, tasks: Task[]): SharePayload {
  return {
    v: 1,
    dayKey,
    exportedAt: Date.now(),
    tasks: tasks
      .filter((t) => t.dayKey === dayKey)
      .map((t) => ({ text: t.text, dueAt: t.dueAt, completedAt: t.completedAt })),
  }
}

export function payloadToLink(baseUrl: string, payload: SharePayload): string {
  const json = JSON.stringify(payload)
  const data = compressToEncodedURIComponent(json)
  const u = new URL(baseUrl)
  u.searchParams.set('import', data)
  return u.toString()
}

export function tryDecodePayload(encoded: string): SharePayload | null {
  try {
    const json = decompressFromEncodedURIComponent(encoded)
    if (!json) return null
    const obj = JSON.parse(json) as SharePayload
    if (!obj || obj.v !== 1 || !obj.dayKey || !Array.isArray(obj.tasks)) return null
    return obj
  } catch {
    return null
  }
}
