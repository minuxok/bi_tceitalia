#!/usr/bin/env python3
# =====================================================================
# Genera il database demo "Nuvola Shop" (SQLite) - verticale E-COMMERCE.
# Dati finti realistici per la demo pubblica sul sito.
#
# Uso:
#   python seed_ecom.py                # crea ./nuvola.db
#   python seed_ecom.py --out path.db  # percorso personalizzato
#
# Deterministico: stesso seed -> stesso database (utile per i test/eval).
# Data di riferimento ("oggi"): 2026-08-27  -> vedi OGGI.
#
# Se esiste ../semantic/views_ecom.sql viene applicato in coda (viste ai_bi_*).
# =====================================================================

import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

OGGI = date(2026, 8, 27)
SEED = 42

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "schema_ecom.sql")
VIEWS_PATH = os.path.join(HERE, "..", "semantic", "views_ecom.sql")

IVA = 0.22

# Finestra ordini/traffico e finestra registrazioni clienti.
INIZIO_ORDINI = date(2025, 1, 1)
INIZIO_REG = date(2023, 1, 1)

# ---------------------------------------------------------------------
# Anagrafiche di base
# ---------------------------------------------------------------------
# citta -> (provincia, regione, peso demografico)
CITTA = [
    ("Milano", "MI", "Lombardia", 9.0),
    ("Roma", "RM", "Lazio", 8.5),
    ("Napoli", "NA", "Campania", 5.0),
    ("Torino", "TO", "Piemonte", 4.5),
    ("Palermo", "PA", "Sicilia", 3.0),
    ("Genova", "GE", "Liguria", 2.2),
    ("Bologna", "BO", "Emilia-Romagna", 3.2),
    ("Firenze", "FI", "Toscana", 3.0),
    ("Bari", "BA", "Puglia", 2.4),
    ("Catania", "CT", "Sicilia", 2.0),
    ("Verona", "VR", "Veneto", 2.2),
    ("Venezia", "VE", "Veneto", 1.8),
    ("Padova", "PD", "Veneto", 2.0),
    ("Brescia", "BS", "Lombardia", 2.4),
    ("Bergamo", "BG", "Lombardia", 1.8),
    ("Parma", "PR", "Emilia-Romagna", 1.6),
    ("Modena", "MO", "Emilia-Romagna", 1.6),
    ("Perugia", "PG", "Umbria", 1.4),
    ("Cagliari", "CA", "Sardegna", 1.6),
    ("Pescara", "PE", "Abruzzo", 1.2),
    ("Ancona", "AN", "Marche", 1.2),
    ("Trento", "TN", "Trentino-Alto Adige", 1.4),
    ("Udine", "UD", "Friuli-Venezia Giulia", 1.2),
    ("Reggio Calabria", "RC", "Calabria", 1.2),
    ("Salerno", "SA", "Campania", 1.4),
    ("Latina", "LT", "Lazio", 1.2),
]

CANALI = ["Organico", "Google Ads", "Meta Ads", "Email", "Referral", "Diretto"]
CANALI_PESO = [0.30, 0.24, 0.22, 0.10, 0.06, 0.08]
# conversion rate "vero" per canale: guida la generazione delle sessioni
CR_CANALE = {
    "Organico": 0.026,
    "Google Ads": 0.022,
    "Meta Ads": 0.015,
    "Email": 0.048,
    "Referral": 0.031,
    "Diretto": 0.036,
}
# traffico di base giornaliero per canale (sessioni), prima del rumore
BASE_SESSIONI = {
    "Organico": 170,
    "Google Ads": 145,
    "Meta Ads": 155,
    "Email": 46,
    "Referral": 36,
    "Diretto": 59,
}

DISPOSITIVI = ["Mobile", "Desktop", "Tablet"]
DISPOSITIVI_PESO = [0.58, 0.34, 0.08]

PAGAMENTI = ["Carta", "PayPal", "Bonifico", "Contrassegno"]
PAGAMENTI_PESO = [0.50, 0.35, 0.05, 0.10]

