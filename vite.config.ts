import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ command, isPreview }) => ({
  plugins: [react()],
  // GitHub Pages serves the site from /<repo>/, so the build (and `vite preview` of
  // it) use that base; the dev server stays at the root.
  base: command === 'build' || isPreview ? '/Cloud_Security/' : '/',
}))
