import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import ar from './locales/ar.json'
import es from './locales/es.json'
import hi from './locales/hi.json'
import de from './locales/de.json'

export const SUPPORTED_LANGS = ['en', 'ar', 'es', 'hi', 'de'] as const
export type SupportedLang = (typeof SUPPORTED_LANGS)[number]

const STORAGE_KEY = 'tt_lang'

function isSupported(lang: string): lang is SupportedLang {
  return (SUPPORTED_LANGS as readonly string[]).includes(lang)
}

export function detectInitialLang(): SupportedLang {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && isSupported(saved)) return saved
  const nav = (navigator.language || 'en').split('-')[0]
  return isSupported(nav) ? nav : 'en'
}

export function setAppLanguage(lang: SupportedLang) {
  i18n.changeLanguage(lang)
  localStorage.setItem(STORAGE_KEY, lang)
}

export function isRtl(lang: SupportedLang): boolean {
  return lang === 'ar'
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ar: { translation: ar },
      es: { translation: es },
      hi: { translation: hi },
      de: { translation: de },
    },
    lng: typeof window === 'undefined' ? 'en' : detectInitialLang(),
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })
  .catch(() => {
    // ignore init errors
  })

export default i18n
