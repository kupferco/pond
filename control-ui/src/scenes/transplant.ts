// Transplant seedling scene: one trip with the cart on its track and the arm on the cart. Step through it with one button per step, or play it all.
// The four steps and the geometry are in src/transplant/ (the choreography is scripted and kinematic, like the Transfer scene; every frame is checked for contacts).
import { Viewer } from '../viewer.ts';
import { Binder, worstContact } from '../transplant/apply.ts';
import { CART_Z0, CART_Z1, CART_ZP, ZH, YC, transplantMjcf } from '../transplant/layout.ts';
import { STEPS, TransplantRun } from '../transplant/task.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'transplant')!;
const VIEWS: Record<string, { target: [number, number, number]; dist: number; az: number; el: number }> = {
  overview: { target: [0.1, 0.1, 0.95], dist: 3.2, az: 0.5, el: 0.2 },
  tray: { target: [-0.1, YC, 0.5], dist: 0.8, az: 0.5, el: 0.25 },
  hole: { target: [-0.03, 0.1, ZH], dist: 0.8, az: 0.6, el: 0.2 },
};

export const transplantScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const model = mujoco.MjModel.from_xml_string(transplantMjcf());
    const data = new mujoco.MjData(model);
    const bind = new Binder(mujoco, model, data);
    const viewer = new Viewer(view, { mujoco, model, data }, { ...VIEWS.overview, maxDist: 5, far: 30 });
    status.textContent = '';
    const run = new TransplantRun();

    panel.innerHTML = `
    <h1>Pond transplant seedling</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Now</dt><dd id="x-now">Ready</dd>
        <dt>Cart height</dt><dd id="x-cart"></dd>
        <dt>Seedling</dt><dd id="x-pod"></dd>
        <dt>Plug</dt><dd id="x-plug"></dd>
        <dt>Hole open</dt><dd id="x-hole">closed (plug in)</dd>
        <dt>Contacts</dt><dd id="x-hit">none</dd>
      </dl>
    </section>
    <h2>Steps</h2>
    <div class="steprows" id="x-steps">${STEPS.map((s, i) => `<div class="row"><button class="big grow" data-step="${i}" title="${s.text}">${s.title}</button></div>`).join('')}</div>
    <p class="hint" id="x-text"></p>
    <div class="row">
      <button class="big grow" id="x-all">Play all</button>
      <button class="big grow" id="x-reset">Reset</button>
    </div>
    <div class="xy stepbar">
      <label>Speed <select class="tall" id="x-speed" aria-label="Speed"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select></label>
    </div>
    <div class="row">
      <button class="big grow" data-view="overview">Overview</button>
      <button class="big grow" data-view="tray">Seedling tray</button>
      <button class="big grow" data-view="hole">Hole</button>
    </div>
    <details class="card">
      <summary>About this scene</summary>
      <p class="hint">One pipe: the growing pipe with its collar (pod seat at 45° up, hole 45 mm, plug holder 44 mm below, from cad/pipe_collar.py), standing on the tank (700 × 400 × 300 mm, from cad/unit_v3_aframe.py) with the seedling tray on the tank lid. One track: the unit's rounded-corner portrait loop of cad/unit_v3_dimensioned.py, 60 mm in front of the pipe, joined to the spine by its top and bottom brackets. The cart is the Transfer scene's cart: ONE of its two hands (one sleeve) rides a leg of the track, the other hand hangs open (it is only for transfers between pipes). Plate, battery, SO-101 stand-in arm and the seedling pod holder come from cad/cart_dims.py and cad/cart_pod_holder.py. One press per step; Play all runs what is left. The arm is posed by inverse kinematics and every frame is checked for contacts (arm, cart, pod and plug against the pipe, track, collar, holder and tray); the line above turns red if anything touches.</p>
      <p class="hint">Assumed (not in the CAD): the hole is ${ZH.toFixed(2)} m up and the collar faces 132° round the pipe. The SO-101 can only point its hand along a plane through its base axis, so the cart stops at three heights: ${CART_Z0.toFixed(2)} m at the tray, ${CART_Z1.toFixed(2)} m at the hole and ${CART_ZP.toFixed(2)} m at the plug holder. Known gap: the pod holder is exactly where cad/cart_pod_holder.py puts it, and there the SO-101 cannot reach the pod in it, so the arm stands still (and the pod is placed in or taken from the holder) during those moves.</p>
    </details>
    <p id="x-msg" class="hint"></p>
`;
    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const stepBtns = Array.from(panel.querySelectorAll<HTMLButtonElement>('[data-step]'));
    let failed = 0, lastNames = '', lastDepth = 0;
    const sync = () => { run.speed = Number($<HTMLSelectElement>('x-speed').value); };
    stepBtns.forEach((b) => b.addEventListener('click', () => { sync(); run.step(); }));
    $('x-all').addEventListener('click', () => { sync(); run.playAll(); });
    $('x-reset').addEventListener('click', () => { run.reset(); failed = 0; lastNames = ''; });
    panel.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((b) => b.addEventListener('click', () => viewer.setView(VIEWS[b.dataset.view!])));
    $<HTMLSelectElement>('x-speed').addEventListener('change', sync);

    const placeText: Record<string, string> = { tray: 'in the tray', cup: 'in the cart holder', seat: 'in the hole', park: 'parked in the plug holder', hand: 'in the hand' };
    const update = () => {
      if (!bind.apply(run.pose)) run.unreachable = 'out of reach';
      const { depth, names } = worstContact(model, data);
      if (depth < 0) { failed++; lastNames = names; lastDepth = depth; }
      const hit = $('x-hit');
      hit.textContent = failed ? `FAIL: ${lastNames} touched (${(-lastDepth * 1000).toFixed(1)} mm, ${failed} frames)` : 'none (arm, cart, pod and plug against pipe, collar, holder, tray)';
      hit.style.color = failed ? '#c0392b' : '';
      $('x-now').textContent = run.label + (run.unreachable ? ' — out of reach' : '');
      $('x-cart').textContent = `${run.pose.cartZ.toFixed(2)} m` + (run.pose.cartZ > CART_Z0 + 1e-6 ? (run.pose.cartZ >= CART_Z1 - 1e-6 ? ' (at the hole)' : ' (driving)') : ' (at the seedling tray)');
      $('x-pod').textContent = placeText[run.pose.places.pod];
      $('x-plug').textContent = placeText[run.pose.places.plug];
      $('x-hole').textContent = run.holeOpen ? `open for ${run.holeOpenS.toFixed(1)} s` : run.holeTimes.length ? `closed again after ${run.holeTimes[0].toFixed(1)} s` : 'closed (plug in)';
      stepBtns.forEach((b, i) => { b.disabled = run.busy || i !== run.next; b.classList.toggle('done', i < run.next); });
      ($('x-all') as HTMLButtonElement).disabled = run.busy || run.next >= STEPS.length;
      $('x-text').textContent = run.next < STEPS.length ? `Next: ${STEPS[run.next].text}` : 'All four steps done. Press Reset to start again.';
    };
    update();

    return {
      frame(dt: number) {
        run.advance(Math.min(dt, 0.1));
        update();
        viewer.render();
      },
      dispose() {
        viewer.dispose();
        data.delete();
        model.delete();
        panel.innerHTML = '';
      },
    };
  },
};
