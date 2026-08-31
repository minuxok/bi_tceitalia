import type { ElencoDomande, Health, Risposta } from './types'

// In sviluppo: '/api' -> proxy Vite -> http://127.0.0.1:8000
// In produzione: passare VITE_API_BASE al build (es. '/bi/api' o URL assoluto).
// Ogni funzione accetta un `base` esplicito: la demo con più verticali passa
// l'apiBase del verticale selezionato (vedi verticals.ts).
const DEFAULT_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || '/api'

const norm = (base?: string) => base?.replace(/\/$/, '') || DEFAULT_BASE

async function json<T>(res: Response): Promise<T> {
  const testo = await res.text()
  let dato: unknown
  try {
    dato = testo ? JSON.parse(testo) : {}
  } catch {
    throw new Error(`Risposta non valida dal server (${res.status}).`)
  }
  return dato as T
}

export async function getHealth(base?: string): Promise<Health> {
  const res = await fetch(`${norm(base)}/health`)
  if (!res.ok) throw new Error(`Servizio non raggiungibile (${res.status}).`)
  return json<Health>(res)
}

export async function getDomande(base?: string): Promise<string[]> {
  const res = await fetch(`${norm(base)}/domande`)
  if (!res.ok) throw new Error(`Impossibile caricare le domande di esempio (${res.status}).`)
  const dato = await json<ElencoDomande>(res)
  return dato.domande ?? []
}

/**
 * Invia una domanda. Il backend risponde SEMPRE con un oggetto tipizzato
 * (anche gli errori applicativi hanno `tipo: 'errore'`), quindi non lanciamo
 * su status 4xx/5xx: normalizziamo tutto in una `Risposta`.
 */
export async function chiedi(
  domanda: string,
  base?: string,
  signal?: AbortSignal,
): Promise<Risposta> {
  let res: Response
  try {
    res = await fetch(`${norm(base)}/chiedi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domanda }),
      signal,
    })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    return { tipo: 'errore', errore: 'Connessione al servizio non riuscita.' }
  }

  const dato = await json<Partial<Risposta> & { detail?: unknown }>(res)

  if (dato && typeof dato === 'object' && 'tipo' in dato && dato.tipo) {
    return dato as Risposta
  }
  // fallback: FastAPI validation error o forma inattesa
  const msg =
    typeof dato?.detail === 'string'
      ? dato.detail
      : `Errore del servizio (${res.status}).`
  return { tipo: 'errore', errore: msg }
}
