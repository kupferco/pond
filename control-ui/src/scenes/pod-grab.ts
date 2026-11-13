// Pod-grab scene: the arm takes a pod out of the store and puts it into a socket of the seedling tray.
// Same layout as the Cart scene (status card, Step and Task tabs); the controller is the Arm scene's scripted pick-and-place.
import { CommandLayer } from '../commands.ts';
import { SimDriver } from '../drivers/simDriver.ts';
import { RealDriver } from '../drivers/realDriver.ts';
import { MOTORS } from '../model.ts';
import { Viewer } from '../viewer.ts';
import { Attempt, POS_TOL_MM, TILT_TOL_DEG, type AttemptResult } from '../arm/attempt.ts';
import { rng } from '../arm/placement.ts';
import {
  MARK_POD, MARK_SLOT, MARK_Z, STORE_PODS, TRAY_SLOTS, podGrabMjcf, podName, slotName,
} from '../podgrab/layout.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'pod-grab')!;
const esc = (v: unknown) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const unitOf = (m: (typeof MOTORS)[number]) => (m.linear ? 'mm' : '°');
const seedNow = () => Math.floor(Math.random() * 0x7fffffff);
const PHASE_LABEL: Record<string, string> = {
  approach: 'Moving above the pod', descend: 'Going down to the pod', grasp: 'Closing the gripper', lift: 'Lifting the pod out of the store',
  move: 'Carrying it to the tray', lower: 'Lowering into the socket', release: 'Opening the gripper', retreat: 'Moving away', done: 'Done',
};

