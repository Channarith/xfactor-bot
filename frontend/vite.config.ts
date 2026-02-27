import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import packageJson from './package.json'

export default defineConfig({
  plugins: [react()],
  define: {
    // Inject version and release date from package.json at build time (keep in sync)
    __APP_VERSION__: JSON.stringify(packageJson.version),
    __APP_RELEASE_DATE__: JSON.stringify((packageJson as { releaseDate?: string }).releaseDate ?? ''),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 9876,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8765',
        ws: true,
      },
    },
  },
})

