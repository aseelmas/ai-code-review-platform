import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { resolveApiUrl } from './src/config.js'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, import.meta.dirname, 'VITE_')
  const apiUrl = resolveApiUrl(env.VITE_API_URL, command === 'build')
  return {
    plugins: [react()],
    define: { 'import.meta.env.VITE_API_URL': JSON.stringify(apiUrl) },
  }
})
