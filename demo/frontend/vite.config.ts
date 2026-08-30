import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// La demo è servita come sito statico dietro nginx (es. /bi/). `base: './'`
// tiene i percorsi degli asset relativi, così il widget è incorporabile
// ovunque senza riscrivere gli URL.
// In sviluppo le chiamate a /api sono inoltrate al backend FastAPI locale.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
