-- =====================================================================
-- LAYER SEMANTICO - verticale "gest" (gestionale acquisti + preventivi)
-- Sorgente: database REALE c2gest (MariaDB 10.11), utente in sola lettura.
--
-- Queste viste NON vengono create nel database del cliente: il backend
-- Conversational_BI le inietta come CTE (WITH ...) davanti a ogni query
-- generata dall'LLM (opzione "C"). Restano gli UNICI oggetti che il
-- motore Text-to-SQL puo' interrogare: il validatore accetta solo nomi
-- che iniziano con "ai_bi_".
--
-- Principi:
--   * nomi parlanti, join gia' risolti, stati gia' normalizzati;
--   * campi calcolati pronti (margine, giorni_ritardo, quantita_mancante);
--   * i dati sono TUTTI FITTIZI (demo): email, telefono, indirizzo, P.IVA,
--     C.F., IBAN sono esposti nelle viste anagrafiche (clienti, fornitori)
--     perche' utilizzabili nella demo. Le note libere restano fuori.
--   * "oggi" = CURDATE() (connessione dati reali, non dataset congelato).
--     ai_bi_meta espone comunque l'ultima data presente nei dati.
--   * dialetto: MariaDB / MySQL.
--
-- Ordine di definizione = ordine nel WITH: le viste che ne referenziano
-- altre vengono dopo. Nessuna referenzia un'altra al momento (tutte
-- partono dalle tabelle base), ma teniamo ai_bi_meta per prima.
-- =====================================================================

-- ---------------------------------------------------------------------
-- ai_bi_meta : una sola riga. Fino a quando arrivano i dati.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_meta AS
SELECT
    GREATEST(
        COALESCE((SELECT MAX(data_offerta) FROM quotes          WHERE deleted_at IS NULL), '2000-01-01'),
        COALESCE((SELECT MAX(data_ordine)  FROM purchase_orders WHERE deleted_at IS NULL), '2000-01-01')
    )                                                            AS data_riferimento,
    (SELECT COUNT(*) FROM quotes          WHERE deleted_at IS NULL) AS n_preventivi,
    (SELECT COUNT(*) FROM purchase_orders WHERE deleted_at IS NULL) AS n_ordini_fornitore;

-- ---------------------------------------------------------------------
-- ai_bi_clienti : una riga per cliente. Attivita' commerciale = preventivi.
-- "accettato" e' l'unico segnale di vendita in questo gestionale.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_clienti AS
SELECT
    c.id                                                        AS cliente_id,
    c.codice_cliente                                            AS codice_cliente,
    c.ragione_sociale                                           AS cliente,
    c.partita_iva                                               AS partita_iva,
    c.codice_fiscale                                            AS codice_fiscale,
    c.email                                                     AS email,
    c.telefono                                                  AS telefono,
    c.indirizzo                                                 AS indirizzo,
    c.citta                                                     AS citta,
    c.provincia                                                 AS provincia,
    c.cap                                                       AS cap,
    c.paese                                                     AS paese,
    c.attivo                                                    AS attivo,
    COUNT(q.id)                                                 AS num_preventivi,
    COALESCE(SUM(q.stato = 'accettata'), 0)                     AS num_preventivi_accettati,
    MIN(q.data_offerta)                                         AS primo_preventivo,
    MAX(q.data_offerta)                                         AS ultimo_preventivo,
    ROUND(COALESCE(SUM(CASE WHEN q.stato = 'accettata' THEN q.totale_imponibile END), 0), 2) AS valore_accettato,
    ROUND(COALESCE(SUM(CASE WHEN q.stato = 'accettata'
                             AND q.data_offerta >= CURDATE() - INTERVAL 12 MONTH
                            THEN q.totale_imponibile END), 0), 2) AS valore_accettato_12m,
    ROUND(100 * COALESCE(SUM(q.stato = 'accettata'), 0) / NULLIF(COUNT(q.id), 0), 1) AS tasso_accettazione_pct,
    CASE WHEN MAX(q.data_offerta) >= CURDATE() - INTERVAL 6 MONTH THEN 1 ELSE 0 END AS attivo_recente
