import Dexie, { type Table } from 'dexie'
import type { Task } from './types'

class AppDB extends Dexie {
  tasks!: Table<Task, string>

  constructor() {
    super('today_tasks_db')

    this.version(1).stores({
      tasks: 'id, dayKey, createdAt, completedAt',
    })

    this.version(2)
      .stores({
        tasks: 'id, dayKey, createdAt, completedAt, pinned',
      })
      .upgrade(async (tx) => {
        const table = tx.table('tasks')
        await table.toCollection().modify((t: any) => {
          if (typeof t.pinned !== 'boolean') t.pinned = false
          if (typeof t.calendarEventId === 'undefined') t.calendarEventId = null
        })
      })
  }
}

export const db = new AppDB()
