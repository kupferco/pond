// Checks the 3D model manifest (docs/models/models.json): valid entries, unique ids, every GLB exists and is a complete binary glTF.
// Usage: node --experimental-strip-types test/models.test.ts   (part of npm test)
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const docs = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'docs');
type M = { id?: string; title?: string; glb?: string; caption?: string; page?: string; section?: string; poster?: string; camera?: { orbit?: string; target?: string; fov?: string } };
const data = JSON.parse(readFileSync(join(docs, 'models', 'models.json'), 'utf8')) as { models: M[] };
const problems: string[] = [];
const ids = new Set<string>();
if (!Array.isArray(data.models) || !data.models.length) problems.push('models.json: no models');
for (const m of data.models ?? []) {
  const w = m.id ?? '(no id)';
  if (!m.id || !/^[a-z0-9-]+$/.test(m.id)) problems.push(`${w}: id missing or not lowercase-kebab`);
  else if (ids.has(m.id)) problems.push(`${w}: duplicate id`);
  else ids.add(m.id);
  if (!m.title) problems.push(`${w}: no title`);
  if (!m.page || !/^[a-z0-9-]+$/.test(m.page)) problems.push(`${w}: page missing`);
  if (!m.section) problems.push(`${w}: section missing`);
  if (m.camera) for (const k of Object.keys(m.camera)) if (!['orbit', 'target', 'fov'].includes(k)) problems.push(`${w}: unknown camera field ${k}`);
  if (m.poster && !existsSync(join(docs, m.poster))) problems.push(`${w}: poster missing: ${m.poster}`);
  if (!m.glb || !/^[A-Za-z0-9._/-]+\.glb$/.test(m.glb) || m.glb.includes('..')) { problems.push(`${w}: glb path invalid (${m.glb})`); continue; }
  const f = join(docs, m.glb);
  if (!existsSync(f)) { problems.push(`${w}: GLB file missing: ${m.glb}`); continue; }
  const b = readFileSync(f);
  if (b.length < 20 || b.toString('latin1', 0, 4) !== 'glTF' || b.readUInt32LE(4) !== 2 || b.readUInt32LE(8) !== b.length) problems.push(`${w}: ${m.glb} is not a complete binary glTF`);
  else {
    const j = JSON.parse(b.toString('utf8', 20, 20 + b.readUInt32LE(12)));
    if (!j.meshes?.length) problems.push(`${w}: ${m.glb} has no geometry`);
  }
}
if (problems.length) { console.error(problems.join('\n')); console.error(`models: ${problems.length} problem(s)`); process.exit(1); }
console.log(`models: ${data.models.length} models, all point to an existing GLB`);
