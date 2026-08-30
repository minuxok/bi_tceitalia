import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import Widget from './Widget.tsx'
import type { WidgetProps } from './Widget.tsx'
import './index.css'

/**
 * API di embed. Sul sito del cliente:
 *
 *   <div id="cbi"></div>
 *   <script type="module" src="/bi/assets/index.js"></script>
 *   <script>ConversationalBI.mount('#cbi', { ctaHref: '/contatti' })</script>
 */
function mount(target: string | HTMLElement, opts: WidgetProps = {}) {
  const el = typeof target === 'string' ? document.querySelector(target) : target
  if (!el) {
    console.error('[ConversationalBI] target non trovato:', target)
    return
  }
  createRoot(el).render(
    <StrictMode>
      <Widget {...opts} />
    </StrictMode>,
  )
}

declare global {
  interface Window {
    ConversationalBI: { mount: typeof mount }
  }
}
window.ConversationalBI = { mount }

// Pagina di sviluppo: monta la demo completa (sito fittizio + widget) su #root.
const root = document.getElementById('root')
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
