// Checks the Drawings page data (docs/drawings/renders.json): every drawing must open a GLB in the 3D viewer and have a
// black and white line-drawing thumbnail. Fails on a missing or broken GLB, a link that is not the local viewer, or a missing thumbnail.
// Usage: node --experimental-strip-types test/drawings.test.ts   (part of npm test)
import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'docs', 'drawings');
const data = JSON.parse(readFileSync(join(dir, 'renders.json'), 'utf8')) as { renders: { id: string; title: string; viewer?: string; thumb?: string }[] };
const problems: string[] = [];

for (const r of data.renders) {
  const where = `${r.id} (${r.title})`;
  const m = /^viewer\.html\?src=(renders\/[A-Za-z0-9._-]+\.glb)(&|$)/.exec(r.viewer ?? '');
  if (!m) { problems.push(`${where}: viewer link is not viewer.html?src=renders/<file>.glb (${r.viewer ?? 'none'})`); }
  else {
    const f = join(dir, m[1]);
    if (!existsSync(f)) problems.push(`${where}: GLB file missing: ${m[1]}`);
    else {
      const b = readFileSync(f);
      // binary glTF: "glTF", version 2, total length field equal to the file size
      if (b.length < 20 || b.toString('latin1', 0, 4) !== 'glTF' || b.readUInt32LE(4) !== 2 || b.readUInt32LE(8) !== b.length) problems.push(`${where}: ${m[1]} is not a complete binary glTF file`);
      else if (b.toString('latin1', 16, 20) !== 'JSON') problems.push(`${where}: ${m[1]} has no glTF JSON chunk`);
      else {
        const n = b.readUInt32LE(12);
        const j = JSON.parse(b.toString('utf8', 20, 20 + n));
        if (!j.meshes?.length || !j.nodes?.length) problems.push(`${where}: ${m[1]} contains no geometry`);
      }
    }
  }
  const t = r.thumb ?? '';
  if (!/^renders\/[A-Za-z0-9._-]+-line\.png$/.test(t)) problems.push(`${where}: thumbnail is not a line drawing renders/<id>-line.png (${t || 'none'})`);
  else if (!existsSync(join(dir, t)) || statSync(join(dir, t)).size < 1000) problems.push(`${where}: thumbnail file missing or empty: ${t}`);
}

const viewer = readFileSync(join(dir, 'viewer.html'), 'utf8');
if (!/model-viewer\s*\{[^}]*background:\s*#fff/.test(viewer)) problems.push('viewer.html: background is not white');
if (!/shadow-intensity="[0-9.]*[1-9]/.test(viewer)) problems.push('viewer.html: ground shadow is off');

if (!/id="back"/.test(viewer)) problems.push('viewer.html: no Back button');
// One entry per part on the Drawings page: the card list is built by "part", so a part must not be spelled several ways.
const home = JSON.parse(readFileSync(join(dir, '..', 'home.json'), 'utf8')) as { hero: { href: string } };
const hm = /^drawings\/viewer\.html\?src=(renders\/[A-Za-z0-9._-]+\.glb)(&|$)/.exec(home.hero.href);
if (!hm || !existsSync(join(dir, hm[1]))) problems.push(`home.json: hero does not open an existing GLB in the shared viewer (${home.hero.href})`);
else if (hm[1] !== 'renders/complete-unit-v2.glb') problems.push(`home.json: hero should open the complete unit GLB (${hm[1]})`);
if (data.renders[0]?.id !== 'complete-unit-v2') problems.push('renders.json: the complete unit must be the first card');
const collar = new Set(data.renders.filter(r => /^pipe-collar-/.test(r.id)).map(r => (r as { part?: string }).part));
if (collar.size !== 1) problems.push(`renders.json: pipe collar entries use ${collar.size} different part names, want 1`);

if (problems.length) { console.error(problems.join('\n')); console.error(`drawings: ${problems.length} problem(s) in ${data.renders.length} drawings`); process.exit(1); }
console.log(`drawings: ${data.renders.length} drawings, all open a GLB and have a line-drawing thumbnail`);
