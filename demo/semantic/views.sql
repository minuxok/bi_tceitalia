-- =====================================================================
-- LAYER SEMANTICO - viste curate "ai_bi_*"
--
-- Sono gli UNICI oggetti che il motore Text-to-SQL puo' interrogare.
-- Il validatore del backend accetta solo nomi che iniziano con "ai_bi_".
--
-- Principi:
--   * nomi parlanti, join gia' risolti, stati normalizzati in italiano;
--   * campi calcolati pronti (ricavo_netto, margine, giorni_ritardo);
--   * NESSUNA PII (email, telefono, partita IVA fuori da qui);
--   * date relative ancorate a ai_bi_meta.data_riferimento (non a "now"),
--     cosi' la demo e' deterministica e gli screenshot restano validi.
-- =====================================================================

DROP VIEW  IF EXISTS ai_bi_vendite;
DROP VIEW  IF EXISTS ai_bi_ordini;
DROP VIEW  IF EXISTS ai_bi_clienti;
DROP VIEW  IF EXISTS ai_bi_scaduto;
DROP VIEW  IF EXISTS ai_bi_prodotti;
DROP VIEW  IF EXISTS ai_bi_agenti;
DROP TABLE IF EXISTS ai_bi_meta;

-- Data di riferimento del dataset demo: "oggi" per tutte le viste.
CREATE TABLE ai_bi_meta (data_riferimento TEXT NOT NULL);
INSERT INTO ai_bi_meta (data_riferimento) VALUES ('2026-08-27');

-- ---------------------------------------------------------------------
-- ai_bi_vendite : una riga per riga d'ordine (grana di dettaglio).
-- Esclude ordini in bozza e annullati -> rappresenta il venduto reale.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_vendite AS
SELECT
    r.id                                   AS riga_id,
    o.id                                   AS ordine_id,
    o.numero                               AS numero_ordine,
    o.data_ordine                          AS data_ordine,
    CAST(strftime('%Y', o.data_ordine) AS INTEGER) AS anno,
    CAST(strftime('%m', o.data_ordine) AS INTEGER) AS mese,
    strftime('%Y-%m', o.data_ordine)       AS anno_mese,
    o.canale                               AS canale,
    c.id                                   AS cliente_id,
    c.ragione_sociale                      AS cliente,
    c.citta                                AS citta,
    c.provincia                            AS provincia,
    c.regione                              AS regione,
    c.settore                              AS settore_cliente,
    a.nome                                 AS agente,
    a.area                                 AS area_agente,
    p.id                                   AS prodotto_id,
    p.codice                               AS codice_prodotto,
    p.descrizione                          AS prodotto,
    p.categoria                            AS categoria_prodotto,
    r.quantita                             AS quantita,
    r.prezzo_unitario                      AS prezzo_unitario,
    r.sconto_pct                           AS sconto_pct,
    ROUND(r.quantita * r.prezzo_unitario * (1 - r.sconto_pct / 100.0), 2) AS ricavo_netto,
    ROUND(r.quantita * pr.costo_medio, 2)  AS costo,
    ROUND(r.quantita * r.prezzo_unitario * (1 - r.sconto_pct / 100.0)
          - r.quantita * pr.costo_medio, 2) AS margine,
    o.stato                                AS stato_ordine
FROM righe_ordine r
JOIN ordini   o  ON o.id = r.ordine_id
JOIN clienti  c  ON c.id = o.cliente_id
JOIN prodotti p  ON p.id = r.prodotto_id
JOIN prodotti pr ON pr.id = r.prodotto_id
LEFT JOIN agenti a ON a.id = o.agente_id
WHERE o.stato NOT IN ('bozza', 'annullato');

