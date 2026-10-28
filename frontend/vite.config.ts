import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Backend routes are proxied so one origin (localhost or a public tunnel URL) serves the whole app.
const BACKEND = process.env.HISAB_BACKEND ?? 'http://localhost:8000'
const proxied = ['/chat', '/api', '/customers', '/metrics', '/tickets', '/health', '/agent', '/admin', '/docs', '/openapi.json']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    allowedHosts: true,
    proxy: Object.fromEntries(proxied.map((p) => [p, { target: BACKEND, changeOrigin: true }])),
  },
})
