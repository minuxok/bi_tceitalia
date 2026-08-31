-- =====================================================================
-- LAYER SEMANTICO - viste curate "ai_bi_*"  (verticale E-COMMERCE, Nuvola Shop)
--
-- Sono gli UNICI oggetti che il motore Text-to-SQL puo' interrogare.
-- Il validatore del backend accetta solo nomi che iniziano con "ai_bi_".
--
-- Principi:
--   * nomi parlanti, join gia' risolti, stati normalizzati in italiano;
--   * campi calcolati pronti (ricavo_netto, margine, conversion_rate_pct);
--   * NESSUNA PII (email fuori da qui);
--   * prezzi grezzi IVA INCLUSA -> qui esposti sia lordo sia netto (imponibile);
--   * date relative ancorate a ai_bi_meta.data_riferimento (non a "now"),
--     cosi' la demo e' deterministica e gli screenshot restano validi.
--
-- "Venduto reale" = ordini con stato diverso da 'annullato' e 'in_attesa'.
-- Gli ordini 'rimborsato' RESTANO nel venduto: il rimborso e' tracciato
-- separatamente in ai_bi_resi (fatturato lordo vs fatturato netto resi).
-- =====================================================================

DROP VIEW  IF EXISTS ai_bi_vendite;
DROP VIEW  IF EXISTS ai_bi_ordini;
DROP VIEW  IF EXISTS ai_bi_clienti;
DROP VIEW  IF EXISTS ai_bi_resi;
DROP VIEW  IF EXISTS ai_bi_prodotti;
DROP VIEW  IF EXISTS ai_bi_traffico;
DROP TABLE IF EXISTS ai_bi_meta;

-- Data di riferimento del dataset demo: "oggi" per tutte le viste.
CREATE TABLE ai_bi_meta (data_riferimento TEXT NOT NULL);
INSERT INTO ai_bi_meta (data_riferimento) VALUES ('2026-08-27');

-- ---------------------------------------------------------------------
-- ai_bi_vendite : una riga per riga d'ordine (grana di dettaglio).
-- Base per fatturato, margine, quantita' per prodotto, categoria,
-- canale (sorgente), dispositivo, regione e tempo. Esclude ordini
-- annullati e in attesa di pagamento.
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
    o.ora                                  AS ora,
    c.id                                   AS cliente_id,
    c.nome                                 AS cliente,
    o.sped_provincia                       AS provincia,
    o.sped_regione                         AS regione,
    o.sorgente                             AS sorgente,
    o.dispositivo                          AS dispositivo,
    o.metodo_pagamento                     AS metodo_pagamento,
    o.coupon                               AS coupon,
    p.id                                   AS prodotto_id,
    p.sku                                  AS sku,
    p.nome                                 AS prodotto,
    p.categoria                            AS categoria_prodotto,
    p.genere                               AS genere_prodotto,
    r.quantita                             AS quantita,
    r.prezzo_unitario                      AS prezzo_unitario,
    ROUND(r.quantita * r.prezzo_unitario, 2)                       AS ricavo_lordo,
    ROUND(r.quantita * r.prezzo_unitario / 1.22, 2)               AS ricavo_netto,
    ROUND(r.quantita * p.costo, 2)                                AS costo,
    ROUND(r.quantita * r.prezzo_unitario / 1.22 - r.quantita * p.costo, 2) AS margine,
    CASE o.stato
        WHEN 'in_attesa'     THEN 'In attesa'
        WHEN 'pagato'        THEN 'Pagato'
        WHEN 'in_lavorazione' THEN 'In lavorazione'
        WHEN 'spedito'       THEN 'Spedito'
        WHEN 'consegnato'    THEN 'Consegnato'
        WHEN 'annullato'     THEN 'Annullato'
        WHEN 'rimborsato'    THEN 'Rimborsato'
        ELSE o.stato
    END                                    AS stato_ordine
FROM righe_ordine r
JOIN ordini   o ON o.id = r.ordine_id
JOIN clienti  c ON c.id = o.cliente_id
JOIN prodotti p ON p.id = r.prodotto_id
WHERE o.stato NOT IN ('annullato', 'in_attesa');

