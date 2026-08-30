import Widget from './Widget'
import './App.css'

// Pagina "ospite" finta: serve solo in sviluppo per vedere il widget nel
// contesto di un sito e verificare che gli stili .cbi- non sporchino la pagina.
export default function App() {
  return (
    <div className="host">
      <header className="host-nav">
        <strong>Acme Analytics</strong>
        <nav>
          <a href="#prodotto">Prodotto</a>
          <a href="#sicurezza">Sicurezza</a>
          <a href="#contatti">Contatti</a>
        </nav>
      </header>

      <main className="host-main">
        <section className="host-hero">
          <h1>La business intelligence che risponde a parole tue</h1>
          <p>
            Fai domande in italiano sui dati aziendali e ottieni tabelle e grafici in pochi
            secondi. Qui sotto una demo dal vivo su un’azienda di esempio.
          </p>
        </section>

        <section className="host-demo" id="prodotto">
          <Widget ctaHref="#contatti" />
        </section>

        <section className="host-copy" id="sicurezza">
          <h2>Paragrafo di prova del sito ospite</h2>
          <p>
            Questo testo usa gli stili della pagina, non quelli del widget. Se il widget qui
            sopra ha un aspetto coerente e questo paragrafo resta invariato, l’isolamento CSS
            funziona.
          </p>
          <button className="host-btn">Bottone del sito</button>
        </section>
      </main>

      <footer className="host-foot" id="contatti">
        © Acme Analytics — pagina dimostrativa
      </footer>
    </div>
  )
}
