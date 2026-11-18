// Transfer roll corridor search (OpenPocket #283, plan task 265 part 9, section 8): rolls the whole omni cart about the STATIC pipe's centre line with the free hand's jaw open, in BOTH
// directions and for BOTH trips (up pipe C releasing hand B, up pipe B releasing hand C), and finds by MuJoCo contact detection which roll angles clear the track.
//   plate = the free hand swings to the plate side (-y, in front of the pipe plane), spine = to the spine side (+y, behind).
// For each (trip, direction):
//   1. at the roll station on the leg: the largest roll angle reachable from 0 with every angle on the way clear (the roll itself, 1 degree steps),
//   2. held through the bend (Q7): the roll angles that stay clear at every 0.25 cm from the roll station to the roll-back point (S_FLAT_CM),
//   3. the corridor = angles in both lists, and the roll-back at S_FLAT_CM (the same sweep, in reverse) is clear.
// The controller (src/cart/omni-transfer-run.ts) takes the direction that clears (Q3), the plate side first when both do.
// Modes:  node --experimental-strip-types scripts/search-swing.ts            the corridors
//         node --experimental-strip-types scripts/search-swing.ts bend       the best trim of the riding sleeve through the bend (TRIM_ROWS)
//         node --experimental-strip-types scripts/search-swing.ts margin     the corridor again for clearances of 0, 1, 2, 3 mm
import loadMujoco from '@mujoco/mujoco';
import { ROLL_STATION_CM, S_FLAT_CM, P_BEND_START, P_BEND_END, TRIM_ROWS, placeTransfer, transferContacts, transferMjcf, trimAt, worstOf, blockedBy, type Trim } from '../src/cart/omni-transfer.ts';
import type { Hand } from '../src/cart/omni.ts';

const mj = await loadMujoco();
const jawA1 = process.env.JAW_A1 ? Number(process.env.JAW_A1) : undefined;   // what-if: the jaw wedge's far edge in degrees (the CAD assumes 110)
const model = mj.MjModel.from_xml_string(transferMjcf({ jawA1 })), data = new mj.MjData(model);
const setMargin = (mm: number) => { for (let i = 0; i < model.ngeom; i++) model.geom_margin[i] = (mm + 0.1) / 1000; };
/** Depth of the worst collision of this pose (m; negative = penetration, bigger = more room), and what is in the way. */
export function probe(rider: Hand, s: number, roll: number, open = 1, trim?: Trim, clearMm = 0) {
  setMargin(clearMm);
  placeTransfer(model as any, data as any, { rider, s, roll, open, trim: trim ?? trimAt(s, TRIM_ROWS) }); mj.mj_forward(model, data);
  const d = transferContacts(model as any, data as any, rider);
  // contact dist is the gap; a contact with gap >= clear is not a collision
  return { ok: blockedBy(d, clearMm / 1000) === '', what: blockedBy(d, clearMm / 1000), depth: worstOf(d), d };
}
const mode = process.argv[2] ?? 'corridor';

if (mode === 'bend') {
  console.log('best trim (dx mm towards the bend centre, yaw deg) of the cart riding pipe C through the bend, roll 0, jaws closed; least penetration of the riding sleeve, the base and the rods (the free hand is left out: with both hands clamped it is round its own pipe, which diverges):');
  const rows: string[] = []; let worst = 0;
  for (let s = P_BEND_START - 4; s <= P_BEND_END + 4 + 1e-9; s += 1) {
    let best = -9, bt = { dx: 0, yaw: 0 };
    for (let dx = -14; dx <= 14; dx += 0.5) for (let yaw = -6; yaw <= 6; yaw += 0.5) {
      setMargin(0); placeTransfer(model as any, data as any, { rider: 'C', s, roll: 0, open: 0, trim: { dx, yaw } }); mj.mj_forward(model, data);
      const d = transferContacts(model as any, data as any, 'C'), w = Math.min(d['rider:pipe'], d['base:pipe'], d['rider:rod']);
      if (w > best) { best = w; bt = { dx, yaw }; }
    }
    worst = Math.min(worst, best); rows.push(`  [${s.toFixed(0)}, ${bt.dx}, ${bt.yaw}],   // ${(best * 1000).toFixed(2)} mm`);
  }
  console.log(rows.join('\n')); console.log(`worst penetration through the bend with the best trim: ${(worst * 1000).toFixed(2)} mm`);
} else {
  const clears = mode === 'margin' ? [0, 1, 2, 3] : [0];
  for (const clearMm of clears) {
    if (mode === 'margin') console.log(`--- clearance ${clearMm} mm`);
    for (const rider of ['C', 'B'] as Hand[]) {
      const trip = rider === 'C' ? 'up pipe C (hand B released)' : 'up pipe B (hand C released)';
      for (const dir of [1, -1]) {
        const name = dir > 0 ? 'plate side' : 'spine side', STEP = 1, MAX = 180;
        // 1. the roll itself at the station, jaw already open
        let reach = -1, why = '';
        for (let a = 0; a <= MAX; a += STEP) { const r = probe(rider, ROLL_STATION_CM, dir * a, 1, undefined, clearMm); if (!r.ok) { why = `${a} deg: ${r.what}`; break; } reach = a; }
        // 2. held along the way
        const held: boolean[] = Array(MAX / STEP + 1).fill(true), whyHeld: string[] = [];
        for (let s = ROLL_STATION_CM; s <= S_FLAT_CM + 1e-9; s += 0.25) for (let a = 0; a <= MAX; a += STEP) if (held[a / STEP]) { const r = probe(rider, s, dir * a, 1, undefined, clearMm); if (!r.ok) { held[a / STEP] = false; whyHeld[a / STEP] = `s ${s.toFixed(2)}: ${r.what}`; } }
        // 3. the roll back at S_FLAT_CM sweeps every angle between phi and 0, which must all be clear there; the corridor is the angles that are held, reachable and can roll back
        let flatPrefix = -1; for (let a = 0; a <= MAX; a += STEP) { if (probe(rider, S_FLAT_CM, dir * a, 1, undefined, clearMm).ok) flatPrefix = a; else break; }
        const valid = held.map((h, i) => h && i * STEP <= reach && i * STEP <= flatPrefix), top = valid.lastIndexOf(true) * STEP;
        const ranges = (() => { const out: string[] = []; let a0 = -1, prev = -1; valid.forEach((v, i) => { if (!v) return; const a = i * STEP; if (a0 < 0) a0 = a; else if (a !== prev + STEP) { out.push(`${a0}-${prev}`); a0 = a; } prev = a; }); if (a0 >= 0) out.push(`${a0}-${prev}`); return out.join(', '); })();
        console.log(`trip ${trip}, ${name}: roll reachable at the station to ${reach} deg${why ? ` (stops at ${why})` : ''}; usable roll angles (held through the bend, can roll back at ${S_FLAT_CM} cm): ${ranges || 'none => NO'}`);
        if (!whyHeld.length) continue;
        const first = whyHeld.findIndex(Boolean); if (first >= 0 && mode !== 'margin') console.log(`    first angle held out: ${first * STEP} deg (${whyHeld[first]})`);
      }
    }
  }
}