export const podGrabScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const sim = new SimDriver(mujoco, podGrabMjcf());
    const cmd = new CommandLayer(sim, new RealDriver());
    const viewer = new Viewer(view, sim);
    status.textContent = '';

    panel.innerHTML = `
    <h1>Pond pod grab</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Pod</dt><dd id="g-pod">Store pod 1</dd>
        <dt>Target</dt><dd id="g-slot">Tray socket 1</dd>
        <dt>State</dt><dd id="g-state">Idle</dd>
      </dl>
      <p class="hint">The arm sits at the origin. The pods stand in a row in the store (right, ${STORE_PODS.length} pods, pod 1 nearest the arm); the seedling tray with ${TRAY_SLOTS.length} sockets is on the left. The orange dots mark the chosen pod and socket.</p>
    </section>
    <p id="g-msg" class="msg"></p>

    <div class="tabs" role="tablist">
      <button role="tab" data-tab="step" aria-selected="true">Step</button>
      <button role="tab" data-tab="task" aria-selected="false">Task</button>
    </div>

    <div class="tabpane" data-pane="step">
      <label class="stepsize">Step size <input class="lock" id="g-step" type="number" inputmode="decimal" min="0.1" step="any" value="10" aria-label="Step size"> <span class="hint">° (mm for linear joints)</span></label>
      <div class="steprows">${MOTORS.map((m) => `
        <div class="steprow" data-step-row="${m.id}">
          <div class="sr-info"><span class="id">${m.id}</span><span class="sr-name">${m.label}<small>${m.min} to ${m.max}${unitOf(m)}</small></span></div>
          <div class="sr-ctl">
            <button class="lock stepbtn" data-dir="-1" aria-label="Motor ${m.id} minus step">−</button>
            <span class="sr-val"><span class="now" data-target="${m.id}">0.0</span><small class="sr-lim" data-lim="${m.id}"></small></span>
            <button class="lock stepbtn" data-dir="1" aria-label="Motor ${m.id} plus step">+</button>
          </div>
        </div>`).join('')}
      </div>
      <p class="hint">Each tap moves one joint by one step. Use the Task tab to let the arm do the whole grab by itself.</p>
      <div class="row"><button class="lock big" id="g-home">Home</button></div>
    </div>

    <div class="tabpane" data-pane="task" hidden>
      <p><strong>Grab a pod from the store and put it in the tray.</strong> Scripted controller: inverse kinematics, then approach, descend, grasp, lift, move, lower, release, retreat. Every run starts from a fresh scene (all pods back in the store).</p>
      <div class="xy stepbar">
        <label>Pod <select class="lock tall" id="g-pod-sel" aria-label="Pod to grab">${STORE_PODS.map((_, i) => `<option value="${i}">Store pod ${i + 1}</option>`).join('')}</select></label>
        <label>Target <select class="lock tall" id="g-slot-sel" aria-label="Tray socket">${TRAY_SLOTS.map((_, i) => `<option value="${i}">Tray socket ${i + 1}</option>`).join('')}</select></label>
        <label>Speed <select class="lock tall" id="g-speed" aria-label="Speed"><option value="1">1×</option><option value="4" selected>4×</option><option value="0">Max</option></select></label>
      </div>
      <div class="row wrap">
        <button class="lock big grow" id="g-go">Grab and move</button>
        <button class="lock big grow" id="g-rand">Randomize</button>
      </div>
      <div class="row"><button class="lock big" id="g-reset">Reset scene</button></div>
      <details class="more"><summary>How success is judged</summary><p class="hint">Success = pod seated in the socket within ${POS_TOL_MM} mm and ${TILT_TOL_DEG}° of the seat pose. The controller sees the pod and socket with 1.2 mm of simulated perception noise. Grasp and release are kinematic (no contact physics yet). Pod 25 × 40 mm and the 28 mm pod pitch are assumed, as in cad/pod_store.py.</p></details>
      <div id="g-result" class="result" hidden></div>
    </div>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const msg = $('g-msg'), stateEl = $('g-state'), result = $('g-result');
    const podSel = $<HTMLSelectElement>('g-pod-sel'), slotSel = $<HTMLSelectElement>('g-slot-sel');
    const say = (t: string, err = false) => { msg.textContent = t; msg.className = err ? 'msg err' : 'msg'; };
    const guard = (fn: () => void) => { try { fn(); } catch (e) { say((e as Error).message, true); } };

    // --- scene: which pod and socket are chosen
    const showChoice = () => {
      const p = Number(podSel.value), s = Number(slotSel.value);
      $('g-pod').textContent = `Store pod ${p + 1}`;
      $('g-slot').textContent = `Tray socket ${s + 1}`;
      sim.setMocap(MARK_POD, [STORE_PODS[p][0], STORE_PODS[p][1], MARK_Z]);
      sim.setMocap(MARK_SLOT, [TRAY_SLOTS[s][0], TRAY_SLOTS[s][1], MARK_Z]);
      mujoco.mj_forward(sim.model, sim.data);
    };
    podSel.addEventListener('change', showChoice);
    slotSel.addEventListener('change', showChoice);
    showChoice();

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
      const m = MOTORS.find((x) => x.id === id)!;
      const step = parseFloat(stepSize.value);
      if (!(step > 0)) return say('Step size must be a positive number', true);
      const want = (cmd.driver.targets()[id] ?? 0) + dir * step;
      const applied = cmd.setJointTarget(id, want);
      const hit = Math.abs(applied - want) > 1e-9;
      showLimit(id, hit ? (dir > 0 ? 'max limit' : 'min limit') : '');
      say(hit ? `Motor ${id} limited to ${applied}${unitOf(m)}` : '');
    });
    panel.querySelectorAll<HTMLButtonElement>('.steprow .stepbtn').forEach((b) => b.addEventListener('click', () => nudge(b.closest<HTMLElement>('.steprow')!.dataset.stepRow!, Number(b.dataset.dir) as 1 | -1)));
    $('g-home').addEventListener('click', () => guard(() => { cmd.home(); MOTORS.forEach((m) => showLimit(m.id, '')); say(''); }));

    // --- task tab
    let attempt: Attempt | null = null;
    const setBusy = (busy: boolean) => {
      panel.querySelectorAll<HTMLInputElement | HTMLButtonElement | HTMLSelectElement>('.lock').forEach((el) => { el.disabled = busy; });
      panel.classList.toggle('busy', busy);
    };
    const start = () => {
      say(''); setBusy(true);
      result.hidden = true;
      const p = Number(podSel.value), s = Number(slotSel.value);
      attempt = new Attempt(sim, cmd, { pod: STORE_PODS[p], slot: TRAY_SLOTS[s], seed: seedNow(), podBody: podName(p), slotBody: slotName(s) });
      showChoice();
    };
    $('g-go').addEventListener('click', start);
    $('g-rand').addEventListener('click', () => {
      const r = rng(seedNow());
      podSel.value = String(Math.floor(r() * STORE_PODS.length));
      slotSel.value = String(Math.floor(r() * TRAY_SLOTS.length));
      start();
    });
    $('g-reset').addEventListener('click', () => { sim.reset(); showChoice(); result.hidden = true; stateEl.textContent = 'Idle'; say(''); });

    const resultHtml = (r: AttemptResult) => `
      <div class="verdict ${r.success ? 'ok' : 'bad'}">${r.success ? '✓ Success' : '✗ Failed'}: ${esc(r.reason)}</div>
      <dl><dt>Position error</dt><dd>${r.posErrMm.toFixed(1)} mm</dd><dt>Orientation error</dt><dd>${r.tiltErrDeg.toFixed(1)}°</dd><dt>Time</dt><dd>${r.durationS.toFixed(1)} s</dd></dl>`;

    // --- frame loop
    const text = (sel: string, f: (id: string) => string) => panel.querySelectorAll<HTMLElement>(sel).forEach((el) => { el.textContent = f(el.dataset.target!); });
    let sinceUi = 1;
    return {
      frame(dt: number) {
        if (attempt) {
          const t0 = performance.now();
          const speed = parseFloat($<HTMLSelectElement>('g-speed').value);
          if (speed > 0) attempt.advance(Math.min(dt, 0.1) * speed);
          else while (!attempt.done && performance.now() - t0 < 14) attempt.advance(0.05);
          if (attempt.done) {
            result.hidden = false; result.innerHTML = resultHtml(attempt.result!);
            stateEl.textContent = attempt.result!.success ? 'Pod in the tray' : 'Failed';
            attempt = null; setBusy(false);
          } else stateEl.textContent = PHASE_LABEL[attempt.phaseName] ?? attempt.phaseName;
        } else {
          sim.advance(dt);
        }
        sinceUi += dt;
        if (sinceUi > 0.1) { sinceUi = 0; const t = cmd.driver.targets(); text('[data-target]', (id) => (t[id] ?? 0).toFixed(1)); }
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
