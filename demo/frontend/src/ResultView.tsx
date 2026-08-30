import { lazy, Suspense } from 'react'
import { fmtNum } from './format'
import type { Cella, Risposta, RispostaRisultato } from './types'

// Recharts pesa ~400 kB: caricato solo quando serve davvero un grafico.
const Chart = lazy(() => import('./Chart'))

function Tabella({ ris }: { ris: RispostaRisultato }) {
  const numeriche = ris.colonne.map((_, i) =>
    ris.righe.some((r) => typeof r[i] === 'number'),
  )
  return (
    <div className="cbi-table-wrap">
      <table className="cbi-table">
        <thead>
          <tr>
            {ris.colonne.map((c, i) => (
              <th key={c} className={numeriche[i] ? 'cbi-num' : undefined}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ris.righe.map((r, ri) => (
            <tr key={ri}>
              {r.map((v: Cella, ci) => (
                <td key={ci} className={numeriche[ci] ? 'cbi-num' : undefined}>
                  {fmtNum(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Kpi({ ris }: { ris: RispostaRisultato }) {
  const riga = ris.righe[0] ?? []
  const celle = ris.colonne
    .map((c, i) => ({ c, v: riga[i] }))
    .filter((x) => typeof x.v === 'number')
  const daMostrare = celle.length ? celle : ris.colonne.map((c, i) => ({ c, v: riga[i] }))
  return (
    <div className="cbi-kpis">
      {daMostrare.map(({ c, v }) => (
        <div className="cbi-kpi" key={c}>
          <p className="cbi-kpi-label">{c}</p>
          <p className="cbi-kpi-value">{fmtNum(v)}</p>
        </div>
      ))}
    </div>
  )
}

function Visualizzazione({ ris }: { ris: RispostaRisultato }) {
  if (ris.n_righe === 0) return <p className="cbi-note">La query non ha restituito righe.</p>
  if (ris.viz.tipo === 'tabella') return <Tabella ris={ris} />
  if (ris.viz.tipo === 'kpi') return <Kpi ris={ris} />
  return (
    <Suspense fallback={<div className="cbi-chart cbi-chart-ph" aria-hidden="true" />}>
      <Chart ris={ris} />
    </Suspense>
  )
}

export default function ResultView({ risposta }: { risposta: Risposta }) {
  if (risposta.tipo === 'errore') {
    return <p className="cbi-info cbi-error">{risposta.errore}</p>
  }

  if (risposta.tipo === 'chiarimento' || risposta.tipo === 'non_disponibile') {
    const etichetta =
      risposta.tipo === 'chiarimento' ? 'Serve una precisazione' : 'Dato non disponibile'
    return (
      <div className="cbi-a">
        <p className="cbi-info">
          <strong>{etichetta}.</strong> {risposta.messaggio}
        </p>
      </div>
    )
  }

  const ris = risposta
  return (
    <div className="cbi-a">
      <p className="cbi-summary">{ris.risposta_testo}</p>

      <Visualizzazione ris={ris} />

      {ris.troncato && (
        <p className="cbi-note">Mostrate le prime {ris.n_righe} righe (risultato troncato).</p>
      )}

      <details className="cbi-details">
        <summary>Mostra la query SQL e la spiegazione</summary>
        <pre className="cbi-sql">{ris.sql}</pre>
        {ris.spiegazione && <p className="cbi-expl">{ris.spiegazione}</p>}
      </details>

      <p className="cbi-note">
        Risposta in {(ris.durata_ms / 1000).toFixed(1)}s · solo lettura · viste{' '}
        <code>ai_bi_*</code>, nessun dato personale.
      </p>
    </div>
  )
}