-- ---------------------------------------------------------------------
-- ai_bi_ordini : una riga per ordine, con totali gia' calcolati.
-- tipo_cliente = 'Nuovo' se e' il primo ordine valido del cliente,
-- altrimenti 'Di ritorno'. Utile per fatturato da nuovi vs ricorrenti.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_ordini AS
SELECT
    o.id                       AS ordine_id,
    o.numero                   AS numero_ordine,
    o.data_ordine              AS data_ordine,
    CAST(strftime('%Y', o.data_ordine) AS INTEGER) AS anno,
    CAST(strftime('%m', o.data_ordine) AS INTEGER) AS mese,
    strftime('%Y-%m', o.data_ordine) AS anno_mese,
    o.ora                      AS ora,
    CASE
        WHEN o.ora BETWEEN 0 AND 6  THEN 'Notte'
        WHEN o.ora BETWEEN 7 AND 12 THEN 'Mattina'
        WHEN o.ora BETWEEN 13 AND 18 THEN 'Pomeriggio'
        ELSE 'Sera'
    END                        AS fascia_oraria,
    o.cliente_id               AS cliente_id,
    c.nome                     AS cliente,
    o.sped_provincia           AS provincia,
    o.sped_regione             AS regione,
    o.sorgente                 AS sorgente,
    o.dispositivo              AS dispositivo,
    o.metodo_pagamento         AS metodo_pagamento,
    o.coupon                   AS coupon,
    CASE WHEN o.coupon IS NOT NULL THEN 1 ELSE 0 END AS con_coupon,
    CASE o.stato
        WHEN 'in_attesa'      THEN 'In attesa'
        WHEN 'pagato'         THEN 'Pagato'
        WHEN 'in_lavorazione' THEN 'In lavorazione'
        WHEN 'spedito'        THEN 'Spedito'
        WHEN 'consegnato'     THEN 'Consegnato'
        WHEN 'annullato'      THEN 'Annullato'
        WHEN 'rimborsato'     THEN 'Rimborsato'
        ELSE o.stato
    END                        AS stato_ordine,
    CASE WHEN o.id = (
        SELECT o2.id FROM ordini o2
        WHERE o2.cliente_id = o.cliente_id
          AND o2.stato NOT IN ('annullato', 'in_attesa')
        ORDER BY o2.data_ordine, o2.id LIMIT 1
    ) THEN 'Nuovo' ELSE 'Di ritorno' END AS tipo_cliente,
    (SELECT COALESCE(SUM(r.quantita), 0) FROM righe_ordine r WHERE r.ordine_id = o.id) AS n_articoli,
    (SELECT COUNT(*) FROM righe_ordine r WHERE r.ordine_id = o.id)                     AS n_righe,
    COALESCE((SELECT ROUND(SUM(r.quantita * r.prezzo_unitario), 2)
              FROM righe_ordine r WHERE r.ordine_id = o.id), 0)      AS valore_merce_lordo,
    COALESCE((SELECT ROUND(SUM(r.quantita * r.prezzo_unitario) / 1.22, 2)
              FROM righe_ordine r WHERE r.ordine_id = o.id), 0)      AS valore_merce_netto,
    o.sconto_totale            AS sconto_coupon,
    o.spedizione_costo         AS spedizione_costo,
    COALESCE((SELECT ROUND(SUM(r.quantita * r.prezzo_unitario), 2)
              FROM righe_ordine r WHERE r.ordine_id = o.id), 0)
        - o.sconto_totale + o.spedizione_costo                       AS totale_ordine,
    o.data_spedizione          AS data_spedizione,
    o.data_consegna            AS data_consegna,
    CASE WHEN o.data_consegna IS NOT NULL
         THEN CAST(julianday(o.data_consegna) - julianday(o.data_ordine) AS INTEGER)
    END                        AS giorni_evasione
FROM ordini o
JOIN clienti c ON c.id = o.cliente_id
WHERE o.stato NOT IN ('annullato', 'in_attesa');