FROM customers c
LEFT JOIN quotes q ON q.customer_id = c.id AND q.deleted_at IS NULL
WHERE c.deleted_at IS NULL
GROUP BY c.id, c.codice_cliente, c.ragione_sociale, c.partita_iva, c.codice_fiscale,
         c.email, c.telefono, c.indirizzo, c.citta, c.provincia, c.cap, c.paese, c.attivo;

-- ---------------------------------------------------------------------
-- ai_bi_fornitori : una riga per fornitore. Spesa e puntualita' consegne.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_fornitori AS
SELECT
    s.id                                                        AS fornitore_id,
    s.codice_fornitore                                          AS codice_fornitore,
    s.ragione_sociale                                           AS fornitore,
    s.partita_iva                                               AS partita_iva,
    s.codice_fiscale                                            AS codice_fiscale,
    s.email                                                     AS email,
    s.telefono                                                  AS telefono,
    s.indirizzo                                                 AS indirizzo,
    s.citta                                                     AS citta,
    s.provincia                                                 AS provincia,
    s.cap                                                       AS cap,
    s.paese                                                     AS paese,
    s.iban                                                      AS iban,
    s.attivo                                                    AS attivo,
    COUNT(po.id)                                                AS num_ordini,
    MIN(po.data_ordine)                                         AS primo_ordine,
    MAX(po.data_ordine)                                         AS ultimo_ordine,
    ROUND(COALESCE(SUM(po.totale_imponibile), 0), 2)            AS valore_ordinato,
    ROUND(COALESCE(SUM(CASE WHEN po.data_ordine >= CURDATE() - INTERVAL 12 MONTH
                            THEN po.totale_imponibile END), 0), 2) AS valore_ordinato_12m,
    COALESCE(SUM(CASE WHEN po.stato = 'ricevuto'
                       AND po.data_consegna_effettiva > po.data_consegna_prevista
                      THEN 1 ELSE 0 END), 0)                    AS consegne_in_ritardo,
    COALESCE(SUM(po.stato = 'ricevuto'), 0)                     AS consegne_totali,
    ROUND(100 * COALESCE(SUM(CASE WHEN po.stato = 'ricevuto'
                                   AND po.data_consegna_effettiva > po.data_consegna_prevista
                                  THEN 1 ELSE 0 END), 0)
              / NULLIF(SUM(po.stato = 'ricevuto'), 0), 1)       AS pct_consegne_in_ritardo
FROM suppliers s
LEFT JOIN purchase_orders po ON po.supplier_id = s.id AND po.deleted_at IS NULL
WHERE s.deleted_at IS NULL
GROUP BY s.id, s.codice_fornitore, s.ragione_sociale, s.partita_iva, s.codice_fiscale,
         s.email, s.telefono, s.indirizzo, s.citta, s.provincia, s.cap, s.paese, s.iban, s.attivo;

-- ---------------------------------------------------------------------
-- ai_bi_prodotti : una riga per articolo. Catalogo + margine + giacenza
-- + quanto e' stato movimentato negli ultimi 12 mesi (offerte e ordini).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_prodotti AS
SELECT
    p.id                                                        AS prodotto_id,
    p.codice_articolo                                           AS codice_articolo,
    p.nome                                                      AS prodotto,
    p.categoria                                                 AS categoria,
    p.unita_misura                                              AS unita_misura,
    p.prezzo_acquisto                                           AS prezzo_acquisto,
    p.prezzo_vendita                                            AS prezzo_vendita,
    ROUND(p.prezzo_vendita - p.prezzo_acquisto, 2)              AS margine_unitario,
    ROUND(100 * (p.prezzo_vendita - p.prezzo_acquisto) / NULLIF(p.prezzo_vendita, 0), 1) AS margine_pct,
    p.giacenza                                                  AS giacenza,
    p.giacenza_minima                                           AS giacenza_minima,
    CASE WHEN p.giacenza < p.giacenza_minima THEN 1 ELSE 0 END  AS sotto_scorta,
    p.is_composto                                               AS is_composto,
    p.attivo                                                    AS attivo,
    COALESCE(qi.quantita_offerta_12m, 0)                        AS quantita_offerta_12m,
    COALESCE(poi.quantita_ordinata_12m, 0)                      AS quantita_ordinata_12m,
    qi.ultima_offerta                                           AS ultima_offerta,
    poi.ultimo_ordine                                           AS ultimo_ordine
