import { defineConfig } from 'vite';

// Same isolation headers as firebase.json, so dev behaves like hosting (needed for threaded WASM).
const isolation = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp',
};

export default defineConfig({
  base: './',
  server: { headers: isolation },
  preview: { headers: isolation },
  build: { target: 'es2022' },
});
