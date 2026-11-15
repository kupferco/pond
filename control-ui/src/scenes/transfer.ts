// Transfer scene (v2 cart, cad/cart_base.py): the cart hangs between two neighbouring pipes (B and C, 120 mm apart) on one rigid plate with a hinge at each hand.
// The track is the Cart scene's: pipe B runs up and bends left, pipe C runs up and bends right. Hand B releases its pipe, the plate rotates a few degrees on hand C's hinge to clear the curve, the cart moves past it, the plate rotates back and hand B clamps again; only the hinge moves,
// the arm stays stowed on the plate. Each step has a control, and one button runs the lot.
import { S_MAX_CM, S_MIN_CM, transferMjcf } from '../cart/transfer-model.ts';
import { PIPE_X } from '../cart/dims.ts';
import {
  DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, HINGE_DEG_S_CAD, MAX_SPEED_CM_S, STEP_LABEL, SWING_RATE_DEG_S, TransferRun, applyPose, kinematics, worstContact, CLEAR_DEG, MAX_HINGE_DEG,
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
    // Camera behind the pipes (+y), a little to one side, looking at the hands; the plate swings out to the front.
    const viewer = new Viewer(view, { mujoco, model, data }, { target: [0.05, 0, 0.35], dist: 1.6, maxDist: 4, az: Math.PI + 0.55, el: 0.25, far: 20 });
    status.textContent = '';

    panel.innerHTML = `
    <h1>Pond cart transfer</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Hands</dt><dd id="t-hands"></dd>
        <dt>Position</dt><dd><span id="t-pos">0.0</span> cm along the pipes (${S_MIN_CM} to ${S_MAX_CM} cm)</dd>
        <dt>Plate rotation</dt><dd><span id="t-swing">0</span>° of ${CLEAR_DEG}°, hinge angles <span id="t-hinges"></span></dd>
        <dt>Arm</dt><dd>stowed on the plate, does not move</dd>
        <dt>Step</dt><dd id="t-step-now">Idle</dd>
        <dt>Contacts</dt><dd id="t-hit">none</dd>
      </dl>
      <p class="hint">Pipes B and C are ${PIPE_X.C - PIPE_X.B} mm apart (cad/cart_dims.py), the plate hangs between the two hinge axes. Each hand is a fixed sleeve with a jaw on a knuckle hinge (jaw motor on the end). Battery under the arm, worm drive on each hinge. A transfer: open hand B's jaw (release), rotate the plate ${CLEAR_DEG}° on hand C's hinge to clear the curve, move past it, rotate back, clamp hand B. The arm stays as it is. Rotation only happens during a transfer; the hinge worm drives hold the plate with the motors off.</p>
    </section>
    <div class="xy stepbar">
      <label>Step <input class="tall" id="t-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
      <label>Speed <input class="tall" id="t-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-up">▶ Forward</button>
      <button class="big grow" id="t-down">◀ Back</button>
    </div>
    <p class="hint">Forward and back drive the cart along the pipes on the drive wheels.</p>
    <h2>Transfer, step by step</h2>
    <p class="hint">Step 3 is Forward / Back above, with hand B released and the plate rotated.</p>
    <div class="row wrap">
      <button class="big grow" id="t-relfree">1. Release hand B</button>
      <button class="big grow" id="t-relc">Release hand C</button>
    </div>
    <div class="xy stepbar">
      <label>Hinge speed <input class="tall" id="t-hspeed" type="number" inputmode="decimal" min="1" max="60" step="1" value="${SWING_RATE_DEG_S}" aria-label="Hinge speed degrees per second"> °/s</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-rplus">2. Rotate to clear curve</button>
      <button class="big grow" id="t-rminus">4. Rotate back</button>
    </div>
    <p class="hint">The CAD worm drive turns a hinge at ${HINGE_DEG_S_CAD.toFixed(1)}°/s (60 rpm motor, 38:1); the field sets the limit used here.</p>
    <div class="row wrap">
      <button class="big grow" id="t-clampfree">5. Clamp hand B</button>
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
      const st = run.st, free = 'B';
      $('t-hands').textContent = `hand ${free}: ${st.open2 < 0.01 ? 'clamped' : st.open2 > 0.99 ? 'released' : 'moving'} ${st.t > 0 ? '(plate rotated, off the pipe)' : 'on pipe B'}; hand C: ${st.open1 < 0.01 ? 'clamped' : st.open1 > 0.99 ? 'released' : 'moving'} on pipe C`;
      $('t-pos').textContent = st.s.toFixed(1);
      $('t-swing').textContent = ((kinematics(st.t).alpha * 180) / Math.PI).toFixed(1);
      const k = kinematics(st.t), deg = (r: number) => ((r * 180) / Math.PI).toFixed(1);
      $('t-hinges').textContent = `C ${deg(k.hinge1)}°, ${free} ${deg(k.hinge2)}°`;
      $('t-step-now').textContent = run.current ? STEP_LABEL[run.current] : 'Idle';
      const m = $('t-msg'); m.textContent = run.done && !run.busy ? `Transfer done: hand B is clamped on pipe B again (hinge angle never above ${MAX_HINGE_DEG}°).` : run.msg;
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