# categoria -> (fascia prezzo IVA inclusa, generi ammessi, fascia costo/prezzo_netto)
# La fascia costo differenzia il margine per categoria (~32%-60%).
CATEGORIE = {
    "Abbigliamento donna": ((12, 85), ["Donna"], (0.42, 0.54)),
    "Abbigliamento uomo": ((14, 95), ["Uomo"], (0.44, 0.56)),
    "Calzature": ((29, 135), ["Donna", "Uomo", "Unisex"], (0.52, 0.63)),
    "Accessori": ((7, 55), ["Donna", "Uomo", "Unisex"], (0.40, 0.50)),
    "Sport": ((15, 75), ["Donna", "Uomo", "Unisex"], (0.48, 0.60)),
    "Outdoor": ((25, 160), ["Donna", "Uomo", "Unisex"], (0.56, 0.68)),
}
NOMI_PRODOTTO = {
    "Abbigliamento donna": ["Maglia", "Camicia", "Pantalone", "Gonna", "Abito", "Felpa", "Giacca", "Cardigan"],
    "Abbigliamento uomo": ["T-shirt", "Camicia", "Chino", "Jeans", "Felpa", "Polo", "Giacca", "Maglione"],
    "Calzature": ["Sneaker", "Stivaletto", "Mocassino", "Sandalo", "Running", "Derby", "Ballerina"],
    "Accessori": ["Zaino", "Cintura", "Sciarpa", "Cappello", "Portafoglio", "Borsa", "Occhiali", "Guanti"],
    "Sport": ["Leggings", "Top sportivo", "Shorts", "Giacca running", "Tuta", "Canotta", "Calze tecniche"],
    "Outdoor": ["Giacca antipioggia", "Piumino", "Zaino trekking", "Pile", "Pantalone trekking", "Borraccia termica"],
}
MATERIALI = ["cotone bio", "lino", "lana merino", "tecnico riciclato", "denim", "pelle", "nylon", "felpa garzata",
             "misto seta", "softshell", "jersey", "gore-tex"]
COLORI = ["nero", "blu navy", "grigio melange", "bianco", "verde oliva", "beige", "bordeaux", "senape", "ruggine"]

COUPON = {
    "BENVENUTO10": ("pct", 10),
    "SALDI20": ("pct", 20),
    "VIP15": ("pct", 15),
    "NEWSLETTER5": ("fisso", 5.0),
    "FREESHIP": ("spedizione", 0.0),
}
COUPON_CODES = list(COUPON.keys())

MOTIVI_RESO = ["Taglia errata", "Difettoso", "Non conforme", "Ripensamento", "Consegna in ritardo"]
MOTIVI_RESO_PESO = [0.46, 0.14, 0.14, 0.20, 0.06]

# Probabilita' che una riga di un ordine consegnato venga resa, per categoria.
# Abbigliamento e calzature: resi alti (problemi di taglia); accessori/outdoor bassi.
RESO_PROB = {
    "Abbigliamento donna": 0.14,
    "Abbigliamento uomo": 0.11,
    "Calzature": 0.13,
    "Sport": 0.08,
    "Outdoor": 0.05,
    "Accessori": 0.04,
}

# Stagionalita' e-commerce: picco Black Friday / Natale, saldi gennaio, calo estivo.
PESO_MESE = {1: 1.20, 2: 0.95, 3: 1.00, 4: 1.00, 5: 1.05, 6: 0.90,
             7: 0.80, 8: 0.65, 9: 1.05, 10: 1.15, 11: 1.55, 12: 1.45}

SOGLIA_SPED_GRATIS = 59.90
COSTO_SPED = 4.90

NOMI = ["Giulia", "Marco", "Sofia", "Luca", "Aurora", "Alessandro", "Martina", "Francesco", "Chiara", "Matteo",
        "Sara", "Andrea", "Elena", "Davide", "Federica", "Simone", "Alice", "Giovanni", "Beatrice", "Lorenzo",
        "Anna", "Riccardo", "Valentina", "Stefano", "Ilaria", "Antonio", "Camilla", "Paolo", "Noemi", "Gabriele"]
COGNOMI = ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco",
           "Bruno", "Gallo", "Conti", "De Luca", "Costa", "Giordano", "Mancini", "Rizzo", "Lombardi", "Moretti",
           "Barbieri", "Fontana", "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini", "Leone"]


