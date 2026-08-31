# Piano di lavoro e offerta — Assistente AI per i gestionali dei clienti

> Servizio di *Conversational BI* (business intelligence conversazionale) per PMI: l'utente scrive una domanda in italiano, l'AI interroga il gestionale/CRM/ERP del cliente in sola lettura e risponde con testo, tabella e grafico.
> Riferimento di mercato: SerGPT di Sernicola Labs.

---

## 1. Cosa penso del piano che ti ha dato Qwen

### Quello che è giusto e va tenuto
- **Inquadramento corretto**: è Conversational BI + architettura *Text-to-SQL*. Il valore non è "vendere l'AI" ma togliere ore di export/Excel a chi non sa scrivere query.
- **Connessione in sola lettura** con utente DB dedicato: è il primo argomento di vendita e va messo al centro.
- **Middleware obbligatorio** tra LLM e database: mai LLM attaccato al DB.
- **Glossario semantico** ("fatturato = SUM(importo) su ordini pagati"): è la vera leva di qualità. Qwen lo cita ma lo sottovaluta.
- **Demo sandbox sul sito** con database fittizio e prompt precompilati: giusto, è lo strumento di vendita numero uno.
- **Struttura di pricing** setup una-tantum + canone mensile: corretta come impianto.
- **Attenzione a GDPR / AI Act, DPA, hosting UE, zero retention**: in Italia è il punto che chiude o blocca il contratto.
- **Verticalizzazione** e **feedback loop 👍/👎**: consigli validi.

### Quello che manca o che è troppo ottimistico
1. **Il problema difficile non è il Text-to-SQL: è collegarsi ai gestionali di terze parti.**
   Zucchetti, TeamSystem, SAP Business One, Danea, Arca, gestionali custom… spesso:
   - non danno accesso diretto al DB (o lo dà solo il loro rivenditore);
   - hanno nomi di tabelle/campi criptici (`RIGHE_DOC`, `C_ANART`, `TD_TESTAT`);
   - girano **on-premise dentro la LAN del cliente**, senza IP pubblico;
   - a volte sono SaaS con **solo API o export**, nessun DB raggiungibile.
   Qwen liquida tutto questo in una riga. È il 60% del rischio del progetto e va gestito con una **fase di assessment tecnico per ogni cliente** e con **due architetture diverse** (vedi §3).
2. **L'accuratezza del Text-to-SQL su schemi reali sporchi è molto più bassa che sul DB demo pulito.** Serve un **layer di viste curate** + glossario + **harness di test** con soglia di go-live. Senza questo è un giocattolo, non un prodotto.
3. **Connettività on-premise**: serve un **connettore installato dal cliente** che apra solo una connessione *in uscita* (tunnel), senza aprire porte in ingresso. È infrastruttura vera e supporto ricorrente: Qwen non lo nomina.
4. **Mostrare la query SQL "per trasparenza" non basta**: un utente non tecnico non sa validarla. Serve anche spiegazione in linguaggio naturale di *cosa ha fatto la query* + drill-down alle righe sorgente.
5. **Pricing e sforzo probabilmente sottostimati**: setup €2–5k è ok solo per il caso "DB accessibile e pulito". Con ETL, più fonti e glossario esteso servono più giornate. Meglio a fasce (vedi §9).
6. **Build vs buy ignorato**: esistono basi open-source/commerciali (WrenAI, Vanna.ai, Dataherald, Databricks Genie, server MCP per Postgres/SQL Server). Valutarle può farti risparmiare settimane rispetto a costruire da zero con LangChain.
   → **Deciso (rev. 2)**: motore **custom lean** (FastAPI + LiteLLM + validatore sqlglot), niente LangChain. Su viste curate + glossario il Text-to-SQL è un compito semplice; un motore proprio è più governabile e senza dipendenze pesanti. WrenAI/Vanna restano un'opzione se in futuro serve onboarding self-service su molti clienti.
7. **Streamlit per la demo sul sito pubblico non è l'ideale** (branding, iframe, cold start del piano gratuito). Ok come prototipo interno; per il sito serve un widget custom.
8. **"Real time vs ETL"**: SerGPT vende "niente CSV notturni, tutto in tempo reale". Se per un cliente devi passare per l'ETL, **non puoi promettere il tempo reale**: vanno dichiarati i limiti per cliente.
9. **MCP**: citarlo fa scena ma per un prodotto controllato una FastAPI ben fatta è più semplice e più governabile. MCP utile solo se vuoi che client esterni (Claude, ecc.) si colleghino: non è prioritario per la v1.
10. **Azioni di scrittura** ("bozza email di riattivazione"): Qwen le propone come differenziazione. In v1 **stai rigorosamente in sola lettura**: le azioni di scrittura moltiplicano rischio e durata della trattativa.