-- ---------------------------------------------------------------------
-- ai_bi_clienti : una riga per cliente registrato, con metriche di ciclo di vita.
-- speso_* = valore merce lordo (IVA inclusa) degli ordini validi, NON al netto dei resi.
-- stato_cliente: 'Mai acquistato' | 'Attivo' (<=180 gg) | 'A rischio' (181-365) | 'Perso' (>365).
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_clienti AS
WITH rif AS (SELECT data_riferimento AS d FROM ai_bi_meta),
ord AS (
    SELECT o.cliente_id,
           o.data_ordine,
           (SELECT SUM(r.quantita * r.prezzo_unitario)
            FROM righe_ordine r WHERE r.ordine_id = o.id) AS lordo
    FROM ordini o
    WHERE o.stato NOT IN ('annullato', 'in_attesa')
)
SELECT
    c.id                       AS cliente_id,
    c.nome                     AS cliente,
    c.citta                    AS citta,
    c.provincia                AS provincia,
    c.regione                  AS regione,
    c.canale_acquisizione      AS canale_acquisizione,
    CASE WHEN c.newsletter = 1 THEN 'Iscritto' ELSE 'Non iscritto' END AS newsletter,
    c.data_registrazione       AS data_registrazione,
    MIN(ord.data_ordine)       AS primo_ordine,
    MAX(ord.data_ordine)       AS ultimo_ordine,
    COUNT(ord.data_ordine)     AS num_ordini,
    COALESCE(SUM(CASE WHEN ord.data_ordine >= date((SELECT d FROM rif), '-12 months')
                      THEN 1 END), 0)                              AS num_ordini_12m,
    COALESCE(ROUND(SUM(ord.lordo), 2), 0)                          AS speso_totale,
    COALESCE(ROUND(SUM(CASE WHEN ord.data_ordine >= date((SELECT d FROM rif), '-12 months')
                            THEN ord.lordo END), 2), 0)            AS speso_12m,
    COALESCE(ROUND(SUM(ord.lordo) / NULLIF(COUNT(ord.data_ordine), 0), 2), 0) AS valore_medio_ordine,
    CASE WHEN MAX(ord.data_ordine) IS NULL THEN NULL
         ELSE CAST(julianday((SELECT d FROM rif)) - julianday(MAX(ord.data_ordine)) AS INTEGER)
    END                        AS giorni_da_ultimo_ordine,
    CASE WHEN COUNT(ord.data_ordine) >= 2 THEN 1 ELSE 0 END        AS ricorrente,
    CASE
        WHEN MAX(ord.data_ordine) IS NULL THEN 'Mai acquistato'
        WHEN MAX(ord.data_ordine) >= date((SELECT d FROM rif), '-180 days') THEN 'Attivo'
        WHEN MAX(ord.data_ordine) >= date((SELECT d FROM rif), '-365 days') THEN 'A rischio'
        ELSE 'Perso'
    END                        AS stato_cliente
FROM clienti c
LEFT JOIN ord ON ord.cliente_id = c.id
GROUP BY c.id;

-- ---------------------------------------------------------------------
-- ai_bi_resi : una riga per prodotto reso.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_resi AS
SELECT
    re.id                      AS reso_id,
    re.ordine_id               AS ordine_id,
    o.numero                   AS numero_ordine,
    re.data_reso               AS data_reso,
    CAST(strftime('%Y', re.data_reso) AS INTEGER) AS anno,
    CAST(strftime('%m', re.data_reso) AS INTEGER) AS mese,
    strftime('%Y-%m', re.data_reso) AS anno_mese,
    o.cliente_id               AS cliente_id,
    c.nome                     AS cliente,
    o.sorgente                 AS sorgente,
    o.sped_regione             AS regione,
    p.id                       AS prodotto_id,
    p.nome                     AS prodotto,
    p.categoria                AS categoria_prodotto,
    p.genere                   AS genere_prodotto,
    re.quantita                AS quantita,
    re.importo_rimborsato      AS importo_rimborsato,
    ROUND(re.importo_rimborsato / 1.22, 2) AS importo_rimborsato_netto,
    re.motivo                  AS motivo,
    CASE WHEN o.data_consegna IS NOT NULL
         THEN CAST(julianday(re.data_reso) - julianday(o.data_consegna) AS INTEGER)
    END                        AS giorni_dopo_consegna
