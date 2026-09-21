// Forme di risposta del backend FastAPI (demo/backend/app/main.py).

export type VizTipo =
  | 'barre'
  | 'barre_raggruppate'
  | 'linea'
  | 'torta'
  | 'tabella'
  | 'kpi'

export interface VizSpec {
  tipo: VizTipo
  x: string | null
  y: string | null
  serie: string | null
}

export type Cella = string | number | boolean | null

export interface RispostaRisultato {
  tipo: 'risultato'
  risposta_testo: string
  spiegazione: string
  sql: string
  /** viste ai_bi_* citate nella query (assente su backend più vecchi) */
  viste_usate?: string[]
  colonne: string[]
  righe: Cella[][]
  n_righe: number
  troncato: boolean
  viz: VizSpec
  durata_ms: number
}

export interface RispostaChiarimento {
  tipo: 'chiarimento'
  messaggio: string
}

export interface RispostaNonDisponibile {
  tipo: 'non_disponibile'
  messaggio: string
}

export interface RispostaErrore {
  tipo: 'errore'
  errore: string
  sql?: string
}

export type Risposta =
  | RispostaRisultato
  | RispostaChiarimento
  | RispostaNonDisponibile
  | RispostaErrore

export interface ElencoDomande {
  domande: string[]
}

export interface Health {
  stato: string
  verticale?: string
  llm_configurato: boolean
  modello: string
  data_riferimento: string
  viste: string[]
}

export interface DemoVista {
  nome: string
  descrizione: string
  colonne: { nome: string; tipo: string }[]
  n_righe: number | null
}

export interface DemoSchema {
  verticale: string
  data_riferimento: string
  periodo: { da: string; a: string; vista: string } | null
  viste: DemoVista[]
}

export interface DemoSample {
  vista: string
  colonne: string[]
  righe: Cella[][]
}