-- ---------------------------------------------------------------------
-- ai_bi_ordini : una riga per ordine (testata) con totali gia' calcolati.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_ordini AS
SELECT
    o.id                       AS ordine_id,
    o.numero                   AS numero_ordine,
    o.data_ordine              AS data_ordine,
    o.data_consegna_prevista   AS data_consegna_prevista,
    o.data_spedizione          AS data_spedizione,
    o.canale                   AS canale,
    c.id                       AS cliente_id,
    c.ragione_sociale          AS cliente,
    c.provincia                AS provincia,
    c.regione                  AS regione,
    c.settore                  AS settore_cliente,
    a.nome                     AS agente,
    CASE o.stato
        WHEN 'bozza'       THEN 'Bozza'
        WHEN 'confermato'  THEN 'Confermato'
        WHEN 'in_evasione' THEN 'In evasione'
        WHEN 'spedito'     THEN 'Spedito'
        WHEN 'consegnato'  THEN 'Consegnato'
        WHEN 'annullato'   THEN 'Annullato'
        ELSE o.stato
    END                        AS stato_ordine,
    (SELECT COUNT(*) FROM righe_ordine r WHERE r.ordine_id = o.id) AS n_righe,
    COALESCE((SELECT ROUND(SUM(r.quantita * r.prezzo_unitario * (1 - r.sconto_pct/100.0)), 2)
              FROM righe_ordine r WHERE r.ordine_id = o.id), 0)    AS totale_netto,
    COALESCE((SELECT ROUND(SUM(r.quantita * r.prezzo_unitario * (1 - r.sconto_pct/100.0)) * 1.22, 2)
              FROM righe_ordine r WHERE r.ordine_id = o.id), 0)    AS totale_ivato
FROM ordini o
JOIN clienti c ON c.id = o.cliente_id
LEFT JOIN agenti a ON a.id = o.agente_id;

-- ---------------------------------------------------------------------
-- ai_bi_clienti : una riga per cliente, con indicatori di attivita'.
-- "attivo" = almeno un ordine (non bozza/annullato) negli ultimi 6 mesi.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_clienti AS
WITH rif AS (SELECT data_riferimento AS d FROM ai_bi_meta),
ord AS (
    SELECT o.cliente_id,
           o.data_ordine,
           (SELECT SUM(r.quantita * r.prezzo_unitario * (1 - r.sconto_pct/100.0))
            FROM righe_ordine r WHERE r.ordine_id = o.id) AS netto
    FROM ordini o
    WHERE o.stato NOT IN ('bozza', 'annullato')
)
SELECT
    c.id                       AS cliente_id,
    c.ragione_sociale          AS cliente,
    c.citta                    AS citta,
    c.provincia                AS provincia,
    c.regione                  AS regione,
    c.settore                  AS settore_cliente,
    c.canale                   AS canale,
    a.nome                     AS agente,
    c.fido_eur                 AS fido_eur,
    c.data_creazione           AS data_acquisizione,
    MIN(ord.data_ordine)       AS primo_ordine,
    MAX(ord.data_ordine)       AS ultimo_ordine,
    COUNT(ord.data_ordine)     AS num_ordini_totali,
    COALESCE(SUM(CASE WHEN ord.data_ordine >= date((SELECT d FROM rif), '-12 months')
                      THEN ord.netto END), 0)                       AS fatturato_12m,
    COALESCE(SUM(CASE WHEN ord.data_ordine >= date((SELECT d FROM rif), '-12 months')
                      THEN 1 END), 0)                               AS num_ordini_12m,
    CASE WHEN MAX(ord.data_ordine) >= date((SELECT d FROM rif), '-6 months')
         THEN 1 ELSE 0 END                                         AS attivo
FROM clienti c
LEFT JOIN agenti a ON a.id = c.agente_id
LEFT JOIN ord ON ord.cliente_id = c.id
GROUP BY c.id;

