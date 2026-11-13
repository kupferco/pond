// Pod-grab scene: a close-up of the bottom of a unit. The cart rides the bottom pipe, the arm on it reaches into the tank,
// takes pods out of the sloped store rows by a pin through the lid and the pod hole and lowers them into the silicone collars of the horizontal 4 × 4 seedling tray.
// Same layout as the Cart scene (status card, Step and Task tabs).
import { CommandLayer } from '../commands.ts';
import { SimDriver } from '../drivers/simDriver.ts';
import { RealDriver } from '../drivers/realDriver.ts';
import { MOTORS } from '../model.ts';
import { Viewer } from '../viewer.ts';
import { rng } from '../arm/placement.ts';
import { CART_X_MAX, CART_X_MIN, STORE_ROWS, TRAY_COLS, TRAY_SLOTS, podGrabMjcf, slotLabel } from '../podgrab/layout.ts';
import { COLLAR_TOL, HOLE_TOL, PodTask, PodWorld, fillJobs, type JobResult } from '../podgrab/task.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'pod-grab')!;
const esc = (v: unknown) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const ARM_MOTORS = MOTORS.filter((m) => m.id !== 'F'); // the pin has no jaw
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
    const rowOptions = Array.from({ length: STORE_ROWS }, (_, i) => `<option value="${i}">Store row ${i + 1}</option>`).join('');
    panel.innerHTML = `
    <h1>Pond pod grab</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Seedling tray</dt><dd><strong id="g-tray">0</strong> of ${TRAY_SLOTS} sockets filled</dd>
        <dt>Pod store</dt><dd id="g-store"></dd>
        <dt>Cart</dt><dd id="g-cart"></dd>
        <dt>State</dt><dd id="g-state">Idle</dd>
      </dl>
      <p class="hint">A close-up of the bottom of a Pond unit, in its real layout. The cart rides the bottom track pipe above the tank; the SO-101 arm is fixed on top of its plate and reaches down into the tank through the silicone pick holes in the lid. The grey pillar in the middle is the unit spine; the trays hang off it on flat brackets and stand clear of it. Right: the pod store, ${STORE_ROWS} rows under the lid, sloped so the pods slide to the pick hole at the front (the little roof keeps the second pod in place while the first is lifted out). Left: the seedling tray, flat, ${TRAY_COLS} × ${TRAY_SLOTS / TRAY_COLS} silicone collars, rows A to D from the front.</p>
    </section>
    <p id="g-msg" class="msg"></p>

    <div class="tabs" role="tablist">
      <button role="tab" data-tab="step" aria-selected="true">Step</button>
      <button role="tab" data-tab="task" aria-selected="false">Task</button>
    </div>

    <div class="tabpane" data-pane="step">
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

    <div class="tabpane" data-pane="task" hidden>
      <p><strong>Fill the seedling tray.</strong> For each socket the cart drives to a store row, the pin goes down through the lid and the hole of the first pod and lifts it up and out (the pods behind slide down one place), the cart drives to the socket and the pod is lowered into its silicone collar. Pods are taken row by row, so the tray ends up filled from several rows.</p>
      <div class="xy stepbar">
        <label>Speed <select class="lock tall" id="g-speed" aria-label="Speed"><option value="1">1×</option><option value="4" selected>4×</option><option value="0">Max</option></select></label>
      </div>
      <div class="row wrap">
        <button class="lock big grow" id="g-fill">Fill the whole tray</button>
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
      <div class="row"><button class="lock big" id="g-reset">Reset scene</button></div>
      <details class="more"><summary>How success is judged</summary><p class="hint">The controller sees the hole and the collar with 0.8 mm of simulated perception noise. The pin must be within ${HOLE_TOL * 1000} mm of the hole axis to get through, and the pod must be within ${(COLLAR_TOL * 1000).toFixed(1)} mm of the collar axis when it is lowered; then it is let go and has to stay standing in the collar. The pods are real bodies: they slide down the 12° slope, stop at the front stop and are held by the rails and the roof. Carrying a pod on the pin is kinematic (the real hand has an expanding collet). Every step checks that no pod appears, disappears or jumps, and that the arm touches nothing of the unit; a run fails with the reason if one does. Pod 25 × 40 mm with a 14 mm hole is assumed, as in cad/pod_store.py; the layout follows cad/unit_v3_dimensioned.py, cad/pod_store_reach.py and the arm-on-cart drawing cad/cart_arm.py.</p></details>
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
      $('g-cart').textContent = `${(world.cartX * 100).toFixed(1)} cm along the pipe`;
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
    $('g-reset').addEventListener('click', () => { world.reset(); cmd.home(); result.hidden = true; stateEl.textContent = 'Idle'; say(''); showCounts(); });

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
          if (speed > 0) task.advance(Math.min(dt, 0.1) * speed);
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