### Voto sintetico
Impianto valido al ~70%. Buono come visione, debole su: connettività ai gestionali reali, garanzia di accuratezza, stima di sforzo/prezzo. Questo documento colma quei buchi.

---

## 2. Posizionamento e proposta di valore

**Promessa al cliente:**
> "Trasformiamo il tuo gestionale in un collega che risponde in italiano. In sola lettura, in totale sicurezza, senza cambiare il software che già usi."

**Pain point da attaccare (nella prima call):**
> "Quante ore a settimana il tuo team perde a esportare CSV, pulire dati su Excel e rifare gli stessi grafici per le riunioni?"

**A chi lo vendi (target iniziale, non 'qualsiasi gestionale'):**
- PMI 10–100 dipendenti con un gestionale **con DB accessibile** (SQL Server / PostgreSQL / MySQL) o con **API/export documentati**.
- Reparti che vivono di numeri: direzione commerciale, amministrazione, acquisti, controllo di gestione.
- Meglio ancora: **un settore che conosci** (manifatturiero, distribuzione, studi professionali, e-commerce…) di cui padroneggi il gergo ("commessa", "DdT", "margine di contribuzione", "scaduto").

**Come ti differenzi da Sernicola / altri generalisti:**
1. **Verticalizzazione**: "l'assistente AI per i gestionali del settore X".
2. **Connettore on-site "a porta chiusa"**: installazione guidata, nessuna porta aperta verso l'esterno.
3. **Trasparenza reale**: ogni risposta = query SQL + spiegazione a parole + link alle righe di origine.
4. **Prezzo chiaro e SLA scritto** (i generalisti spesso non lo danno).
5. **Opzione on-premise/ibrida** per chi non vuole dati in cloud.

### 2.1 Secondo verticale: gli e-commerce self-hosted

Oltre ai gestionali, lo stesso prodotto si vende agli **e-commerce che girano su database proprio** (WooCommerce, PrestaShop, Magento). È un secondo cuneo, non un prodotto nuovo:

- **Riuso quasi gratuito dell'architettura.** Il motore non conosce il dominio: tutto il "verticale" vive in 4 file dati (schema + seed, viste `ai_bi_*`, glossario, domande d'oro). Nuovo verticale = swap di quei file, zero modifiche al backend.
- **Schemi standardizzati.** Woo/Presta/Magento hanno modelli dati noti e stabili: il connettore lo costruisci una volta e lo riusi su molti clienti — l'opposto dei gestionali, dove ogni installazione ha il suo schema.
- **KPI universali.** Conversion rate, AOV, marginalità per categoria, rotazione di magazzino, resi, riacquisto, prodotti fermi: stesse domande per tutti → lavoro semantico riutilizzabile.
- **Utente ideale.** Il merchant non è tecnico, l'analytics nativa di Woo/Presta è povera, GA4 è ostico: il divario tra "ho i dati" e "so leggerli" è esattamente il vuoto che riempiamo.
- **Canale di distribuzione.** Le web agency che costruiscono e mantengono siti WooCommerce sono l'analogo dei rivenditori di gestionali: stesso schema di partnership.

**Perimetro (v1 e-commerce):** solo e-commerce **self-hosted** con MySQL/MariaDB raggiungibile — stesso pattern tecnico dei gestionali (§3.2, Pattern A/B). Posizionamento su domande **operative e di merchandising**: magazzino, margini, performance prodotto, segmenti cliente, riacquisto.

**Fuori ambito (fase 2, solo se la trazione lo giustifica):**
- **Shopify**: niente accesso al DB, si passa dalle API → è un pezzo di prodotto diverso, non un adattamento.
- **Attribution pubblicitaria multi-fonte** ("quanto rende la campagna Meta" = ordini + ad spend + GA + tool email): richiede più fonti, e la concorrenza è fittissima (Triple Whale, Polar, Lifetimer…). Un motore che interroga solo il DB risponde a metà: meglio non entrarci in v1.

---

## 3. Architettura tecnica

### 3.1 Principio generale

