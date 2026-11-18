// Transfer scene on the omni cart (OpenPocket #283, plan task 265 part 9, owner answers Q3, Q7, Q8): the cart hangs between two neighbouring pipes (B and C, 120 mm apart) on its omni wheels, as one rigid base.
// The track is the Cart scene's: pipe B runs up and bends left, pipe C runs up and bends right. A transfer: one hand's jaw opens, the WHOLE cart rolls about the other hand's pipe so the free hand swings clear of its pipe,
// the cart drives round the bend with the roll held, rolls back flat at the start of the top run and drives to the top. The roll goes the way that clears; if neither does, the controller stops and says so.
// Run the scene with the jaw wedge as the CAD draws it (0 to 110 degrees: no roll direction clears, the finding of this task) or with the wedge to 150 degrees (the plate side clears).
import { P_TOP_CM, S_FLAT_CM, S_MAX_CM, transferMjcf, placeTransfer, transferContacts, blockedBy, PIPE_SPACING_NOTE } from '../cart/omni-transfer.ts';
import { DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, JAW_A1_DEG, MAX_SPEED_CM_S, ROLL_DEG_S, ROLL_PREVIEW_DEG_S, TransferRun, stepLabel, rollPlan, ROLL_WINDOW_CM, type Variant } from '../cart/omni-transfer-run.ts';
import { OMNI_R } from '../cart/omni.ts';
import { Viewer } from '../viewer.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'transfer')!;

