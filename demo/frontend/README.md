# Widget demo — Conversational BI

Widget React **incorporabile** che parla con il backend FastAPI (`demo/backend`).
Prompt precompilati, grafico (Recharts), SQL a scomparsa + spiegazione, badge di
isolamento, CTA. Stili confinati sotto `.cbi-root` (prefisso `.cbi-`), non
collidono con il sito ospite.

## Sviluppo

```bash
# 1. backend (altra shell)
cd demo/backend
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

# 2. frontend
cd demo/frontend
npm install
npm run dev            # http://localhost:5173
```

In dev le chiamate a `/api/*` sono inoltrate a `http://127.0.0.1:8000` (proxy in
`vite.config.ts`). La pagina di sviluppo (`src/App.tsx`) monta un finto sito
"ospite" attorno al widget per verificare l'isolamento CSS.

## Build di produzione

```bash
VITE_API_BASE=/bi/api npm run build      # -> dist/
```

`base: './'` tiene gli asset relativi. Servire `dist/` come sito statico dietro
nginx (es. location `/bi/`), con `/bi/api/` in reverse-proxy verso uvicorn.

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
`maxEsempi`.

## File

| File | Ruolo |
|---|---|
| `src/Widget.tsx` | shell: header + badge, chip esempi (`/domande`), input, conversazione, footer CTA |
| `src/ResultView.tsx` | render di una risposta: sintesi, viz, dettaglio SQL, note; info-box per chiarimento / non_disponibile / errore |
| `src/Chart.tsx` | Recharts da `viz` = `{tipo,x,y,serie}`: barre / barre_raggruppate / linea / torta; tabella e kpi stanno in ResultView. Caricato in lazy |
| `src/format.ts` | `fmtNum` / `tickNum` (formattazione IT), separato per non tirare Recharts nel bundle iniziale |
| `src/api.ts` | client `/health` `/domande` `/chiedi`; normalizza tutto in `Risposta` tipizzata |
| `src/types.ts` | forme di risposta del backend |
| `src/widget.css` | stili con prefisso `.cbi-`, ambito `.cbi-root` |
| `src/main.tsx` | espone `window.ConversationalBI.mount`; in dev monta `App` su `#root` |
