// Exports the Cart scene (the omni cart riding ONE track pipe, OpenPocket #447: the cart as in the CAD Complete unit, riding hand C with hand B hanging outside the bend)
// as triangle lists (JSON, for scripts/render_scene_stages.py) and GLBs. Usage: node --experimental-strip-types scripts/export-cart-track.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { omniTrackMjcf, placeOmniCart, bendTrim, trackContacts } from '../src/cart/omni-track.ts';
import { pathAt } from '../src/cart/track.ts';
import { glb, triangles, type Tri } from './tri-export.ts';

const out = process.argv[2];
if (!out) throw new Error('usage: export-cart-track.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const m = mj.MjModel.from_xml_string(omniTrackMjcf()), d = new mj.MjData(m);
const round = (t: Tri[]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
const stages = [
  { id: '1-leg', label: 'Cart on the straight leg (30 cm): hand C clamps the track pipe, hand B hangs on the outside', s: 30, roll: 0 },
  { id: '2-bend', label: 'Round the bend (72 cm), trimmed to the pipe', s: 72, roll: 0 },
  { id: '3-top', label: 'On the top run (110 cm)', s: 110, roll: 0 },
  { id: '4-rolled', label: 'Rolled 180 degrees about the leg (30 cm): plate towards the unit, hand B over the unit', s: 30, roll: 180 },
];
const list: object[] = [];
for (const st of stages) {
  placeOmniCart(m as never, d as never, st.s, (st.roll * Math.PI) / 180, bendTrim(st.s)); mj.mj_forward(m, d);
  const c = trackContacts(m as never, d as never), tris = triangles(mj, m, d), p = pathAt(st.s);
  writeFileSync(join(out, st.id + '.json'), JSON.stringify(round(tris)));
  writeFileSync(join(out, st.id + '.glb'), glb(tris, 'pond control-ui export-cart-track'));
  list.push({ id: st.id, label: st.label, centre: [0, 0, p.z], half: st.s > 100 ? 0.45 : 0.3 });
  console.log(st.id, st.label, `rider ${(c.rider * 1000).toFixed(2)} mm, free hand ${(c.freehand * 1000).toFixed(2)} mm, base ${(c.base * 1000).toFixed(2)} mm`);
}
writeFileSync(join(out, 'stages.json'), JSON.stringify(list));
