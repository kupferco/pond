// Transfer scene (v2 cart, cad/cart_base.py): the cart hangs between two neighbouring pipes (B and C, 120 mm apart) on one rigid plate with a hinge at each hand.
// Hand B releases its pipe, the cart lifts on C, the plate swings half a turn on hand C's hinge and hand B lands on pipe D and clamps it. Each step has a control, and one button runs the lot.
import { transferMjcf } from '../cart/transfer-model.ts';
import { PIPE_X } from '../cart/dims.ts';
import {
  DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, HINGE_DEG_S_CAD, LIFT_CM, MAX_SPEED_CM_S, STEP_LABEL, SWING_RATE_DEG_S, TOP_S_CM, TransferRun, applyPose, kinematics, pipeOf, worstContact,
} from '../cart/transfer.ts';
import { Viewer } from '../viewer.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'transfer')!;

export const transferScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const model = mujoco.MjModel.from_xml_string(transferMjcf());
    const data = new mujoco.MjData(model);
    // Camera behind the pipes (+y), a little to one side, looking at the hands near the pipe ends; the plate swings out to the front.
    const viewer = new Viewer(view, { mujoco, model, data }, { target: [0.06, 0, TOP_S_CM / 100], dist: 1.1, maxDist: 4, az: Math.PI + 0.55, el: 0.25, far: 20 });
    status.textContent = '';

    panel.innerHTML = `
    <h1>Pond cart transfer</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Hands</dt><dd id="t-hands"></dd>
        <dt>Height</dt><dd><span id="t-pos">0.0</span> cm (pipe ends at ${TOP_S_CM + 5} cm)</dd>
        <dt>Plate swing</dt><dd><span id="t-swing">0</span>° of 180°, hinge angles <span id="t-hinges"></span></dd>
        <dt>Arm</dt><dd id="t-arm"></dd>
        <dt>Step</dt><dd id="t-step-now">Idle</dd>
        <dt>Contacts</dt><dd id="t-hit">none</dd>
      </dl>
      <p class="hint">Pipes B and C are ${PIPE_X.C - PIPE_X.B} mm apart (cad/cart_dims.py), the plate hangs between the two hinge axes. A transfer: fold the arm in, release hand B, lift the cart on pipe C so hand B clears the end of its pipe, swing the plate half a turn on hand C's hinge, lower hand B onto pipe D (${PIPE_X.D - PIPE_X.C} mm from C) and clamp it. Rotation only happens during a transfer; the hinge worm drives hold the plate with the motors off.</p>
    </section>
    <div class="xy stepbar">
      <label>Step <input class="tall" id="t-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
      <label>Speed <input class="tall" id="t-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-up">▲ Up</button>
      <button class="big grow" id="t-down">▼ Down</button>
    </div>
    <p class="hint">Up and down drive the cart along the pipes on the drive wheels. With hand <span class="t-free">B</span> released it can lift ${LIFT_CM} cm above the pipe end.</p>
    <h2>Transfer, step by step</h2>
    <div class="row wrap">
      <button class="big grow" id="t-fold">1. Fold arm</button>
      <button class="big grow" id="t-unfold">Unfold arm</button>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-relfree">2. Release hand <span class="t-free">B</span></button>
      <button class="big grow" id="t-relc">Release hand C</button>
    </div>
    <div class="xy stepbar">
      <label>Hinge speed <input class="tall" id="t-hspeed" type="number" inputmode="decimal" min="1" max="60" step="1" value="${SWING_RATE_DEG_S}" aria-label="Hinge speed degrees per second"> °/s</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-rplus">3. Rotate ⟳ onto D</button>
      <button class="big grow" id="t-rminus">Rotate ⟲ back to B</button>
    </div>
    <p class="hint">The CAD worm drive turns a hinge at ${HINGE_DEG_S_CAD.toFixed(1)}°/s (60 rpm motor, 38:1); the field sets the limit used here.</p>
    <div class="row wrap">
      <button class="big grow" id="t-clampfree">4. Clamp hand <span class="t-free">B</span></button>
      <button class="big grow" id="t-clampc">Clamp hand C</button>
    </div>
    <div class="row"><button class="big" id="t-stop">Stop</button></div>
    <div class="row"><button class="big grow" id="t-transfer">Run full transfer</button></div>
    <p id="t-msg" class="hint"></p>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const run = new TransferRun();
    const num = (id: string, fallback: number) => { const v = parseFloat($<HTMLInputElement>(id).value); return Number.isFinite(v) && v > 0 ? v : fallback; };
    const sync = () => { run.setSpeed(num('t-speed', DEFAULT_SPEED_CM_S)); run.swingDegS = Math.min(60, num('t-hspeed', SWING_RATE_DEG_S)); };
    const act = (id: string, fn: () => unknown) => $(id).addEventListener('click', () => { sync(); fn(); });
    act('t-up', () => run.nudge(num('t-step', DEFAULT_STEP_CM)));
    act('t-down', () => run.nudge(-num('t-step', DEFAULT_STEP_CM)));
    act('t-fold', () => run.fold(true));
    act('t-unfold', () => run.fold(false));
    act('t-relfree', () => run.clampHand(2, true));
    act('t-relc', () => run.clampHand(1, true));
    act('t-clampfree', () => run.clampHand(2, false));
    act('t-clampc', () => run.clampHand(1, false));
    act('t-rplus', () => run.rotate(1));
    act('t-rminus', () => run.rotate(0));
    act('t-stop', () => run.stop());
    act('t-transfer', () => run.start());

    let failed = 0, lastNames = ''; // frames with any contact of the cart with the pipes (or its own plate with a hand): a failure of the run
    const update = () => {
      applyPose(model, data, run.st);
      mujoco.mj_forward(model, data);
      const { depth, names } = worstContact(model, data);
      if (depth < 0) { failed++; lastNames = names; }
      const el = $('t-hit');
      el.textContent = failed ? `FAIL: ${lastNames} touched (${(-depth * 1000).toFixed(1)} mm now, ${failed} frames)` : 'none (cart, plate and hands against the pipes and each other)';
      el.style.color = failed ? '#c0392b' : '';
    };
    const show = () => {
      const st = run.st, free = pipeOf(2, st.t);
      panel.querySelectorAll('.t-free').forEach((e) => { e.textContent = free; });
      $('t-hands').textContent = `hand ${free}: ${st.open2 < 0.01 ? 'clamped' : st.open2 > 0.99 ? 'released' : 'moving'} on pipe ${st.t > 0 && st.t < 1 ? '(in the air)' : free}; hand C: ${st.open1 < 0.01 ? 'clamped' : st.open1 > 0.99 ? 'released' : 'moving'} on pipe C`;
      $('t-pos').textContent = st.s.toFixed(1);
      $('t-swing').textContent = (st.t * 180).toFixed(0);
      const k = kinematics(st.t), deg = (r: number) => ((r * 180) / Math.PI).toFixed(0);
      $('t-hinges').textContent = `C ${deg(k.hinge1)}°, ${free} ${deg(k.hinge2)}°`;
      $('t-arm').textContent = st.fold < 0.01 ? 'unfolded' : st.fold > 0.99 ? 'folded in close' : `folding (${(st.fold * 100).toFixed(0)}%)`;
      $('t-step-now').textContent = run.current ? STEP_LABEL[run.current] : 'Idle';
      const m = $('t-msg'); m.textContent = run.done && !run.busy ? `Transfer done: hand ${free} is clamped on pipe ${free}.` : run.msg;
    };
    update(); show();

    return {
      frame(dt: number) {
        run.advance(Math.min(dt, 0.1));
        update(); show();
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