FROM resi re
JOIN ordini   o ON o.id = re.ordine_id
JOIN clienti  c ON c.id = o.cliente_id
JOIN prodotti p ON p.id = re.prodotto_id;

-- ---------------------------------------------------------------------
-- ai_bi_prodotti : una riga per prodotto, con performance ultimi 12 mesi.
-- quantita_12m = 0 -> prodotto fermo (invenduto nell'ultimo anno).
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
),
res AS (
    SELECT prodotto_id, SUM(quantita) AS qta_resa
    FROM ai_bi_resi
    WHERE data_reso >= date((SELECT d FROM rif), '-12 months')
    GROUP BY prodotto_id
)
SELECT
    p.id                       AS prodotto_id,
    p.sku                      AS sku,
    p.nome                     AS prodotto,
    p.categoria                AS categoria_prodotto,
    p.genere                   AS genere_prodotto,
    p.prezzo                   AS prezzo_listino,
    p.costo                    AS costo_unitario,
    ROUND((p.prezzo / 1.22 - p.costo) * 100.0 / NULLIF(p.prezzo / 1.22, 0), 1) AS margine_pct,
    CASE WHEN p.attivo = 1 THEN 'attivo' ELSE 'non attivo' END AS stato_prodotto,
    COALESCE(v.qta, 0)         AS quantita_12m,
    COALESCE(res.qta_resa, 0)  AS quantita_resa_12m,
    ROUND(COALESCE(res.qta_resa, 0) * 100.0 / NULLIF(v.qta, 0), 1) AS tasso_reso_pct,
    COALESCE(ROUND(v.ricavo, 2), 0) AS fatturato_12m,
    COALESCE(v.ordini, 0)      AS num_ordini_12m,
    v.ultima_vendita           AS ultima_vendita
FROM prodotti p
LEFT JOIN v   ON v.prodotto_id = p.id
LEFT JOIN res ON res.prodotto_id = p.id;

-- ---------------------------------------------------------------------
-- ai_bi_traffico : una riga per (giorno, canale) di acquisizione.
-- Unisce le sessioni al numero di ordini validi con quella sorgente
-- in quel giorno -> conversion rate e ricavo per sessione.
-- ---------------------------------------------------------------------
CREATE VIEW ai_bi_traffico AS
WITH ord_giorno AS (
    SELECT o.data_ordine AS d, o.sorgente AS canale,
           COUNT(*) AS n_ordini,
           SUM((SELECT SUM(r.quantita * r.prezzo_unitario) / 1.22
                FROM righe_ordine r WHERE r.ordine_id = o.id)) AS ricavo_netto
    FROM ordini o
    WHERE o.stato NOT IN ('annullato', 'in_attesa')
    GROUP BY o.data_ordine, o.sorgente
)
SELECT
    s.data                     AS data,
    CAST(strftime('%Y', s.data) AS INTEGER) AS anno,
    CAST(strftime('%m', s.data) AS INTEGER) AS mese,
    strftime('%Y-%m', s.data)  AS anno_mese,
    s.canale                   AS canale,
    s.sessioni                 AS sessioni,
    s.utenti                   AS utenti,
    s.aggiunte_carrello        AS aggiunte_carrello,
    s.checkout_avviati         AS checkout_avviati,
    COALESCE(og.n_ordini, 0)   AS ordini,
    COALESCE(ROUND(og.ricavo_netto, 2), 0) AS ricavo_netto,
    ROUND(COALESCE(og.n_ordini, 0) * 100.0 / NULLIF(s.sessioni, 0), 2) AS conversion_rate_pct,
    ROUND(COALESCE(og.ricavo_netto, 0) / NULLIF(s.sessioni, 0), 2)     AS ricavo_per_sessione
FROM sessioni_giorno s
LEFT JOIN ord_giorno og ON og.d = s.data AND og.canale = s.canale;