```
[Gestionale/DB cliente]  →  [Connettore sola-lettura]  →  [Backend/Middleware]  →  [Motore Text-to-SQL + LLM UE]
                                    (tunnel in uscita)         (API, sicurezza,        (schema + glossario +
                                                                logging, cache)         validazione query)
                                                                     ↓
                                                        [Widget chat sul sito/portale del cliente
                                                         + eventuale bot Teams/Slack]
```

L'LLM **non vede mai il database**. Vede: lo **schema delle viste curate**, il **glossario**, alcuni **esempi** e la **domanda**. Genera una query SQL che il backend **valida ed esegue** al posto suo.

### 3.2 Due pattern di connettività (da scegliere per cliente in fase di assessment)

**Pattern A — Accesso diretto in sola lettura (preferito)**
- Utente DB dedicato con permessi **solo SELECT** e visibilità **solo sullo schema `ai_bi`** (le viste curate, non le tabelle grezze).
- Connettore = piccolo container Docker / servizio Windows presso il cliente che apre **solo una connessione in uscita** verso il tuo backend tramite tunnel (WireGuard / Tailscale / Cloudflare Tunnel). **Nessuna porta in ingresso** aperta sul firewall del cliente.
- Dati **in tempo reale**. È il caso che puoi vendere come SerGPT.

**Pattern B — ETL verso un tuo data mart (quando il DB non è raggiungibile)**
- Il gestionale espone solo API o export → un job schedulato (ogni 15 min / ogni ora / notte) porta i dati in un **PostgreSQL/DuckDB gestito da te**, con trasformazioni in **dbt**.
- Diventi di fatto un mini fornitore di data warehouse. Più lavoro, più valore, ma **niente promessa di tempo reale**: dichiara la latenza (es. "dati aggiornati ogni ora").
- Isolamento per cliente: uno schema/database separato per ciascuno (nessun dato condiviso tra clienti).

### 3.3 Layer semantico (il pezzo che determina la qualità)

Per ogni cliente crei uno schema `ai_bi` con **viste SQL curate**:
- nomi parlanti (`vendite`, `clienti_attivi`, `scaduto_per_cliente`);
- join già risolti;
- stati normalizzati (`'EV' → 'in evasione'`);
- campi calcolati pronti (`margine`, `giorni_ritardo`);
- **PII mascherate dove non servono** (email, telefono, codice fiscale).

E un **glossario** (file YAML/JSON versionato) tipo:
```yaml
fatturato: "SUM(importo_netto) da ai_bi.vendite dove stato = 'confermato'"
cliente attivo: "cliente con almeno un ordine negli ultimi 6 mesi"
scaduto: "SUM(importo) da ai_bi.partite_aperte dove data_scadenza < CURRENT_DATE"
anno in corso: "EXTRACT(YEAR FROM data) = EXTRACT(YEAR FROM CURRENT_DATE)"
```

Vantaggi: l'LLM lavora su 8–15 viste pulite invece che su 300 tabelle criptiche → accuratezza molto più alta, contesto più corto, costo token più basso.

### 3.4 Motore Text-to-SQL

**Valuta prima il "buy":**
- **WrenAI** (open source): text-to-SQL con semantic layer (MDL), UI inclusa, self-host. Buona base white-label.
- **Vanna.ai** (open source / SaaS): RAG su schema + esempi, libreria Python, si integra ovunque.
- **Dataherald**, **Databricks Genie**, **MotherDuck**: alternative da conoscere.

**Se costruisci custom**, i componenti minimi:
1. **Schema retrieval**: passa all'LLM solo le viste rilevanti alla domanda (se sono >15).
2. **Few-shot**: 10–30 esempi "domanda → SQL corretta" per cliente.
3. **Glossario** iniettato nel system prompt.
4. **Validazione query** (obbligatoria):
   - solo `SELECT` (parser che rifiuta DDL/DML/`;` multipli/`PRAGMA`/`COPY`/funzioni di sistema);
   - `LIMIT` forzato (es. 1000 righe);
   - `statement_timeout` (es. 10s);
   - whitelist: solo schema `ai_bi`.
5. **Gestione ambiguità**: se la domanda è vaga, l'AI **fa una domanda di chiarimento**, non inventa.
6. **Spiegazione**: oltre alla query, una frase in italiano ("Ho sommato gli importi degli ordini confermati del 2025, raggruppati per mese").
7. **Drill-down**: bottone "vedi le righe" che esegue la stessa query senza aggregazione.

