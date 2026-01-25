import { useEffect, useMemo, useState } from 'react'
import './app.css'

export type DayKey = `${number}-${number}-${number}`

export interface Task {
  id: string
  title: string
  done: boolean
  dayKey: DayKey
}

function toDayKey(d: Date): DayKey {
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}` as DayKey
}

function addDays(base: Date, days: number): Date {
  const d = new Date(base)
  d.setDate(d.getDate() + days)
  return d
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [input, setInput] = useState('')

  const todayKey = useMemo(() => toDayKey(new Date()), [])
  const [selectedDayKey, setSelectedDayKey] = useState<DayKey>(todayKey)

  useEffect(() => {
    const raw = localStorage.getItem('tasks')
    if (raw) {
      try {
        setTasks(JSON.parse(raw))
      } catch {}
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('tasks', JSON.stringify(tasks))
  }, [tasks])

  const visibleTasks = useMemo(
    () => tasks.filter(t => t.dayKey === selectedDayKey),
    [tasks, selectedDayKey]
  )

  function addTask() {
    if (!input.trim()) return
    const newTask: Task = {
      id: crypto.randomUUID(),
      title: input.trim(),
      done: false,
      dayKey: selectedDayKey,
    }
    setTasks(prev => [...prev, newTask])
    setInput('')
  }

  function toggleTask(id: string) {
    setTasks(prev => prev.map(t => (t.id === id ? { ...t, done: !t.done } : t)))
  }

  function removeTask(id: string) {
    setTasks(prev => prev.filter(t => t.id !== id))
  }

  const dayChips = useMemo(() => {
    const base = new Date()
    const keys: DayKey[] = [0, 1, 2, 3].map(i => toDayKey(addDays(base, i)))
    return keys
  }, [])

  return (
    <div className="app">
      <header className="top">
        <h1>Today</h1>
      </header>

      <div className="daybar">
        {dayChips.map(k => (
          <button
            key={k}
            className={k === selectedDayKey ? 'chip chipActive' : 'chip'}
            onClick={() => setSelectedDayKey(k)}
          >
            {k}
          </button>
        ))}
      </div>

      <div className="controls">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Write a task…"
          onKeyDown={e => e.key === 'Enter' && addTask()}
        />
        <button onClick={addTask}>Add</button>
      </div>

      <ul className="tasks">
        {visibleTasks.length === 0 && <li className="empty">No tasks</li>}

        {visibleTasks.map(task => (
          <li key={task.id} className={`task ${task.done ? 'done' : ''}`}>
            <label>
              <input type="checkbox" checked={task.done} onChange={() => toggleTask(task.id)} />
              <span>{task.title}</span>
            </label>

            <button className="remove" onClick={() => removeTask(task.id)}>
              ✕
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
