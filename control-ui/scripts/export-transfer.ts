// Exports the Transfer scene on the omni cart for pictures (OpenPocket #283): poses of a transfer with the jaw wedge widened to 150 degrees and the attempt with the wedge as the CAD draws it (0 to 110),
// as triangle lists (JSON, for scripts/render_transfer.py: there is no GPU here) and GLBs of the whole scene (for the 3D viewer).
// Usage: node --experimental-strip-types scripts/export-transfer.ts OUT_DIR
import loadMujoco from '@mujoco/mujoco';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { placeTransfer, transferMjcf, transferContacts, blockedBy, S_FLAT_CM, P_TOP_CM, ROLL_STATION_CM } from '../src/cart/omni-transfer.ts';
import { JAW_A1_DEG, TRANSFER_ROLL_DEG, type Variant } from '../src/cart/omni-transfer-run.ts';
import { pathAt } from '../src/cart/track.ts';
import { glb, triangles, type Tri } from './tri-export.ts';

const out = process.argv[2];
if (!out) throw new Error('usage: export-transfer.ts OUT_DIR');
mkdirSync(out, { recursive: true });
const mj = await loadMujoco();
const round = (t: Tri[]) => t.map((r) => r.map((v, i) => (i < 9 ? +v.toFixed(4) : v)));
interface Stage { id: string; label: string; variant: Variant; rider: 'B' | 'C'; s: number; roll: number; open: number }
const R = TRANSFER_ROLL_DEG;
const stages: Stage[] = [
  { id: 'wide-1-start', label: 'Wedge 150: start, both hands clamped at the roll station', variant: 'wide', rider: 'C', s: ROLL_STATION_CM, roll: 0, open: 0 },
  { id: 'wide-2-released', label: 'Wedge 150: hand B released (jaw open 92 degrees)', variant: 'wide', rider: 'C', s: ROLL_STATION_CM, roll: 0, open: 1 },
  { id: 'wide-3-rolled', label: `Wedge 150: rolled ${R} degrees about pipe C, hand B off pipe B`, variant: 'wide', rider: 'C', s: ROLL_STATION_CM, roll: R, open: 1 },
  { id: 'wide-4-bend', label: 'Wedge 150: round the bend, roll held', variant: 'wide', rider: 'C', s: 72, roll: R, open: 1 },
  { id: 'wide-5-rollback', label: 'Wedge 150: start of the top run, rolling back flat', variant: 'wide', rider: 'C', s: S_FLAT_CM, roll: 40, open: 1 },
  { id: 'wide-6-top', label: 'Wedge 150: flat on pipe C top bar, hand B free', variant: 'wide', rider: 'C', s: P_TOP_CM, roll: 0, open: 1 },
  { id: 'cad-1-released', label: 'CAD wedge (0 to 110): hand B released, roll 0', variant: 'cad', rider: 'C', s: ROLL_STATION_CM, roll: 0, open: 1 },
  { id: 'cad-2-roll3', label: 'CAD wedge: rolled 3 degrees to the plate side, hand B already hits pipe B', variant: 'cad', rider: 'C', s: ROLL_STATION_CM, roll: 3, open: 1 },
  { id: 'cad-3-roll20', label: 'CAD wedge: forced 20 degrees, pipe B inside the sleeve', variant: 'cad', rider: 'C', s: ROLL_STATION_CM, roll: 20, open: 1 },
];
const models = new Map<Variant, { m: ReturnType<typeof mj.MjModel.from_xml_string>; d: InstanceType<typeof mj.MjData> }>();
const list: object[] = [];
for (const st of stages) {
  if (!models.has(st.variant)) { const m = mj.MjModel.from_xml_string(transferMjcf({ jawA1: JAW_A1_DEG[st.variant] })); models.set(st.variant, { m, d: new mj.MjData(m) }); }
  const { m, d } = models.get(st.variant)!;
  placeTransfer(m as never, d as never, { rider: st.rider, s: st.s, roll: st.roll, open: st.open }); mj.mj_forward(m, d);
  const hit = blockedBy(transferContacts(m as never, d as never, st.rider)), p = pathAt(st.s);
  const tris = triangles(mj, m, d);
  writeFileSync(join(out, st.id + '.json'), JSON.stringify(round(tris)));
  writeFileSync(join(out, st.id + '.glb'), glb(tris, 'pond control-ui export-transfer'));
  list.push({ id: st.id, label: st.label, hit, centre: [0.06 + p.x, 0, p.z] });
  console.log(st.id, hit ? `HIT ${hit}` : 'clear');
}
writeFileSync(join(out, 'stages.json'), JSON.stringify(list));
