import { useEffect, useState } from 'react'
import { getDemoSample, getDemoSchema } from './api'
import { fmtNum } from './format'
import type { DemoSample, DemoSchema, DemoVista } from './types'

/* Pannello "Dati della demo": mostra su quali viste ai_bi_* lavora il motore
   (descrizione, colonne, righe di esempio) e quali sono state usate
   nell'ultima risposta. Dati fittizi, sola lettura. */

const nf = new Intl.NumberFormat('it-IT')

function fmtMese(m: string): string {
  const [a, mm] = m.split('-')
  if (!a || !mm) return m
  const nomi = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic']
  return `${nomi[Number(mm) - 1] ?? mm} ${a}`
}

function fmtData(iso: string): string {
  const [a, m, g] = iso.split('-')
  return g && m && a ? `${g}/${m}/${a}` : iso
}

function Campione({ vista, apiBase }: { vista: string; apiBase?: string }) {
  const [dati, setDati] = useState<DemoSample | null>(null)
  const [errore, setErrore] = useState(false)

  useEffect(() => {
    let vivo = true
    getDemoSample(vista, apiBase)
      .then((d) => vivo && setDati(d))
      .catch(() => vivo && setErrore(true))
    return () => {
      vivo = false
    }
  }, [vista, apiBase])

  if (errore) return <p className="cbi-note">Righe di esempio non disponibili.</p>
  if (!dati) return <p className="cbi-note">Carico le righe di esempio…</p>
  const numeriche = dati.colonne.map((_, i) => dati.righe.some((r) => typeof r[i] === 'number'))
  return (
    <div className="cbi-table-wrap">
      <table className="cbi-table">
        <thead>
          <tr>
            {dati.colonne.map((c, i) => (
              <th key={c} className={numeriche[i] ? 'cbi-num' : undefined}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dati.righe.map((r, ri) => (
            <tr key={ri}>
              {r.map((v, ci) => (
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

function Vista({
  v,
  usata,
  aperta,
  onToggle,
  apiBase,
}: {
  v: DemoVista
  usata: boolean
  aperta: boolean
  onToggle: (open: boolean) => void
  apiBase?: string
}) {
  return (
    <details
      className={'cbi-vista' + (usata ? ' is-used' : '')}
      open={aperta}
      onToggle={(e) => onToggle((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary>
        <code className="cbi-vista-nome">{v.nome}</code>
        {usata && <span className="cbi-vista-tag">usata nell’ultima risposta</span>}
        {v.n_righe !== null && <span className="cbi-vista-n">{nf.format(v.n_righe)} righe</span>}
      </summary>
      <p className="cbi-vista-desc">{v.descrizione}</p>
      {aperta && (
        <>
          <p className="cbi-vista-lbl">Colonne ({v.colonne.length})</p>
          <ul className="cbi-cols-list">
            {v.colonne.map((c) => (
              <li key={c.nome}>
                <span>{c.nome}</span>
                <em>{c.tipo.toLowerCase()}</em>
              </li>
            ))}
          </ul>
          <p className="cbi-vista-lbl">Prime 5 righe</p>
          <Campione vista={v.nome} apiBase={apiBase} />
        </>
      )}
    </details>
  )
}

export interface DatiDemoProps {
  apiBase?: string
  /** viste da evidenziare (quelle dell'ultima risposta) */
  usate: string[]
  /** cambia a ogni richiesta esplicita "Mostra i dati usati": apre le viste `usate` */
  apriToken: number
}

export default function DatiDemo({ apiBase, usate, apriToken }: DatiDemoProps) {
  const [schema, setSchema] = useState<DemoSchema | null>(null)
  const [errore, setErrore] = useState(false)
  const [aperte, setAperte] = useState<Set<string>>(new Set())

  useEffect(() => {
    let vivo = true
    getDemoSchema(apiBase)
      .then((d) => vivo && setSchema(d))
      .catch(() => vivo && setErrore(true))
    return () => {
      vivo = false
    }
  }, [apiBase])

  useEffect(() => {
    if (apriToken > 0) setAperte(new Set(usate))
    // solo su richiesta esplicita: le nuove risposte non riaprono le viste da sole
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apriToken])

  function toggle(nome: string, open: boolean) {
    setAperte((prev) => {
      const next = new Set(prev)
      if (open) next.add(nome)
      else next.delete(nome)
      return next
    })
  }

  if (errore) {
    return <p className="cbi-note">Il catalogo dei dati non è disponibile al momento.</p>
  }
  if (!schema) return <p className="cbi-note">Carico il catalogo dei dati…</p>

  // le viste usate salgono in cima, l'ordine originale è mantenuto per il resto
  const viste = [...schema.viste].sort(
    (a, b) => Number(usate.includes(b.nome)) - Number(usate.includes(a.nome)),
  )

  return (
    <div className="cbi-dati">
      <p className="cbi-dati-fittizi">
        Dati fittizi generati a scopo dimostrativo. Il motore vede solo queste viste, mai le
        tabelle grezze.
      </p>

      <dl className="cbi-dati-stat">
        {schema.periodo && (
          <div>
            <dt>Periodo coperto</dt>
            <dd>
              {fmtMese(schema.periodo.da)} – {fmtMese(schema.periodo.a)}
            </dd>
          </div>
        )}
        {schema.data_riferimento && (
          <div>
            <dt>Dati congelati al</dt>
            <dd>{fmtData(schema.data_riferimento)}</dd>
          </div>
        )}
        <div>
          <dt>Viste disponibili</dt>
          <dd>{schema.viste.length}</dd>
        </div>
      </dl>

      <div className="cbi-viste">
        {viste.map((v) => (
          <Vista
            key={v.nome}
            v={v}
            usata={usate.includes(v.nome)}
            aperta={aperte.has(v.nome)}
            onToggle={(o) => toggle(v.nome, o)}
            apiBase={apiBase}
          />
        ))}
      </div>
    </div>
  )
}