FROM products p
LEFT JOIN (
    SELECT qi.product_id,
           SUM(CASE WHEN q.data_offerta >= CURDATE() - INTERVAL 12 MONTH THEN qi.quantita END) AS quantita_offerta_12m,
           MAX(q.data_offerta)                                                                 AS ultima_offerta
    FROM quote_items qi
    JOIN quotes q ON q.id = qi.quote_id AND q.deleted_at IS NULL
    GROUP BY qi.product_id
) qi ON qi.product_id = p.id
LEFT JOIN (
    SELECT poi.product_id,
           SUM(CASE WHEN po.data_ordine >= CURDATE() - INTERVAL 12 MONTH THEN poi.quantita_ordinata END) AS quantita_ordinata_12m,
           MAX(po.data_ordine)                                                                            AS ultimo_ordine
    FROM purchase_order_items poi
    JOIN purchase_orders po ON po.id = poi.purchase_order_id AND po.deleted_at IS NULL
    GROUP BY poi.product_id
) poi ON poi.product_id = p.id
WHERE p.deleted_at IS NULL;

-- ---------------------------------------------------------------------
-- ai_bi_preventivi : una riga per preventivo (testata). Valore offerte,
-- tasso di conversione, pipeline commerciale.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_preventivi AS
SELECT
    q.id                                                        AS preventivo_id,
    q.numero_offerta                                            AS numero_offerta,
    q.customer_id                                               AS cliente_id,
    c.ragione_sociale                                           AS cliente,
    c.provincia                                                 AS cliente_provincia,
    q.data_offerta                                              AS data_offerta,
    YEAR(q.data_offerta)                                        AS anno,
    MONTH(q.data_offerta)                                       AS mese,
    DATE_FORMAT(q.data_offerta, '%Y-%m')                        AS anno_mese,
    q.data_scadenza                                             AS data_scadenza,
    q.stato                                                     AS stato,
    CASE WHEN q.stato = 'accettata' THEN 1 ELSE 0 END           AS accettato,
    q.validita_giorni                                           AS validita_giorni,
    q.totale_imponibile                                         AS totale_imponibile,
    q.totale_iva                                                AS totale_iva,
    q.totale_generale                                           AS totale_generale,
    (SELECT COUNT(*) FROM quote_items qi WHERE qi.quote_id = q.id) AS n_righe
FROM quotes q
JOIN customers c ON c.id = q.customer_id
WHERE q.deleted_at IS NULL;

-- ---------------------------------------------------------------------
-- ai_bi_righe_preventivo : una riga per riga di preventivo. Dettaglio
-- per prodotto / categoria / cliente. totale_riga e' IVA esclusa,
-- gia' al netto dello sconto.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_righe_preventivo AS
SELECT
    qi.id                                                       AS riga_id,
    qi.quote_id                                                 AS preventivo_id,
    q.numero_offerta                                            AS numero_offerta,
    q.data_offerta                                              AS data_offerta,
    YEAR(q.data_offerta)                                        AS anno,
    DATE_FORMAT(q.data_offerta, '%Y-%m')                        AS anno_mese,
    q.stato                                                     AS stato_preventivo,
    CASE WHEN q.stato = 'accettata' THEN 1 ELSE 0 END           AS accettato,
    q.customer_id                                               AS cliente_id,
    c.ragione_sociale                                           AS cliente,
    c.provincia                                                 AS cliente_provincia,
    qi.product_id                                               AS prodotto_id,
    p.codice_articolo                                           AS codice_articolo,
    COALESCE(p.nome, qi.descrizione)                            AS prodotto,
    p.categoria                                                 AS categoria,
    qi.quantita                                                 AS quantita,
    qi.unita_misura                                             AS unita_misura,
    qi.prezzo_unitario                                          AS prezzo_unitario,
    qi.sconto_percentuale                                       AS sconto_percentuale,
    qi.iva_percentuale                                          AS iva_percentuale,
    qi.totale_riga                                              AS totale_riga
