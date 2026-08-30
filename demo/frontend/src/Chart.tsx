import type { ReactElement } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Cella, RispostaRisultato } from './types'
import { fmtNum, tickNum } from './format'

const COLORI = ['#2f6df6', '#1f8a5b', '#e08a1e', '#8e44ad', '#c0392b', '#16a3b8', '#6b7280', '#d1477a']

const tipTip = (v: number | string) => fmtNum(v as Cella)

type Riga = Record<string, Cella>

function toRows(colonne: string[], righe: Cella[][]): Riga[] {
  return righe.map((r) => {
    const o: Riga = {}
    colonne.forEach((c, i) => (o[c] = r[i]))
    return o
  })
}

function isColonnaNumerica(colonne: string[], righe: Cella[][], nome: string): boolean {
  const i = colonne.indexOf(nome)
  if (i < 0) return false
  let almenoUno = false
  for (const r of righe) {
    const v = r[i]
    if (v === null || v === undefined) continue
    if (typeof v !== 'number') return false
    almenoUno = true
  }
  return almenoUno
}

const ALTEZZA = 280

// NB: gli assi devono essere figli DIRETTI del grafico. Un React.Fragment
// attorno a XAxis/YAxis/CartesianGrid impedisce a Recharts di rilevarli,
// quindi li passiamo come array di elementi con key.
function assiCartesiani(xKey: string, molteCategorie: boolean): ReactElement[] {
  return [
    <CartesianGrid key="grid" strokeDasharray="3 3" stroke="#eef1f6" />,
    <XAxis
      key="x"
      dataKey={xKey}
      tick={{ fontSize: 11, fill: '#5b6472' }}
      interval={molteCategorie ? 'preserveStartEnd' : 0}
      angle={molteCategorie ? -25 : 0}
      textAnchor={molteCategorie ? 'end' : 'middle'}
      height={molteCategorie ? 60 : 28}
    />,
    <YAxis key="y" tick={{ fontSize: 11, fill: '#5b6472' }} tickFormatter={tickNum} width={56} />,
    <Tooltip
      key="tip"
      formatter={tipTip}
      contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e3e7ee' }}
    />,
  ]
}

interface Props {
  ris: RispostaRisultato
}

export default function Chart({ ris }: Props) {
  const { colonne, righe, viz } = ris
  const rows = toRows(colonne, righe)
  const molte = rows.length > 6

  const xKey =
    viz.x && colonne.includes(viz.x)
      ? viz.x
      : colonne.find((c) => !isColonnaNumerica(colonne, righe, c)) ?? colonne[0]

  const numeriche = colonne.filter(
    (c) => c !== xKey && c !== viz.serie && isColonnaNumerica(colonne, righe, c),
  )
  const yKey =
    viz.y && colonne.includes(viz.y) && viz.y !== xKey ? viz.y : numeriche[0] ?? colonne[1]

  const margine = { top: 8, right: 12, bottom: 0, left: 0 }

  // ---- barre raggruppate ----
  if (viz.tipo === 'barre_raggruppate') {
    if (viz.serie && colonne.includes(viz.serie)) {
      const iS = colonne.indexOf(viz.serie)
      const iX = colonne.indexOf(xKey)
      const iY = colonne.indexOf(yKey)
      const serieVals = [...new Set(righe.map((r) => String(r[iS])))]
      const mappa = new Map<string, Riga>()
      for (const r of righe) {
        const kx = String(r[iX])
        if (!mappa.has(kx)) mappa.set(kx, { [xKey]: r[iX] })
        mappa.get(kx)![String(r[iS])] = r[iY]
      }
      return (
        <div className="cbi-chart">
          <ResponsiveContainer width="100%" height={ALTEZZA}>
            <BarChart data={[...mappa.values()]} margin={margine}>
              {assiCartesiani(xKey, molte)}
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {serieVals.map((s, i) => (
                <Bar key={s} dataKey={s} fill={COLORI[i % COLORI.length]} radius={[3, 3, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    }
    return (
      <div className="cbi-chart">
        <ResponsiveContainer width="100%" height={ALTEZZA}>
          <BarChart data={rows} margin={margine}>
            {assiCartesiani(xKey, molte)}
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {numeriche.map((c, i) => (
              <Bar key={c} dataKey={c} fill={COLORI[i % COLORI.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ---- linea ----
  if (viz.tipo === 'linea') {
    return (
      <div className="cbi-chart">
        <ResponsiveContainer width="100%" height={ALTEZZA}>
          <LineChart data={rows} margin={margine}>
            {assiCartesiani(xKey, molte)}
            <Line
              type="monotone"
              dataKey={yKey}
              stroke={COLORI[0]}
              strokeWidth={2}
              dot={{ r: 2.5 }}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ---- torta ----
  if (viz.tipo === 'torta') {
    return (
      <div className="cbi-chart">
        <ResponsiveContainer width="100%" height={ALTEZZA}>
          <PieChart>
            <Tooltip formatter={tipTip} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Pie data={rows} dataKey={yKey} nameKey={xKey} outerRadius={95} label={false}>
              {rows.map((_, i) => (
                <Cell key={i} fill={COLORI[i % COLORI.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ---- barre (default) ----
  return (
    <div className="cbi-chart">
      <ResponsiveContainer width="100%" height={ALTEZZA}>
        <BarChart data={rows} margin={margine}>
          {assiCartesiani(xKey, molte)}
          <Bar dataKey={yKey} fill={COLORI[0]} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
