# Piano di lavoro — Conversational BI per e-commerce (plugin PHP)

Progetto di destinazione: `conversational_bi_php`
Data: 2026-09-21 · Stato: bozza per validazione · Origine: progetto `Conversational_BI` (demo web + backend FastAPI)

---

## 1. Idea in una frase

Plugin **a abbonamento** per WooCommerce, PrestaShop (poi Magento, Shopify app) che permette al negoziante di **fare domande in italiano sui propri dati** (ordini, prodotti, clienti, margini) e ottenere testo + tabella + grafico, tramite un'AI esterna gestita da noi o dal cliente.

## 2. Cosa si riusa dal progetto attuale

| Componente esistente | Uso nel nuovo progetto |
|---|---|
| Backend FastAPI (Text-to-SQL, LiteLLM, validator `ai_bi_*`) | **Gateway AI** unico per tutti i plugin |
| Verticale `ecom` (viste `ai_bi_*`, domande di esempio, eval) | Base delle viste per WooCommerce/PrestaShop |
| Widget React embeddabile (`demo/frontend`) | UI dentro la pagina admin del plugin |
| Landing page + demo pubblica | Vetrina commerciale e demo e-commerce |
| Docker + AEGIS su VPS OVH | Hosting del gateway |

Principio: **una sola pipeline AI (Python), tanti adattatori sottili (PHP)**. Non si riscrive la logica Text-to-SQL in PHP.

---

## 3. Decisioni da prendere (con raccomandazione)

### D1. Modello di abbonamento
Raccomandato: **3 livelli** con quota di domande/mese inclusa.
- **Start**: 1 negozio, quota domande bassa, un solo utente.
- **Pro**: quota più alta, più utenti, storico e report salvati.
- **Agency / Enterprise**: multi-negozio, BYOK o server proprietario, SLA, DPA dedicato.
- Licenza legata al dominio del negozio (`license_key` + verifica periodica al gateway).
- Prezzi da definire dopo aver misurato il costo reale per domanda (vedi §9).

### D2. Chi paga l'API dell'AI: rivendita o chiave del cliente
| | Rivendita (managed) | BYOK (chiave del cliente) |
|---|---|---|
| Onboarding | Immediato, zero attrito | Il cliente deve aprire un account provider |
| Margine | Sì, sul consumo | No, solo canone |
| Rischio costi | **A nostro carico** (serve quota e rate limit) | Nessuno |
| GDPR | Noi siamo responsabili del trattamento AI (DPA con provider EU) | Il cliente è titolare del rapporto col provider |
| Supporto | Un solo stack da controllare | Molti provider, molti errori possibili |

**Raccomandazione: ibrido.** Default = *managed* con quota inclusa nel piano e pacchetti extra acquistabili. BYOK solo per Pro/Agency, con chiave salvata cifrata sul gateway (mai nel DB del negozio in chiaro) e provider limitati a un elenco testato (Gemini/Vertex, OpenAI, Claude).

### D3. Dove gira il codice AI
- **Fase 1 (raccomandata):** tutte le chiamate passano dal **nostro gateway** (anche in BYOK). Motivo: prompt, validator ed eval in un solo posto, log e limiti centralizzati, una sola codebase da mantenere.
- **Fase 3 (opzionale):** modalità "direct" in PHP, che chiama il provider dal plugin, solo se emerge una richiesta forte (clienti che non vogliono alcun intermediario). Richiede portare prompt e validator in PHP: costo alto, da fare solo su domanda.

### D4. Quale AI installare (server proprietario)
- **Default cloud:** Gemini Flash su **Vertex AI EU** (già in uso, ottimo rapporto costo/qualità sul Text-to-SQL). Provider sempre swappable via LiteLLM.
- **Server proprietario (locale o cloud):** *non* offrirlo al lancio. Un modello open decente per Text-to-SQL (classe Qwen2.5-Coder 32B / Llama 3.3 70B) richiede GPU da 24-48 GB VRAM, con costi e gestione superiori al margine di un piano PMI.
- **Se richiesto (Enterprise):** endpoint OpenAI-compatibile (vLLM/Ollama) configurabile nel gateway, con eval obbligatoria prima di promettere la qualità. Da trattare come progetto su misura.
- **Criterio di scelta modello:** eseguire la suite eval ecommerce (domande italiane) su ogni candidato e confrontare accuratezza, latenza, costo per domanda. Non scegliere "a sensazione".

