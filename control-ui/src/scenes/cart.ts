// Cart scene: the omni-wheel cart riding a single pipe (up, bend, right), rolling about it (OpenPocket #282, plan task 265 part 8).
// Position is one coordinate, the distance along the track in cm; the cart's pose follows the path.
import { MARKER_HIDDEN_Z } from '../cart/model.ts';
import { bendTrim, omniTrackMjcf, placeOmniCart, trackContacts } from '../cart/omni-track.ts';
import { OMNI_R } from '../cart/omni.ts';
import { RollMotion, ROLL_DEG_S, canRoll, driveLimit, pickRollDirection, sweep } from '../cart/roll.ts';
import { RING_CM, POINT_CM, hall, runHoming } from '../cart/homing.ts';
import {
  ARRIVE_TOL_CM, CartMotion, DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, L_ARC, L_VERT, MAX_SPEED_CM_S, TRACK_LENGTH_CM,
  clampS, pathAt, randomTarget, type Section,
} from '../cart/track.ts';
import { Viewer } from '../viewer.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'cart')!;
const SECTION_LABEL: Record<Section, string> = { vertical: 'Vertical section', curve: 'Curve', horizontal: 'Horizontal section' };

export const cartScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const model = mujoco.MjModel.from_xml_string(omniTrackMjcf());
    const data = new mujoco.MjData(model);
    const sim = { mujoco, model, data };
    const viewer = new Viewer(view, sim, { target: [0.3, 0, 0.4], dist: 2.1, maxDist: 4, az: 0.45, el: 0.2, far: 20 });
    const markerMocap = model.body_mocapid[model.body('marker').id];
    status.textContent = '';

    panel.innerHTML = `
    <h1>Pond cart on track</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Position</dt><dd><strong id="c-pos">0.0</strong> cm of ${TRACK_LENGTH_CM.toFixed(1)} cm</dd>
        <dt>Section</dt><dd id="c-sec">Vertical section</dd>
        <dt>Goal</dt><dd id="c-goal">0.0 cm</dd>
        <dt>Roll</dt><dd><strong id="c-roll">0</strong>° (sensed <span id="c-rollest">0</span>°)</dd>
        <dt>Sensed position</dt><dd id="c-posest">0.0 cm</dd>
        <dt>Hall sensor</dt><dd id="c-hall">nothing</dd>
        <dt>Contact</dt><dd id="c-clear">clear</dd>
      </dl>
      <p class="hint">0 cm is the bottom of the vertical pipe; the track goes up, bends and runs to the right. Vertical: 0 to ${L_VERT.toFixed(1)} cm, curve: ${L_VERT.toFixed(1)} to ${(L_VERT + L_ARC).toFixed(1)} cm, horizontal: ${(L_VERT + L_ARC).toFixed(1)} to ${TRACK_LENGTH_CM.toFixed(1)} cm.</p>
    </section>

    <div class="tabs" role="tablist">
      <button role="tab" data-tab="step" aria-selected="true">Step</button>
      <button role="tab" data-tab="task" aria-selected="false">Task</button>
      <button role="tab" data-tab="roll" aria-selected="false">Roll</button>
    </div>

    <div class="tabpane" data-pane="step">
      <div class="xy stepbar">
        <label>Step <input class="tall" id="c-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
        <label>Speed <input class="tall" id="c-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
      </div>
      <div class="row wrap">
        <button class="big grow" id="c-up">▲ Up / forward</button>
        <button class="big grow" id="c-down">▼ Down / back</button>
      </div>
      <p class="hint">Each tap moves the goal by one step (taps add up). Up / forward moves toward ${TRACK_LENGTH_CM.toFixed(1)} cm, Down / back toward 0 cm; the cart stops at the track ends.</p>
      <div class="row"><button class="big" id="c-stop">Stop</button><button class="big" id="c-home">Back to 0</button></div>
    </div>

    <div class="tabpane" data-pane="roll" hidden>
      <p><strong>Roll the cart round the pipe.</strong> The whole base spins on the omni wheels. 0° is flat (the free hand on the inside of the bend). Only on the vertical legs, up to 180°; on the bend the roll is held; on the runs the cart stays flat.</p>
      <div class="xy stepbar">
        <label>Roll to <input class="tall" id="c-rollto" type="number" inputmode="decimal" min="-180" max="180" step="15" value="90" aria-label="Roll angle degrees"> °</label>
      </div>
      <div class="row wrap"><button class="big grow" id="c-rolldo">Roll</button><button class="big grow" id="c-rollflat">Back to flat</button></div>
      <label><input type="checkbox" id="c-carry"> Carry the roll through the bend (declared transfer roll)</label>
      <div class="row wrap"><button class="big grow" id="c-find">Find home (ring, then point)</button><button class="big grow" id="c-lose">Let the sensing drift</button></div>
      <p id="c-rollmsg" class="hint"></p>
    </div>

    <div class="tabpane" data-pane="task" hidden>
      <p><strong>Go to position.</strong> The cart drives to the target at the speed set on the Step tab and reports how it did.</p>
      <div class="xy stepbar">
        <label>Target <input class="tall" id="c-target" type="number" inputmode="decimal" min="0" max="${TRACK_LENGTH_CM.toFixed(1)}" step="1" placeholder="cm" aria-label="Target position cm"> cm</label>
        <label>Speed <input class="tall" id="c-speed2" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
      </div>
      <div class="row wrap">
        <button class="big grow" id="c-go">Go to position</button>
        <button class="big grow" id="c-rand">Randomize target</button>
      </div>
      <p id="c-msg" class="hint"></p>
      <div id="c-result" class="result" hidden></div>
    </div>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const motion = new CartMotion();
    const roll = new RollMotion();
    const RUN_START_CM = L_VERT + L_ARC;
    const DRIFT = 0.03;                                  // the sensing drifts 3 % of the distance driven and 5 % of the roll (wheel slip)
    let estS = 0, estRoll = 0;
    let seed = Math.floor(Math.random() * 0x7fffffff);
    let task: { target: number; start: number; t: number } | null = null;
    let targetMarker: number | null = null;

    // --- tabs
    panel.querySelectorAll<HTMLElement>('[data-tab]').forEach((b) => b.addEventListener('click', () => {
      panel.querySelectorAll<HTMLElement>('[data-tab]').forEach((x) => x.setAttribute('aria-selected', String(x === b)));
      panel.querySelectorAll<HTMLElement>('[data-pane]').forEach((p) => { p.hidden = p.dataset.pane !== b.dataset.tab; });
    }));

    // --- speed: one value shared by both tabs
    const speedIn = [$<HTMLInputElement>('c-speed'), $<HTMLInputElement>('c-speed2')];
    const readSpeed = () => {
      const v = parseFloat(speedIn[0].value);
      return Number.isFinite(v) && v > 0 ? Math.min(v, MAX_SPEED_CM_S) : DEFAULT_SPEED_CM_S;
    };
    speedIn.forEach((el, i) => el.addEventListener('input', () => { speedIn[1 - i].value = el.value; motion.speed = readSpeed(); }));
    motion.speed = readSpeed();
    const readStep = () => { const v = parseFloat($<HTMLInputElement>('c-step').value); return Number.isFinite(v) && v > 0 ? v : DEFAULT_STEP_CM; };

    // --- step tab
    const cancelTask = () => { task = null; };
    const nudge = (dir: 1 | -1) => { cancelTask(); motion.speed = readSpeed(); motion.nudge(dir * readStep()); };
    $('c-up').addEventListener('click', () => nudge(1));
    $('c-down').addEventListener('click', () => nudge(-1));
    $('c-stop').addEventListener('click', () => { cancelTask(); motion.moveTo(motion.s); });
    $('c-home').addEventListener('click', () => { cancelTask(); motion.speed = readSpeed(); motion.moveTo(0); });

    // --- task tab
    const msg = $('c-msg'), result = $('c-result'), targetIn = $<HTMLInputElement>('c-target');
    const setMarker = (s: number | null) => { targetMarker = s; };
    const startTask = (target: number) => {
      motion.speed = readSpeed();
      task = { target, start: motion.s, t: 0 };
      setMarker(target);
      motion.moveTo(target);
      result.hidden = true;
      msg.textContent = `Driving to ${target.toFixed(1)} cm…`;
    };
    $('c-go').addEventListener('click', () => {
      const v = parseFloat(targetIn.value);
      if (!Number.isFinite(v)) { msg.textContent = 'Enter a target position in cm, or tap Randomize target.'; return; }
      if (v < 0 || v > TRACK_LENGTH_CM) { msg.textContent = `The track runs from 0 to ${TRACK_LENGTH_CM.toFixed(1)} cm; the target was clamped.`; }
      const t = clampS(v);
      targetIn.value = String(t);
      startTask(t);
    });
    $('c-rand').addEventListener('click', () => {
      const t = randomTarget(seed++);
      targetIn.value = t.toFixed(1);
      startTask(t);
    });

    // --- roll tab
    const rollMsg = $('c-rollmsg'), carryIn = $<HTMLInputElement>('c-carry');
    const freeHandClears = (fromDeg: number, toDeg: number) => {   // the swept corridor at this position, free hand and base against the track
      for (const a of sweep(fromDeg, toDeg)) {
        placeOmniCart(model as any, data as any, motion.s, (a * Math.PI) / 180, bendTrim(motion.s), 0);
        mujoco.mj_forward(model, data);
        const c = trackContacts(model as any, data as any);
        if (c.freehand < -1e-9 || c.base < -1e-9) return false;
      }
      return true;
    };
    const startRoll = (target: number) => {
      cancelTask();
      if (motion.moving) motion.moveTo(motion.s);
      const full = Math.abs(target) >= 180;
      // Q3: when the direction is not given by the sign (a half turn), use the direction that clears
      const dirPick = full ? pickRollDirection({ plus: freeHandClears(roll.roll, 180), minus: freeHandClears(roll.roll, -180) }) : { dir: (target < 0 ? -1 : 1) as 1 | -1 | null };
      if (dirPick.dir === null) { rollMsg.textContent = dirPick.reason ?? ''; return; }
      const goal = full ? dirPick.dir * 180 : target;
      const v = canRoll(motion.s, goal);
      if (!v.ok) { rollMsg.textContent = v.reason ?? ''; return; }
      if (!freeHandClears(roll.roll, goal)) { rollMsg.textContent = 'The free hand or the base would touch the track on the way: not rolling.'; return; }
      roll.moveTo(goal);
      rollMsg.textContent = `Rolling to ${goal.toFixed(0)}° at ${ROLL_DEG_S.toFixed(0)}°/s.`;
    };
    $('c-rolldo').addEventListener('click', () => { const v = parseFloat($<HTMLInputElement>('c-rollto').value); if (Number.isFinite(v)) startRoll(Math.max(-180, Math.min(180, v))); });
    $('c-rollflat').addEventListener('click', () => startRoll(0));
    $('c-find').addEventListener('click', () => {
      cancelTask(); roll.goal = roll.roll; motion.moveTo(motion.s);
      const r = runHoming(motion.s, roll.roll, { slip: DRIFT, rollSlip: 0.05 });
      if (!r.ok) { rollMsg.textContent = `${r.reason} (${r.steps.join('; ')})`; return; }
      motion.s = motion.goal = POINT_CM + r.sErr; roll.roll = roll.goal = r.rollErr; estS = POINT_CM; estRoll = 0;
      rollMsg.textContent = `Home: ${r.steps.join('; ')}. Drove ${r.travelCm.toFixed(0)} cm and rolled ${r.rollDeg.toFixed(0)}°; left error ${r.sErr.toFixed(2)} cm and ${r.rollErr.toFixed(1)}°. Ring at ${RING_CM} cm, point at ${POINT_CM} cm.`;
    });
    $('c-lose').addEventListener('click', () => { estS += 4; estRoll += 25; rollMsg.textContent = 'The sensed position and roll are now off by 4 cm and 25°. Use Find home.'; });

    // --- per-frame
    const place = (mocap: number, s: number) => {
      const p = pathAt(s);
      data.mocap_pos[3 * mocap] = p.x; data.mocap_pos[3 * mocap + 1] = 0; data.mocap_pos[3 * mocap + 2] = p.z;
      data.mocap_quat[4 * mocap] = 1; data.mocap_quat[4 * mocap + 1] = 0; data.mocap_quat[4 * mocap + 2] = 0; data.mocap_quat[4 * mocap + 3] = 0;
    };
    const posEl = $('c-pos'), secEl = $('c-sec'), goalEl = $('c-goal'), rollEl = $('c-roll'), rollEstEl = $('c-rollest'), posEstEl = $('c-posest'), hallEl = $('c-hall'), clearEl = $('c-clear');
    const show = () => {
      posEl.textContent = motion.s.toFixed(1);
      secEl.textContent = SECTION_LABEL[pathAt(motion.s).section];
      goalEl.textContent = `${motion.goal.toFixed(1)} cm`;
      rollEl.textContent = roll.roll.toFixed(0); rollEstEl.textContent = estRoll.toFixed(0); posEstEl.textContent = `${estS.toFixed(1)} cm`;
      const h = hall(motion.s, roll.roll);
      hallEl.textContent = h.ring ? 'ring (home)' : h.point ? 'point (zero)' : 'nothing';
    };
    const update = () => {
      placeOmniCart(model as any, data as any, motion.s, (roll.roll * Math.PI) / 180, bendTrim(motion.s), (motion.s * 10) / OMNI_R);
      if (targetMarker === null) data.mocap_pos[3 * markerMocap + 2] = MARKER_HIDDEN_Z;
      else place(markerMocap, targetMarker);
      mujoco.mj_forward(model, data);
      const c = trackContacts(model as any, data as any);
      const hit = Math.min(c.rider, c.freehand, c.base);
      clearEl.textContent = hit < -1e-9 ? `touching the track by ${(-hit * 1000).toFixed(1)} mm (${c.rider < -1e-9 ? 'riding sleeve' : c.freehand < -1e-9 ? 'free hand' : 'base'})` : 'clear';
    };
    update(); show();

    return {
      frame(dt: number) {
        const d = Math.min(dt, 0.1);
        if (task) task.t += d;
        const rolling = roll.advance(d);
        if (rolling) rollMsg.textContent = `Rolled to ${roll.roll.toFixed(0)}°.`;
        if (roll.moving) motion.moveTo(motion.s);   // no driving while rolling
        const lim = driveLimit(motion.s, motion.goal, roll.roll, carryIn.checked, RUN_START_CM);
        if (lim.reason && lim.s !== motion.goal) { motion.moveTo(lim.s); rollMsg.textContent = lim.reason; if (task) { task = null; msg.textContent = lim.reason; } }
        const s0 = motion.s, r0 = roll.roll;
        const r = motion.advance(d);
        estS += (motion.s - s0) / (1 - DRIFT); estRoll += (roll.roll - r0) / (1 - 0.05);
        if (task && (r.arrived || !motion.moving)) {
          const err = motion.s - task.target;
          const ok = Math.abs(err) <= ARRIVE_TOL_CM;
          const sec: Section = pathAt(motion.s).section;
          result.hidden = false;
          result.innerHTML = `<div class="verdict ${ok ? 'ok' : 'bad'}">${ok ? 'Arrived' : 'Did not arrive'}</div>
            <dl><dt>Target</dt><dd>${task.target.toFixed(1)} cm</dd><dt>Final position</dt><dd>${motion.s.toFixed(2)} cm (${SECTION_LABEL[sec].toLowerCase()})</dd>
            <dt>Position error</dt><dd>${err.toFixed(2)} cm</dd><dt>Distance driven</dt><dd>${Math.abs(motion.s - task.start).toFixed(1)} cm</dd>
            <dt>Time</dt><dd>${task.t.toFixed(2)} s at ${motion.speed} cm/s</dd></dl>`;
          msg.textContent = '';
          task = null;
        }
        update();
        show();
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
