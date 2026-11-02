"""Yaw control tests: does the cart stay square on the pipe so it clears the brackets?

Two modes:
- mode="single": one vertical pipe B. Optional guide: a pair of rails on the pipe forming a
  channel that is wide at BOTH ends and narrow in the middle (double-ended funnel), centred
  in the hand's free gap at 120 deg. A pin on the cart rides in the channel. A sideways
  mass offset makes the cart spiral (as in pipe_climb), so we see whether the funnel
  catches it and squares it up, going up and then coming back down.
- mode="twin": pipes B and C, pipe_gap_m apart, one hand on each, both rigid to the base.
  No guide. Tests whether gripping two pipes alone stops the drift.

Drive goes up for half the run, then reverses. yaw = atan2(cart_xaxis[1], cart_xaxis[0]).
Single-row wheels, point contact (sideways grip understated).
"""

from constants import (
    CART_MASS, DRIVE_RPM, DRIVE_WHEEL_ANGLE, FRICTION, GRAVITY, IDLER_WHEEL_ANGLES, PAYLOAD_MASS,
    PIPE_R, SPRING_K, SPRING_PRELOAD_N, SPRING_TRAVEL, WHEEL_R, WHEEL_W,
)
import math

PARAMS = {
    "mode": ("single", "single (pipe B only) or twin (pipes B and C)"),
    "guide": (True, "single mode: add the double-ended funnel guide"),
    "surface": ("dry", "dry or wet"),
    "mass_offset_mm": (10.0, "sideways offset of the centre of mass, mm"),
    "start_yaw_deg": (0.0, "single mode: cart starts twisted this much about the pipe"),
    "pipe_gap_m": (0.3, "twin mode: distance between pipes B and C"),
    "guide_z_m": (0.30, "height of the guide centre"),
    "guide_mid_mm": (30.0, "length of the narrow middle section, mm"),
    "guide_flare_mm": (40.0, "length of each flared end, mm"),
    "guide_mouth_deg": (31.0, "half-width of each mouth, degrees around the pipe"),
    "pin_clear_mm": (1.0, "pin-to-rail clearance in the narrow middle, mm"),
    "start_height_m": (0.15, "cart centre height at t=0"),
    "timestep_s": (0.0005, "integrator step"),
}

TRACK_BODY = "cart"
CAMERAS = ["top", "side"]
OMEGA = DRIVE_RPM * 2 * math.pi / 60.0
DEFAULT_CONTROLS = {"drive": [[0, OMEGA], [6, -OMEGA]]}

GAP_ANG = 120.0  # middle of the free gap between idler at 60 and drive at 180
RAIL_RAD = PIPE_R + 0.004
RAIL_R = 0.0015
PIN_R = 0.0025


def _truthy(v):
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