**LLM + hosting (per il DPO del cliente):**
- **Demo pubblica sul sito** (dati fittizi): **Gemini 2.x Flash / Flash-Lite** via API — costo minimo, ottimo su Text-to-SQL con viste pulite.
- **Clienti reali** — uno di questi, scelto insieme al DPO:
  - **Google Vertex AI** region UE (`europe-west*`) — Gemini, con data residency e no-training;
  - **Azure OpenAI** region UE (Svezia/Francia) — GPT-4o / 4o-mini;
  - **AWS Bedrock** region UE — Claude;
  - tutti con **zero data retention** e **nessun training sui dati**.
- ⚠️ La **Gemini API di Google AI Studio (tier gratuito)** usa i dati per il training e **non ha DPA**: va bene **solo** per la demo con dati finti, **mai** per un cliente. Per i clienti reali → **Vertex AI** (region UE).
- Astrai il provider con **LiteLLM** per poter cambiare fornitore senza riscrivere: la demo usa Gemini Flash, il primo cliente userà Vertex AI/Azure/Bedrock, stesso codice.

### 3.5 Osservabilità e qualità

- Log strutturato di **ogni** interazione: domanda → viste usate → SQL → righe → esito → 👍/👎.
- Tracing LLM e costi con **Langfuse** o **Helicone**.
- **Harness di valutazione**: 30–50 domande per cliente con risultato atteso; gira in automatico a ogni modifica di prompt/glossario/viste. **Soglia di go-live: ≥ 90% sulle domande target.**

### 3.6 Stack consigliato

| Livello | Scelta | Note |
|---|---|---|
| Connettore on-site | Docker / servizio Windows + WireGuard/Tailscale | solo uscita, nessun inbound |
| Backend | Python **FastAPI** | API, auth, validazione query, cache, logging |
| Layer semantico | viste `ai_bi` nel DB cliente **oppure** Postgres/DuckDB + **dbt** (pattern B) | |
| Motore T2SQL | **Custom lean**: FastAPI + LiteLLM + validatore SQL (sqlglot) | scelta presa; WrenAI/Vanna da riconsiderare solo se onboarding massivo |
| LLM | Demo: **Gemini Flash**. Prod: **Vertex AI UE** / Azure OpenAI UE / Bedrock UE, via **LiteLLM** | zero retention; AI Studio tier gratuito NO (training sui dati) |
| Grafici | ECharts / Chart.js / Plotly | generati lato client |
| Widget prodotto | React embeddabile + bot Teams/Slack | |
| Demo sito | Next.js/React + FastAPI + **SQLite** fittizio | **non** Streamlit; la demo è una **fetta verticale del prodotto vero** (stesso backend, validazione, layer semantico) |
| Osservabilità | Langfuse/Helicone + dashboard interna | |
| Hosting | Render / Railway / Fly.io / Hetzner (UE) | |

---

## 4. Sicurezza e conformità (kit da mettere sul tavolo del cliente)

**Tecnico**
- [ ] Utente DB dedicato **solo SELECT**, visibilità solo su schema `ai_bi`.
- [ ] Connessione cifrata (TLS), tunnel **in sola uscita**, nessuna porta aperta lato cliente.
- [ ] Parser che consente **solo SELECT**; blocco DDL/DML; `LIMIT` + `timeout` forzati.
- [ ] **Masking PII** nelle viste dove non necessarie (email, telefono, CF, IBAN).
- [ ] All'LLM vanno **schema + glossario + dati aggregati**, non dump di righe grezze quando evitabile.
- [ ] Log cifrati, retention limitata (es. 30–90 gg), accesso ristretto.
- [ ] Segregazione per cliente (schema/DB separati, chiavi separate).
- [ ] Security review / pen-test prima del go-live.
- [ ] Piano di incident response documentato.

**Legale / privacy**
- [ ] **DPA** (accordo art. 28 GDPR): tu = Responsabile del trattamento, cliente = Titolare.
- [ ] **Elenco sub-responsabili** (Microsoft/AWS/Anthropic/OpenAI + hosting), tutti con dati in **UE**.
- [ ] Clausola: **i dati del cliente non vengono usati per addestrare modelli**; zero retention lato LLM.
- [ ] Proprietà esclusiva dei dati in capo al cliente; su richiesta: **export completo + cancellazione**.
- [ ] **AI Act**: l'assistente è un sistema a **rischio limitato** (strumento analitico, nessuna decisione automatizzata su persone) → obblighi di **trasparenza**; predisponi una scheda tecnica.
- [ ] Template di **DPIA** pronto per i clienti che lo chiedono.

