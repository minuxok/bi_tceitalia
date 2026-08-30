# L'Assistente AI per il Tuo Gestionale Aziendale

> **Trasforma i dati del tuo ERP o CRM in un collega virtuale che risponde alle tue domande in italiano semplice. In sola lettura, in totale sicurezza, senza cambiare il software che già usi.**

---

## 🎯 Cos'è e Cosa Fa il Prodotto

Il nostro **Assistente di Conversational BI** è un software di intelligenza artificiale che si collega al tuo gestionale aziendale (ERP, CRM o gestionale custom con database accessibile — SQL Server, PostgreSQL, MySQL… — oppure con API/export documentati) e ti permette di interrogare i tuoi dati semplicemente **scrivendo una domanda in italiano**.

Elimina passaggi intermedi, formule Excel complesse e attese dall'ufficio IT: ottieni risposte in pochi secondi, **verificabili riga per riga** e visive, basate sui dati del tuo sistema.

### 💡 Esempio Pratico: Trasparenza a 360°

> **Tu chiedi:** *"Quali sono stati i 5 clienti con maggior fatturato nell'ultimo trimestre? Mostrami anche un grafico a barre."*
>
> **L'AI risponde in pochi secondi con:**
>
> 1. 📝 **Spiegazione in italiano**: *"Ho sommato gli importi delle fatture saldate tra ottobre e dicembre, raggruppando per cliente e ordinando dal fatturato più alto…"*
> 2. 📊 **Grafico & Tabella**: i 5 clienti ordinati per fatturato, con grafico a barre.
> 3. 🔍 **Drill-down (vedi righe sorgente)**: un click per aprire il dettaglio delle singole righe di documento da cui è tratto il risultato.
> 4. ⚙️ **Query in chiaro**: puoi vedere esattamente come l'AI ha calcolato il numero. Zero effetto "scatola nera".

---

## 🛑 Il Problema che Risolviamo

Oggi in moltissime PMI il tempo prezioso di manager e collaboratori viene sprecato così:

- **Export continui su CSV / Excel** anche per analisi banali.
- **File Excel pesanti e complessi** che rischiano di rompersi, sovrascriversi o contenere errori di calcolo.
- **Colli di bottiglia e attesa**: dipendenza dall'ufficio IT o dai consulenti esterni per ogni nuovo report.
- **Decisioni ritardate o "a sensazione"**: perché estrarre e verificare i numeri richiede troppo tempo.

### ✨ La Soluzione

Chiedi quello che ti serve quando ti serve — durante una riunione o una trattativa — e ottieni un numero che puoi controllare in pochi secondi.

---

## ⚙️ Come Funziona (in breve, per l'IT)

1. **Connettore in sola lettura**: si collega al database o alle API del gestionale con un'utenza dedicata a permessi minimi (solo `SELECT`).
2. **Layer semantico**: un dizionario che descrive tabelle, viste e metriche aziendali nel linguaggio del tuo settore. L'AI lavora su questo layer, non "a caso" sullo schema grezzo.
3. **Generazione della query**: il modello linguistico traduce la domanda in italiano in una query SQL.
4. **Motore di sicurezza**: ogni query generata viene validata *prima* dell'esecuzione — solo sintassi `SELECT`, blocco di qualsiasi comando di modifica, timeout, limite massimo di righe e accesso consentito solo alle viste concordate.
5. **Esecuzione e risposta**: la query viene eseguita in sola lettura; il risultato torna come spiegazione in italiano + tabella + grafico, con accesso alle righe sorgente.

**Due modalità di collegamento** (scelte in fase di assessment, in base alla tua infrastruttura):

- **Accesso diretto (dati in tempo reale)**: quando il database del gestionale è raggiungibile in sola lettura. L'assistente lavora sempre sul dato aggiornato all'istante.
- **Sincronizzazione periodica**: quando il gestionale espone solo API o export, i dati vengono copiati a intervalli regolari in un ambiente isolato dedicato a te. In questo caso i dati non sono in tempo reale e la frequenza di aggiornamento (es. ogni ora) viene dichiarata esplicitamente.

---

## 🔒 Sicurezza, Privacy e Conformità (kit pronto per DPO / IT)

I dati aziendali sono la risorsa più critica. L'architettura è costruita con standard di sicurezza enterprise.

