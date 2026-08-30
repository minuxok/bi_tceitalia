#!/usr/bin/env python3
# =====================================================================
# Genera il database demo "Acme Srl" (SQLite) con dati finti realistici.
#
# Uso:
#   python seed.py                # crea ./acme.db
#   python seed.py --out path.db  # percorso personalizzato
#
# Deterministico: stesso seed -> stesso database (utile per i test).
# Data di riferimento ("oggi"): 2026-08-27  -> vedi OGGI.
# =====================================================================

import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

OGGI = date(2026, 8, 27)
SEED = 42

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "schema.sql")
VIEWS_PATH = os.path.join(HERE, "..", "semantic", "views.sql")

IVA = 0.22

# ---------------------------------------------------------------------
# Anagrafiche di base
# ---------------------------------------------------------------------
AGENTI = [
    ("Marco Bianchi", "Nord-Ovest", "2015-03-01"),
    ("Giulia Ferrari", "Nord-Est", "2017-09-15"),
    ("Luca Esposito", "Centro", "2019-01-10"),
    ("Sara Romano", "Sud e Isole", "2020-06-01"),
    ("Davide Greco", "Nord-Ovest", "2021-11-02"),
    ("Elena Conti", "Nord-Est", "2023-02-20"),
]

# citta -> (provincia, regione, area commerciale)
CITTA = [
    ("Milano", "MI", "Lombardia", "Nord-Ovest"),
    ("Torino", "TO", "Piemonte", "Nord-Ovest"),
    ("Bergamo", "BG", "Lombardia", "Nord-Ovest"),
    ("Genova", "GE", "Liguria", "Nord-Ovest"),
    ("Brescia", "BS", "Lombardia", "Nord-Ovest"),
    ("Verona", "VR", "Veneto", "Nord-Est"),
    ("Padova", "PD", "Veneto", "Nord-Est"),
    ("Venezia", "VE", "Veneto", "Nord-Est"),
    ("Bologna", "BO", "Emilia-Romagna", "Nord-Est"),
    ("Udine", "UD", "Friuli-Venezia Giulia", "Nord-Est"),
    ("Firenze", "FI", "Toscana", "Centro"),
    ("Roma", "RM", "Lazio", "Centro"),
    ("Perugia", "PG", "Umbria", "Centro"),
    ("Ancona", "AN", "Marche", "Centro"),
    ("Pescara", "PE", "Abruzzo", "Centro"),
    ("Napoli", "NA", "Campania", "Sud e Isole"),
    ("Bari", "BA", "Puglia", "Sud e Isole"),
    ("Catania", "CT", "Sicilia", "Sud e Isole"),
    ("Palermo", "PA", "Sicilia", "Sud e Isole"),
    ("Cagliari", "CA", "Sardegna", "Sud e Isole"),
]

SETTORI = ["Retail arredo", "Contract", "GDO", "Ecommerce", "Studio progettazione"]
CANALI = ["Diretto", "Agente", "Ecommerce"]

PREFIX = ["Arredamenti", "Casa", "Design", "Studio", "Gruppo", "Mobili", "Spazio",
          "Interni", "La Bottega", "Nuova"]
CORE = ["Rossi", "Verdi", "Bianchi", "Aurora", "Moderna", "Duemila", "Ideal",
        "Progetti", "Contract", "Living", "Habitat", "Domus", "Ferrari", "Costa",
        "Marino", "Sole", "Lombarda", "Adriatica", "Tirrena", "Alpina"]
SUFFIX = ["Srl", "Spa", "Snc", "Sas", "& C. Srl"]

