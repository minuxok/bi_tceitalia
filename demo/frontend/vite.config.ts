import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// La demo è servita come sito statico dietro nginx (es. /bi/). `base: './'`
// tiene i percorsi degli asset relativi, così il widget è incorporabile
// ovunque senza riscrivere gli URL.
// In sviluppo le chiamate sono inoltrate ai due backend FastAPI locali:
//   /api      -> :8000  (VERTICAL=acme, gestionale)
//   /api-ecom -> :8001  (VERTICAL=ecom, e-commerce)
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api-ecom': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api-ecom/, ''),
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
