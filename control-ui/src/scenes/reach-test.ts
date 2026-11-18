// Reach test scene: the unit of the Transplant scene with all 24 planting holes (collar and plug each) on the central pipe and all 16 pods in the 4 x 4 seedling tray (in the front of the tank under the lid, as in the Pod grab scene). At load the arm tries every hole and every pod,
// with the cart at every station of the track (both legs and both runs), as it is and rolled 180 degrees about the pipe it rides (src/reach/test.ts); each plug cap and pod cap is coloured green (reachable as is), amber (only after the roll) or red (not reachable).
// Pick a part to see the arm do it. Contacts stay at none (the pose shown is checked every time).
import { Viewer } from '../viewer.ts';
import { worstContact } from '../transplant/apply.ts';
import { YC } from '../transplant/layout.ts';
import { HOLES, reachMjcf } from '../reach/layout.ts';
import { ANGLE_TOL, Rig, RESULT_RGB, colourParts, runReach, summary, type Attempt, type Colour, type Target } from '../reach/test.ts';
import { checkPass } from '../reach/pass.ts';
import { stations, type Station } from '../reach/station.ts';

/** The cart as shown at load and when the arm is folded: rolled 180° about leg A's own axis, at 1.0 m. */
const ROLLED_HOME = stations('leg A', 180).find((s) => Math.abs(s.at - 1.0) < 1e-6)!;
import { JAW_CAP_DEG } from '../transplant/layout.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'reach-test')!;
const VIEWS: Record<string, { target: [number, number, number]; dist: number; az: number; el: number }> = {
  overview: { target: [0.1, 0.1, 0.95], dist: 3.2, az: 0.5, el: 0.2 },
  tray: { target: [0.1, -0.24, 0.3], dist: 0.9, az: 0.4, el: 0.45 },
  pipe: { target: [0, 0, 1.1], dist: 1.9, az: -0.6, el: 0.15 },
};
export const COLOUR: Record<Colour, { css: string; word: string }> = {
  green: { css: '#2eb84d', word: 'green' },
  amber: { css: '#f5b21a', word: 'amber' },
  red: { css: '#db3a30', word: 'red' },
};
const NAMES = { A: 'shoulder pan', B: 'shoulder lift', C: 'elbow', D: 'wrist' };

/** Plain words for one orientation's result. */
export function describe(a: Attempt): string {
  if (a.ok) return `reachable, cart on ${a.station!.label}, ${a.margin!.toFixed(0)}° from the nearest joint limit`;
  const why = a.reason === 'distance' ? `distance: ${a.detail}` : a.reason === 'joint limit' ? `joint limit: ${a.detail}` : a.reason === 'angle' ? `angle: ${a.detail} (limit ${ANGLE_TOL}°)` : `collision: ${a.detail}`;
  return why;
}

