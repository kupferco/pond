// Builds the whole hub for Firebase: docs/ as-is, plus the built sim page at /sim.
import { cpSync, rmSync } from 'node:fs';
rmSync('site', { recursive: true, force: true });
cpSync('../docs', 'site', { recursive: true });
cpSync('dist', 'site/sim', { recursive: true });
console.log('site/ ready (docs + /sim)');