### D5. Modalità di accesso ai dati del negozio
Raccomandato: **query proxy** (approccio C già discusso).
1. Il gateway genera l'SQL sulle viste `ai_bi_*` note.
2. Il plugin riceve l'SQL (richiesta firmata HMAC), lo **rivalida localmente**, lo esegue con un utente DB in sola lettura, applica limiti di righe e tempo, restituisce i risultati.
3. Nessuna porta DB esposta, funziona su hosting condivisi, dati sempre freschi.

Alternativa per negozi molto grandi (lentezza sulle tabelle live): sync periodico verso una copia analitica. Rimandata.

---

## 4. Architettura

```
Browser (admin negozio)
   │  widget React (embed)
   ▼
Plugin PHP (WooCommerce / PrestaShop)
   ├─ Admin UI: pagina "Assistente BI", configurazione, licenza
   ├─ Proxy REST locale  ──►  Gateway CBI (FastAPI, VPS)
   └─ Endpoint "esegui query" (firmato) ◄── SQL generato dal gateway
   │
   ▼
DB del negozio (MySQL/MariaDB) — solo viste ai_bi_*, utente read-only
```

Flusso di una domanda:
1. L'utente scrive la domanda nel widget.
2. Il plugin la inoltra al gateway (licenza + firma).
3. Il gateway costruisce il prompt con lo schema delle viste e chiama l'AI.
4. Il gateway valida l'SQL (whitelist `ai_bi_*`, solo SELECT, LIMIT) e lo rimanda al plugin.
5. Il plugin rivalida, esegue, restituisce righe.
6. Il gateway fa formattare la risposta (testo + tabella + spec grafico) e la manda al widget.

**Struttura del repo `conversational_bi_php`:**
```
/core-php        libreria condivisa (client gateway, firma HMAC, validator SQL, licenza)
/wc-plugin       adattatore WooCommerce (viste HPOS, admin page, REST)
/ps-module       adattatore PrestaShop
/views-sql       definizione viste ai_bi_* per piattaforma (una cartella ciascuna)
/gateway         (submodule o riferimento al backend FastAPI esistente)
/widget          widget React (riuso da demo/frontend), build da includere nei plugin
/demo            demo pubblica ecommerce
/docs            documentazione, DPA, guide installazione
/tests           unit, integrazione, eval Text-to-SQL
```

---

## 5. Viste semantiche (`ai_bi_*`) per piattaforma

Set minimo comune (nomi uguali su tutte le piattaforme, così il prompt resta identico):
`ai_bi_ordini`, `ai_bi_righe_ordine`, `ai_bi_prodotti`, `ai_bi_categorie`, `ai_bi_clienti`, `ai_bi_coupon`, `ai_bi_spedizioni`, `ai_bi_resi`.

- **WooCommerce:** HPOS (`wc_orders`, `wc_order_product_lookup`, `wc_order_stats`) con fallback al sistema legacy `posts/postmeta`; prodotti da `posts` + `wc_product_meta_lookup`.
- **PrestaShop:** `ps_orders`, `ps_order_detail`, `ps_product(_lang)`, `ps_category(_lang)`, `ps_customer`, prefisso tabelle configurabile.
- Prefisso tabelle WordPress/PrestaShop sempre parametrico.
- **Privacy by design:** le viste non espongono email, telefono, indirizzi completi né note. Il cliente appare come id + città/provincia. Opzione "mostra nomi" disattivata di default.
- Le viste vengono create/aggiornate dal plugin all'attivazione e a ogni aggiornamento (migrazioni versionate).

---

## 6. Sicurezza e conformità

