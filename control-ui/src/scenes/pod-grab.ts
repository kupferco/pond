// Pod-grab scene: a close-up of the bottom of a unit. The cart rides the bottom pipe, the arm on it reaches into the tank,
// takes pods out of the sloped store rows by a two-finger claw through the lid and lowers them into the 6 × 3 seedling tray.
// Same layout as the Cart scene (status card, Step and Task tabs).
import { CommandLayer } from '../commands.ts';
import { SimDriver } from '../drivers/simDriver.ts';
import { RealDriver } from '../drivers/realDriver.ts';
import { MOTORS } from '../model.ts';
import { Viewer } from '../viewer.ts';
import { rng } from '../arm/placement.ts';
import { CART_X_MAX, CART_X_MIN, SLOPE, STORE_ROWS, TRAY_COLS, TRAY_SLOTS, TRANSIT_PITCH, podGrabMjcf, slotLabel } from '../podgrab/layout.ts';
import { COLLAR_TOL, HOLE_TOL, PodTask, PodWorld, fillJobs, type JobResult } from '../podgrab/task.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'pod-grab')!;
const esc = (v: unknown) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const ARM_MOTORS = MOTORS.filter((m) => m.id !== 'F'); // the claw is opened and closed by the task, not by the jaw motor
const unitOf = (m: (typeof MOTORS)[number]) => (m.linear ? 'mm' : '°');
const seedNow = () => Math.floor(Math.random() * 0x7fffffff);