export const reachScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const model = mujoco.MjModel.from_xml_string(reachMjcf());
    const data = new mujoco.MjData(model);
    status.textContent = 'Trying every hole and pod…';
    await new Promise((r) => setTimeout(r, 30));
    const results = runReach(mujoco, model, data);
    const passes = checkPass(mujoco, model, data, [0, 90, 180, 270]);
    const sum = summary(results);
    colourParts(model, results);
    const rig = new Rig(mujoco, model, data);
    const viewer = new Viewer(view, { mujoco, model, data }, { ...VIEWS.overview, maxDist: 6, far: 30 });
    status.textContent = '';

    const dot = (c: Colour) => `<span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:${COLOUR[c].css};vertical-align:-1px"></span>`;
    const chip = (t: Target) => `<button data-t="${t.id}" title="${t.label}: ${COLOUR[t.colour].word}" style="min-width:42px;padding:6px 4px;border:2px solid ${COLOUR[t.colour].css};border-radius:8px;background:${COLOUR[t.colour].css}33">${t.id}</button>`;
    const reds = results.filter((t) => t.colour === 'red'), ambers = results.filter((t) => t.colour === 'amber');
    const reasonRows = reds.map((t) => `<tr><td>${t.id}</td><td>${describe(t.direct)}</td><td>${describe(t.rolled)}</td><td>${t.other.ok ? 'works: ' : ''}${describe(t.other)}</td></tr>`).join('');
    const best = (t: Target) => (t.colour === 'green' ? t.direct : t.colour === 'amber' ? t.rolled : null);
    const fullRows = (k: 'hole' | 'pod') => results.filter((t) => t.kind === k).map((t) => { const b = best(t); return `<tr><td>${dot(t.colour)} ${t.id}</td><td>${b ? `${t.colour === 'green' ? 'as is' : 'rolled 180°'}: ${b.station!.label}, ${b.margin!.toFixed(0)}° joint margin` : `${t.direct.reason} ${t.direct.detail} / rolled 180°: ${t.rolled.reason} ${t.rolled.detail}`}</td></tr>`; }).join('');
    const near = (k: 'holes' | 'pods') => results.filter((t) => t.kind === (k === 'holes' ? 'hole' : 'pod') && t.colour === 'red' && (t.direct.looseErr !== undefined || t.rolled.looseErr !== undefined));
    const passRows = passes.map((p) => `<tr><td>${p.run}</td><td>${p.roll}°</td><td>${p.bracket ? `touches (${(-p.bracketWorst * 1000).toFixed(0)} mm)` : 'clear'}</td><td>${p.pipe ? 'touches' : 'clear'}</td></tr>`).join('');
    const row = (n: string, s: typeof sum.holes) => `<tr><td>${n}</td><td>${dot('green')} ${s.green}</td><td>${dot('amber')} ${s.amber}</td><td>${dot('red')} ${s.red}</td><td>${s.total}</td></tr>`;

    panel.innerHTML = `
    <h1>Pond reach test</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Showing</dt><dd id="r-now">Nothing picked: arm folded</dd>
        <dt>Cart</dt><dd id="r-cart"></dd>
        <dt>Contacts</dt><dd id="r-hit">none</dd>
      </dl>
    </section>
    <h2>Result</h2>
    <table><thead><tr><th></th><th>Green: as is</th><th>Amber: after the roll</th><th>Red: no</th><th>Total</th></tr></thead><tbody>${row('Holes', sum.holes)}${row('Pods', sum.pods)}</tbody></table>
    <p class="hint">${sum.holes.green + sum.holes.amber === 0 ? 'No hole can be reached, with or without the roll.' : `Holes that need the roll: ${ambers.filter((t) => t.kind === 'hole').map((t) => t.id).join(', ') || 'none'}.`} ${sum.pods.amber ? `Pods that need the roll: ${ambers.filter((t) => t.kind === 'pod').map((t) => t.id).join(', ')}.` : 'No pod needs the roll.'} A hand that could reach the point but not point along the part's axis within ${ANGLE_TOL}° counts as red: ${near('holes').length} holes and ${near('pods').length} pods get their point reached that way. ${results.filter((t) => t.colour === 'red' && t.other.ok).length} of the red parts would be reachable at another roll angle (see the list below).</p>
    <h2>Pick a part (colour = result)</h2>
    <p class="hint">Holes, numbered from the bottom, three to a level:</p>
    <div class="row wrap" id="r-holes">${results.filter((t) => t.kind === 'hole').map(chip).join('')}</div>
    <p class="hint">Seedling pods, row by row (row 1 is the deepest in the tank):</p>
    <div class="row wrap" id="r-pods">${results.filter((t) => t.kind === 'pod').map(chip).join('')}</div>
    <div class="row">
      <button class="big grow" id="r-direct">Show as is</button>
      <button class="big grow" id="r-rolled">Show rolled 180°</button>
      <button class="big grow" id="r-fold">Fold</button>
    </div>
    <p class="hint" id="r-text"></p>
    <div class="row">
      <button class="big grow" data-view="overview">Overview</button>
      <button class="big grow" data-view="pipe">Pipe</button>
      <button class="big grow" data-view="tray">Seedling tray</button>
    </div>
    <details class="card"><summary>Best result for every hole</summary><table class="runs"><tbody>${fullRows('hole')}</tbody></table></details>
    <details class="card"><summary>Best result for every pod</summary><table class="runs"><tbody>${fullRows('pod')}</tbody></table></details>
    <details class="card"><summary>Why each red part is red</summary>
      <table class="runs"><thead><tr><th>Part</th><th>Cart as is (best station)</th><th>Cart rolled 180° (best station)</th><th>Any other roll (30° steps)</th></tr></thead><tbody>${reasonRows}</tbody></table>
    </details>
    <details class="card"><summary>Can the cart pass the bracket that joins the spine to the track (on the top and bottom run), and the pipe?</summary>
      <table class="runs"><thead><tr><th>Run</th><th>Roll</th><th>Spine bracket</th><th>Pipe</th></tr></thead><tbody>${passRows}</tbody></table>
      <p class="hint">The cart is driven along the straight part of the run (arm folded) with the cart rolled about the track pipe's own axis by the angle shown; "touches" is the deepest overlap in mm. On the legs (where the cart stands for the tests above) there is no bracket in the way, only on the runs.</p>
    </details>
    <details class="card"><summary>What would make the holes reachable (study, no collision test)</summary>
      <p class="hint">Rolling the cart 180° about leg A's own axis puts the plate and the arm in FRONT of the track (arm base 109 mm in front of the track plane, 60 mm outside the loop) with the arm pointing at the front of the tank, so it faces the tray side, not the spine: it does not point at the pipe, and no hole is reached. Study (scripts/reach-variants.ts; distance, angle and joint limits only, cart on both legs, 20 mm steps): with the plate in front of the track and the arm pointing at the spine (the cart mirrored, not rolled) 7 of the 24 holes are reachable (H1, H5, H7, H11, H13, H17, H19); the same with the arm base 100 mm inside the loop (from the leg) instead of 60 mm, 10 holes (H1, H3, H5 … every odd hole to H19); the best mount found, arm base 200 mm in front of the track plane and 150 mm inside the loop, 15 of the 24. None of the 16 pods is reached by any mount: they need the cart at the bottom run, where, with today's mount, rolled 180°, P15 is 3 mm and P9 5 mm out of reach.</p>
    </details>
    <details class="card">
      <summary>About this scene</summary>
      <p class="hint">The unit, track, cart (one sleeve on the −y leg), straight 90° pod holder and tank are those of the Transplant scene. The 24 holes are the unit's own planting-site rule (cad/unit_v1_assembly.py): three columns 120° apart round the growing pipe, every other level turned 60°, 130 mm between levels, the lowest at ${HOLES[0].z.toFixed(3)} m, eight levels (the rule gives nine with today's pipe top; the ninth, at 1.694 m, is left out to make 24). Each has its collar, seat, plug holder and plug (cad/pipe_collar.py). The 16 pods stand in a 4 × 4 tray (45 mm between columns, 38 mm between rows) flat on two rails in the front half of the tank, under the lid, and are reached through 16 pick holes (34 mm, silicone collar) in the lid, exactly as in the Pod grab scene; the sloping pod store with its 6 pick holes is there too, and the central pipe is the spine.</p>
      <p class="hint">The test tries the cart at every height of the straight part of both legs (leg A, the one it stands on, and leg B; ${0.635} to ${1.67} m, 5 mm steps) and along the straight part of the bottom and top run (5 mm steps), as is and rolled 180° about the pipe's own axis (the arm then stands on the other side of the pipe, pointing the other way); the best station is kept for each part. Other roll angles (30° steps) are tried too and listed under the red parts, but do not change the colour. A height passes when the arm can put the hand on the cap with the hand within ${ANGLE_TOL}° of the part's axis, also at a waiting point 60 mm out along the axis, inside all joint limits, with no contact of arm, cart or the part itself against anything. The SO-101 can point its hand only along a plane through its base axis, which is why the cart height matters.</p>
    </details>
    <p id="r-msg" class="hint"></p>
`;
    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    let sel: Target | null = null, showRolled = false;
    const show = () => {
      let text = 'Nothing picked: arm folded', cart = '', pose: { st: Station; z: number; j: Attempt["joints"] } = { st: ROLLED_HOME, z: 1.0, j: { A: 0, B: 0, C: 0, D: 0, E: 0 } };
      if (sel) {
        const a = showRolled ? sel.rolled : sel.direct;
        text = `${sel.label}: ${COLOUR[sel.colour].word}`;
        if (a.ok) { pose = { st: a.station!, z: a.station!.at, j: a.joints }; cart = a.station!.label;
          const j = a.joints!; $('r-text').textContent = `${sel.label}. ${describe(a)}. Joints: ${(['A', 'B', 'C', 'D'] as const).map((k) => `${NAMES[k]} ${j[k].toFixed(0)}°`).join(', ')}.`; }
        else { cart = 'arm folded, ' + ROLLED_HOME.label; $('r-text').textContent = `${sel.label}. ${showRolled ? 'Rolled 180°' : 'As is'}: ${describe(a)}.${a.looseErr !== undefined ? ` (The point can be reached with the hand ${a.looseErr.toFixed(0)}° off the axis.)` : ''}`; }
      } else $('r-text').textContent = 'Pick a hole or a pod. Green parts the arm reaches as the cart is, amber ones only after the cart is rolled 180° about its leg of the track, red ones not at all.';
      rig.pose(pose.st, pose.j ?? null, JAW_CAP_DEG);
      const { depth, names } = worstContact(model, data);
      $('r-now').textContent = text; $('r-cart').textContent = cart || `${ROLLED_HOME.label}`;
      const hit = $('r-hit'); hit.textContent = depth < 0 ? `FAIL: ${names} touched (${(-depth * 1000).toFixed(1)} mm)` : 'none (arm, cart and the part against pipe, collars, other plugs and pods, tank, track)'; hit.style.color = depth < 0 ? '#c0392b' : '';
      ($('r-direct') as HTMLButtonElement).disabled = !sel || !sel.direct.ok; ($('r-rolled') as HTMLButtonElement).disabled = !sel || !sel.rolled.ok;
    };
    panel.querySelectorAll<HTMLButtonElement>('[data-t]').forEach((b) => b.addEventListener('click', () => {
      sel = results.find((t) => t.id === b.dataset.t)!; showRolled = !sel.direct.ok && sel.rolled.ok; show();
      if (sel.kind === 'pod') viewer.setView(VIEWS.tray); else viewer.setView({ ...VIEWS.pipe, target: [0, 0, sel.z] });
    }));
    $('r-direct').addEventListener('click', () => { showRolled = false; show(); });
    $('r-rolled').addEventListener('click', () => { showRolled = true; show(); });
    $('r-fold').addEventListener('click', () => { sel = null; showRolled = false; show(); });
    panel.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((b) => b.addEventListener('click', () => viewer.setView(VIEWS[b.dataset.view!])));
    show();
    void RESULT_RGB;

    return {
      frame() { viewer.render(); },
      dispose() { viewer.dispose(); data.delete(); model.delete(); panel.innerHTML = ''; },
    };
  },
};
