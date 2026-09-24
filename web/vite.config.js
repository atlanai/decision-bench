import {rmSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

/* The site is served from ../site, next to data.json, corpus.json, datasets.json and the row images that
   `python3 -m decision_bench report` writes there. The build writes index.html and app/ into it and leaves
   everything else alone; `npm run dev` serves ../site as static files so the data loads with hot reload. */
const site = fileURLToPath(new URL('../site', import.meta.url));

export default defineConfig(({command}) => ({
  base: '/',
  plugins: [
    react(),
    tailwindcss(),
    {name: 'clean-app-dir', apply: 'build', buildStart() { rmSync(`${site}/app`, {recursive: true, force: true}); }},
  ],
  resolve: {alias: {'@': fileURLToPath(new URL('./src', import.meta.url))}},
  publicDir: command === 'serve' ? site : false,
  build: {outDir: site, emptyOutDir: false, assetsDir: 'app', cssMinify: true, chunkSizeWarningLimit: 700},
  server: {port: 5173},
}));