**Frase da usare in trattativa:**
> "Accesso in sola lettura, solo su viste che decidiamo insieme, connessione che parte da voi verso di noi senza aprire nulla sul vostro firewall, dati in Europa, mai usati per addestrare modelli. Il DPA è già pronto."

---

## 5. Ambito della v1 (MVP) — cosa fare e cosa NON fare

**Fare**
- 1–2 gestionali/DB **che conosci**, 1 cliente pilota.
- Sola lettura, un solo dominio dati prioritario (es. vendite + clienti).
- Chat web + risposta testo/tabella/grafico + query visibile + drill-down.
- Glossario + viste curate + harness di test.
- Logging completo e feedback 👍/👎.

**NON fare in v1**
- Azioni di scrittura (email, aggiornamento record).
- Onboarding self-service multi-tenant.
- "Qualsiasi gestionale".
- Dashboard salvate complesse, permessi granulari per utente, multi-lingua.
- MCP / integrazioni con client esterni.

---

## 6. Roadmap operativa (indicativa: 1 sviluppatore + tu sul commerciale)

> **Strategia (rev. 2): demo-first.** L'obiettivo immediato è la **demo pubblica sul sito** come strumento di vendita e di ricerca di mercato. L'implementazione **su misura per un cliente (Fase 2)** parte **solo su richiesta di un cliente reale**, non come step lineare. La demo è costruita come **fetta verticale del prodotto** (stesso backend, validazione, layer semantico), quindi il passaggio a un cliente è incrementale, non una riscrittura.

### Fase 0 — Fondamenta tecniche · settimana 1–2  ✅ in gran parte fatta
- [ ] Scegli **1 gestionale/DB target** e **1 cliente pilota** disponibile ("cliente amico"). *(commerciale, in corso)*
- [x] **Build vs buy deciso**: motore **custom lean** (FastAPI + LiteLLM + validatore sqlglot). WrenAI/Vanna rimandati.
- [ ] Ottieni **API key Gemini** (per la demo). Per il primo cliente reale: aprire **Vertex AI UE** (o Azure OpenAI UE / Bedrock UE).
- [x] **DB demo "Acme Srl"** in `demo/db/` (90 clienti, ~1.900 ordini, 6 tabelle + 6 viste `ai_bi_*`, glossario) + **12 "domande d'oro"** con SQL atteso + harness offline.
- [x] **Motore Text-to-SQL** funzionante in `demo/backend/` (FastAPI: `/chiedi`, `/domande`, `/health`); pipeline validata offline su tutte le domande d'oro.

### Fase 1 — Demo pubblica sul sito · settimana 3–4  ← **focus attuale**
- [ ] Widget demo (React/Next + FastAPI) con DB "Acme Srl", **prompt precompilati**, query visibile, grafico.
- [ ] Badge "🔒 Ambiente isolato. Nessun dato reale elaborato o memorizzato."
- [ ] **CTA** sotto la demo: *"Colleghiamo l'AI al tuo gestionale reale, in sola lettura → Prenota una demo di 15 minuti."*
- [ ] **Logging** delle domande provate dai visitatori (ti dice cosa vuole il mercato).
- [ ] Pagina landing con: problema → soluzione → sicurezza → demo → prezzi.
- [x] **Secondo verticale nella demo — e-commerce "Nuvola Shop"** (§2.1): dataset + viste `ai_bi_*` + glossario + 12 domande d'oro; backend parametrizzato per verticale (`VERTICAL=acme|ecom`); toggle "Gestionale / E-commerce" nella sezione demo della landing (due istanze backend, `/api` + `/api-ecom`). Verificato dal vivo su entrambi i verticali. Resta l'eval live sul set e-commerce.

### Fase 2 — Cliente pilota · **solo su richiesta di un cliente reale**
- [ ] Esegui il **runbook di onboarding** (§7) end-to-end.
- [ ] Connettore on-site + tunnel in sola uscita.
- [ ] Viste `ai_bi` + glossario + 30–50 test.
- [ ] **Hardening sicurezza** (checklist §4).
- [ ] UAT con 3–5 utenti reali del cliente per 1 settimana.
- [ ] Go-live + formazione 1h + cheat sheet.

