import { Fragment, useState } from 'react'
import Widget from './Widget'
import { VERTICALS, VERTICALE_DEFAULT } from './verticals'
import './App.css'

/* Landing page pubblica di "TCE Analytics System".
   Montata su #root da main.tsx. Il widget della demo è lo stesso
   componente incorporabile (ConversationalBI.mount), qui usato diretto. */

const EMAIL = 'info@tceitalia.com'
const MAILTO =
  `mailto:${EMAIL}` +
  `?subject=${encodeURIComponent('Demo Conversational BI')}` +
  `&body=${encodeURIComponent(
    'Salve,\n' +
      'vorremmo vedere una demo del sistema sui nostri dati.\n\n' +
      'Gestionale o piattaforma e-commerce in uso: \n' +
      'Tipo di database: \n' +
      'Aree dati di interesse: \n',
  )}`

const FAQ: { q: string; a: string }[] = [
  {
    q: 'Dobbiamo cambiare gestionale o piattaforma e-commerce?',
    a: 'No. Il sistema legge i dati che avete già, non modifica il gestionale né l’e-commerce e non richiede migrazioni. Si affianca a quello che usate.',
  },
  {
    q: 'L’AI può inventarsi i numeri?',
    a: 'I numeri arrivano sempre da una query SQL eseguita sul database, non dal modello linguistico. La query resta visibile e le righe di origine sono consultabili.',
  },
  {
    q: 'I dati aziendali sono al sicuro?',
    a: 'L’accesso è in sola lettura e limitato a viste concordate. I dati restano in UE, non vengono usati per addestrare modelli, e c’è un DPA pronto da firmare.',
  },
  {
    q: 'Serve saper scrivere SQL o query?',
    a: 'No. Si scrive una domanda in italiano. La query la genera e la esegue il motore.',
  },
  {
    q: 'Quanto tempo serve per attivarlo?',
    a: 'Con un database accessibile e schema noto, tipicamente una o due settimane, più una settimana di test con utenti reali prima del via libera.',
  },
  {
    q: 'E se il database non è raggiungibile dall’esterno?',
    a: 'Si usa la sincronizzazione periodica: i dati arrivano via API o export in un archivio gestito da noi, con una latenza dichiarata (per esempio aggiornati ogni ora).',
  },
  {
    q: 'Il sistema può scrivere o modificare dati?',
    a: 'No. La versione attuale è rigorosamente in sola lettura. Ogni istruzione che non sia una SELECT viene rifiutata dal validatore.',
  },
  {
    q: 'Su quali dati risponde?',
    a: 'Sulle aree che decidiamo insieme all’avvio, per esempio vendite e clienti. Altre aree si aggiungono in un secondo momento.',
  },
]

function Nav() {
  return (
    <nav className="lp-nav">
      <div className="lp-wrap">
        <a className="lp-brand" href="#top">
          TCE <span>Analytics System</span>
        </a>
        <div className="lp-nav-links">
          <a href="#come-funziona">Come funziona</a>
          <a href="#trasparenza">Trasparenza</a>
          <a href="#sicurezza">Sicurezza</a>
          <a href="#demo">Demo</a>
        </div>
        <a className="lp-btn lp-btn-primary" href={MAILTO}>
          Prenota una demo
        </a>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <header className="lp-hero" id="top">
      <div className="lp-wrap">
        <div>
          <p className="lp-eyebrow">Business intelligence conversazionale</p>
          <h1>Fai domande ai tuoi dati aziendali. In italiano.</h1>
          <p className="lp-hero-sub">
            Il tuo gestionale o e-commerce risponde con numeri, tabelle e grafici in pochi
            secondi. In sola lettura, senza esportare niente.
          </p>
          <div className="lp-hero-actions">
            <a className="lp-btn lp-btn-primary" href={MAILTO}>
              Prenota una demo
            </a>
            <a className="lp-btn lp-btn-ghost" href="#come-funziona">
              Come funziona
            </a>
          </div>
        </div>
        <div className="lp-hero-demo">
          <Widget ctaHref="#contatto" ctaLabel="Prenota una demo" maxEsempi={4} />
        </div>
      </div>
    </header>
  )
}