export const podGrabScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const sim = new SimDriver(mujoco, podGrabMjcf());
    const cmd = new CommandLayer(sim, new RealDriver());
    const world = new PodWorld(sim);
    const viewer = new Viewer(view, sim, { target: [-0.05, -0.06, 0.4], dist: 1.15, maxDist: 3, az: 0.5, el: 0.3, far: 20 });
    status.textContent = '';

    const slotOptions = Array.from({ length: TRAY_SLOTS }, (_, i) => `<option value="${i}">Socket ${slotLabel(i)}</option>`).join('');
    const rowOptions = Array.from({ length: STORE_ROWS }, (_, i) => `<option value="${i}">Store lane ${i + 1}</option>`).join('');
    panel.innerHTML = `
    <h1>Pond pod grab</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Seedling tray</dt><dd><strong id="g-tray">0</strong> of ${TRAY_SLOTS} sockets filled</dd>
        <dt>Pod store</dt><dd id="g-store"></dd>
        <dt>Cart</dt><dd id="g-cart"></dd>
        <dt>State</dt><dd id="g-state">Idle</dd>
      </dl>
    </section>
    <div class="row wrap controls">
      <button class="lock big grow" id="g-fill">Fill the whole tray</button>
      <button class="big grow" id="g-stop" disabled>Stop</button>
      <button class="big grow" id="g-reset">Reset scene</button>
    </div>
    <p id="g-msg" class="msg"></p>
    <p class="hint">A close-up of the bottom of a Pond unit, in its real layout (the unit CAD, cad/pond_unit_bottom.py, no offsets of its own). The omni cart stays upright and rides the bottom track pipe on its top hand (the bottom hand is closed, taking less room); the 18 mm slot in each sleeve faces the spine and the spine-to-track bracket passes through it. The SO-101 arm is bolted straight on the cart plate, centred, with the battery beside it, and has a real 160 mm claw. Right: the gravity-feed pod store under the lid: ${STORE_ROWS} lanes sloping at ${(SLOPE * 180 / Math.PI).toFixed(0)}° towards the front, each ending in a flat landing with a stop lip at the front row, so the pod being picked stands vertical and the next one slides forward onto the landing when it is lifted (4 pods per lane, ${STORE_ROWS * 4} in all; the slope is an assumption to test with the real dry pots). Left: the seedling tray, ${TRAY_COLS} × ${TRAY_SLOTS / TRAY_COLS} cells under the lid, rows A to C from the front; pods stand vertical in it. The lid has slots about 70 × 50 mm over the cells and the lanes; at the 35 mm and 30 mm pitch they run together into one window over the tray and one over the store. The arm can only hold the claw straight down when the pin is below about 225 mm, but the lid is at 304, so over the lid the claw is tilted (${TRANSIT_PITCH}°) and straightens as it goes down through the slot; beyond the cart's straight run (x ±140 mm, the corners are not used: the cart would tilt) the pan joint reaches sideways. The water testing station stands on the lid behind the track as a solid block. The reach and collision results of this layout are in the pull request.</p>

    <div class="tabs" role="tablist">
      <button role="tab" data-tab="task" aria-selected="true">Task</button>
      <button role="tab" data-tab="step" aria-selected="false">Step</button>
    </div>

    <div class="tabpane" data-pane="step" hidden>
      <label class="stepsize">Step size <input class="lock" id="g-step" type="number" inputmode="decimal" min="0.1" step="any" value="10" aria-label="Step size"> <span class="hint">° for joints, cm for the cart</span></label>
      <div class="steprows">
        <div class="steprow" data-step-row="cart">
          <div class="sr-info"><span class="id">X</span><span class="sr-name">Cart along the pipe<small>${(CART_X_MIN * 100).toFixed(0)} to ${(CART_X_MAX * 100).toFixed(0)} cm</small></span></div>
          <div class="sr-ctl">
            <button class="lock stepbtn" data-dir="-1" aria-label="Cart minus step">−</button>
            <span class="sr-val"><span class="now" id="g-cartnow">0.0</span><small class="sr-lim" data-lim="cart"></small></span>
            <button class="lock stepbtn" data-dir="1" aria-label="Cart plus step">+</button>
          </div>
        </div>${ARM_MOTORS.map((m) => `
        <div class="steprow" data-step-row="${m.id}">
          <div class="sr-info"><span class="id">${m.id}</span><span class="sr-name">${m.label}<small>${m.min} to ${m.max}${unitOf(m)}</small></span></div>
          <div class="sr-ctl">
            <button class="lock stepbtn" data-dir="-1" aria-label="Motor ${m.id} minus step">−</button>
            <span class="sr-val"><span class="now" data-target="${m.id}">0.0</span><small class="sr-lim" data-lim="${m.id}"></small></span>
            <button class="lock stepbtn" data-dir="1" aria-label="Motor ${m.id} plus step">+</button>
          </div>
        </div>`).join('')}
      </div>
      <p class="hint">Each tap moves the cart or one joint by one step. Use the Task tab to let the arm do the work by itself.</p>
      <div class="row"><button class="lock big" id="g-home">Home</button></div>
    </div>

    <div class="tabpane" data-pane="task">
      <p><strong>Fill the seedling tray.</strong> For each socket the cart drives to a store row, the open claw goes down through the lid slot, closes on the pod on the landing and lifts it up and out (the next pod in the lane slides onto the landing), the cart drives to the socket and the pod is lowered onto the tray. Pods are taken lane by lane.</p>
      <div class="xy stepbar">
        <label>Speed <select class="lock tall" id="g-speed" aria-label="Speed"><option value="1">1×</option><option value="4" selected>4×</option><option value="0">Max</option></select></label>
      </div>
      <p><strong>Or move one pod.</strong></p>
      <div class="xy stepbar">
        <label>From <select class="lock tall" id="g-row-sel" aria-label="Store row">${rowOptions}</select></label>
        <label>To <select class="lock tall" id="g-slot-sel" aria-label="Tray socket">${slotOptions}</select></label>
      </div>
      <div class="row wrap">
        <button class="lock big grow" id="g-go">Move one pod</button>
        <button class="lock big grow" id="g-rand">Randomize</button>
      </div>
      <details class="more"><summary>How success is judged</summary><p class="hint">The controller sees the hole and the collar with 0.8 mm of simulated perception noise. The open claw must be within ${HOLE_TOL * 1000} mm of the pod axis across the fingers to straddle the pod and pass the lid hole, and the pod must be within ${(COLLAR_TOL * 1000).toFixed(1)} mm of the collar axis when it is lowered; then it is let go and has to stay standing in the collar. The pods are real bodies: they slide down the ${(SLOPE * 180 / Math.PI).toFixed(0)}° ramp onto the flat landing and stop at the lip. Gripping is kinematic: once the claw is closed the pod is held between the fingers and follows the hand. Every step checks that no pod appears, disappears or jumps, and that the arm touches nothing of the unit; a run fails with the reason if one does. Pod 25 × 40 mm with a 14 mm hole is assumed, as in cad/pod_store.py; the layout follows cad/pond_unit_bottom.py.</p></details>
      <div id="g-result" class="result" hidden></div>
    </div>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const msg = $('g-msg'), stateEl = $('g-state'), result = $('g-result');
    const rowSel = $<HTMLSelectElement>('g-row-sel'), slotSel = $<HTMLSelectElement>('g-slot-sel');
    const say = (t: string, err = false) => { msg.textContent = t; msg.className = err ? 'msg err' : 'msg'; };
    const guard = (fn: () => void) => { try { fn(); } catch (e) { say((e as Error).message, true); } };

    const showCounts = () => {
      $('g-tray').textContent = String(world.trayCount);
      $('g-store').textContent = Array.from({ length: STORE_ROWS }, (_, r) => `${r + 1}: ${world.rowCount(r)}`).join('  ·  ') + '  pods per row';
      const hit = world.cartHit;
      $('g-cart').textContent = `${(world.cartX * 100).toFixed(1)} cm along the pipe` + (hit.ticks > 0 ? `; the sleeves touch the ${hit.names === 'spine_tube' ? 'spine' : 'track bracket'} (${(-hit.depth * 1000).toFixed(0)} mm into it at ${(hit.x * 100).toFixed(1)} cm)` : '');
      $('g-cartnow').textContent = (world.cartX * 100).toFixed(1);
    };
    showCounts();

    // --- tabs
    panel.querySelectorAll<HTMLElement>('.tabs [data-tab]').forEach((b) => b.addEventListener('click', () => {
      panel.querySelectorAll<HTMLElement>('.tabs [data-tab]').forEach((x) => x.setAttribute('aria-selected', String(x === b)));
      panel.querySelectorAll<HTMLElement>('.tabpane').forEach((p) => { p.hidden = p.dataset.pane !== b.dataset.tab; });
    }));

    // --- step tab
    const stepSize = $<HTMLInputElement>('g-step');
    const showLimit = (id: string, lim: string) => {
      const row = panel.querySelector<HTMLElement>(`[data-step-row="${id}"]`);
      if (!row) return;
      row.classList.toggle('atlimit', lim !== '');
      row.querySelector<HTMLElement>('[data-lim]')!.textContent = lim;
    };
    const nudge = (id: string, dir: 1 | -1) => guard(() => {
      const step = parseFloat(stepSize.value);
      if (!(step > 0)) return say('Step size must be a positive number', true);
      if (id === 'cart') {
        const want = world.cartX + dir * step / 100;
        world.setCart(want);
        const hit = Math.abs(world.cartX - want) > 1e-9;
        showLimit(id, hit ? (dir > 0 ? 'end of pipe' : 'start of pipe') : '');
        say(hit ? 'The cart stops at the end of the pipe' : '');
        return;
      }
      const m = MOTORS.find((x) => x.id === id)!;
      const want = (cmd.driver.targets()[id] ?? 0) + dir * step;
      const applied = cmd.setJointTarget(id, want);
      const hit = Math.abs(applied - want) > 1e-9;
      showLimit(id, hit ? (dir > 0 ? 'max limit' : 'min limit') : '');
      say(hit ? `Motor ${id} limited to ${applied}${unitOf(m)}` : '');
    });
    panel.querySelectorAll<HTMLButtonElement>('.steprow .stepbtn').forEach((b) => b.addEventListener('click', () => nudge(b.closest<HTMLElement>('.steprow')!.dataset.stepRow!, Number(b.dataset.dir) as 1 | -1)));
    $('g-home').addEventListener('click', () => guard(() => { cmd.home(); ARM_MOTORS.forEach((m) => showLimit(m.id, '')); say(''); }));

    // --- task tab
    let task: PodTask | null = null;
    let shown = 0;
    const setBusy = (busy: boolean) => {
      panel.querySelectorAll<HTMLInputElement | HTMLButtonElement | HTMLSelectElement>('.lock').forEach((el) => { el.disabled = busy; });
      panel.classList.toggle('busy', busy);
      $<HTMLButtonElement>('g-stop').disabled = !busy;   // Stop is not a .lock button: it is the one control that works while a run is going
    };
    const start = (jobs: { row: number; slot: number }[]) => {
      say('');
      if (jobs.length === 0) return say('Nothing to do: the tray is full or the store is empty. Press Reset scene.', true);
      setBusy(true); result.hidden = true; shown = 0;
      task = new PodTask(world, cmd, { jobs, seed: seedNow() });
    };
    $('g-fill').addEventListener('click', () => start(fillJobs(world)));
    $('g-go').addEventListener('click', () => start([{ row: Number(rowSel.value), slot: Number(slotSel.value) }]));
    $('g-rand').addEventListener('click', () => {
      const r = rng(seedNow());
      const rows = Array.from({ length: STORE_ROWS }, (_, i) => i).filter((i) => world.rowCount(i) > 0);
      const slots = Array.from({ length: TRAY_SLOTS }, (_, i) => i).filter((i) => world.trayPod(i) < 0);
      if (!rows.length || !slots.length) return start([]);
      rowSel.value = String(rows[Math.floor(r() * rows.length)]);
      slotSel.value = String(slots[Math.floor(r() * slots.length)]);
      start([{ row: Number(rowSel.value), slot: Number(slotSel.value) }]);
    });
    $('g-stop').addEventListener('click', () => {
      if (!task) return;
      const n = task.results.length;
      task = null; setBusy(false); showCounts();
      stateEl.textContent = 'Stopped';
      say(`Stopped after ${n} pod${n === 1 ? '' : 's'} seated. Press Reset scene before starting a new run (the arm may be mid-move).`);
    });
    $('g-reset').addEventListener('click', () => { task = null; setBusy(false); world.reset(); cmd.home(); result.hidden = true; stateEl.textContent = 'Idle'; say(''); showCounts(); });

    const resultHtml = (t: PodTask) => {
      const rs: JobResult[] = t.results;
      const ok = t.failReason === '';
      const rows = rs.map((r) => `<dt>Socket ${slotLabel(r.job.slot)}</dt><dd>from row ${r.job.row + 1}, ${r.posErrMm.toFixed(1)} mm off, ${r.durationS.toFixed(1)} s</dd>`).join('');
      return `<div class="verdict ${ok ? 'ok' : 'bad'}">${ok ? `✓ Success: ${rs.length} pod${rs.length === 1 ? '' : 's'} seated` : `✗ Failed: ${esc(t.failReason)}`}</div>
      <dl>${rows}<dt>Time</dt><dd>${t.time.toFixed(1)} s</dd></dl>`;
    };

    // --- frame loop
    const text = (sel: string, f: (id: string) => string) => panel.querySelectorAll<HTMLElement>(sel).forEach((el) => { el.textContent = f(el.dataset.target!); });
    let sinceUi = 1;
    return {
      frame(dt: number) {
        if (task) {
          const t0 = performance.now();
          const speed = parseFloat($<HTMLSelectElement>('g-speed').value);
          // Never spend more than ~10 ms of a frame on physics, so the page keeps its frame rate: the run goes as fast as the
          // device allows, up to the chosen speed (the sim clock is the sim's own, so the result does not depend on it).
          if (speed > 0) { let left = Math.min(dt, 0.1) * speed; while (left > 1e-9 && !task.done && performance.now() - t0 < 10) { const c = Math.min(left, 0.02); task.advance(c); left -= c; } }
          else while (!task.done && performance.now() - t0 < 14) task.advance(0.05);
          if (task.done) {
            result.hidden = false; result.innerHTML = resultHtml(task);
            stateEl.textContent = task.failReason === '' ? 'Done' : 'Failed';
            task = null; setBusy(false); showCounts();
          } else {
            const n = task.cfg.jobs.length;
            stateEl.textContent = `Pod ${task.jobIndex + 1} of ${n}: ${task.label}`;
            if (task.results.length !== shown) { shown = task.results.length; showCounts(); }
          }
        } else {
          sim.advance(dt);
          world.tick(Math.min(dt, 0.1));
        }
        sinceUi += dt;
        if (sinceUi > 0.1) { sinceUi = 0; const t = cmd.driver.targets(); text('[data-target]', (id) => (t[id] ?? 0).toFixed(1)); showCounts(); }
        viewer.render();
      },
      dispose() {
        viewer.dispose();
        sim.dispose();
        panel.innerHTML = '';
      },
    };
  },
};
