-- =====================================================================
-- Nuvola Shop - Database demo per la Conversational BI (verticale E-COMMERCE)
-- Contesto: e-commerce B2C proprietario (abbigliamento, calzature, accessori),
--           sito su piattaforma tipo WooCommerce.
-- Scopo: dati finti realistici per la demo pubblica sul sito.
--
-- NB: SQLite non ha schemi. Le TABELLE GREZZE stanno qui;
--     le VISTE CURATE (prefisso ai_bi_) stanno in semantic/views_ecom.sql
--     e sono le uniche interrogabili dal motore Text-to-SQL.
--
-- Mapping concettuale WooCommerce (solo indicativo):
--   clienti          ~ wp_users + wc_customer_lookup
--   prodotti         ~ wp_posts(product) + postmeta (prezzo, sku)
--   ordini           ~ wc_orders / wc_order_stats
--   righe_ordine     ~ wc_order_product_lookup
--   resi             ~ rimborsi (refunds) con dettaglio prodotto
--   sessioni_giorno  ~ aggregato analytics (GA4 / statistiche Woo), NON tabella nativa
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS resi;
DROP TABLE IF EXISTS righe_ordine;
DROP TABLE IF EXISTS ordini;
DROP TABLE IF EXISTS sessioni_giorno;
DROP TABLE IF EXISTS prodotti;
DROP TABLE IF EXISTS clienti;

-- ---------------------------------------------------------------------
-- Clienti (account registrati sullo shop)
-- ---------------------------------------------------------------------
CREATE TABLE clienti (
    id                  INTEGER PRIMARY KEY,
    email               TEXT    NOT NULL UNIQUE,     -- PII: mascherata nelle viste
    nome                TEXT    NOT NULL,
    citta               TEXT    NOT NULL,
    provincia           TEXT    NOT NULL,            -- sigla (MI, TO, RM, ...)
    regione             TEXT    NOT NULL,
    data_registrazione  TEXT    NOT NULL,            -- ISO date: creazione account
    canale_acquisizione TEXT    NOT NULL,            -- Organico, Google Ads, Meta Ads, Email, Referral, Diretto
    newsletter          INTEGER NOT NULL DEFAULT 0   -- 1 = iscritto alla newsletter
);

-- ---------------------------------------------------------------------
-- Prodotti / catalogo
-- Prezzi IVA INCLUSA (aliquota unica 22% in questo dataset).
-- costo = costo di acquisto unitario (COGS), IVA esclusa.
-- ---------------------------------------------------------------------
CREATE TABLE prodotti (
    id         INTEGER PRIMARY KEY,
    sku        TEXT    NOT NULL UNIQUE,
    nome       TEXT    NOT NULL,
    categoria  TEXT    NOT NULL,   -- Abbigliamento donna, Abbigliamento uomo, Calzature, Accessori, Sport, Outdoor
    genere     TEXT    NOT NULL,   -- Donna, Uomo, Unisex
    prezzo     REAL    NOT NULL,   -- prezzo di listino corrente, IVA inclusa
    costo      REAL    NOT NULL,   -- costo di acquisto unitario, IVA esclusa
    attivo     INTEGER NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------
-- Ordini (testata)
-- ---------------------------------------------------------------------
CREATE TABLE ordini (
    id               INTEGER PRIMARY KEY,
    numero           TEXT    NOT NULL UNIQUE,        -- es. NV-2026-014532
    cliente_id       INTEGER NOT NULL REFERENCES clienti(id),
    data_ordine      TEXT    NOT NULL,               -- ISO date
    ora              INTEGER NOT NULL,               -- ora del giorno (0-23) in cui e' stato creato
    stato            TEXT    NOT NULL,               -- in_attesa, pagato, in_lavorazione, spedito, consegnato, annullato, rimborsato
    sorgente         TEXT    NOT NULL,               -- canale di acquisizione dell'ordine (stessi valori di clienti.canale_acquisizione)
    dispositivo      TEXT    NOT NULL,               -- Desktop, Mobile, Tablet
    metodo_pagamento TEXT    NOT NULL,               -- Carta, PayPal, Bonifico, Contrassegno
    spedizione_costo REAL    NOT NULL DEFAULT 0,     -- spese di spedizione addebitate, IVA inclusa
    sconto_totale    REAL    NOT NULL DEFAULT 0,     -- sconto da coupon a livello ordine, IVA inclusa
    coupon           TEXT,                           -- codice coupon usato (NULL se assente)
    sped_citta       TEXT    NOT NULL,               -- indirizzo di spedizione
    sped_provincia   TEXT    NOT NULL,
    sped_regione     TEXT    NOT NULL,
    data_spedizione  TEXT,                           -- ISO date (NULL se non ancora spedito)
    data_consegna    TEXT                            -- ISO date (NULL se non ancora consegnato)
);

-- ---------------------------------------------------------------------
-- Righe ordine (dettaglio)
-- prezzo_unitario = prezzo effettivamente pagato per unita', IVA inclusa,
--                   gia' al netto dell'eventuale sconto di riga.
-- ---------------------------------------------------------------------
CREATE TABLE righe_ordine (
    id              INTEGER PRIMARY KEY,
    ordine_id       INTEGER NOT NULL REFERENCES ordini(id),
    prodotto_id     INTEGER NOT NULL REFERENCES prodotti(id),
    quantita        INTEGER NOT NULL,
    prezzo_unitario REAL    NOT NULL,
    sconto_pct      REAL    NOT NULL DEFAULT 0       -- sconto di riga in percentuale (0-100)
);

-- ---------------------------------------------------------------------
-- Resi / rimborsi (una riga per prodotto reso)
-- ---------------------------------------------------------------------
CREATE TABLE resi (
    id                 INTEGER PRIMARY KEY,
    ordine_id          INTEGER NOT NULL REFERENCES ordini(id),
    prodotto_id        INTEGER NOT NULL REFERENCES prodotti(id),
    data_reso          TEXT    NOT NULL,             -- ISO date
    quantita           INTEGER NOT NULL,
    importo_rimborsato REAL    NOT NULL,             -- IVA inclusa
    motivo             TEXT    NOT NULL              -- Taglia errata, Difettoso, Non conforme, Ripensamento, Consegna in ritardo
);

-- ---------------------------------------------------------------------
-- Sessioni per giorno e canale (aggregato di traffico)
-- Serve per il conversion rate: ordini / sessioni.
-- ---------------------------------------------------------------------
CREATE TABLE sessioni_giorno (
    data              TEXT    NOT NULL,              -- ISO date
    canale            TEXT    NOT NULL,              -- Organico, Google Ads, Meta Ads, Email, Referral, Diretto
    sessioni          INTEGER NOT NULL,
    utenti            INTEGER NOT NULL,              -- utenti unici
    aggiunte_carrello INTEGER NOT NULL,              -- sessioni con almeno un add-to-cart
    checkout_avviati  INTEGER NOT NULL,              -- sessioni che hanno iniziato il checkout
    PRIMARY KEY (data, canale)
);

CREATE INDEX idx_ordini_cliente  ON ordini(cliente_id);
CREATE INDEX idx_ordini_data     ON ordini(data_ordine);
CREATE INDEX idx_righe_ordine    ON righe_ordine(ordine_id);
CREATE INDEX idx_righe_prodotto  ON righe_ordine(prodotto_id);
CREATE INDEX idx_resi_ordine     ON resi(ordine_id);
CREATE INDEX idx_resi_prodotto   ON resi(prodotto_id);
CREATE INDEX idx_sessioni_data   ON sessioni_giorno(data);