function Pipeline() {
  const nodes: { b: string; s: string; check?: boolean }[] = [
    {
      b: 'Domanda in italiano',
      s: 'Scritta dall’utente, senza sintassi tecnica.',
    },
    {
      b: 'Motore Text-to-SQL',
      s: 'Riceve schema delle viste, glossario ed esempi. Non vede il database.',
    },
    {
      b: 'Validatore',
      s: 'Solo SELECT, LIMIT e timeout forzati, solo viste ai_bi_.',
      check: true,
    },
    {
      b: 'Esecuzione',
      s: 'La query gira in sola lettura sulle viste concordate del cliente.',
    },
    {
      b: 'Risposta',
      s: 'Numeri, tabella, grafico, più la query e la spiegazione.',
    },
  ]
  return (
    <div className="lp-pipe">
      <p className="lp-pipe-cap">Cosa succede dietro le quinte</p>
      <div className="lp-pipe-flow">
        {nodes.map((n, i) => (
          <Fragment key={n.b}>
            <div className={'lp-pipe-node' + (n.check ? ' is-check' : '')}>
              <b>{n.b}</b>
              <span>{n.s}</span>
            </div>
            {i < nodes.length - 1 && (
              <div className="lp-pipe-arrow" aria-hidden="true">
                &rarr;
              </div>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  )
}

function HowItWorks() {
  const steps = [
    {
      t: 'Scrivi la domanda',
      d: 'In linguaggio naturale, come la chiederesti a un collega. Nessuna formula da ricordare.',
    },
    {
      t: 'Il motore scrive la query e la controlla',
      d: 'Genera una SELECT sulle viste concordate, verifica che sia solo lettura e dentro il perimetro, poi la esegue.',
    },
    {
      t: 'Ricevi la risposta',
      d: 'Numeri, tabella e grafico. Con la query usata e una spiegazione a parole di cosa fa.',
    },
  ]
  return (
    <section className="lp-section" id="come-funziona">
      <div className="lp-wrap">
        <h2 className="lp-h2">Dalla domanda al grafico, in tre passaggi</h2>
        <div className="lp-steps">
          {steps.map((s, i) => (
            <div className="lp-step" key={s.t}>
              <div className="lp-step-n">{i + 1}</div>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </div>
          ))}
        </div>
        <Pipeline />
      </div>
    </section>
  )
}

function SemanticLayer() {
  return (
    <section className="lp-section is-alt" id="motore">
      <div className="lp-wrap lp-split">
        <div>
          <h2 className="lp-h2">L’AI non vede il tuo database. Vede una mappa pulita.</h2>
          <p className="lp-lead">
            Invece di centinaia di tabelle con nomi come RIGHE_DOC o C_ANART, il motore lavora
            su poche viste con nomi parlanti e su un glossario che fissa le definizioni.
          </p>
          <ul className="lp-split-list">
            <li>8-15 viste curate, con i join già risolti e gli stati normalizzati</li>
            <li>
              Un glossario che dice cosa significa &ldquo;fatturato&rdquo;, chi è un
              &ldquo;cliente attivo&rdquo;, cosa conta come &ldquo;scaduto&rdquo;
            </li>
            <li>Dati personali (email, telefono, P.IVA) tenuti fuori dalle viste</li>
            <li>Meno ambiguità, contesto più corto, risposte più affidabili</li>
          </ul>
        </div>
        <div className="lp-code">
          <div className="lp-code-head">glossario.yaml</div>
          <pre>
            <span className="k">fatturato:</span>{'      SUM(ricavo_netto) su ai_bi_vendite,\n'}
            {'               IVA esclusa, esclusi bozza e annullati\n'}
            <span className="k">cliente attivo:</span>{' almeno un ordine negli ultimi 6 mesi\n'}
            <span className="k">scaduto:</span>{'        SUM(importo) su ai_bi_scaduto,\n'}
            {'               scadenze passate e non incassate\n'}
            <span className="k">margine:</span>{'        ricavo_netto meno costo\n'}
            {'\n'}
            {'# viste esposte al motore\n'}
            {'ai_bi_vendite  ai_bi_ordini   ai_bi_clienti\n'}
            {'ai_bi_scaduto  ai_bi_prodotti ai_bi_agenti\n'}
          </pre>
        </div>
      </div>
    </section>
  )
}

function Transparency() {
  return (
    <section className="lp-section is-band" id="trasparenza">
      <div className="lp-wrap">
        <p className="lp-eyebrow">Trasparenza</p>
        <h2 className="lp-h2">Ogni numero è verificabile</h2>
        <p className="lp-lead">
          Con ogni risposta arriva la query SQL che l’ha prodotta, una spiegazione in italiano
          di cosa fa, e la possibilità di aprire le righe di origine.
        </p>
        <div className="lp-verify">
          <div className="lp-code">
            <div className="lp-code-head">query eseguita</div>
            <pre>
              <span className="k">SELECT</span>{' anno_mese, ROUND(SUM(ricavo_netto), 2) '}
              <span className="k">AS</span>{' fatturato\n'}
              <span className="k">FROM</span>{' ai_bi_vendite\n'}
              <span className="k">WHERE</span>{' anno = 2026\n'}
              <span className="k">GROUP BY</span>{' anno_mese\n'}
              <span className="k">ORDER BY</span>{' anno_mese;'}
            </pre>
            <div className="lp-verify-expl">
              Ho sommato i ricavi netti degli ordini del 2026, esclusi bozza e annullati,
              raggruppati per mese.
            </div>
          </div>
          <div className="lp-points">
            <div className="lp-point">
              <b>Query sempre visibile</b>
              <span>Il tuo team, o il vostro IT, può controllare cosa è stato chiesto al database.</span>
            </div>
            <div className="lp-point">
              <b>Spiegazione a parole</b>
              <span>Una frase in italiano descrive filtri, periodo e aggregazioni usate.</span>
            </div>
            <div className="lp-point">
              <b>Drill-down alle righe</b>
              <span>Dalla stessa risposta si aprono i record che compongono il totale.</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function DemoSection() {
  const [vid, setVid] = useState(VERTICALE_DEFAULT.id)
  const v = VERTICALS.find((x) => x.id === vid) ?? VERTICALE_DEFAULT
  return (
    <section className="lp-section is-alt" id="demo">
      <div className="lp-wrap lp-demo-inner">
        <h2 className="lp-h2">Provala adesso</h2>
        <p className="lp-lead">
          Stesso motore, più mondi. Scegli il tipo di attività e fai una domanda ai suoi dati.
        </p>
        <div className="lp-seg" role="tablist" aria-label="Tipo di attività">
          {VERTICALS.map((x) => (
            <button
              key={x.id}
              type="button"
              role="tab"
              aria-selected={x.id === vid}
              className={'lp-seg-btn' + (x.id === vid ? ' is-on' : '')}
              onClick={() => setVid(x.id)}
            >
              {x.label}
            </button>
          ))}
        </div>
        <p className="lp-demo-note">{v.lead}</p>
        <div className="lp-demo-mount">
          <Widget
            key={v.id}
            apiBase={v.apiBase}
            storeName={v.store}
            ctaHref="#contatto"
            ctaLabel="Prenota una demo"
          />
        </div>
      </div>
    </section>
  )
}

function Security() {
  const tech = [
    'Accesso in sola lettura: solo SELECT, solo sulle viste concordate',
    'Query validata: niente comandi di modifica, LIMIT e timeout forzati',
    'Dati personali mascherati dove non servono (email, telefono, P.IVA)',
    'La connessione parte dalla tua rete verso di noi, nessuna porta aperta in ingresso',
    'Log cifrati, conservazione limitata, un ambiente separato per ogni cliente',
  ]
  const legal = [
    'DPA ai sensi dell’art. 28 GDPR, pronto da firmare',
    'Sub-responsabili e hosting nell’Unione Europea',
    'I tuoi dati non vengono usati per addestrare modelli',
    'Export completo e cancellazione su richiesta',
    'AI Act: strumento analitico a rischio limitato, con scheda di trasparenza',
  ]
  return (
    <section className="lp-section" id="sicurezza">
      <div className="lp-wrap">
        <h2 className="lp-h2">Pensata per chi deve dare il via libera: IT e privacy</h2>
        <p className="lp-lead">
          La sicurezza non è un modulo aggiuntivo. È il modo in cui il sistema è costruito.
        </p>
        <div className="lp-cols2">
          <div>
            <h3>Sul piano tecnico</h3>
            <ul className="lp-checklist">
              {tech.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Sul piano legale</h3>
            <ul className="lp-checklist">
              {legal.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

function Connectivity() {
  return (
    <section className="lp-section is-alt" id="collegamento">
      <div className="lp-wrap">
        <h2 className="lp-h2">Due modi per collegarci ai tuoi dati</h2>
        <p className="lp-lead">
          Si sceglie in fase di assessment, in base a come sono raggiungibili i dati del
          gestionale o dell’e-commerce.
        </p>
        <div className="lp-panels">
          <div className="lp-panel is-primary">
            <div className="lp-panel-tag">Accesso diretto</div>
            <h3>Dati in tempo reale</h3>
            <p>
              Un utente di sola lettura sul database. È la modalità preferita quando il DB è
              raggiungibile: SQL Server, PostgreSQL, MySQL.
            </p>
            <div className="lp-panel-foot">Nessuna copia dei dati, risposte sullo stato attuale.</div>
          </div>
          <div className="lp-panel">
            <div className="lp-panel-tag">Sincronizzazione periodica</div>
            <h3>Quando il DB non è raggiungibile</h3>
            <p>
              Il gestionale espone solo API o export: portiamo i dati in un archivio gestito da
              noi, aggiornato a intervalli regolari.
            </p>
            <div className="lp-panel-foot">La latenza viene dichiarata, per esempio dati aggiornati ogni ora.</div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Faq() {
  return (
    <section className="lp-section" id="faq">
      <div className="lp-wrap">
        <h2 className="lp-h2">Domande frequenti</h2>
        <div className="lp-faq">
          {FAQ.map((f) => (
            <details key={f.q}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="lp-section is-alt lp-final" id="contatto">
      <div className="lp-wrap">
        <h2 className="lp-h2">Colleghiamo l’AI ai tuoi dati, in sola lettura</h2>
        <p className="lp-lead">
          Gestionale o e-commerce: ti mostriamo in 15 minuti come funziona sui tuoi dati.
        </p>
        <a className="lp-btn lp-btn-primary" href={MAILTO}>
          Prenota una demo
        </a>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="lp-foot">
      <div className="lp-wrap">
        <span>TCE Analytics System &middot; Business intelligence conversazionale</span>
        <a href={MAILTO}>{EMAIL}</a>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <div className="lp">
      <Nav />
      <Hero />
      <HowItWorks />
      <SemanticLayer />
      <Transparency />
      <DemoSection />
      <Security />
      <Connectivity />
      <Faq />
      <FinalCta />
      <Footer />
    </div>
  )
}
