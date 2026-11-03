"""Arm test 1: can an SO-101-like arm pull a seed pod with a 400 g lettuce out of its hole?

Planar SO-101 approximation (link lengths and masses ASSUMED, check against the real arm):
base yaw, shoulder pitch, elbow, wrist pitch, wrist roll, gripper pointing down. Each joint is
a position servo limited to the STS3215 stall torque (`stall_nm`). The gripper is assumed to
have already grasped the pod (weld), so this tests torque only, not grasping.

The pod sits on a vertical slide in a hole, with `pull_n` of friction (roots, sponge, lid)
resisting the pull. Lettuce mass rides on the pod. The arm starts with the gripper on the pod
top and is commanded to a pose `lift_mm` higher. Watch force.<joint> against stall_nm and
q.pod_lift (how far the pod actually came out).
"""
from constants import GRAVITY
import math

PARAMS = {
    "stall_nm": (1.9, "servo stall torque, N m (STS3215 7.4 V ~1.9; 12 V version ~2.9)"),
    "lettuce_kg": (0.4, "lettuce + roots + water mass on the pod, kg"),
    "pull_n": (10.0, "friction holding the pod in its hole, N (unknown: sweep it)"),
    "reach_mm": (180.0, "horizontal distance from shoulder to pod, mm"),
    "lift_mm": (100.0, "how far to lift the pod, mm"),
    "l1_mm": (116.0, "upper arm length, mm (assumed)"),
    "l2_mm": (135.0, "forearm length, mm (assumed)"),
    "l3_mm": (100.0, "wrist pitch axis to grip point, mm (assumed)"),
    "kp": (12.0, "servo position gain, N m / rad"),
    "timestep_s": (0.001, "integrator step"),
}
TRACK_BODY = "pod"
CAMERAS = ["side"]
_JOINTS = ["base_yaw", "shoulder", "elbow", "wrist_pitch", "wrist_roll"]
DEFAULT_CONTROLS = {}


def _ik(dx, dz, l1, l2, l3):
    wx, wz = dx, dz + l3  # wrist point above the grip point (gripper points down)
    d2 = wx * wx + wz * wz
    c2 = (d2 - l1 * l1 - l2 * l2) / (2 * l1 * l2)
    if abs(c2) > 1:
        raise ValueError(f"target out of reach: wrist at {math.sqrt(d2):.3f} m, max {l1 + l2:.3f} m")
    a2 = -math.acos(c2)  # elbow up
    a1 = math.atan2(wz, wx) - math.atan2(l2 * math.sin(a2), l1 + l2 * math.cos(a2))
    a3 = -math.pi / 2 - a1 - a2
    return a1, a2, a3


def build(**p) -> str:
    l1, l2, l3 = (float(p[k]) / 1000 for k in ("l1_mm", "l2_mm", "l3_mm"))
    reach = float(p["reach_mm"]) / 1000
    lift = float(p["lift_mm"]) / 1000
    sh_z = 0.08
    pod_top = 0.03
    s = _ik(reach, pod_top - sh_z, l1, l2, l3)
    e = _ik(reach, pod_top + lift - sh_z, l1, l2, l3)
    delta = [0.0, e[0] - s[0], e[1] - s[1], e[2] - s[2], 0.0]
    DEFAULT_CONTROLS.clear()
    DEFAULT_CONTROLS.update({f"{j}_servo": d for j, d in zip(_JOINTS, delta)})
    stall = float(p["stall_nm"])
    kp = float(p["kp"])
    deg = math.degrees
    ng = 'contype="0" conaffinity="0"'
    act = "".join(
        f'<position name="{j}_servo" joint="{j}" kp="{kp}" forcerange="-{stall} {stall}" forcelimited="true" '
        f'ctrlrange="-3.2 3.2" ctrllimited="true"/>' for j in _JOINTS)
    return f"""<mujoco model="arm_pod_pull">
  <option timestep="{p['timestep_s']}" gravity="0 0 -{GRAVITY}" integrator="implicitfast"/>
  <visual><global offwidth="960" offheight="720"/><headlight ambient="0.4 0.4 0.4" diffuse="0.6 0.6 0.6"/></visual>
  <default><joint damping="0.6" armature="0.01"/></default>
  <worldbody>
    <light pos="0.3 -0.6 1" dir="0 0.5 -1"/>
    <geom name="floor" type="plane" size="1 1 0.1" pos="0 0 -0.1" rgba="0.3 0.32 0.35 1"/>
    <geom name="grow_pipe" type="box" size="0.08 0.06 0.01" pos="{reach:.4f} 0 -0.01" {ng} rgba="0.55 0.57 0.6 1"/>
    <camera name="side" pos="{reach/2:.3f} -0.75 0.15" xyaxes="1 0 0 0 0 1" fovy="45"/>
    <body name="base" pos="0 0 0.04">
      <geom type="box" size="0.04 0.04 0.04" {ng} mass="0.3" rgba="0.9 0.9 0.92 1"/>
      <joint name="base_yaw" type="hinge" axis="0 0 1" range="-3 3"/>
      <body name="upper" pos="0 0 0.04" euler="0 {-deg(s[0]):.4f} 0">
        <joint name="shoulder" type="hinge" axis="0 -1 0"/>
        <geom type="capsule" fromto="0 0 0 {l1:.4f} 0 0" size="0.015" {ng} mass="0.12" rgba="0.95 0.95 0.95 1"/>
        <body name="fore" pos="{l1:.4f} 0 0" euler="0 {-deg(s[1]):.4f} 0">
          <joint name="elbow" type="hinge" axis="0 -1 0"/>
          <geom type="capsule" fromto="0 0 0 {l2:.4f} 0 0" size="0.014" {ng} mass="0.12" rgba="0.95 0.95 0.95 1"/>
          <body name="wrist" pos="{l2:.4f} 0 0" euler="0 {-deg(s[2]):.4f} 0">
            <joint name="wrist_pitch" type="hinge" axis="0 -1 0"/>
            <joint name="wrist_roll" type="hinge" axis="1 0 0"/>
            <geom type="capsule" fromto="0 0 0 {l3 - 0.01:.4f} 0 0" size="0.013" {ng} mass="0.1" rgba="0.2 0.6 0.9 1"/>
            <body name="grip" pos="{l3:.4f} 0 0"><site name="grip" size="0.006"/></body>
          </body>
        </body>
      </body>
    </body>
    <body name="pod" pos="{reach:.4f} 0 {pod_top - 0.025:.4f}">
      <joint name="pod_lift" type="slide" axis="0 0 1" range="0 0.3" limited="true" damping="1" frictionloss="{float(p['pull_n'])}"/>
      <geom type="cylinder" size="0.02 0.025" {ng} mass="0.02" rgba="0.95 0.6 0.2 1"/>
      <geom name="lettuce" type="sphere" size="0.07" pos="0 0 0.09" {ng} mass="{float(p['lettuce_kg'])}" rgba="0.3 0.8 0.3 0.6"/>
    </body>
  </worldbody>
  <equality><weld body1="grip" body2="pod"/></equality>
  <actuator>{act}</actuator>
  <sensor><framepos name="grip_pos" objtype="site" objname="grip"/></sensor>
</mujoco>"""
