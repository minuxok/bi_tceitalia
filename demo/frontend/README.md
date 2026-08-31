# Widget demo — Conversational BI

Widget React **incorporabile** che parla con il backend FastAPI (`demo/backend`).
Prompt precompilati, grafico (Recharts), SQL a scomparsa + spiegazione, badge di
isolamento, CTA. Stili confinati sotto `.cbi-root` (prefisso `.cbi-`), non
collidono con il sito ospite.

## Due verticali

La landing (`src/App.tsx`, sezione "Provala adesso") ha un interruttore
**Gestionale / E-commerce**. I due poggiano su **due istanze del backend**, una
per verticale (stesso codice, `VERTICAL` diverso — vedi `demo/backend/README.md`):

| Verticale | Backend dev | Proxy Vite | Store demo |
|---|---|---|---|
| Gestionale | `:8000` (`VERTICAL=acme`) | `/api` | Acme Srl |
| E-commerce | `:8001` (`VERTICAL=ecom`) | `/api-ecom` | Nuvola Shop |

La mappa dei verticali (label, store, `apiBase`) è in `src/verticals.ts`.

## Sviluppo

```bash
# 1. i due backend (due shell, o in background)
cd demo/backend
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000                 # gestionale
VERTICAL=ecom .venv/Scripts/python.exe -m uvicorn app.main:app --port 8001   # e-commerce

# 2. frontend
cd demo/frontend
npm install
npm run dev            # http://localhost:5173
```

In dev `/api/*` → `:8000` e `/api-ecom/*` → `:8001` (proxy in `vite.config.ts`).
La pagina di sviluppo monta un finto sito "ospite" attorno al widget per
verificare l'isolamento CSS.

## Build di produzione

```bash
VITE_API_BASE_GESTIONALE=/bi/api \
VITE_API_BASE_ECOMMERCE=/bi/api-ecom \
  npm run build      # -> dist/
```

`base: './'` tiene gli asset relativi. Servire `dist/` come sito statico dietro
nginx (es. location `/bi/`), con **due** reverse-proxy: `/bi/api/` → uvicorn
`VERTICAL=acme` e `/bi/api-ecom/` → uvicorn `VERTICAL=ecom` (due servizi/container
separati). Se si passa solo `VITE_API_BASE`, entrambi i verticali lo usano come
fallback (utile per una demo a verticale singolo).

Bundle: `index.js` ~201 kB (63 kB gzip) + chunk `Chart-*.js` ~409 kB (Recharts,
caricato in lazy solo quando serve il primo grafico).

## Incorporare nel sito del cliente

```html
<div id="cbi"></div>
<script type="module" src="/bi/assets/index-XXXX.js"></script>
<script>
  ConversationalBI.mount('#cbi', { ctaHref: '/contatti' })
</script>
```

`mount(target, opts)` — `opts`: `titolo`, `sottotitolo`, `ctaHref`, `ctaLabel`,
`maxEsempi`, `apiBase` (backend da interrogare), `storeName` (nome store nel
sottotitolo e nel placeholder).

## File

| File | Ruolo |
|---|---|
| `src/Widget.tsx` | shell: header + badge, chip esempi (`/domande`), input, conversazione, footer CTA |
| `src/ResultView.tsx` | render di una risposta: sintesi, viz, dettaglio SQL, note; info-box per chiarimento / non_disponibile / errore |
| `src/Chart.tsx` | Recharts da `viz` = `{tipo,x,y,serie}`: barre / barre_raggruppate / linea / torta; tabella e kpi stanno in ResultView. Caricato in lazy |
| `src/format.ts` | `fmtNum` / `tickNum` (formattazione IT), separato per non tirare Recharts nel bundle iniziale |
| `src/api.ts` | client `/health` `/domande` `/chiedi`; ogni funzione accetta un `base` esplicito; normalizza tutto in `Risposta` tipizzata |
| `src/verticals.ts` | mappa dei due verticali: label, store, `apiBase`, testo intro |
| `src/types.ts` | forme di risposta del backend |
| `src/widget.css` | stili con prefisso `.cbi-`, ambito `.cbi-root` |
| `src/main.tsx` | espone `window.ConversationalBI.mount`; in dev monta `App` su `#root` |