def rnd_date(d0: date, d1: date) -> date:
    return d0 + timedelta(days=random.randint(0, (d1 - d0).days))


def rnd_date_stagionale(d0: date, d1: date) -> date:
    """Estrae una data pesando i mesi per stagionalita'."""
    picco = max(PESO_MESE.values())
    for _ in range(24):
        d = rnd_date(d0, d1)
        if random.random() < PESO_MESE[d.month] / picco:
            return d
    return rnd_date(d0, d1)


def rnd_ora() -> int:
    """Ora del giorno pesata: picchi pausa pranzo e sera."""
    ore = list(range(24))
    pesi = [0.4, 0.2, 0.1, 0.1, 0.1, 0.2, 0.5, 1.2, 2.2, 3.0, 3.4, 3.6,
            3.8, 3.2, 2.8, 2.6, 2.8, 3.2, 3.6, 4.2, 4.6, 4.0, 2.6, 1.2]
    return random.choices(ore, weights=pesi, k=1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "nuvola.db"))
    args = ap.parse_args()

    random.seed(SEED)

    if os.path.exists(args.out):
        os.remove(args.out)
    con = sqlite3.connect(args.out)
    cur = con.cursor()

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        cur.executescript(f.read())

    # ---------------- clienti ----------------
    N_CLIENTI = 3600
    email_seen = set()
    clienti = []  # (id, canale_acq, data_reg, provincia, regione, citta, propensione)
    for cid in range(1, N_CLIENTI + 1):
        citta, prov, regione, _peso = random.choices(
            CITTA, weights=[c[3] for c in CITTA], k=1)[0]
        nome = f"{random.choice(NOMI)} {random.choice(COGNOMI)}"
        base = nome.lower().replace(" ", ".").replace("'", "")
        while True:
            email = f"{base}{random.randint(1, 9999)}@example.it"
            if email not in email_seen:
                email_seen.add(email)
                break
        canale_acq = random.choices(CANALI, weights=CANALI_PESO, k=1)[0]
        # registrazioni piu' fitte col passare del tempo (shop in crescita)
        u = random.random() ** 1.7
        giorni = int(u * (OGGI - INIZIO_REG).days)
        data_reg = INIZIO_REG + timedelta(days=giorni)
        newsletter = 1 if random.random() < (0.75 if canale_acq == "Email" else 0.42) else 0
        # propensione all'acquisto ripetuto: coda lunga, ma non troppo concentrata
        propensione = round(random.random() ** 1.35 + 0.05, 4)

        cur.execute(
            """INSERT INTO clienti
               (id, email, nome, citta, provincia, regione, data_registrazione,
                canale_acquisizione, newsletter)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (cid, email, nome, citta, prov, regione, data_reg.isoformat(),
             canale_acq, newsletter),
        )
        clienti.append((cid, canale_acq, data_reg, prov, regione, citta, propensione))

    # ---------------- prodotti ----------------
    N_PRODOTTI = 120
    prodotti = []  # (id, categoria, prezzo, costo, attivo)
    sku_seen = set()
    cat_ciclo = list(CATEGORIE.keys())
    for pid in range(1, N_PRODOTTI + 1):
        # allocazione bilanciata: ~20 prodotti per categoria (+ un po' di rumore)
        categoria = cat_ciclo[pid % len(cat_ciclo)] if random.random() < 0.8 \
            else random.choice(cat_ciclo)
        (lo, hi), generi, (clo, chi) = CATEGORIE[categoria]
        genere = random.choice(generi)
        prezzo = round(random.uniform(lo, hi) - 0.10, 2)   # ...,90 / ,99 vibes
        prezzo_netto = prezzo / (1 + IVA)
        costo = round(prezzo_netto * random.uniform(clo, chi), 2)
        nome = f"{random.choice(NOMI_PRODOTTO[categoria])} {random.choice(MATERIALI)} {random.choice(COLORI)}"
        while True:
            sku = f"{categoria[:3].upper()}-{random.randint(10000, 99999)}"
            if sku not in sku_seen:
                sku_seen.add(sku)
                break
        attivo = 0 if random.random() < 0.10 else 1
        cur.execute(
            """INSERT INTO prodotti (id, sku, nome, categoria, genere, prezzo, costo, attivo)
               VALUES (?,?,?,?,?,?,?,?)""",
            (pid, sku, nome, categoria, genere, prezzo, costo, attivo),
        )
        prodotti.append((pid, categoria, prezzo, costo, attivo))

    # 8 prodotti "fermi": non venduti negli ultimi 12 mesi
    prodotti_fermi = set(random.sample([p[0] for p in prodotti], 8))
    prezzo_by_id = {p[0]: p[2] for p in prodotti}
    cat_by_id = {p[0]: p[1] for p in prodotti}

    # ---------------- ordini + righe + resi ----------------
    N_ORDINI = 9000
    ord_id = 0
    riga_id = 0
    reso_id = 0
    contatore_anno = {}
    ordini_per_giorno_canale: dict[tuple[str, str], int] = {}

    pesi_cli = [c[6] for c in clienti]
    # consegnati/spediti candidati al reso: (ordine_id, data_rif, [(prodotto_id, qta, prezzo_pagato)])
    consegnati = []

    for _ in range(N_ORDINI):
        cliente = random.choices(clienti, weights=pesi_cli, k=1)[0]
        cid, canale_acq, data_reg, prov, regione, citta, _prop = cliente

        d_start = max(data_reg, INIZIO_ORDINI)
        if d_start >= OGGI:
            continue
        d_ord = rnd_date_stagionale(d_start, OGGI)
        ora = rnd_ora()

        anno = d_ord.year
        contatore_anno[anno] = contatore_anno.get(anno, 0) + 1
        numero = f"NV-{anno}-{contatore_anno[anno]:06d}"

        # sorgente ordine: di solito il canale di acquisizione del cliente,
        # ma ~35% arriva da re-engagement (Email/Diretto/Organico).
        if random.random() < 0.35:
            sorgente = random.choices(
                ["Email", "Diretto", "Organico", "Google Ads", "Meta Ads", "Referral"],
                weights=[0.34, 0.28, 0.20, 0.09, 0.06, 0.03], k=1)[0]
        else:
            sorgente = canale_acq

        dispositivo = random.choices(DISPOSITIVI, weights=DISPOSITIVI_PESO, k=1)[0]
        metodo = random.choices(PAGAMENTI, weights=PAGAMENTI_PESO, k=1)[0]

        # righe: 1-4 prodotti distinti (desktop carrelli piu' grandi, mobile piu' piccoli)
        n_righe = random.choices([1, 2, 3, 4], weights=[46, 31, 16, 7])[0]
        if dispositivo == "Mobile" and n_righe > 1 and random.random() < 0.18:
            n_righe -= 1
        elif dispositivo == "Desktop" and n_righe < 4 and random.random() < 0.18:
            n_righe += 1
        recente = (OGGI - d_ord).days <= 365
        pool = [p for p in prodotti if not (recente and p[0] in prodotti_fermi)]
        scelti = random.sample(pool, min(n_righe, len(pool)))

        ord_id += 1
        righe_ins = []
        subtotale = 0.0
        for p in scelti:
            pid, categoria, prezzo, costo, attivo = p
            qta = random.choices([1, 2, 3], weights=[74, 20, 6])[0]
            sconto = random.choices([0, 10, 15, 20, 30], weights=[70, 12, 10, 5, 3])[0]
            prezzo_eff = round(prezzo * random.uniform(0.98, 1.02) * (1 - sconto / 100.0), 2)
            riga_id += 1
            righe_ins.append((riga_id, ord_id, pid, qta, prezzo_eff, sconto))
            subtotale += qta * prezzo_eff

        # coupon (~22%)
        coupon = None
        sconto_totale = 0.0
        if random.random() < 0.22:
            coupon = random.choice(COUPON_CODES)
            tipo, val = COUPON[coupon]
            if tipo == "pct":
                sconto_totale = round(subtotale * val / 100.0, 2)
            elif tipo == "fisso":
                sconto_totale = min(val, round(subtotale * 0.5, 2))
            # "spedizione": nessuno sconto sul valore merce

        # spedizione: gratis sopra soglia o con coupon FREESHIP
        if subtotale - sconto_totale >= SOGLIA_SPED_GRATIS or coupon == "FREESHIP":
            spedizione_costo = 0.0
        else:
            spedizione_costo = COSTO_SPED

        # stato in funzione dell'eta' dell'ordine
        eta = (OGGI - d_ord).days
        r = random.random()
        if eta > 30:
            if r < 0.02:
                stato = "annullato"
            elif r < 0.07:
                stato = "rimborsato"
            else:
                stato = "consegnato"
        elif eta > 12:
            stato = "annullato" if r < 0.03 else ("consegnato" if r < 0.7 else "spedito")
        elif eta > 4:
            stato = "annullato" if r < 0.03 else random.choice(["spedito", "in_lavorazione", "in_lavorazione"])
        elif eta > 1:
            stato = random.choice(["pagato", "in_lavorazione", "pagato"])
        else:
            stato = random.choice(["in_attesa", "pagato", "pagato"])

        data_sped = None
        data_cons = None
        if stato in ("spedito", "consegnato", "rimborsato"):
            data_sped = (d_ord + timedelta(days=random.randint(1, 4))).isoformat()
        if stato in ("consegnato", "rimborsato"):
            data_cons = (d_ord + timedelta(days=random.randint(2, 9))).isoformat()

        cur.execute(
            """INSERT INTO ordini
               (id, numero, cliente_id, data_ordine, ora, stato, sorgente, dispositivo,
                metodo_pagamento, spedizione_costo, sconto_totale, coupon,
                sped_citta, sped_provincia, sped_regione, data_spedizione, data_consegna)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ord_id, numero, cid, d_ord.isoformat(), ora, stato, sorgente, dispositivo,
             metodo, spedizione_costo, sconto_totale, coupon,
             citta, prov, regione, data_sped, data_cons),
        )
        cur.executemany(
            """INSERT INTO righe_ordine
               (id, ordine_id, prodotto_id, quantita, prezzo_unitario, sconto_pct)
               VALUES (?,?,?,?,?,?)""",
            righe_ins,
        )

        if stato not in ("annullato", "in_attesa"):
            key = (d_ord.isoformat(), sorgente)
            ordini_per_giorno_canale[key] = ordini_per_giorno_canale.get(key, 0) + 1

        if stato in ("consegnato", "rimborsato") and data_cons:
            consegnati.append((
                ord_id, stato, date.fromisoformat(data_cons),
                [(r_[2], r_[3], r_[4]) for r_ in righe_ins],
            ))

    # ---------------- resi ----------------
    # Ordini 'rimborsato' -> reso totale. Altri consegnati -> ~9% delle righe.
    for ordine_id, stato, d_cons, righe in consegnati:
        for pid, qta, prezzo_pagato in righe:
            reso_intero = stato == "rimborsato"
            if not reso_intero and random.random() >= RESO_PROB[cat_by_id[pid]]:
                continue
            q_reso = qta if reso_intero else random.randint(1, qta)
            giorni = random.randint(3, 30)
            d_reso = d_cons + timedelta(days=giorni)
            if d_reso > OGGI:
                d_reso = OGGI
            motivo = random.choices(MOTIVI_RESO, weights=MOTIVI_RESO_PESO, k=1)[0]
            reso_id += 1
            cur.execute(
                """INSERT INTO resi
                   (id, ordine_id, prodotto_id, data_reso, quantita, importo_rimborsato, motivo)
                   VALUES (?,?,?,?,?,?,?)""",
                (reso_id, ordine_id, pid, d_reso.isoformat(), q_reso,
                 round(q_reso * prezzo_pagato, 2), motivo),
            )

    # ---------------- sessioni per giorno e canale ----------------
    giorno = INIZIO_ORDINI
    while giorno <= OGGI:
        g_iso = giorno.isoformat()
        fatt_mese = PESO_MESE[giorno.month]
        weekend = giorno.weekday() >= 5
        for canale in CANALI:
            ordini_gc = ordini_per_giorno_canale.get((g_iso, canale), 0)
            cr = CR_CANALE[canale] * random.uniform(0.8, 1.2)
            base = BASE_SESSIONI[canale] * fatt_mese * (0.9 if weekend else 1.0)
            base *= random.uniform(0.8, 1.2)
            attese_da_ordini = ordini_gc / cr if ordini_gc else 0
            sessioni = int(max(base, attese_da_ordini) + random.uniform(0, 20))
            sessioni = max(sessioni, ordini_gc * 3, 1)
            utenti = int(sessioni * random.uniform(0.78, 0.9))
            aggiunte = int(sessioni * random.uniform(0.09, 0.16))
            aggiunte = max(aggiunte, ordini_gc)
            checkout = int(aggiunte * random.uniform(0.5, 0.68))
            checkout = max(checkout, ordini_gc)
            cur.execute(
                """INSERT INTO sessioni_giorno
                   (data, canale, sessioni, utenti, aggiunte_carrello, checkout_avviati)
                   VALUES (?,?,?,?,?,?)""",
                (g_iso, canale, sessioni, utenti, aggiunte, checkout),
            )
        giorno += timedelta(days=1)

    # ---------------- viste curate (se presenti) ----------------
    if os.path.exists(VIEWS_PATH):
        with open(VIEWS_PATH, encoding="utf-8") as f:
            cur.executescript(f.read())
        viste_ok = True
    else:
        viste_ok = False

    con.commit()

    # ---------------- riepilogo ----------------
    def scalar(q):
        row = cur.execute(q).fetchone()
        return row[0] if row and row[0] is not None else 0

    print(f"DB creato: {args.out}")
    print(f"  clienti ......... {scalar('SELECT COUNT(*) FROM clienti')}")
    print(f"  prodotti ........ {scalar('SELECT COUNT(*) FROM prodotti')}")
    print(f"  ordini .......... {scalar('SELECT COUNT(*) FROM ordini')}")
    print(f"  righe_ordine .... {scalar('SELECT COUNT(*) FROM righe_ordine')}")
    print(f"  resi ............ {scalar('SELECT COUNT(*) FROM resi')}")
    print(f"  sessioni_giorno . {scalar('SELECT COUNT(*) FROM sessioni_giorno')}")

    valido = "stato NOT IN ('annullato','in_attesa')"
    ric = f"""SELECT ROUND(SUM(ro.quantita * ro.prezzo_unitario) / {1 + IVA:.2f}, 2)
              FROM righe_ordine ro JOIN ordini o ON o.id = ro.ordine_id WHERE {valido}"""
    ric25 = ric + " AND o.data_ordine >= '2025-01-01' AND o.data_ordine < '2026-01-01'"
    ric26 = ric + " AND o.data_ordine >= '2026-01-01'"
    n_ord_validi = scalar(f"SELECT COUNT(*) FROM ordini WHERE {valido}")
    aov = scalar(f"""SELECT ROUND(AVG(t), 2) FROM (
                       SELECT SUM(ro.quantita * ro.prezzo_unitario) AS t
                       FROM righe_ordine ro JOIN ordini o ON o.id = ro.ordine_id
                       WHERE {valido} GROUP BY o.id)""")
    reso_pct = scalar("""SELECT ROUND(100.0 * (SELECT COALESCE(SUM(importo_rimborsato),0) FROM resi) /
                          NULLIF((SELECT SUM(ro.quantita * ro.prezzo_unitario)
                                  FROM righe_ordine ro JOIN ordini o ON o.id = ro.ordine_id
                                  WHERE o.stato IN ('consegnato','rimborsato')), 0), 2)""")
    sess_tot = scalar("SELECT SUM(sessioni) FROM sessioni_giorno")
    cr_globale = round(100.0 * n_ord_validi / sess_tot, 2) if sess_tot else 0

    print(f"  fatturato 2025 .. EUR {scalar(ric25):,.2f}  (imponibile)")
    print(f"  fatturato 2026 .. EUR {scalar(ric26):,.2f}  (YTD, imponibile)")
    print(f"  AOV (IVA incl.) . EUR {aov:,.2f}")
    print(f"  tasso di reso ... {reso_pct}%  (su consegnato+rimborsato)")
    print(f"  conversion rate . {cr_globale}%  (ordini validi / sessioni)")
    print(f"  viste ai_bi_* ... {'applicate da views_ecom.sql' if viste_ok else 'NON presenti (views_ecom.sql mancante)'}")

    con.close()


if __name__ == "__main__":
    main()
