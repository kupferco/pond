// SO-101 follower arm, six STS3215 servos (12 V, ~30 kg·cm stall ≈ 2.9 N·m).
// Link lengths follow cad/so101_servo_layout.py (upper arm 115, forearm 135, wrist 60 mm).
// Geometry is primitives only; it is a faithful-enough stand-in, not the real STEP meshes.
// Zero pose: upper arm vertical, forearm horizontal (an "L"). Positive lift/elbow/wrist pitch forward/down.

import { JAW_PIVOT_X, PAD_END_X, POD_H, POD_R, POD_REST_Z, SLOT_BASE, SLOT_OPEN, SLOT_WALL, SLOT_RIM_Z } from './arm/dims.ts';

export interface MotorSpec {
  id: string;       // A..F, the bus order on the arm (servo IDs 1..6)
  joint: string;    // MJCF joint name
  label: string;    // human label
  min: number;      // degrees
  max: number;      // degrees
  home: number;     // degrees
  linear?: boolean; // true for a linear joint: the Step tab then counts in mm instead of degrees
}

export const MOTORS: MotorSpec[] = [
  { id: 'A', joint: 'shoulder_pan',  label: 'Shoulder pan (base rotation)', min: -110, max: 110, home: 0 },
  { id: 'B', joint: 'shoulder_lift', label: 'Shoulder lift',                min: -100, max: 100, home: 0 },
  { id: 'C', joint: 'elbow_flex',    label: 'Elbow flex',                   min: -97,  max: 97,  home: 0 },
  { id: 'D', joint: 'wrist_flex',    label: 'Wrist flex',                   min: -95,  max: 95,  home: 0 },
  { id: 'E', joint: 'wrist_roll',    label: 'Wrist roll',                   min: -160, max: 160, home: 0 },
  { id: 'F', joint: 'gripper',       label: 'Gripper (jaw)',                min: 0,    max: 100, home: 0 },
];

const STALL_NM = 2.9;

const act = (m: MotorSpec) =>
  `<position name="${m.joint}" joint="${m.joint}" kp="30" kv="1.2" ctrllimited="true" ` +
  `ctrlrange="${(m.min * Math.PI / 180).toFixed(5)} ${(m.max * Math.PI / 180).toFixed(5)}" ` +
  `forcelimited="true" forcerange="-${STALL_NM} ${STALL_NM}"/>`;

export interface ArmMjcfOpts {
  /** Extra attributes for the arm's base body (default "pos=\"0 0 0\""). Use mocap="true" to let a scene move it (a cart). */
  baseAttrs?: string;
  /** Leave out the default floor and base plate (the scene brings its own). */
  noGround?: boolean;
  /** Extra MJCF inside the hand body (a tool). */
  handExtra?: string;
}

