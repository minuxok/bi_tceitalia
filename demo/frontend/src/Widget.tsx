import { useEffect, useMemo, useRef, useState } from 'react'
import { chiedi, getDomande, getHealth } from './api'
import ResultView from './ResultView'
import type { Health, Risposta } from './types'
import './widget.css'

export interface WidgetProps {
  titolo?: string
  sottotitolo?: string
  ctaHref?: string
  ctaLabel?: string
  /** massimo di esempi mostrati come chip */
  maxEsempi?: number
}

interface Turno {
  id: number
  domanda: string
  stato: 'loading' | 'done'
  risposta?: Risposta
}

let contatore = 0

export default function Widget({
  titolo = 'Chiedi ai tuoi dati',
  sottotitolo = 'Demo su un’azienda fittizia ("Acme Srl"). Domande in italiano, risposte in pochi secondi.',
  ctaHref = '#contatti',
  ctaLabel = 'Vuoi la stessa cosa sui tuoi dati? Parliamone',
  maxEsempi = 6,
}: WidgetProps) {
  const [esempi, setEsempi] = useState<string[]>([])
  const [salute, setSalute] = useState<Health | null>(null)
  const [bozza, setBozza] = useState('')
  const [turni, setTurni] = useState<Turno[]>([])
  const [inCorso, setInCorso] = useState(false)
  const [esempiAperti, setEsempiAperti] = useState(false)
  const ultimoTurnoRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    getDomande()
      .then((d) => setEsempi(d.slice(0, maxEsempi)))
      .catch(() => setEsempi([]))
    getHealth()
      .then(setSalute)
      .catch(() => setSalute(null))
  }, [maxEsempi])

  useEffect(() => {
    ultimoTurnoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [turni])

  async function invia(testo: string) {
    const domanda = testo.trim()
    if (!domanda || inCorso) return
    setBozza('')
    setInCorso(true)
    const id = ++contatore
    setTurni((t) => [...t, { id, domanda, stato: 'loading' }])
    let risposta: Risposta
    try {
      risposta = await chiedi(domanda)
    } catch {
      risposta = { tipo: 'errore', errore: 'Richiesta interrotta.' }
    }
    setTurni((t) => t.map((x) => (x.id === id ? { ...x, stato: 'done', risposta } : x)))
    setInCorso(false)
    inputRef.current?.focus()
  }

  const servizioKo = salute !== null && !salute.llm_configurato
  const chips = esempi.length > 0 && (
    <div className="cbi-chips">
      {esempi.map((q) => (
        <button
          key={q}
          type="button"
          className="cbi-chip"
          disabled={inCorso || servizioKo}
          onClick={() => {
            setEsempiAperti(false)
            invia(q)
          }}
        >
          {q}
        </button>
      ))}
    </div>
  )
  const dataRif = useMemo(() => {
    if (!salute?.data_riferimento) return null
    const [a, m, g] = salute.data_riferimento.split('-')
    return g && m && a ? `${g}/${m}/${a}` : salute.data_riferimento
  }, [salute])

  return (
    <div className="cbi-root" role="region" aria-label="Assistente Conversational BI">
      <header className="cbi-header">
        <div>
          <p className="cbi-title">{titolo}</p>
          <p className="cbi-subtitle">{sottotitolo}</p>
        </div>
        <span
          className="cbi-badge"
          title="Il motore accede in sola lettura a viste preparate (ai_bi_*). Nessun dato personale (email, telefono, P.IVA). Ambiente isolato per cliente."
        >
          <svg className="cbi-badge-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          sola lettura · isolato
        </span>
      </header>

      <div className="cbi-body" aria-live="polite" aria-busy={inCorso}>
        {turni.length === 0 && (
          <>
            <p className="cbi-hint">
              Prova con un esempio{dataRif ? ` (dati congelati al ${dataRif})` : ''}:
            </p>
            {chips}
          </>
        )}

        {turni.map((t, i) => (
          <div
            className="cbi-turn"
            key={t.id}
            ref={i === turni.length - 1 ? ultimoTurnoRef : undefined}
          >
            <div className="cbi-q">{t.domanda}</div>
            {t.stato === 'loading' || !t.risposta ? (
              <div className="cbi-a">
                <span className="cbi-loading">
                  <span className="cbi-spinner" aria-hidden="true" />
                  Interrogo i dati…
                </span>
              </div>
            ) : (
              <ResultView risposta={t.risposta} />
            )}
          </div>
        ))}

        {servizioKo && (
          <p className="cbi-info cbi-error">
            Il servizio non è configurato correttamente (LLM assente). Riprova più tardi.
          </p>
        )}
      </div>

      <footer className="cbi-footer">
        {turni.length > 0 && esempi.length > 0 && (
          <div className="cbi-esempi">
            <button
              type="button"
              className="cbi-esempi-toggle"
              aria-expanded={esempiAperti}
              onClick={() => setEsempiAperti((v) => !v)}
            >
              {esempiAperti ? '▾' : '▸'} Esempi di domande
            </button>
            {esempiAperti && chips}
          </div>
        )}

        <form
          className="cbi-form"
          onSubmit={(e) => {
            e.preventDefault()
            invia(bozza)
          }}
        >
          <textarea
            ref={inputRef}
            className="cbi-input"
            placeholder="Scrivi una domanda sui dati di Acme Srl…"
            value={bozza}
            rows={1}
            maxLength={500}
            disabled={inCorso || servizioKo}
            onChange={(e) => setBozza(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                invia(bozza)
              }
            }}
          />
          <button className="cbi-send" type="submit" disabled={inCorso || servizioKo || !bozza.trim()}>
            {inCorso ? '…' : 'Chiedi'}
          </button>
        </form>
        <div className="cbi-cta">
          <a href={ctaHref} target="_top" rel="noopener">
            {ctaLabel} →
          </a>
        </div>
      </footer>
    </div>
  )
}
