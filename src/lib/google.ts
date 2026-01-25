export type GoogleUser = {
  name: string
  email: string
  picture?: string
}

const USER_KEY = 'tt_google_user'
const CAL_TOKEN_KEY = 'tt_google_cal_token'
const PROFILE_TOKEN_KEY = 'tt_google_profile_token'
const SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${SCRIPT_SRC}"]`)) return resolve()
    const s = document.createElement('script')
    s.src = SCRIPT_SRC
    s.async = true
    s.defer = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('Failed to load Google script'))
    document.head.appendChild(s)
  })
}

function getClientId(): string | null {
  return (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID || null
}

export function getSavedUser(): GoogleUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as GoogleUser) : null
  } catch {
    return null
  }
}

export function signOutGoogle() {
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(CAL_TOKEN_KEY)
  localStorage.removeItem(PROFILE_TOKEN_KEY)
}

async function fetchUserInfo(token: string): Promise<GoogleUser> {
  const resp = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!resp.ok) throw new Error('Failed to fetch user profile')
  const json = (await resp.json()) as any
  return {
    name: json.name || 'User',
    email: json.email || '',
    picture: json.picture,
  }
}

// Optional sign-in to enable sync features.
export async function signInWithGoogle(): Promise<GoogleUser> {
  const clientId = getClientId()
  if (!clientId) throw new Error('Missing VITE_GOOGLE_CLIENT_ID')
  await loadScript()

  const g = (window as any).google
  if (!g?.accounts?.oauth2) throw new Error('Google oauth2 not available')

  const token = await new Promise<string>((resolve, reject) => {
    const tokenClient = g.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: 'openid email profile https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
      callback: (resp: any) => {
        const t = resp?.access_token
        if (!t) return reject(new Error('No access token'))
        resolve(t)
      },
    })
    tokenClient.requestAccessToken({ prompt: 'consent' })
  })

  localStorage.setItem(PROFILE_TOKEN_KEY, token)
  const user = await fetchUserInfo(token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  return user
}

export function getSavedCalendarToken(): string | null {
  return localStorage.getItem(CAL_TOKEN_KEY)
}

export async function requestCalendarAccessToken(): Promise<string> {
  const clientId = getClientId()
  if (!clientId) throw new Error('Missing VITE_GOOGLE_CLIENT_ID')
  await loadScript()

  const g = (window as any).google
  if (!g?.accounts?.oauth2) throw new Error('Google oauth2 not available')

  const token = await new Promise<string>((resolve, reject) => {
    const tokenClient = g.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: 'https://www.googleapis.com/auth/calendar.events',
      callback: (resp: any) => {
        const t = resp?.access_token
        if (!t) return reject(new Error('No access token'))
        resolve(t)
      },
    })
    tokenClient.requestAccessToken({ prompt: 'consent' })
  })

  localStorage.setItem(CAL_TOKEN_KEY, token)
  return token
}

export async function createCalendarEvent(params: {
  token: string
  summary: string
  start: Date
  end: Date
}): Promise<{ id: string; htmlLink?: string }> {
  const body = {
    summary: params.summary,
    start: { dateTime: params.start.toISOString() },
    end: { dateTime: params.end.toISOString() },
  }

  const resp = await fetch('https://www.googleapis.com/calendar/v3/calendars/primary/events', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${params.token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!resp.ok) {
    const t = await resp.text().catch(() => '')
    throw new Error(`Calendar API error (${resp.status}): ${t}`)
  }

  const json = (await resp.json()) as any
  return { id: json.id, htmlLink: json.htmlLink }
}