export const armMjcf = (world: string, opts: ArmMjcfOpts = {}) => `
<mujoco model="so101">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <default>
    <joint damping="0.15" armature="0.02" frictionloss="0.02"/>
    <geom contype="0" conaffinity="0"/>
  </default>
  <worldbody>
    ${opts.noGround ? '' : `<geom name="floor" type="plane" size="0.6 0.6 0.01" rgba="0.18 0.2 0.24 1"/>
    <geom name="base_plate" type="box" size="0.06 0.06 0.004" pos="0 0 0.004" rgba="0.3 0.3 0.3 1"/>`}
    ${world}
    <body name="base" ${opts.baseAttrs ?? 'pos="0 0 0"'}>
      <geom name="servo1" type="box" size="0.0225 0.012 0.0175" pos="0 0 0.026" rgba="0.9 0.2 0.2 1" mass="0.06"/>
      <body name="turntable" pos="0 0 0.048">
        <joint name="shoulder_pan" type="hinge" axis="0 0 1" range="-1.9199 1.9199"/>
        <geom type="cylinder" size="0.03 0.006" rgba="0.2 0.2 0.2 1" mass="0.05"/>
        <geom name="bracket" type="box" size="0.025 0.02 0.015" pos="0 0 0.02" rgba="0.85 0.85 0.85 1" mass="0.05"/>
        <body name="shoulder" pos="0 0 0.047">
          <joint name="shoulder_lift" type="hinge" axis="0 1 0" range="-1.7453 1.7453"/>
          <geom name="servo2" type="box" size="0.0225 0.0175 0.012" rgba="1 0.55 0.1 1" mass="0.06"/>
          <geom name="upper_arm" type="box" size="0.015 0.01 0.0575" pos="0 0 0.0575" rgba="0.85 0.85 0.85 1" mass="0.08"/>
          <body name="elbow" pos="0 0 0.115">
            <joint name="elbow_flex" type="hinge" axis="0 1 0" range="-1.6930 1.6930"/>
            <geom name="servo3" type="box" size="0.0225 0.0175 0.012" rgba="0.95 0.85 0.1 1" mass="0.06"/>
            <geom name="forearm" type="box" size="0.0675 0.01 0.0125" pos="0.0675 0 0" rgba="0.85 0.85 0.85 1" mass="0.08"/>
            <body name="wrist" pos="0.135 0 0">
              <joint name="wrist_flex" type="hinge" axis="0 1 0" range="-1.6581 1.6581"/>
              <geom name="servo4" type="box" size="0.012 0.0175 0.0225" rgba="0.2 0.7 0.3 1" mass="0.06"/>
              <body name="hand" pos="0.03 0 0">
                <joint name="wrist_roll" type="hinge" axis="1 0 0" range="-2.7925 2.7925"/>
                <geom name="servo5" type="box" size="0.0175 0.012 0.0225" pos="0.0175 0 0" rgba="0.2 0.45 0.95 1" mass="0.06"/>
                <geom name="jaw_fixed" type="box" size="${((PAD_END_X - 0.038) / 2).toFixed(5)} 0.004 0.006" pos="${((PAD_END_X + 0.038) / 2).toFixed(5)} 0 -0.012" rgba="0.85 0.85 0.85 1" mass="0.02"/>
                <body name="jaw" pos="${JAW_PIVOT_X} 0 -0.006">
                  <joint name="gripper" type="hinge" axis="0 -1 0" range="0 1.7453"/>
                  <geom name="servo6" type="box" size="0.012 0.012 0.0175" pos="-0.01 0.02 0.01" rgba="0.6 0.25 0.85 1" mass="0.06"/>
                  <geom name="jaw_moving" type="box" size="${((PAD_END_X - JAW_PIVOT_X) / 2).toFixed(5)} 0.004 0.006" pos="${((PAD_END_X - JAW_PIVOT_X) / 2).toFixed(5)} 0 0.006" rgba="0.95 0.95 0.95 1" mass="0.02"/>
                </body>
                ${opts.handExtra ?? ''}
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    ${MOTORS.map(act).join('\n    ')}
  </actuator>
</mujoco>`;

/** Arm scene: one pod and one slot (geometry unchanged, names fixed: the logged runs refer to them). */
const ARM_SCENE_WORLD = `
    <!-- Pod and slot are mocap bodies: poses are set by the scene code, not by physics. -->
    <body name="pod" mocap="true" pos="0.16 -0.06 ${POD_REST_Z}">
      <geom name="pod_body" type="cylinder" size="${POD_R} ${POD_H / 2}" rgba="0.62 0.42 0.2 1"/>
    </body>
    <body name="slot" mocap="true" pos="0.16 0.08 0">
      <geom name="slot_base" type="box" size="${SLOT_OPEN / 2 + SLOT_WALL} ${SLOT_OPEN / 2 + SLOT_WALL} ${SLOT_BASE / 2}" pos="0 0 ${SLOT_BASE / 2}" rgba="0.2 0.55 0.35 1"/>
      <geom name="slot_wall_n" type="box" size="${SLOT_OPEN / 2 + SLOT_WALL} ${SLOT_WALL / 2} ${(SLOT_RIM_Z - SLOT_BASE) / 2}" pos="0 ${SLOT_OPEN / 2 + SLOT_WALL / 2} ${(SLOT_RIM_Z + SLOT_BASE) / 2}" rgba="0.3 0.7 0.45 1"/>
      <geom name="slot_wall_s" type="box" size="${SLOT_OPEN / 2 + SLOT_WALL} ${SLOT_WALL / 2} ${(SLOT_RIM_Z - SLOT_BASE) / 2}" pos="0 ${-(SLOT_OPEN / 2 + SLOT_WALL / 2)} ${(SLOT_RIM_Z + SLOT_BASE) / 2}" rgba="0.3 0.7 0.45 1"/>
      <geom name="slot_wall_e" type="box" size="${SLOT_WALL / 2} ${SLOT_OPEN / 2} ${(SLOT_RIM_Z - SLOT_BASE) / 2}" pos="${SLOT_OPEN / 2 + SLOT_WALL / 2} 0 ${(SLOT_RIM_Z + SLOT_BASE) / 2}" rgba="0.3 0.7 0.45 1"/>
      <geom name="slot_wall_w" type="box" size="${SLOT_WALL / 2} ${SLOT_OPEN / 2} ${(SLOT_RIM_Z - SLOT_BASE) / 2}" pos="${-(SLOT_OPEN / 2 + SLOT_WALL / 2)} 0 ${(SLOT_RIM_Z + SLOT_BASE) / 2}" rgba="0.3 0.7 0.45 1"/>
    </body>
`;
export const MJCF = armMjcf(ARM_SCENE_WORLD);
