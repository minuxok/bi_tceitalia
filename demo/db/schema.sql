-- =====================================================================
-- Acme Srl - Database demo per la Conversational BI
-- Contesto: PMI di distribuzione/produzione (arredo e complementi).
-- Scopo: dati finti realistici per la demo pubblica sul sito.
--
-- NB: SQLite non ha schemi. Le TABELLE GREZZE stanno qui;
--     le VISTE CURATE (prefisso ai_bi_) stanno in semantic/views.sql
--     e sono le uniche interrogabili dal motore Text-to-SQL.
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS pagamenti;
DROP TABLE IF EXISTS righe_ordine;
DROP TABLE IF EXISTS ordini;
DROP TABLE IF EXISTS prodotti;
DROP TABLE IF EXISTS clienti;
DROP TABLE IF EXISTS agenti;

-- ---------------------------------------------------------------------
-- Agenti / venditori
-- ---------------------------------------------------------------------
CREATE TABLE agenti (
    id              INTEGER PRIMARY KEY,
    nome            TEXT    NOT NULL,
    area            TEXT    NOT NULL,          -- Nord-Ovest, Nord-Est, Centro, Sud e Isole
    data_assunzione TEXT    NOT NULL,          -- ISO date
    attivo          INTEGER NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------
-- Clienti (aziende B2B)
-- ---------------------------------------------------------------------
CREATE TABLE clienti (
    id                INTEGER PRIMARY KEY,
    ragione_sociale   TEXT    NOT NULL,
    partita_iva       TEXT    NOT NULL UNIQUE,
    citta             TEXT    NOT NULL,
    provincia         TEXT    NOT NULL,        -- sigla (MI, TO, RM, ...)
    regione           TEXT    NOT NULL,
    settore           TEXT    NOT NULL,        -- Retail arredo, Contract, GDO, Ecommerce, Studio progettazione
    canale            TEXT    NOT NULL,        -- Diretto, Agente, Ecommerce
    agente_id         INTEGER REFERENCES agenti(id),
    email             TEXT,                    -- PII: mascherata nelle viste
    telefono          TEXT,                    -- PII: mascherata nelle viste
    fido_eur          REAL    NOT NULL DEFAULT 0,
    data_creazione    TEXT    NOT NULL         -- ISO date: data di acquisizione cliente
);

-- ---------------------------------------------------------------------
-- Prodotti / listino
-- ---------------------------------------------------------------------
CREATE TABLE prodotti (
    id              INTEGER PRIMARY KEY,
    codice          TEXT    NOT NULL UNIQUE,
    descrizione     TEXT    NOT NULL,
    categoria       TEXT    NOT NULL,          -- Sedute, Tavoli, Contenitori, Illuminazione, Complementi, Outdoor
    prezzo_listino  REAL    NOT NULL,
    costo_medio     REAL    NOT NULL,          -- costo di acquisto/produzione unitario
    attivo          INTEGER NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------
-- Ordini (testata)
-- ---------------------------------------------------------------------
CREATE TABLE ordini (
    id                     INTEGER PRIMARY KEY,
    numero                 TEXT    NOT NULL UNIQUE,   -- es. 2025/00123
    cliente_id             INTEGER NOT NULL REFERENCES clienti(id),
    agente_id              INTEGER REFERENCES agenti(id),
    canale                 TEXT    NOT NULL,          -- Diretto, Agente, Ecommerce
    data_ordine            TEXT    NOT NULL,          -- ISO date
    data_consegna_prevista TEXT,                      -- ISO date
    data_spedizione        TEXT,                      -- ISO date (NULL se non spedito)
    stato                  TEXT    NOT NULL,          -- bozza, confermato, in_evasione, spedito, consegnato, annullato
    note                   TEXT
);

-- ---------------------------------------------------------------------
-- Righe ordine (dettaglio)
-- ---------------------------------------------------------------------
CREATE TABLE righe_ordine (
    id              INTEGER PRIMARY KEY,
    ordine_id       INTEGER NOT NULL REFERENCES ordini(id),
    prodotto_id     INTEGER NOT NULL REFERENCES prodotti(id),
    quantita        INTEGER NOT NULL,
    prezzo_unitario REAL    NOT NULL,          -- prezzo effettivo di vendita (netto listino)
    sconto_pct      REAL    NOT NULL DEFAULT 0 -- sconto di riga in percentuale (0-100)
);

-- ---------------------------------------------------------------------
-- Pagamenti / partite (una riga per scadenza)
-- ---------------------------------------------------------------------
CREATE TABLE pagamenti (
    id             INTEGER PRIMARY KEY,
    ordine_id      INTEGER NOT NULL REFERENCES ordini(id),
    importo        REAL    NOT NULL,           -- importo della scadenza (IVA inclusa)
    data_scadenza  TEXT    NOT NULL,           -- ISO date
    data_pagamento TEXT,                       -- ISO date, NULL se non ancora incassato
    stato          TEXT    NOT NULL            -- pagato, aperto, scaduto
);

CREATE INDEX idx_ordini_cliente   ON ordini(cliente_id);
CREATE INDEX idx_ordini_data      ON ordini(data_ordine);
CREATE INDEX idx_righe_ordine     ON righe_ordine(ordine_id);
CREATE INDEX idx_righe_prodotto   ON righe_ordine(prodotto_id);
CREATE INDEX idx_pagamenti_ordine ON pagamenti(ordine_id);
