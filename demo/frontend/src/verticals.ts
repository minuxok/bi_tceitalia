// I due verticali della demo. Ognuno punta a una propria istanza del backend
// (stesso motore, dataset + layer semantico diversi).
//
// In sviluppo gli apiBase sono percorsi proxati da Vite (vite.config.ts):
//   /api      -> http://127.0.0.1:8000  (VERTICAL=acme)
//   /api-ecom -> http://127.0.0.1:8001  (VERTICAL=ecom)
// In produzione si passano gli URL al build:
//   VITE_API_BASE_GESTIONALE=/bi/api  VITE_API_BASE_ECOMMERCE=/bi/api-ecom

export interface VerticalDef {
  id: 'gestionale' | 'ecommerce'
  label: string
  store: string
  apiBase: string
  lead: string
}

const env = import.meta.env

export const VERTICALS: VerticalDef[] = [
  {
    id: 'gestionale',
    label: 'Gestionale',
    store: 'Acme Srl',
    apiBase:
      (env.VITE_API_BASE_GESTIONALE as string | undefined) ||
      (env.VITE_API_BASE as string | undefined) ||
      '/api',
    lead:
      'Dati di un’azienda di distribuzione di esempio, “Acme Srl”. Nessun dato reale, niente viene memorizzato.',
  },
  {
    id: 'ecommerce',
    label: 'E-commerce',
    store: 'Nuvola Shop',
    apiBase: (env.VITE_API_BASE_ECOMMERCE as string | undefined) || '/api-ecom',
    lead:
      'Dati di un e-commerce di esempio, “Nuvola Shop” (abbigliamento e calzature). Nessun dato reale, niente viene memorizzato.',
  },
]

export const VERTICALE_DEFAULT = VERTICALS[0]
