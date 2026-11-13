import { defineConfig } from 'vite'

// The dashboard loads ui/dist/index.mjs and resolves these imports from the host's
// import map (docs: /apps/build-first-app/, "vite.config.ts"). Nothing else is bundled
// from outside this package.
export default defineConfig({
  esbuild: { jsx: 'automatic' },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    minify: true,
    sourcemap: false,
    lib: {
      entry: 'src/App.tsx',
      formats: ['es'],
      fileName: () => 'index.mjs',
    },
    rollupOptions: {
      external: ['react', 'react-dom', 'react/jsx-runtime', 'lucide-react', /^@kirocrew\/app-sdk/],
    },
  },
})
