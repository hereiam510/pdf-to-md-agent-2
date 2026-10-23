import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { input: { index: resolve('src/desktop/main.ts') } } }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { input: { index: resolve('src/desktop/preload.ts') } } }
  },
  renderer: {
    root: 'src/renderer',
    plugins: [react()],
    build: { rollupOptions: { input: resolve('src/renderer/index.html') } }
  }
})