- **Accesso in sola lettura**: l'AI opera esclusivamente con permessi di soli comandi `SELECT`, e solo sulle viste concordate insieme a te — non sulle tabelle grezze. Non può modificare, cancellare dati o bloccare il gestionale.
- **Motore di validazione delle query**: ogni istruzione generata dall'AI passa da un controllo automatico (whitelist sintattica, blocco dei comandi non-`SELECT`, timeout, limite righe, accesso alle sole viste autorizzate) prima di essere eseguita.
- **Nessun impatto sul gestionale**: il software attuale (on-premise o cloud) continua a funzionare esattamente come prima, senza modifiche strutturali. Quando il gestionale espone solo API/export, si lavora su una copia sincronizzata in un ambiente isolato, senza alcun carico aggiuntivo sul sistema di produzione.
- **Mascheramento dei dati personali**: nelle viste in cui non servono, i campi personali (email, telefono, codice fiscale, IBAN) vengono mascherati e non arrivano mai al modello.
- **Architettura di connessione sicura**: nella maggior parte delle infrastrutture standard, il connettore installato presso di te apre una connessione cifrata **esclusivamente in uscita** (tunnel TLS), senza richiedere l'apertura di porte in ingresso sul firewall aziendale. L'architettura viene comunque valutata e verificata caso per caso.
- **Isolamento per cliente**: i dati di ogni azienda risiedono in ambienti separati, con credenziali separate. Nessun dato è condiviso tra clienti.
- **Dati in Europa (GDPR & AI Act)**: in produzione, infrastruttura e modelli sono ospitati esclusivamente in data center UE. È disponibile un accordo DPA (Art. 28 GDPR) già pronto, con elenco dei sub-responsabili.
- **Zero retention e nessun training**: i dati non vengono conservati né utilizzati per addestrare i modelli. Restano al 100% di proprietà esclusiva del cliente; su richiesta, export completo e cancellazione.

---

## ✅ Limiti e Controllo Qualità (trasparenza)

Nessun sistema di AI è infallibile. Ecco come manteniamo i risultati affidabili:

- **Glossario semantico condiviso**: definiamo insieme cosa significano i termini aziendali (*fatturato netto*, *cliente attivo*, *margine*), così l'AI usa sempre le stesse regole di calcolo.
- **Ogni numero è verificabile**: la query è visibile e le righe sorgente sono a un click. Non chiediamo un atto di fede.
- **Domande fuori perimetro**: se una richiesta è ambigua o non copribile con i dati disponibili, l'assistente lo dichiara invece di "inventare".
- **Workflow con azioni**: qualsiasi automazione che produce un effetto verso l'esterno (es. email a clienti) passa sempre da validazione umana prima dell'invio.

---

## 💬 Cosa Puoi Chiedere all'Assistente

Alcuni esempi pratici divisi per reparto.

### 📈 Direzione Commerciale e Vendite

- *"Mostrami l'andamento del fatturato mese per mese, confrontando l'anno in corso con l'anno precedente."*
- *"Quali prodotti hanno generato il margine di contribuzione più alto nell'ultimo mese?"*
- *"Elenca i clienti attivi che non effettuano un ordine da più di 90 giorni."*

### 💰 Amministrazione, Finanza e Controllo

- *"Qual è il totale dello scaduto da incassare, diviso per cliente e per fascia di ritardo?"*
- *"Quali fatture sopra i 5.000 € sono in ritardo di pagamento oltre 30 giorni?"*

### 📦 Acquisti, Logistica e Magazzino

- *"Quali articoli a magazzino sono attualmente sotto la scorta minima di sicurezza?"*
- *"Quanti ordini d'acquisto sono in attesa di consegna dai fornitori questo mese?"*

---

## 🗺️ Canali di Accesso e Sviluppi

**Disponibile oggi**

- 🌐 **Widget web riservato**: accessibile via browser da PC, tablet e smartphone con credenziali aziendali. La fattibilità tecnica e le modalità d'accesso vengono definite caso per caso in base alla disponibilità di database / API.

**Sul piano di sviluppo (attivabile su richiesta nei progetti dedicati)**

- 💬 **Integrazione chat (Microsoft Teams / Slack)**: porre domande all'assistente direttamente dai canali di comunicazione già in uso in azienda.
- ✉️ **Workflow di re-engagement semiautomatici**: l'AI individua i clienti inattivi e predispone bozze di email personalizzate (sconti dedicati, prodotti correlati agli acquisti storici). L'invio avviene sempre dopo validazione umana.

---

## 🧪 Vuoi Provare Senza Rischi? Il Pacchetto POC (Proof of Concept)

Per far toccare con mano il valore del servizio senza impegnare l'azienda in contratti a lungo termine:

- 📌 **Obiettivo**: automatizziamo **3 report aziendali ricorrenti** scelti da voi.
- ⏱️ **Durata**: 3–4 settimane di prova sul vostro gestionale.
- 👥 **Utenti**: fino a 3 utenti del vostro team.
- 💶 **Investimento**: prezzo fisso contenuto, interamente scomputabile dal costo di attivazione finale in caso di conferma.

---

## 📋 I Passi per l'Attivazione

1. **Discovery & Demo (30 min)**: verifichiamo il gestionale in uso, il tipo di accesso ai dati e definiamo le risposte prioritarie da ottenere.
2. **Setup & Glossario Semantico (1–2 settimane)**: installiamo il connettore sicuro, prepariamo le viste dati e insegniamo all'AI il "gergo" specifico del tuo settore (es. cosa si intende per *fatturato netto*, *cliente attivo*, *margine*). In questa fase misuriamo l'accuratezza su un set di domande concordate, con una soglia minima prima del go-live.
3. **Test con il tuo team (1 settimana)**: 3–5 utenti reali usano l'assistente sul lavoro quotidiano e raccogliamo i feedback per l'ultima messa a punto.
4. **Go-Live e Formazione (1 ora)**: breve sessione formativa per il team, cheat sheet delle domande e operatività a regime.

---

📞 **Vuoi vedere l'assistente al lavoro sui dati del tuo settore?**
Contattaci per prenotare una dimostrazione dedicata di 15 minuti.
