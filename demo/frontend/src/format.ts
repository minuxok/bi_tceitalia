import type { Cella } from './types'

// Formattazione numerica italiana. Modulo separato da Chart.tsx così
// ResultView può usarla senza tirarsi dentro Recharts nel bundle iniziale.

const nfIt = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 2 })
const nfCompact = new Intl.NumberFormat('it-IT', { notation: 'compact', maximumFractionDigits: 1 })

export function fmtNum(v: Cella): string {
  if (typeof v === 'number') return nfIt.format(v)
  if (v === null || v === undefined) return '—'
  return String(v)
}

export const tickNum = (v: number) =>
  Math.abs(v) >= 1000 ? nfCompact.format(v) : nfIt.format(v)