-- ---------------------------------------------------------------------
-- ai_bi_scaduto : una riga per scadenza non incassata.
-- "scaduto" = scadenza passata (rispetto a data_riferimento) e non pagata.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_scaduto AS
WITH rif AS (SELECT data_riferimento AS d FROM ai_bi_meta)
SELECT
    pg.id                      AS pagamento_id,
    o.numero                   AS numero_ordine,
    c.id                       AS cliente_id,
    c.ragione_sociale          AS cliente,
    c.provincia                AS provincia,
    c.regione                  AS regione,
    a.nome                     AS agente,
    pg.importo                 AS importo,
    pg.data_scadenza           AS data_scadenza,
    CAST(julianday((SELECT d FROM rif)) - julianday(pg.data_scadenza) AS INTEGER) AS giorni_ritardo,
    CASE
        WHEN julianday((SELECT d FROM rif)) - julianday(pg.data_scadenza) <= 30  THEN '0-30'
        WHEN julianday((SELECT d FROM rif)) - julianday(pg.data_scadenza) <= 60  THEN '31-60'
        WHEN julianday((SELECT d FROM rif)) - julianday(pg.data_scadenza) <= 90  THEN '61-90'
        ELSE 'oltre 90'
    END                        AS fascia_ritardo
FROM pagamenti pg
JOIN ordini  o ON o.id = pg.ordine_id
JOIN clienti c ON c.id = o.cliente_id
LEFT JOIN agenti a ON a.id = o.agente_id
WHERE pg.data_pagamento IS NULL
  AND pg.data_scadenza < (SELECT d FROM rif);

-- ---------------------------------------------------------------------
-- ai_bi_prodotti : una riga per prodotto, con venduto ultimi 12 mesi.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_prodotti AS
WITH rif AS (SELECT data_riferimento AS d FROM ai_bi_meta),
v AS (
    SELECT prodotto_id,
           SUM(quantita)     AS qta,
           SUM(ricavo_netto) AS ricavo,
           COUNT(DISTINCT ordine_id) AS ordini,
           MAX(data_ordine)  AS ultima_vendita
    FROM ai_bi_vendite
    WHERE data_ordine >= date((SELECT d FROM rif), '-12 months')
    GROUP BY prodotto_id
)
SELECT
    p.id                       AS prodotto_id,
    p.codice                   AS codice_prodotto,
    p.descrizione              AS prodotto,
    p.categoria                AS categoria_prodotto,
    p.prezzo_listino           AS prezzo_listino,
    p.costo_medio              AS costo_medio,
    CASE WHEN p.attivo = 1 THEN 'attivo' ELSE 'non attivo' END AS stato_prodotto,
    COALESCE(v.qta, 0)         AS quantita_12m,
    COALESCE(ROUND(v.ricavo, 2), 0) AS fatturato_12m,
    COALESCE(v.ordini, 0)      AS num_ordini_12m,
    v.ultima_vendita           AS ultima_vendita
FROM prodotti p
LEFT JOIN v ON v.prodotto_id = p.id;

-- ---------------------------------------------------------------------
-- ai_bi_agenti : una riga per agente, con portafoglio e fatturato.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_agenti AS
WITH rif AS (SELECT data_riferimento AS d FROM ai_bi_meta)
SELECT
    a.id                       AS agente_id,
    a.nome                     AS agente,
    a.area                     AS area,
    a.data_assunzione          AS data_assunzione,
    CASE WHEN a.attivo = 1 THEN 'attivo' ELSE 'non attivo' END AS stato_agente,
    (SELECT COUNT(*) FROM clienti c WHERE c.agente_id = a.id) AS num_clienti,
    COALESCE((SELECT ROUND(SUM(v.ricavo_netto), 2) FROM ai_bi_vendite v
              WHERE v.agente = a.nome
                AND v.data_ordine >= date((SELECT d FROM rif), '-12 months')), 0) AS fatturato_12m,
    COALESCE((SELECT ROUND(SUM(v.ricavo_netto), 2) FROM ai_bi_vendite v
              WHERE v.agente = a.nome
                AND v.anno = CAST(strftime('%Y', (SELECT d FROM rif)) AS INTEGER)), 0) AS fatturato_ytd
FROM agenti a;