CATEGORIE = {
    "Sedute":        (90, 650),
    "Tavoli":        (180, 1400),
    "Contenitori":   (120, 900),
    "Illuminazione": (35, 480),
    "Complementi":   (15, 220),
    "Outdoor":       (110, 980),
}
NOMI_PRODOTTO = {
    "Sedute": ["Sedia", "Poltrona", "Sgabello", "Panca", "Divano 2p", "Divano 3p"],
    "Tavoli": ["Tavolo pranzo", "Tavolino", "Scrivania", "Consolle", "Tavolo riunioni"],
    "Contenitori": ["Libreria", "Madia", "Cassettiera", "Armadio", "Mobile TV", "Vetrina"],
    "Illuminazione": ["Lampada da terra", "Lampada da tavolo", "Sospensione", "Applique", "Piantana LED"],
    "Complementi": ["Vaso", "Specchio", "Tappeto", "Portariviste", "Appendiabiti", "Orologio parete"],
    "Outdoor": ["Sedia giardino", "Tavolo giardino", "Lettino", "Ombrellone", "Set lounge"],
}
MATERIALI = ["rovere", "noce", "frassino", "metallo nero", "ottone", "vetro",
             "marmo", "tessuto grigio", "velluto blu", "cuoio", "rattan", "alluminio"]

# Peso relativo dei mesi -> stagionalita' (fiere primavera/autunno, calo ad agosto)
PESO_MESE = {1: 0.7, 2: 0.9, 3: 1.2, 4: 1.3, 5: 1.2, 6: 1.0,
             7: 0.8, 8: 0.35, 9: 1.35, 10: 1.4, 11: 1.25, 12: 0.9}


def rnd_date(d0: date, d1: date) -> date:
    return d0 + timedelta(days=random.randint(0, (d1 - d0).days))


