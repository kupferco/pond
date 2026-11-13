// Clamp–track clearance for the transfer, measured on the real MuJoCo model: place the cart, the hands and the rotation motors, and look for contacts.
import { clampTrackContacts } from './model.ts';
import { SB, SC, applyCart, cartPose, cartTrims, type ClearCheck } from './transfer.ts';

type Mj = { mj_forward(m: unknown, d: unknown): void };
/** Clearance check for a model holding pipes B and C and the cart (see transfer scene). The riding hand is closed, the free hand open on the other pipe. */
export function makeClearCheck(mujoco: Mj, model: any, data: any): ClearCheck {
  const mocap = model.body_mocapid[model.body('cart').id];
  return (pipe, s, swing) => {
    const c = cartPose(pipe, s), hinge = (pipe === 'B' ? SB : SC) * swing, tr = cartTrims(pipe, c, hinge);
    data.mocap_pos[3 * mocap] = c.x; data.mocap_pos[3 * mocap + 1] = 0; data.mocap_pos[3 * mocap + 2] = c.z;
    for (let k = 0; k < 4; k++) data.mocap_quat[4 * mocap + k] = c.q[k];
    applyCart(model, data, pipe, c, tr, { B: 1, C: 1, [pipe]: 0 }, [0, 0], hinge);
    mujoco.mj_forward(model, data);
    return clampTrackContacts(data) === 0;
  };
}