def build(**p) -> str:
    mu = FRICTION[p["surface"]]
    twin = str(p["mode"]).lower() == "twin"
    guide = (not twin) and _truthy(p["guide"])
    ring_r = PIPE_R + WHEEL_R
    k, preload, travel = SPRING_K, SPRING_PRELOAD_N, SPRING_TRAVEL
    z0 = float(p["start_height_m"])
    mass = CART_MASS + PAYLOAD_MASS
    off = float(p["mass_offset_mm"]) / 1000.0
    gap = float(p["pipe_gap_m"])
    yaw0 = math.radians(float(p["start_yaw_deg"])) if not twin else 0.0

    def wheel(name, cx, cy, ang, driven):
        a = math.radians(ang)
        wx, wy = cx + ring_r * math.cos(a), cy + ring_r * math.sin(a)
        radial = f"{math.cos(a):.6f} {math.sin(a):.6f} 0"
        s = -1.0 if driven else 1.0
        tan = f"{s*-math.sin(a):.6f} {s*math.cos(a):.6f} 0"
        sp = "" if driven else (
            f'<joint name="spring_{name}" type="slide" axis="{radial}" range="{-travel:.5f} {travel:.5f}" '
            f'stiffness="{k}" springref="{-preload/k:.6f}" damping="4" limited="true"/>')
        return f"""
      <body name="{name}" pos="{wx:.6f} {wy:.6f} 0">
        {sp}
        <joint name="wheel_{name}" type="hinge" axis="{tan}" damping="0.0005"/>
        <geom type="sphere" size="{WHEEL_R}" mass="0.02" friction="{mu} 0.005 0.0001" condim="3"
              solref="0.005 1" solimp="0.95 0.99 0.001" rgba="0.15 0.15 0.15 1"/>
        <geom type="cylinder" size="{WHEEL_R} {WHEEL_W/2}" zaxis="{tan}" contype="0" conaffinity="0" mass="0" rgba="0.2 0.2 0.25 1"/>
      </body>"""

    def hand(tag, cx, driven):
        x = wheel(f"{tag}drive", cx, 0, DRIVE_WHEEL_ANGLE, driven)
        for i, a in enumerate(IDLER_WHEEL_ANGLES):
            x += wheel(f"{tag}idler{i+1}", cx, 0, a, False)
        return x

    wheels = hand("", 0.0, True)
    pipes = f'<geom name="pipeB" type="capsule" fromto="0 0 0 0 0 1.2" size="{PIPE_R}" friction="{mu} 0.005 0.0001" rgba="0.55 0.57 0.6 1"/>'
    if twin:
        wheels += hand("c_", gap, False)
        pipes += f'<geom name="pipeC" type="capsule" fromto="{gap} 0 0 {gap} 0 1.2" size="{PIPE_R}" friction="{mu} 0.005 0.0001" rgba="0.55 0.57 0.6 1"/>'
        mass_pos = f"{gap/2:.4f} {off:.5f} 0"
    else:
        mass_pos = f"{-ring_r*0.5:.5f} {off:.5f} 0"

    rails = ""
    if guide:
        zg = float(p["guide_z_m"])
        lm, lf = float(p["guide_mid_mm"]) / 1000, float(p["guide_flare_mm"]) / 1000
        w0 = (PIN_R + RAIL_R + float(p["pin_clear_mm"]) / 1000) / RAIL_RAD
        wm = math.radians(float(p["guide_mouth_deg"]))
        prof = [(zg - lm/2 - lf, wm), (zg - lm/2, w0), (zg + lm/2, w0), (zg + lm/2 + lf, wm)]
        c = math.radians(GAP_ANG)
        for side in (1, -1):
            for (za, ha), (zb, hb) in zip(prof[:-1], prof[1:]):
                ta, tb = c + side*ha, c + side*hb
                rails += (f'<geom type="capsule" size="{RAIL_R}" fromto="{RAIL_RAD*math.cos(ta):.5f} {RAIL_RAD*math.sin(ta):.5f} {za:.4f} '
                          f'{RAIL_RAD*math.cos(tb):.5f} {RAIL_RAD*math.sin(tb):.5f} {zb:.4f}" rgba="0.9 0.6 0.1 1"/>')
        # the bracket the guide protects, sitting in the gap at the guide's middle
        rails += (f'<geom name="bracket" type="box" size="0.006 0.004 0.008" pos="{(PIPE_R+0.006)*math.cos(c):.5f} '
                  f'{(PIPE_R+0.006)*math.sin(c):.5f} {zg:.4f}" euler="0 0 {GAP_ANG}" contype="0" conaffinity="0" rgba="0.8 0.1 0.1 0.6"/>')

    pa = math.radians(GAP_ANG)
    pin = (f'<geom name="pin" type="sphere" size="{PIN_R}" pos="{RAIL_RAD*math.cos(pa):.5f} {RAIL_RAD*math.sin(pa):.5f} 0" '
           f'mass="0.002" friction="0.2" rgba="0.1 0.5 0.9 1"/>'
           f'<site name="pin_s" pos="{RAIL_RAD*math.cos(pa):.5f} {RAIL_RAD*math.sin(pa):.5f} 0"/>') if not twin else ""
    quat = f"{math.cos(yaw0/2):.6f} 0 0 {math.sin(yaw0/2):.6f}"

    return f"""<mujoco model="guide_test">
  <option timestep="{p['timestep_s']}" gravity="0 0 -{GRAVITY}" integrator="implicitfast"/>
  <visual><global offwidth="960" offheight="720"/><headlight ambient="0.4 0.4 0.4" diffuse="0.6 0.6 0.6"/></visual>
  <custom><numeric name="wheel_radius" data="{WHEEL_R}"/></custom>
  <worldbody>
    <light pos="0.5 -0.5 2" dir="-0.3 0.3 -1"/>
    <geom type="plane" size="1 1 0.1" rgba="0.3 0.32 0.35 1"/>
    {pipes}
    {rails}
    <camera name="top" pos="{gap/2 if twin else 0:.3f} 0 1.6" xyaxes="1 0 0 0 1 0" fovy="{40 if twin else 6}"/>
    <camera name="side" pos="-0.25 0.35 0.3" xyaxes="-0.814 -0.581 0 0 0 1" fovy="40"/>
    <body name="cart" pos="0 0 {z0}" quat="{quat}">
      <freejoint/>
      <geom type="sphere" size="0.006" pos="{mass_pos}" mass="{mass}" contype="0" conaffinity="0" rgba="1 0.4 0.2 1"/>
      {pin}
      {wheels}
    </body>
  </worldbody>
  <actuator>
    <velocity name="drive" joint="wheel_drive" kv="1.0" ctrlrange="-20 20" forcerange="-0.3 0.3" ctrllimited="true" forcelimited="true"/>
  </actuator>
  <sensor>
    <framepos name="cart_pos" objtype="body" objname="cart"/>
    <framexaxis name="cart_xaxis" objtype="body" objname="cart"/>
    <framezaxis name="cart_zaxis" objtype="body" objname="cart"/>
  </sensor>
</mujoco>"""
