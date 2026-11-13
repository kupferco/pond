// Transfer scene: two neighbouring units side by side, only pipes B and C with their top bars (B's runs left, C's runs right).
// The cart rides one pipe and hands over to the other on a vertical section (Hand B clamps the neighbour, Hand A releases).
import { cartActuators, cartBody, clampTrackContacts, pipeGeoms, setCart, setMotors } from '../cart/model.ts';
import { DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, L_VERT, MAX_SPEED_CM_S, L_ARC } from '../cart/track.ts';
import {
  HAND_SPACING_MM, SWING_STEP_DEG, TRANSFER_DEFAULT_CM, TRANSFER_HORIZ_MM, TRANSFER_MIN_CM, TransferRun, cartPose, cartTrims, other, pipeX,
  type Pipe, type XferPhase,
} from '../cart/transfer.ts';
import { Viewer } from '../viewer.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'transfer')!;
function transferMjcf(): string {
  return `
<mujoco model="pond_transfer">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" pos="0.07 0 -0.05" size="1.4 0.9 0.1" rgba="0.82 0.86 0.9 1"/>
    ${pipeGeoms(pipeX('B'), -1, TRANSFER_HORIZ_MM, 'b')}
    ${pipeGeoms(pipeX('C'), 1, TRANSFER_HORIZ_MM, 'c')}
    ${cartBody(HAND_SPACING_MM)}
  </worldbody>
  ${cartActuators()}
</mujoco>`;
}

