import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// Local preview build only (npm run preview:build): bundles React and a mocked SDK so
// the page can be viewed and screenshotted without Crew. Output is git-ignored.
export default defineConfig({
  root: fileURLToPath(new URL('./preview', import.meta.url)),
  base: './',
  esbuild: { jsx: 'automatic' },
  resolve: { alias: { '@kirocrew/app-sdk': fileURLToPath(new URL('./preview/sdk-mock.ts', import.meta.url)) } },
  build: { outDir: fileURLToPath(new URL('./preview-dist', import.meta.url)), emptyOutDir: true },
})
