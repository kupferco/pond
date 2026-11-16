// Transfer scene (v2 cart, cad/cart_base.py): the cart hangs between two neighbouring pipes (B and C, 120 mm apart) on one rigid plate with a hinge at each hand.
// The track is the Cart scene's: pipe B runs up and bends left, pipe C runs up and bends right. The cart waits at the top of the straight part, clamped on B and C. A transfer: hand B releases its pipe,
// the plate rotates a few degrees on hand C's hinge to clear pipe B, the cart drives on pipe C round the bend to the top right of C, the plate rotates back. The hands are true mirrors, so it works the other way round too: hand C releases, the plate rotates on hand B's hinge and the cart drives up pipe B to the top left. The arm stays stowed on the plate.
// Each step has a control, and one button runs the lot.
import { S_MAX_CM, transferMjcf } from '../cart/transfer-model.ts';
import { PIPE_X } from '../cart/dims.ts';
import {
  DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, HINGE_DEG_S_CAD, MAX_SPEED_CM_S, P_BEND_END, P_STRAIGHT_END, P_TOP_CM, stepLabel, handName, SWING_RATE_DEG_S, TransferRun, applyPose, kinematics, worstContact, CLEAR_DEG, MAX_HINGE_DEG, bendTrim,
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
    // Camera in front of the pipes (-y side, as the CAD front view: pipe B on the left, C on the right), a little to one side, looking at the hands.
    const viewer = new Viewer(view, { mujoco, model, data }, { target: [0.05, 0, 0.35], dist: 1.6, maxDist: 4, az: 0.55, el: 0.25, far: 20 });
    status.textContent = '';

    panel.innerHTML = `
    <h1>Pond cart transfer</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Cart on</dt><dd id="t-pipe"></dd>
        <dt>Step</dt><dd id="t-step-now">Idle</dd>
        <dt>Contacts</dt><dd id="t-hit">none</dd>
      </dl>
    </section>
    <div class="row"><button class="big grow" id="t-press">Press: next trip (1: up pipe C, 2: back, up pipe B, 3: back, up pipe C ...)</button></div>
    <div class="row"><button class="big grow" id="t-transfer">Run transfer to pipe C (release hand B)</button></div>
    <div class="row"><button class="big grow" id="t-transfer-b">Run transfer to pipe B (release hand C)</button></div>
    <div class="row"><button class="big grow" id="t-reset">Reset</button></div>
    <p id="t-msg" class="hint"></p>
    <details class="card">
      <summary>Advanced</summary>
      <dl>
        <dt>Hands</dt><dd id="t-hands"></dd>
        <dt>Position</dt><dd><span id="t-pos">0.0</span> cm along the track: <span id="t-where"></span></dd>
        <dt>Plate rotation</dt><dd><span id="t-swing">0</span>° of ${CLEAR_DEG}°, hinge angles <span id="t-hinges"></span></dd>
        <dt>Arm</dt><dd>stowed on the plate, does not move</dd>
      </dl>
      <p class="hint">Pipes B and C are ${PIPE_X.C - PIPE_X.B} mm apart (cad/cart_dims.py). A transfer opens hand B's jaw, rotates the plate ${CLEAR_DEG}° on hand C's hinge, drives round pipe C's bend, rotates back flat and drives to the top right; pressed again it comes back. The hinge worm drives hold the plate with the motors off.</p>
      <div class="row"><button class="big grow" id="t-stop">Stop</button></div>
      <h2>Clamps</h2>
      <div class="row">
        <button class="big grow" id="t-clampb"></button>
        <button class="big grow" id="t-clampc"></button>
      </div>
      <h2>Plate rotation</h2>
      <div class="row">
        <button class="big grow" id="t-rplus">Rotate to clear curve</button>
        <button class="big grow" id="t-rminus">Rotate back</button>
      </div>
      <div class="xy stepbar">
        <label>Hinge speed <input class="tall" id="t-hspeed" type="number" inputmode="decimal" min="1" max="60" step="1" value="${SWING_RATE_DEG_S}" aria-label="Hinge speed degrees per second"> °/s</label>
      </div>
      <p class="hint">The CAD worm drive turns a hinge at ${HINGE_DEG_S_CAD.toFixed(1)}°/s (60 rpm motor, 38:1); the field sets the limit used here.</p>
      <h2>Drive</h2>
      <div class="row">
        <button class="big grow" id="t-down">◀ Back</button>
        <button class="big grow" id="t-up">▶ Forward</button>
      </div>
      <div class="xy stepbar">
        <label>Step <input class="tall" id="t-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
        <label>Speed <input class="tall" id="t-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
      </div>
      <p class="hint">Forward and back drive the cart on both pipes up to ${S_MAX_CM} cm; with hand B released, on round pipe C's bend (${P_STRAIGHT_END.toFixed(0)} to ${P_BEND_END.toFixed(0)} cm) to its top right (${P_TOP_CM.toFixed(0)} cm).</p>
    </details>
`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const run = new TransferRun(); run.reset();
    const num = (id: string, fallback: number) => { const v = parseFloat($<HTMLInputElement>(id).value); return Number.isFinite(v) && v > 0 ? v : fallback; };
    const sync = () => { run.setSpeed(num('t-speed', DEFAULT_SPEED_CM_S)); run.swingDegS = Math.min(60, num('t-hspeed', SWING_RATE_DEG_S)); };
    const act = (id: string, fn: () => unknown) => $(id).addEventListener('click', () => { sync(); fn(); });
    act('t-up', () => run.nudge(num('t-step', DEFAULT_STEP_CM)));
    act('t-down', () => run.nudge(-num('t-step', DEFAULT_STEP_CM)));
    // one toggle per hand: releases when clamped, clamps when released
    const toggle = (hand: 1 | 2) => () => { const open = hand === 1 ? run.goal.open1 : run.goal.open2; run.clampHand(hand, open < 0.5); };
    act('t-clampb', toggle(2));
    act('t-clampc', toggle(1));
    act('t-rplus', () => run.rotate(1));
    act('t-rminus', () => run.rotate(0));
    act('t-stop', () => run.stop());
    act('t-reset', () => { run.reset(); failed = 0; lastNames = ''; });
    act('t-press', () => run.press());
    act('t-transfer', () => run.start(2));
    act('t-transfer-b', () => run.start(1));

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
      const st = run.st, onTop = st.s > S_MAX_CM + 1e-6, F = run.free, S = F === 1 ? 2 : 1, fN = handName(F), sN = handName(S), fo = F === 1 ? st.open1 : st.open2, so = S === 1 ? st.open1 : st.open2;
      const word = (o: number) => (o < 0.01 ? 'clamped' : o > 0.99 ? 'released' : 'moving');
      $('t-hands').textContent = `hand ${fN}: ${word(fo)} ${st.t > 0 ? '(plate rotated, off the pipe)' : onTop ? `(free, off pipe ${fN})` : `on pipe ${fN}`}; hand ${sN}: ${word(so)} on pipe ${sN}`;
      $('t-pipe').textContent = onTop ? `pipe ${sN} (top ${sN === 'C' ? 'right' : 'left'}), hand ${sN} clamped` : 'pipes B and C (top of the straight part), both hands clamped';
      $('t-pos').textContent = st.s.toFixed(1);
      $('t-where').textContent = st.s < P_STRAIGHT_END - 1e-6 ? 'straight part' : st.s < P_BEND_END - 1e-6 ? `pipe ${sN}'s bend` : st.s >= P_TOP_CM - 1e-6 ? `top ${sN === 'C' ? 'right' : 'left'} of pipe ${sN}` : `top bar of pipe ${sN}`;
      $('t-swing').textContent = Math.abs((kinematics(st.t, S, bendTrim(st.s).da).alpha * 180) / Math.PI).toFixed(1);
      const k = kinematics(st.t, S), deg = (r: number) => ((r * 180) / Math.PI).toFixed(1);
      $('t-hinges').textContent = `C ${deg(k.hinge1)}°, B ${deg(k.hinge2)}°`;
      $('t-clampb').textContent = run.goal.open2 < 0.5 ? 'Release hand B' : 'Clamp hand B'; $('t-clampc').textContent = run.goal.open1 < 0.5 ? 'Release hand C' : 'Clamp hand C';
      $('t-step-now').textContent = run.current ? stepLabel(run.current, run.free) : 'Idle';
      const m = $('t-msg'); m.textContent = run.done && !run.busy ? (onTop ? `Transfer done: the cart is at the top ${sN === 'C' ? 'right of pipe C' : 'left of pipe B'}, hand ${sN} clamped, hand ${fN} free. Press it again to bring it back, or the other Run transfer button to go on up the other pipe in one go.` : 'Back at the top of pipes B and C, clamped on both.') : run.msg;
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