- Utente DB read-only dedicato, con `SELECT` solo sulle viste `ai_bi_*` (dove l'hosting lo consente; altrimenti validazione applicativa rigida).
- Doppia validazione SQL (gateway e plugin): solo `SELECT`, whitelist viste, niente funzioni pericolose, niente multi-statement, `LIMIT` forzato, timeout di esecuzione.
- Richieste gateway↔plugin firmate HMAC con timestamp e nonce (anti-replay); TLS obbligatorio.
- Chiavi BYOK cifrate a riposo sul gateway; mai loggate.
- Log delle domande: retention breve e configurabile, nessun dato personale nelle risposte se non abilitato.
- **GDPR:** DPA con il cliente, sub-processor dichiarati (provider AI EU), AI in regione UE senza training sui dati (Vertex EU / Azure OpenAI EU / Bedrock EU). Informativa privacy modello da fornire al negoziante.
- Difese da prompt injection: i contenuti dei dati (nomi prodotto, note) non devono mai poter alterare le istruzioni; l'SQL passa comunque dal validator.
- Rate limit e quota per licenza per proteggere i costi in modalità managed.

---

## 7. Demo e-commerce (richiesta esplicita)

Obiettivo: chi prova la demo capisce **su quali dati** vengono fatte le risposte.

1. **Verticale `ecom` completo** già presente nel selettore della landing: verificare copertura domande di esempio e ampliare le eval con casi tipici del negoziante (top prodotti, margini, clienti ricorrenti, coupon, carrelli/resi, stagionalità).
2. **Pannello "Dati della demo"** accanto (o sotto) alla chat:
   - elenco delle viste `ai_bi_*` con descrizione in italiano;
   - per ogni vista: colonne, tipo, esempio di 5 righe (sola lettura, dati fittizi);
   - conteggi riepilogativi (n. ordini, prodotti, periodo coperto, data di riferimento congelata);
   - link/pulsante "Mostra i dati usati" collegato a ogni risposta, che evidenzia le viste consultate e l'SQL eseguito (per chi vuole approfondire).
3. **Endpoint backend** di sola lettura per esporre catalogo viste + sample (`/demo/schema`, `/demo/sample/{vista}`), con cache e limite di righe.
4. **Suggerimenti di domande** cliccabili, legati ai dati effettivamente presenti (per evitare risposte vuote in demo).
5. Nota chiara "dati fittizi generati a scopo dimostrativo".

## 8. Miglioramento UI: finestra prompt più ampia su desktop (richiesta esplicita)

- Layout a **larghezza fluida** su schermi ≥ 1200 px: contenitore chat fino a ~1100-1280 px (attuale da verificare), con `max-width` in `clamp()`.
- Layout a **due colonne** su desktop largo: chat a sinistra, pannello "Dati della demo" / tabella risultati a destra; una colonna su tablet e mobile.
- Campo di input più alto, multi-riga espandibile, tabelle e grafici che usano tutta la larghezza disponibile.
- Nel plugin: la pagina admin usa tutta l'area contenuti di WordPress/PrestaShop, con modalità "schermo intero".
- Test visivi a 1280, 1440, 1920 e 2560 px, oltre a tablet e mobile.

---

## 9. Economia (da misurare prima di fissare i prezzi)

- **Costo per domanda** = token input (prompt con schema viste) + token output + eventuale seconda chiamata di formattazione. Strumentare il gateway per registrare token e costo per licenza.
- Ridurre i costi: schema compatto delle viste, prompt caching, modello piccolo per classificare/riformulare, cache delle domande identiche, risposta senza 2ª chiamata dove possibile.
- Quote per piano con superamento gestito: blocco morbido, pacchetto extra o passaggio a piano superiore.
- Costi fissi: VPS, monitoraggio, supporto, manutenzione compatibilità con le release di WooCommerce/PrestaShop.
- Pagamenti/licenze: valutare Freemius, Stripe Billing o sistema proprio. Per WordPress.org valutare se il plugin "gratuito + servizio a pagamento" è ammesso con le loro regole di disclosure.

## 10. Distribuzione

- **Fase 1:** download diretto dal nostro sito (zip firmato), nessuna review esterna, aggiornamenti tramite updater proprio.
- **Fase 2:** WordPress.org (versione "lite" con disclosure servizio esterno) e PrestaShop Addons Marketplace, dopo aver stabilizzato prodotto e documentazione.
- Compatibilità dichiarata: versioni minime di PHP (≥ 7.4/8.0), WordPress, WooCommerce (HPOS on/off), PrestaShop 1.7/8/9.

---

## 11. Fasi di lavoro

### Fase 0 — Decisioni e preparazione (1 settimana)
- Validare D1-D5 con questo documento.
- Creare il repo `conversational_bi_php`, struttura cartelle, convenzioni, CI base (PHPStan, PHPCS, PHPUnit).
- Ambiente di test: WordPress + WooCommerce con dati demo, PrestaShop in Docker.
- **Uscita:** decisioni firmate, ambienti pronti.

### Fase 1 — Demo e-commerce migliorata (1-2 settimane)
- Pannello "Dati della demo" + endpoint schema/sample.
- Layout desktop allargato a due colonne.
- Ampliamento eval ecommerce.
- Deploy sulla landing (frontend statico + backend Docker).
- **Uscita:** demo pubblica che mostra chiaramente i dati sottostanti; eval ecommerce verde.

### Fase 2 — Gateway multi-tenant (2 settimane)
- Modello licenza/tenant, API key per licenza, quota e rate limit.
- Firma HMAC e protocollo "query proxy" (generazione SQL → ritorno al plugin).
- Astrazione provider (Gemini/OpenAI/Claude) e supporto BYOK con chiavi cifrate.
- Metering costi/token per tenant, dashboard interna minima.
- **Uscita:** gateway che serve più negozi in isolamento, con contatori di consumo.

### Fase 3 — Plugin WooCommerce MVP (3-4 settimane)
- Core PHP: client gateway, HMAC, validator SQL, licenza.
- Creazione/migrazione viste `ai_bi_*` (HPOS + legacy), utente read-only.
- Wizard di configurazione iniziale: licenza → scelta AI (managed / BYOK) → test connessione → anteprima dati.
- Pagina admin con widget, storico domande, esporta CSV.
- Endpoint firmato di esecuzione query.
- Test: unitari PHP, integrazione su WooCommerce reale, eval end-to-end, test di sicurezza (SQL injection, replay, bypass validator).
- **Uscita:** plugin installabile su un negozio reale pilota, funzionante end-to-end.

### Fase 4 — Pilota e hardening (2-3 settimane)
- 2-3 negozi pilota (anche propri o di conoscenti) su hosting diversi.
- Raccolta feedback, correzione bug, ottimizzazione prompt e costi sui dati reali.
- Documentazione utente, guida installazione, DPA e informativa privacy.
- Pagina commerciale con piani e checkout abbonamento.
- **Uscita:** versione 1.0 vendibile.

### Fase 5 — Modulo PrestaShop (3 settimane)
- Riuso del core PHP; viste PrestaShop; pagina admin Symfony/legacy secondo versione.
- Test su 1.7, 8, 9.
- **Uscita:** modulo installabile e testato.

### Fase 6 — Marketplace e crescita (continuo)
- Sottomissione a WordPress.org e PrestaShop Addons.
- Magento / Shopify (app esterna con OAuth, via API invece di SQL diretto).
- Funzioni avanzate: report programmati via email, alert (es. calo vendite), domande salvate, dashboard fissa.
- Opzione Enterprise: server AI proprietario/locale con endpoint OpenAI-compatibile.

---

## 12. Rischi principali

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Costi AI fuori controllo in modalità managed | Margine negativo | Quote, rate limit, cache, metering dal giorno 1 |
| SQL generato non sicuro o costoso | Sicurezza, performance del negozio | Doppia validazione, utente read-only, timeout, LIMIT |
| Schemi diversi tra installazioni (plugin terzi, campi custom) | Risposte errate | Viste come strato di normalizzazione, diagnostica all'attivazione, test su hosting reali |
| Hosting condiviso lento o con restrizioni | Timeout, viste non creabili | Fallback senza viste (validazione applicativa), timeout gestiti |
| Rifiuto da marketplace | Distribuzione ridotta | Partire da vendita diretta, preparare la disclosure |
| GDPR / dati personali verso AI | Rischio legale | Mascheratura nelle viste, provider EU, DPA, retention corta |
| Manutenzione multipiattaforma | Carico di lavoro | Core condiviso, adattatori sottili, CI su versioni multiple |
| Qualità AI variabile in italiano | Fiducia degli utenti | Eval continua, domande guidate, mostrare SQL/dati usati |

## 13. Criteri di accettazione della v1.0

- Suite eval ecommerce ≥ 90% di risposte corrette (soglia da confermare) sui dati demo e su almeno 2 negozi pilota.
- Nessuna query non-SELECT o fuori whitelist eseguibile (test di penetrazione superati).
- Installazione e configurazione iniziale completabili in meno di 10 minuti da un negoziante non tecnico.
- Costo medio per domanda misurato e compatibile con il prezzo del piano.
- Documentazione, DPA e informativa disponibili.

## 14. Domande aperte

1. Quota di domande e prezzi dei piani: dopo la misura dei costi reali in Fase 2.
2. Il marchio/nome del prodotto per la vendita (es. TCE Italia) e il dominio di distribuzione.
3. Hosting definitivo del gateway: solo VPS OVH attuale o anche un secondo nodo per affidabilità.
4. Livello di supporto promesso (orari, tempi di risposta) per ciascun piano.
5. Se offrire un periodo di prova gratuito con quota limitata.

## 15. Prossimi passi immediati

1. Validare le decisioni D1-D5 (in particolare D2 ibrido e D5 query proxy).
2. Creare il repo `conversational_bi_php` e copiare questo documento in `docs/`.
3. Partire dalla **Fase 1** (demo con pannello dati + layout largo), perché è la più rapida, non dipende dal PHP e valida subito il messaggio commerciale.
