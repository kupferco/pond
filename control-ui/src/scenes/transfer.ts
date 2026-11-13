// Transfer scene: two neighbouring units side by side, only pipes B and C with their top bars (B's runs left, C's runs right).
// The cart rides one pipe and hands over to the other on a vertical section (Hand B clamps the neighbour, Hand A releases).
import { cartBody, pipeGeoms } from '../cart/model.ts';
import { CartMotion, DEFAULT_SPEED_CM_S, DEFAULT_STEP_CM, L_VERT, MAX_SPEED_CM_S, L_ARC, clampS } from '../cart/track.ts';
import {
  HAND_SPACING_MM, TRANSFER_DEFAULT_CM, TRANSFER_HORIZ_MM, TRANSFER_MIN_CM, TRANSFER_S, canTransfer, cartPose, other, pipeX, transferPose,
  type Pipe,
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
</mujoco>`;
}

export const transferScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const model = mujoco.MjModel.from_xml_string(transferMjcf());
    const data = new mujoco.MjData(model);
    const viewer = new Viewer(view, { mujoco, model, data }, { target: [0.07, 0, 0.6], dist: 2.4, maxDist: 5, az: 0.3, el: 0.15, far: 20 });
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
      </dl>
      <p class="hint">Two units side by side, ${HAND_SPACING_MM / 10} cm apart: pipe B (right pipe of unit 1, top bar to the left) and pipe C (left pipe of unit 2, top bar to the right). 0 cm is the bottom of each pipe. You can hand over on the straight part, from ${TRANSFER_MIN_CM} to ${L_VERT.toFixed(0)} cm.</p>
    </section>
    <div class="xy stepbar">
      <label>Step <input class="tall" id="t-step" type="number" inputmode="decimal" min="0.1" step="1" value="${DEFAULT_STEP_CM}" aria-label="Step size cm"> cm</label>
      <label>Speed <input class="tall" id="t-speed" type="number" inputmode="decimal" min="0.1" max="${MAX_SPEED_CM_S}" step="1" value="${DEFAULT_SPEED_CM_S}" aria-label="Speed cm per second"> cm/s</label>
    </div>
    <div class="row wrap">
      <button class="big grow" id="t-up">▲ Up / forward</button>
      <button class="big grow" id="t-down">▼ Down / back</button>
    </div>
    <div class="row"><button class="big" id="t-stop">Stop</button><button class="big" id="t-ready">Go to ${TRANSFER_DEFAULT_CM} cm</button></div>
    <div class="row"><button class="big grow" id="t-transfer">Transfer to the other pipe</button></div>
    <p id="t-msg" class="hint"></p>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const motion = new CartMotion();
    let pipe: Pipe = 'B';
    let xfer: { from: Pipe; s: number; t: number } | null = null;
    const msg = $('t-msg');
    const clamp = (s: number) => Math.min(maxS, clampS(s));
    const readNum = (id: string, fallback: number) => { const v = parseFloat($<HTMLInputElement>(id).value); return Number.isFinite(v) && v > 0 ? v : fallback; };
    const readSpeed = () => Math.min(readNum('t-speed', DEFAULT_SPEED_CM_S), MAX_SPEED_CM_S);
    const goTo = (s: number) => { motion.speed = readSpeed(); motion.goal = clamp(s); };
    const nudge = (d: number) => { if (!xfer) { motion.speed = readSpeed(); motion.goal = clamp(motion.goal + d); } };

    $('t-up').addEventListener('click', () => nudge(readNum('t-step', DEFAULT_STEP_CM)));
    $('t-down').addEventListener('click', () => nudge(-readNum('t-step', DEFAULT_STEP_CM)));
    $('t-stop').addEventListener('click', () => { if (!xfer) motion.goal = motion.s; });
    $('t-ready').addEventListener('click', () => { if (!xfer) goTo(TRANSFER_DEFAULT_CM); });
    $('t-transfer').addEventListener('click', () => {
      if (xfer) return;
      if (motion.moving || !canTransfer(motion.s)) {
        msg.textContent = `Park the cart on the straight part (${TRANSFER_MIN_CM} to ${L_VERT.toFixed(0)} cm) before handing over.`;
        return;
      }
      msg.textContent = '';
      xfer = { from: pipe, s: motion.s, t: 0 };
    });

    const place = (x: number, z: number, q: number[]) => {
      data.mocap_pos[3 * cartMocap] = x; data.mocap_pos[3 * cartMocap + 1] = 0; data.mocap_pos[3 * cartMocap + 2] = z;
      for (let k = 0; k < 4; k++) data.mocap_quat[4 * cartMocap + k] = q[k];
    };
    const show = () => {
      $('t-pipe').textContent = xfer ? `Pipe ${xfer.from} to ${other(xfer.from)}` : `Pipe ${pipe}`;
      $('t-pos').textContent = motion.s.toFixed(1);
      const h = (from: Pipe, t: number) => (t < 0.25 ? `Hand on ${from} clamped; neighbour hand opens` : t < 0.5 ? `Both hands clamped (${from} and ${other(from)})` : t < 0.9 ? `Hand on ${from} releases, cart swaps sides` : `Riding on ${other(from)}`);
      $('t-hands').textContent = xfer ? h(xfer.from, xfer.t / TRANSFER_S) : `Riding on pipe ${pipe}`;
    };
    const update = () => {
      if (xfer) {
        const p = transferPose(xfer.from, xfer.s, xfer.t / TRANSFER_S);
        place(p.x, p.z, p.q);
      } else {
        const p = cartPose(pipe, motion.s);
        place(p.x, p.z, p.q);
      }
      mujoco.mj_forward(model, data);
    };
    update(); show();

    return {
      frame(dt: number) {
        const d = Math.min(dt, 0.1);
        if (xfer) {
          xfer.t += d;
          if (xfer.t >= TRANSFER_S) { pipe = other(xfer.from); xfer = null; msg.textContent = `Handed over: now riding on pipe ${pipe}.`; }
        } else {
          motion.advance(d);
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