export const transferScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const model = mujoco.MjModel.from_xml_string(transferMjcf());
    const data = new mujoco.MjData(model);
    const viewer = new Viewer(view, { mujoco, model, data }, { target: [0.07, 0, 0.6], dist: 2.4, maxDist: 5, az: Math.PI + 0.3, el: 0.15, far: 20 });
    const cartMocap = model.body_mocapid[model.body('cart').id];
    status.textContent = '';
    const maxS = L_VERT + L_ARC + TRANSFER_HORIZ_MM / 10; // end of the (shortened) top bar

    panel.innerHTML = `
    <h1>Pond cart transfer</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Riding on</dt><dd><strong id="t-pipe">Pipe B</strong></dd>
        <dt>Position</dt><dd><span id="t-pos">0.0</span> cm of ${maxS.toFixed(1)} cm</dd>
        <dt>Hands</dt><dd id="t-hands"></dd>
        <dt>Motors</dt><dd>2 drive (wheel spin) + 2 rotation (swing about the pipe)</dd>
        <dt>Swing</dt><dd><span id="t-swing">0</span>° (rotation motors holding)</dd>
        <dt>Clamp / track</dt><dd id="t-hit">no contact</dd>
      </dl>
      <p class="hint">Two units side by side, ${HAND_SPACING_MM / 10} cm apart: pipe B (right pipe of unit 1, top bar to the left) and pipe C (left pipe of unit 2, top bar to the right). 0 cm is the bottom of each pipe. Transfer takes the cart from wherever it is to the straight part (${TRANSFER_MIN_CM} to ${L_VERT.toFixed(0)} cm), closes its free clamp on the other pipe, releases the first one, then rides to the top of the other unit.</p>
    </section>
    <div class="xy stepbar">
      <label>Step <input class="tall" id="t-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
      <label>Speed <input class="tall" id="t-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-up">▲ Up / forward</button>
      <button class="big grow" id="t-down">▼ Down / back</button>
    </div>
    <div class="xy stepbar">
      <label>Rotation step <input class="tall" id="t-rstep" type="number" inputmode="decimal" min="1" max="90" step="5" value="${SWING_STEP_DEG}" aria-label="Rotation step degrees"> °</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-rplus">⟳ Rotate +</button>
      <button class="big grow" id="t-rminus">⟲ Rotate −</button>
    </div>
    <div class="row"><button class="big" id="t-stop">Stop</button><button class="big" id="t-ready">Go to ${TRANSFER_DEFAULT_CM} cm</button></div>
    <div class="row"><button class="big grow" id="t-transfer">Transfer to the other unit</button></div>
    <p id="t-msg" class="hint"></p>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const run = new TransferRun();
    const motion = run.motion;
    const msg = $('t-msg');
    const readNum = (id: string, fallback: number) => { const v = parseFloat($<HTMLInputElement>(id).value); return Number.isFinite(v) && v > 0 ? v : fallback; };
    const readSpeed = () => Math.min(readNum('t-speed', DEFAULT_SPEED_CM_S), MAX_SPEED_CM_S);

    $('t-up').addEventListener('click', () => run.nudge(readNum('t-step', DEFAULT_STEP_CM), readSpeed()));
    $('t-down').addEventListener('click', () => run.nudge(-readNum('t-step', DEFAULT_STEP_CM), readSpeed()));
    const rot = (sign: number) => run.turn((sign * readNum('t-rstep', SWING_STEP_DEG) * Math.PI) / 180);
    $('t-rplus').addEventListener('click', () => rot(1));
    $('t-rminus').addEventListener('click', () => rot(-1));
    $('t-stop').addEventListener('click', () => run.stop());
    $('t-ready').addEventListener('click', () => { if (!run.xfer) run.goTo(TRANSFER_DEFAULT_CM, readSpeed()); });
    $('t-transfer').addEventListener('click', () => {
      msg.textContent = '';
      motion.speed = readSpeed();
      run.start();
    });

    const place = (x: number, z: number, q: number[]) => {
      data.mocap_pos[3 * cartMocap] = x; data.mocap_pos[3 * cartMocap + 1] = 0; data.mocap_pos[3 * cartMocap + 2] = z;
      for (let k = 0; k < 4; k++) data.mocap_quat[4 * cartMocap + k] = q[k];
    };
    const PHASE_LABEL: Record<XferPhase, string> = {
      swingout: 'Rotation motors swinging the clamp off the pipe',
      approach: 'Going to the straight part',
      swingin: 'Rotation motors swinging back to the pipe',
      grip: 'Free hand closing on the other pipe',
      release: 'Old hand opening',
      swingout2: 'Rotation motors swinging the clamp off the pipe',
      climb: 'Riding to the top',
      swingin2: 'Rotation motors swinging back to the pipe',
    };
    const show = () => {
      $('t-pipe').textContent = run.xfer ? `Pipe ${run.xfer.from} to ${other(run.xfer.from)}` : `Pipe ${run.pipe}`;
      $('t-pos').textContent = motion.s.toFixed(1);
      $('t-swing').textContent = ((run.swingW * 180) / Math.PI).toFixed(0);
      $('t-hands').textContent = run.xfer ? PHASE_LABEL[run.xfer.phase] : `Riding on pipe ${run.pipe}`;
    };
    let failed = 0; // frames with a clamp–track contact: a failure of the run
    const update = () => {
      const { pipe, open } = run;
      const p = cartPose(pipe, motion.s);
      place(p.x, p.z, p.q);
      const tr = cartTrims(pipe, p, run.swing);
      setCart(model, data.qpos, open[pipe], open[other(pipe)], p.plateSide, tr.hand1, tr.hand2);
      setMotors(model, data, run.spin[0], run.spin[1], run.swing);
      mujoco.mj_forward(model, data);
      const hit = clampTrackContacts(data);
      if (hit < 0) failed++;
      const el = $('t-hit');
      el.textContent = failed ? `FAIL: clamp touched the track (${(-hit * 1000).toFixed(1)} mm now, ${failed} frames)` : 'no contact';
      el.style.color = failed ? '#c0392b' : '';
    };
    update(); show();

    return {
      frame(dt: number) {
        const d = Math.min(dt, 0.1);
        const was = run.done;
        run.advance(d);
        if (run.done && !was) msg.textContent = `Transferred: riding on pipe ${run.pipe}, at the top.`;
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