def rnd_date_stagionale(d0: date, d1: date) -> date:
    """Estrae una data pesando i mesi per stagionalita'."""
    for _ in range(20):
        d = rnd_date(d0, d1)
        if random.random() < PESO_MESE[d.month] / 1.4:
            return d
    return rnd_date(d0, d1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "acme.db"))
    args = ap.parse_args()

    random.seed(SEED)

    if os.path.exists(args.out):
        os.remove(args.out)
    con = sqlite3.connect(args.out)
    cur = con.cursor()

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        cur.executescript(f.read())

    # ---------------- agenti ----------------
    for i, (nome, area, ass) in enumerate(AGENTI, start=1):
        cur.execute(
            "INSERT INTO agenti (id, nome, area, data_assunzione, attivo) VALUES (?,?,?,?,1)",
            (i, nome, area, ass),
        )
    agenti_per_area = {}
    for i, (_, area, _) in enumerate(AGENTI, start=1):
        agenti_per_area.setdefault(area, []).append(i)

    # ---------------- clienti ----------------
    N_CLIENTI = 90
    piva_seen = set()
    clienti = []  # (id, area, canale, data_creazione, peso, dormiente)
    for cid in range(1, N_CLIENTI + 1):
        citta, prov, regione, area = random.choice(CITTA)
        rs = f"{random.choice(PREFIX)} {random.choice(CORE)} {random.choice(SUFFIX)}"
        while True:
            piva = "".join(str(random.randint(0, 9)) for _ in range(11))
            if piva not in piva_seen:
                piva_seen.add(piva)
                break
        settore = random.choice(SETTORI)
        canale = "Ecommerce" if settore == "Ecommerce" else random.choice(["Diretto", "Agente", "Agente"])
        agente_id = None if canale == "Ecommerce" else random.choice(agenti_per_area[area])
        data_creazione = rnd_date(date(2018, 1, 1), date(2026, 3, 1))
        email = f"ordini@{rs.split()[1].lower()}{cid}.example.it"
        telefono = f"0{random.randint(2,9)} {random.randint(100,999)} {random.randint(1000,9999)}"
        fido = random.choice([0, 0, 5000, 10000, 15000, 25000, 50000])
        # ~17% clienti dormienti: nessun ordine dopo fine 2025
        dormiente = random.random() < 0.17
        peso = round(random.random() ** 2 + 0.05, 4)  # pochi grandi, molti piccoli

        cur.execute(
            """INSERT INTO clienti
               (id, ragione_sociale, partita_iva, citta, provincia, regione, settore,
                canale, agente_id, email, telefono, fido_eur, data_creazione)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, rs, piva, citta, prov, regione, settore, canale, agente_id,
             email, telefono, fido, data_creazione.isoformat()),
        )
        clienti.append((cid, area, canale, data_creazione, peso, dormiente, agente_id))

    # ---------------- prodotti ----------------
    N_PRODOTTI = 60
    prodotti = []  # (id, categoria, prezzo_listino, costo_medio, attivo)
    cod_seen = set()
    for pid in range(1, N_PRODOTTI + 1):
        categoria = random.choice(list(CATEGORIE.keys()))
        lo, hi = CATEGORIE[categoria]
        prezzo = round(random.uniform(lo, hi), 2)
        # marginalita' lorda 35-60% -> costo = prezzo * (1 - markup)
        costo = round(prezzo * random.uniform(0.40, 0.65), 2)
        nome = f"{random.choice(NOMI_PRODOTTO[categoria])} {random.choice(MATERIALI)}"
        while True:
            cod = f"{categoria[:3].upper()}-{random.randint(1000,9999)}"
            if cod not in cod_seen:
                cod_seen.add(cod)
                break
        attivo = 0 if random.random() < 0.08 else 1
        cur.execute(
            """INSERT INTO prodotti
               (id, codice, descrizione, categoria, prezzo_listino, costo_medio, attivo)
               VALUES (?,?,?,?,?,?,?)""",
            (pid, cod, nome, categoria, prezzo, costo, attivo),
        )
        prodotti.append((pid, categoria, prezzo, costo, attivo))

    # 6 prodotti "fermi": non venduti negli ultimi 12 mesi (esclusi dalle vendite recenti)
    prodotti_fermi = set(random.sample([p[0] for p in prodotti], 6))

    # ---------------- ordini + righe + pagamenti ----------------
    N_ORDINI = 1900
    ord_id = 0
    riga_id = 0
    pag_id = 0
    contatore_anno = {}

    # distribuzione ordini sui clienti in base al peso
    pesi = [c[4] for c in clienti]

    for _ in range(N_ORDINI):
        cliente = random.choices(clienti, weights=pesi, k=1)[0]
        cid, area, canale_cli, data_creazione, _peso, dormiente, agente_cli = cliente

        d_start = max(data_creazione, date(2024, 1, 1))
        d_end = date(2025, 12, 20) if dormiente else OGGI
        if d_start >= d_end:
            continue
        d_ord = rnd_date_stagionale(d_start, d_end)

        anno = d_ord.year
        contatore_anno[anno] = contatore_anno.get(anno, 0) + 1
        numero = f"{anno}/{contatore_anno[anno]:05d}"

        canale = canale_cli
        agente_id = agente_cli if canale != "Ecommerce" else None

        eta = (OGGI - d_ord).days
        r = random.random()
        if eta > 120:
            stato = "annullato" if r < 0.05 else "consegnato"
        elif eta > 45:
            stato = "annullato" if r < 0.04 else ("consegnato" if r < 0.75 else "spedito")
        elif eta > 20:
            stato = "annullato" if r < 0.03 else random.choice(
                ["spedito", "in_evasione", "in_evasione", "confermato"])
        elif eta > 7:
            stato = random.choice(["confermato", "in_evasione", "confermato"])
        else:
            stato = random.choice(["bozza", "confermato", "confermato"])

        consegna_prev = (d_ord + timedelta(days=random.randint(15, 45))).isoformat()
        spedizione = None
        if stato in ("spedito", "consegnato"):
            spedizione = (d_ord + timedelta(days=random.randint(10, 40))).isoformat()

        ord_id += 1
        cur.execute(
            """INSERT INTO ordini
               (id, numero, cliente_id, agente_id, canale, data_ordine,
                data_consegna_prevista, data_spedizione, stato, note)
               VALUES (?,?,?,?,?,?,?,?,?,NULL)""",
            (ord_id, numero, cid, agente_id, canale, d_ord.isoformat(),
             consegna_prev, spedizione, stato),
        )

        # righe: 1-6 prodotti distinti
        n_righe = random.choices([1, 2, 3, 4, 5, 6], weights=[25, 28, 22, 13, 8, 4])[0]
        recente = (OGGI - d_ord).days <= 365
        pool = [p for p in prodotti if not (recente and p[0] in prodotti_fermi)]
        scelti = random.sample(pool, min(n_righe, len(pool)))
        imponibile = 0.0
        for p in scelti:
            pid, categoria, prezzo, costo, attivo = p
            qta = random.choices([1, 2, 3, 4, 6, 8, 10],
                                 weights=[30, 22, 16, 12, 9, 6, 5])[0]
            sconto = random.choice([0, 0, 0, 5, 10, 10, 15, 20, 25])
            # prezzo effettivo: listino con leggera oscillazione
            prezzo_eff = round(prezzo * random.uniform(0.97, 1.03), 2)
            riga_id += 1
            cur.execute(
                """INSERT INTO righe_ordine
                   (id, ordine_id, prodotto_id, quantita, prezzo_unitario, sconto_pct)
                   VALUES (?,?,?,?,?,?)""",
                (riga_id, ord_id, pid, qta, prezzo_eff, sconto),
            )
            imponibile += qta * prezzo_eff * (1 - sconto / 100.0)

        if stato in ("annullato", "bozza"):
            continue

        # pagamenti: 1-3 scadenze (30/60/90 gg) su totale IVA inclusa
        totale = round(imponibile * (1 + IVA), 2)
        n_scad = random.choices([1, 2, 3], weights=[55, 30, 15])[0]
        quota = round(totale / n_scad, 2)
        for k in range(n_scad):
            importo = quota if k < n_scad - 1 else round(totale - quota * (n_scad - 1), 2)
            scad = d_ord + timedelta(days=30 * (k + 1) + random.randint(-3, 5))
            data_pag = None
            stato_pag = "aperto"
            if scad <= OGGI:
                # Scadenze molto vecchie: quasi tutte incassate (le insolute
                # storiche verrebbero girate a sofferenza, non restano "scadute").
                p_pagato = 0.985 if (OGGI - scad).days > 240 else 0.90
                if random.random() < p_pagato:
                    ritardo = max(0, int(random.gauss(4, 7)))
                    dp = scad + timedelta(days=ritardo)
                    if dp <= OGGI:
                        data_pag = dp.isoformat()
                        stato_pag = "pagato"
                    else:
                        stato_pag = "scaduto"
                else:
                    stato_pag = "scaduto"
            else:
                stato_pag = "aperto"
            pag_id += 1
            cur.execute(
                """INSERT INTO pagamenti
                   (id, ordine_id, importo, data_scadenza, data_pagamento, stato)
                   VALUES (?,?,?,?,?,?)""",
                (pag_id, ord_id, importo, scad.isoformat(), data_pag, stato_pag),
            )

    # ---------------- viste curate ----------------
    with open(VIEWS_PATH, encoding="utf-8") as f:
        cur.executescript(f.read())

    con.commit()

    # ---------------- riepilogo ----------------
    def scalar(q):
        return cur.execute(q).fetchone()[0]

    print(f"DB creato: {args.out}")
    print(f"  agenti .......... {scalar('SELECT COUNT(*) FROM agenti')}")
    print(f"  clienti ......... {scalar('SELECT COUNT(*) FROM clienti')}")
    print(f"  prodotti ........ {scalar('SELECT COUNT(*) FROM prodotti')}")
    print(f"  ordini .......... {scalar('SELECT COUNT(*) FROM ordini')}")
    print(f"  righe_ordine .... {scalar('SELECT COUNT(*) FROM righe_ordine')}")
    print(f"  pagamenti ....... {scalar('SELECT COUNT(*) FROM pagamenti')}")
    q_scaduto = "SELECT ROUND(SUM(importo),2) FROM ai_bi_scaduto"
    q_fatt25 = "SELECT ROUND(SUM(ricavo_netto),2) FROM ai_bi_vendite WHERE anno = 2025"
    print(f"  scaduto totale .. EUR {scalar(q_scaduto):,.2f}")
    print(f"  fatturato 2025 .. EUR {scalar(q_fatt25):,.2f}")

    con.close()


if __name__ == "__main__":
    main()