FROM quote_items qi
JOIN quotes q     ON q.id = qi.quote_id AND q.deleted_at IS NULL
JOIN customers c  ON c.id = q.customer_id
LEFT JOIN products p ON p.id = qi.product_id;

-- ---------------------------------------------------------------------
-- ai_bi_ordini_fornitore : una riga per ordine d'acquisto (testata).
-- Spesa verso fornitori, stato, ritardo di consegna.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_ordini_fornitore AS
SELECT
    po.id                                                       AS ordine_id,
    po.numero_ordine                                            AS numero_ordine,
    po.supplier_id                                              AS fornitore_id,
    s.ragione_sociale                                           AS fornitore,
    s.provincia                                                 AS fornitore_provincia,
    po.data_ordine                                              AS data_ordine,
    YEAR(po.data_ordine)                                        AS anno,
    MONTH(po.data_ordine)                                       AS mese,
    DATE_FORMAT(po.data_ordine, '%Y-%m')                        AS anno_mese,
    po.data_consegna_prevista                                   AS data_consegna_prevista,
    po.data_consegna_effettiva                                  AS data_consegna_effettiva,
    CASE WHEN po.data_consegna_effettiva IS NOT NULL
          AND po.data_consegna_prevista IS NOT NULL
         THEN DATEDIFF(po.data_consegna_effettiva, po.data_consegna_prevista)
    END                                                         AS giorni_ritardo_consegna,
    po.stato                                                    AS stato,
    CASE WHEN po.stato = 'ricevuto'  THEN 1 ELSE 0 END          AS ricevuto,
    CASE WHEN po.stato = 'annullato' THEN 1 ELSE 0 END          AS annullato,
    po.totale_imponibile                                        AS totale_imponibile,
    po.totale_iva                                               AS totale_iva,
    po.totale_generale                                          AS totale_generale,
    (SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS n_righe
FROM purchase_orders po
JOIN suppliers s ON s.id = po.supplier_id
WHERE po.deleted_at IS NULL;

-- ---------------------------------------------------------------------
-- ai_bi_righe_ordine_fornitore : una riga per riga d'ordine d'acquisto.
-- Dettaglio per prodotto / categoria / fornitore; ordinato vs ricevuto.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ai_bi_righe_ordine_fornitore AS
SELECT
    poi.id                                                      AS riga_id,
    poi.purchase_order_id                                       AS ordine_id,
    po.numero_ordine                                            AS numero_ordine,
    po.data_ordine                                              AS data_ordine,
    YEAR(po.data_ordine)                                        AS anno,
    DATE_FORMAT(po.data_ordine, '%Y-%m')                        AS anno_mese,
    po.stato                                                    AS stato_ordine,
    po.supplier_id                                              AS fornitore_id,
    s.ragione_sociale                                           AS fornitore,
    s.provincia                                                 AS fornitore_provincia,
    poi.product_id                                              AS prodotto_id,
    p.codice_articolo                                           AS codice_articolo,
    COALESCE(p.nome, poi.descrizione)                           AS prodotto,
    p.categoria                                                 AS categoria,
    poi.quantita_ordinata                                       AS quantita_ordinata,
    poi.quantita_ricevuta                                       AS quantita_ricevuta,
    GREATEST(poi.quantita_ordinata - poi.quantita_ricevuta, 0)  AS quantita_mancante,
    poi.unita_misura                                            AS unita_misura,
    poi.prezzo_unitario                                         AS prezzo_unitario,
    poi.sconto_percentuale                                      AS sconto_percentuale,
    poi.iva_percentuale                                         AS iva_percentuale,
    poi.totale_riga                                             AS totale_riga
FROM purchase_order_items poi
JOIN purchase_orders po ON po.id = poi.purchase_order_id AND po.deleted_at IS NULL
JOIN suppliers s        ON s.id = po.supplier_id
LEFT JOIN products p     ON p.id = poi.product_id;