export const transferScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const variant: Variant = new URLSearchParams(location.search).get('jaw') === 'wide' ? 'wide' : 'cad';
    const model = mujoco.MjModel.from_xml_string(transferMjcf({ jawA1: JAW_A1_DEG[variant] }));
    const data = new mujoco.MjData(model);
    for (let i = 0; i < model.ngeom; i++) model.geom_margin[i] = 0.0002;
    // Camera in front of the pipes (-y side, as the CAD front view: pipe B on the left, C on the right), a little to one side, looking at the hands.
    const viewer = new Viewer(view, { mujoco, model, data }, { target: [0.05, 0, 0.5], dist: 1.7, maxDist: 4, az: 0.55, el: 0.25, far: 20 });
    status.textContent = '';
    const plate = rollPlan(variant, 'C');

    panel.innerHTML = `
    <h1>Pond cart transfer (roll about the pipe)</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Cart on</dt><dd id="t-pipe"></dd>
        <dt>Step</dt><dd id="t-step-now">Idle</dd>
        <dt>Roll</dt><dd id="t-roll">0°</dd>
        <dt>Contacts</dt><dd id="t-hit">none</dd>
        <dt>Jaw wedge</dt><dd>0 to ${JAW_A1_DEG[variant]}° (${variant === 'cad' ? 'as the CAD draws it' : 'widened, proposed'}): ${plate.dir === null ? 'NO roll direction clears' : `the ${plate.side} side clears`}</dd>
      </dl>
    </section>
    <div class="row"><button class="big grow" id="t-press">Press: next trip (1: up pipe C, 2: back, up pipe B, 3: back, up pipe C ...)</button></div>
    <div class="row"><button class="big grow" id="t-transfer">Run transfer to pipe C (release hand B)</button></div>
    <div class="row"><button class="big grow" id="t-transfer-b">Run transfer to pipe B (release hand C)</button></div>
    <div class="row"><button class="big grow" id="t-reset">Reset</button></div>
    <div class="row"><button class="big grow" id="t-variant">${variant === 'cad' ? 'Show it with the jaw wedge widened to 150°' : 'Show it with the jaw wedge as the CAD draws it (110°)'}</button></div>
    <p id="t-msg" class="hint"></p>
    <details class="card">
      <summary>Advanced</summary>
      <dl>
        <dt>Hands</dt><dd id="t-hands"></dd>
        <dt>Position</dt><dd><span id="t-pos">0.0</span> cm along the track: <span id="t-where"></span></dd>
        <dt>Arm</dt><dd>stowed on the base, does not move</dd>
      </dl>
      <p class="hint">${PIPE_SPACING_NOTE} A transfer opens one jaw, rolls the whole cart about the other pipe's centre line (${plate.dir === null ? 'no direction clears with this wedge' : `${plate.roll}° to the ${plate.side} side`}), drives round the bend with the roll held, rolls back flat at ${S_FLAT_CM.toFixed(1)} cm (the start of the top run) and drives to the top. The roll is only allowed at ${ROLL_WINDOW_CM[0]} to ${ROLL_WINDOW_CM[1]} cm on the leg (clear of the track-joint rods) and at the start of the top run.</p>
      <div class="row"><button class="big grow" id="t-stop">Stop</button></div>
      <h2>Jaws</h2>
      <div class="row">
        <button class="big grow" id="t-clampb"></button>
        <button class="big grow" id="t-clampc"></button>
      </div>
      <h2>Roll</h2>
      <div class="row">
        <button class="big grow" id="t-rplus">Roll to clear</button>
        <button class="big grow" id="t-rminus">Roll back</button>
      </div>
      <div class="row"><button class="big grow" id="t-rtry">Try a 20° roll to the plate side anyway</button></div>
      <div class="xy stepbar">
        <label>Roll speed <input class="tall" id="t-rspeed" type="number" inputmode="decimal" min="1" max="${Math.round(ROLL_DEG_S)}" step="1" value="${ROLL_PREVIEW_DEG_S}" aria-label="Roll speed degrees per second"> °/s</label>
      </div>
      <p class="hint">The roll motor can turn the cart at about ${Math.round(ROLL_DEG_S)}°/s (cart/omni.ts rollBudget); the field sets the speed used here so the roll can be followed.</p>
      <h2>Drive</h2>
      <div class="row">
        <button class="big grow" id="t-down">◀ Back</button>
        <button class="big grow" id="t-up">▶ Forward</button>
      </div>
      <div class="xy stepbar">
        <label>Step <input class="tall" id="t-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
        <label>Speed <input class="tall" id="t-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
      </div>
      <p class="hint">Forward and back drive the cart on both pipes up to ${S_MAX_CM} cm; with one hand released and the cart rolled, round the bend to ${S_FLAT_CM.toFixed(1)} cm; released and flat on the run, to the top (${P_TOP_CM.toFixed(0)} cm).</p>
    </details>
`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const run = new TransferRun(variant); run.reset();
    const num = (id: string, fallback: number) => { const v = parseFloat($<HTMLInputElement>(id).value); return Number.isFinite(v) && v > 0 ? v : fallback; };
    const sync = () => { run.setSpeed(num('t-speed', DEFAULT_SPEED_CM_S)); run.rollDegS = Math.min(ROLL_DEG_S, num('t-rspeed', ROLL_PREVIEW_DEG_S)); };
    const act = (id: string, fn: () => unknown) => $(id).addEventListener('click', () => { sync(); fn(); });
    act('t-up', () => run.nudge(num('t-step', DEFAULT_STEP_CM)));
    act('t-down', () => run.nudge(-num('t-step', DEFAULT_STEP_CM)));
    const toggle = (hand: 'B' | 'C') => () => { const open = hand === 'B' ? run.goal.openB : run.goal.openC; run.clampHand(hand, open < 0.5); };
    act('t-clampb', toggle('B'));
    act('t-clampc', toggle('C'));
    act('t-rplus', () => run.rollTo(1));
    act('t-rminus', () => run.rollTo(0));
    act('t-rtry', () => run.rollTo(1, 20));
    act('t-stop', () => run.stop());
    act('t-reset', () => { run.reset(); failed = 0; lastNames = ''; });
    act('t-press', () => run.press());
    act('t-transfer', () => run.start('B'));
    act('t-transfer-b', () => run.start('C'));
    act('t-variant', () => { const u = new URL(location.href); if (variant === 'cad') u.searchParams.set('jaw', 'wide'); else u.searchParams.delete('jaw'); location.href = u.toString(); });

    let failed = 0, lastNames = ''; // frames where the free hand, the base or the rods are hit (the riding sleeve against its own pipe is a separate, known finding)
    const update = () => {
      placeTransfer(model as never, data as never, { rider: run.rider, s: run.st.s, roll: run.st.roll, open: run.open(run.free), riderOpen: run.open(run.rider) }, -(run.st.s * 10) / OMNI_R);
      mujoco.mj_forward(model, data);
      const hit = blockedBy(transferContacts(model as never, data as never, run.rider));
      if (hit) { failed++; lastNames = hit; }
      const el = $('t-hit');
      el.textContent = failed ? `FAIL: ${lastNames} touched (${failed} frames)` : 'none (free hand, base and rods against the track)';
      el.style.color = failed ? '#c0392b' : '';
    };
    const show = () => {
      const st = run.st, onTop = st.s > S_MAX_CM + 1e-6, F = run.free, S = run.rider, fo = run.open(F), so = run.open(S);
      const word = (o: number) => (o < 0.01 ? 'clamped' : o > 0.99 ? 'released' : 'moving');
      $('t-hands').textContent = `hand ${F}: ${word(fo)} ${run.rolled ? '(rolled, off its pipe)' : onTop ? `(free, off pipe ${F})` : `on pipe ${F}`}; hand ${S}: ${word(so)} on pipe ${S}`;
      $('t-pipe').textContent = onTop ? `pipe ${S} (top ${S === 'C' ? 'right' : 'left'}), hand ${S} clamped` : 'pipes B and C (leg), both hands clamped';
      $('t-pos').textContent = st.s.toFixed(1);
      $('t-where').textContent = run.where === 'leg' ? 'leg' : run.where === 'bend' ? `pipe ${S}'s bend` : st.s >= P_TOP_CM - 1e-6 ? `top ${S === 'C' ? 'right' : 'left'} of pipe ${S}` : `top bar of pipe ${S}`;
      $('t-roll').textContent = `${st.roll.toFixed(0)}° ${st.roll > 0.5 ? '(free hand to the plate side)' : st.roll < -0.5 ? '(free hand to the spine side)' : ''}`;
      $('t-clampb').textContent = run.goal.openB < 0.5 ? 'Release hand B' : 'Clamp hand B'; $('t-clampc').textContent = run.goal.openC < 0.5 ? 'Release hand C' : 'Clamp hand C';
      $('t-step-now').textContent = run.current ? stepLabel(run.current, run.free) : 'Idle';
      const m = $('t-msg'); m.textContent = run.done && !run.busy ? (onTop ? `Transfer done: the cart is at the top ${S === 'C' ? 'right of pipe C' : 'left of pipe B'}, hand ${S} clamped, hand ${F} free. Press it again to bring it back, or the other Run transfer button to go on up the other pipe in one go.` : 'Back at the top of the leg, clamped on both pipes.') : run.msg;
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