### Fase 3 — Prodotto e mercato · settimana 9–12
- [ ] Rifinisci offerta e listino con i numeri reali del pilota (giornate, costi LLM).
- [ ] Materiali commerciali (§10): 6 slide, one-pager sicurezza, DPA, video demo di 90s.
- [ ] Pacchettizza: connettore installabile, **template di viste per il gestionale X**, libreria glossario.
- [ ] Acquisisci cliente 2 e 3.

### Trimestre 2 — Scala
- [ ] Verticalizzazione: libreria di glossari e viste per settore.
- [ ] Bot Teams/Slack.
- [ ] Dashboard con grafici salvati + "aggiorna tutto".
- [ ] Secondo gestionale supportato.
- [ ] Eventuale offerta **on-premise** (LLM open-source sui server del cliente) per i clienti "paranoici".

---

## 7. Runbook di onboarding per cliente (da rendere ripetibile)

| # | Fase | Durata tipica | Output |
|---|---|---|---|
| 1 | **Discovery tecnico** | 0,5–1 gg | Quale gestionale/versione, dove gira il DB, tipo DB, accesso possibile? API/export? Referente IT o rivenditore. Volumi dati. Aree dati prioritarie. |
| 2 | **Accesso & connettività** | 0,5–2 gg | Utente read-only creato, connettore installato, tunnel testato |
| 3 | **Modellazione semantica** | 1–3 gg | Schema `ai_bi` con 8–15 viste curate + glossario |
| 4 | **Configurazione motore** | 0,5–1 gg | Schema + glossario + few-shot caricati; lista domande campione |
| 5 | **Eval & tuning** | 1–2 gg | Harness ≥ 90% sulle domande target |
| 6 | **UAT col cliente** | 1 settimana | 3–5 utenti reali, feedback raccolto, 👍/👎 |
| 7 | **Go-live + formazione** | 0,5 gg | Sessione 1h, cheat sheet domande, canale supporto attivo |
| 8 | **Manutenzione continua** | ricorrente | Review mensile domande fallite, aggiornamento glossario/viste |

**Prerequisito contrattuale**: l'accesso ai dati (diretto o via API/export) è a carico del cliente. Se il fornitore del gestionale lo nega, si passa al pattern B (ETL) con adeguamento di tempi e prezzo.

---

## 8. Rischi e mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Il fornitore del gestionale nega l'accesso al DB | Alto | Pattern B (ETL via export/API); coinvolgere il fornitore; clausola "accesso = prerequisito" nel contratto |
| Accuratezza Text-to-SQL insufficiente su schema reale | Alto | Layer di viste curate + glossario + harness con soglia; fallback "chiedo chiarimenti" |
| Costi LLM fuori controllo | Medio | Modelli mini/haiku, cache, rate limiting, monitor costi, *fair use* in contratto |
| Cambio schema dopo update del gestionale | Medio | Monitoraggio + contratto di manutenzione che copre gli adeguamenti minori |
| Dubbi GDPR/AI Act del cliente | Alto (blocca la firma) | Kit compliance pronto: DPA, region UE, zero retention, DPIA template, scheda AI Act |
| Lock-in su un fornitore LLM | Medio | Astrazione con LiteLLM |
| Allucinazioni presentate come fatti | Alto (reputazione) | Query sempre visibile + spiegazione + drill-down; disclaimer "verifica i numeri prima di decisioni critiche" |
| Concorrenza sul prezzo | Medio | Verticalizzazione + servizio + relazione locale, non competere al ribasso |
| Demo pubblica usata in modo improprio / costi | Basso | Rate limit per IP, solo DB fittizio, prompt guidati, budget cap sull'API |

---

## 9. Offerta commerciale (bozza da personalizzare)

> I numeri sono **indicativi per il mercato PMI italiano 2026** e vanno calibrati sul tuo costo/giornata e sul costo reale LLM misurato col pilota.

### 9.1 Pacchetto POC (consigliato come primo passo)
**"Automatizziamo 3 report che fate ogni settimana"**
- Durata: 3–4 settimane. Su un obiettivo misurabile concordato.
- Accesso in sola lettura, 1 dominio dati, fino a 3 utenti.
- **Prezzo: € 1.500 – 2.500** (scomputabile al 100% dall'attivazione se si prosegue entro 30 gg).
- Deliverable: assistente funzionante sui 3 report + report di accuratezza + raccomandazioni.

### 9.2 Attivazione (una tantum)

| Livello | Quando | Prezzo |
|---|---|---|
| **Standard** | DB accessibile, schema noto, 1 dominio dati | **€ 2.500 – 4.000** |
| **Avanzato** | ETL richiesto e/o più fonti e/o glossario esteso | **€ 5.000 – 9.000** |

Comprende: assessment, connettore, utente read-only, viste `ai_bi`, glossario, few-shot, harness di test, hardening sicurezza, DPA, UAT, formazione.

### 9.3 Canone mensile (SaaS + supporto)

| Piano | Utenti | Domini dati | Prezzo/mese |
|---|---|---|---|
| **Base** | fino a 3 | 1 | **€ 180 – 300** |
| **Business** | fino a 10 | fino a 3 + dashboard | **€ 400 – 700** |
| **Enterprise** | oltre 10 / on-premise | su misura | **da € 900** |

Il canone copre: infrastruttura, costi token LLM (entro *fair use*, es. 1.500–3.000 domande/mese poi a consumo), monitoraggio, aggiornamenti minori di glossario/viste, supporto.

### 9.4 Add-on
- Nuovo dominio dati: **€ 800 – 2.000** una tantum.
- Bot Teams/Slack: **€ 800 – 1.500** una tantum.
- Dashboard con grafici salvati: **€ 1.000 – 2.500** una tantum.
- Deploy on-premise con LLM open-source: **quotazione dedicata**.
- Adeguamento per cambio gestionale / migrazione schema: **a giornata (€ 400 – 600/gg)**.

### 9.5 Condizioni
- Durata minima 12 mesi, poi rinnovo tacito; disdetta con 60 gg di preavviso.
- **Proprietà dei dati sempre del cliente**; export + cancellazione su richiesta entro 15 gg.
- SLA supporto: risposta entro 1 giorno lavorativo; uptime target 99,5%.
- Prerequisito: accesso ai dati fornito dal cliente (diretto o API/export).
- Fuori ambito: correzioni di dati errati nel gestionale, sviluppi sul gestionale stesso, azioni di scrittura.

### 9.6 Esempio di conto economico per cliente (piano Business)
```
Ricavi:   attivazione € 3.500 (una tantum) + € 550/mese = € 6.600/anno ricorrente
Costi:    LLM ~€ 15–40/mese · infra ~€ 20/mese · supporto ~2 h/mese
Margine ricorrente lordo stimato: ~75–85%
```

---

## 10. Materiali commerciali da preparare

1. **Demo sul sito** (la vera arma) + video di 90 secondi che mostra: domanda → query → grafico in pochi secondi.
2. **6 slide**: (1) tempo perso su Excel · (2) parla col tuo gestionale · (3) sicurezza: sola lettura + UE + DPA · (4) demo/screenshot · (5) come funziona, passo per passo · (6) prezzi e prossimo passo.
3. **One-pager sicurezza** (1 facciata) per il DPO / responsabile IT.
4. **DPA + elenco sub-responsabili** pronti da firmare.
5. **Listino** con i 3 pacchetti.
6. **Case study del pilota** appena disponibile (numeri: ore risparmiate, report automatizzati).
7. **Cheat sheet "50 domande che puoi fare"** per gli utenti dopo il go-live.

**Copione della demo in riunione:** database di esempio già pronto → *"Quali sono i 5 clienti più redditizi degli ultimi 6 mesi? Fammi un grafico a barre."* → risposta in pochi secondi. Poi: *"Questo lo colleghiamo al vostro gestionale in sola lettura in circa X giorni."*

---

## 11. KPI da monitorare

**Demo sito**: visitatori che provano, domande per sessione, % di click sulla CTA, domande più frequenti (per capire il mercato).
**Delivery**: giornate di onboarding per cliente, accuratezza sull'harness, % di domande risolte senza intervento umano.
**Business**: MRR, churn, margine per cliente (canone − costo LLM − ore supporto), tempo medio POC → contratto.

---

## 12. Prossimi passi immediati (checklist)

- [x] ~~Spike WrenAI/Vanna → build vs buy~~ → **deciso**: motore custom lean (FastAPI + LiteLLM + sqlglot).
- [x] **DB demo "Acme Srl"** + **12 domande d'oro** + harness offline (`demo/db/`, `demo/eval/`).
- [x] **Motore Text-to-SQL** + API (`demo/backend/`): `/chiedi`, `/domande`, `/health`; validatore query; pipeline testata offline.
- [x] **API key Gemini** + verifica accuratezza reale: `eval_live.py` **12/12** golden (soglia ≥ 90%) + 3/3 controlli negativi + `probe_live.py` 16/17 su domande fuori set. Billing risolto (progetto su account con credito AI Studio).
- [x] **Widget** React embeddabile (`demo/frontend/`, Vite+React+TS+Recharts): prompt precompilati, grafico (tutti i tipi provati dal vivo), SQL a scomparsa + spiegazione, badge isolamento, CTA, stili `.cbi-` scoped, API di embed `ConversationalBI.mount()`, responsive, bundle code-split (201 kB + Recharts in lazy). Fix in corsa: inferenza tipi colonne vista, assi Recharts, overflow conversazione. Eval ancora 12/12.
- [x] **Secondo verticale demo — e-commerce "Nuvola Shop"** (§2.1): `demo/db/schema_ecom.sql` + `seed_ecom.py` → `nuvola.db` (abbigliamento/calzature: 3.600 clienti, 120 prodotti, 9.000 ordini, 1.852 resi, traffico giornaliero per canale → conversion rate senza GA); `demo/semantic/views_ecom.sql` (6 viste `ai_bi_*`); `glossario_ecom.yaml` (33 termini + regola "ROAS/CPA → non disponibile"); `demo/eval/golden_questions_ecom.yaml` (12 domande d'oro + 3 controlli negativi, tutte le SQL di riferimento eseguite e verificate).
- [x] **Backend parametrizzato per verticale**: env `VERTICAL=acme|ecom` seleziona DB + viste + glossario + golden (`config.py`), `VIEW_DESCRIPTIONS` e `_VERTICAL_PROMPT` per verticale (`semantic.py`, `prompt.py`), `/health` riporta il verticale. `test_offline.py` verde su entrambi.
- [x] **Toggle "Gestionale / E-commerce"** nella sezione demo della landing (`src/verticals.ts` + interruttore in `App.tsx`; `Widget` con prop `apiBase`/`storeName`). Due istanze del backend: `/api` (`:8000`, acme) e `/api-ecom` (`:8001`, ecom); in prod due servizi/container dietro nginx. Provato dal vivo: entrambi i verticali rispondono con grafico.
- [x] `eval_live.py` sul set e-commerce: **12/12 golden (100%)**, di cui 7/7 "cieche", + **3/3 controlli negativi** (ROAS→rifiutato, email→PII rifiutata, domanda vaga→chiarimento). Modello `gemini/gemini-3.6-flash`. Esito in `demo/eval/last_run_ecom.json`.
- [ ] Deploy della demo sul **VPS OVH** (uvicorn + systemd + nginx `/bi/`) + **logging** delle domande dei visitatori.
- [ ] Pagina landing: problema → soluzione → sicurezza → demo → prezzi.
- [ ] Prepara il **kit compliance** (DPA, one-pager sicurezza) e **6 slide + listino**.
- [ ] Scegli **1 gestionale/DB target** e **1 cliente pilota** (commerciale, in parallelo).
- [ ] L'onboarding su misura (§6 Fase 2) parte **solo su richiesta di un cliente reale**.

---

*Documento di lavoro interno. Revisione 4 — 2026-08-31.*
*Rev. 2: provider LLM (Gemini demo / Vertex AI UE prod, con avviso su AI Studio tier gratuito), build-vs-buy deciso (custom lean), DB demo e motore realizzati, strategia demo-first.*
*Rev. 3: allineato il documento cliente-facing (`cliente.md`) al piano — claim di latenza "pochi secondi" (non "3 secondi"), due modalità di collegamento (accesso diretto / sincronizzazione periodica con latenza dichiarata), masking PII e isolamento per cliente nel kit sicurezza, timeline di attivazione realistica con settimana di UAT, perimetro DB ristretto (no "qualsiasi gestionale").*
*Rev. 4: aggiunto il **secondo verticale e-commerce self-hosted** (§2.1) come nuovo cuneo che riusa l'architettura senza modifiche al backend; realizzato il dataset demo "Nuvola Shop" (schema/seed/viste `ai_bi_*`/glossario/12 domande d'oro validate). Restano: backend parametrizzato per verticale (`VERTICAL=acme|ecom`), toggle "Gestionale / E-commerce" nel widget, eval live sul nuovo set. Shopify e attribution pubblicitaria esplicitamente fuori dalla v1 e-commerce.*
