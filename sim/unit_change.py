"""Unit change animation: the cart crosses unit 1 -> unit 2 -> unit 3 (corner unit) and lands on F.

Scripted, not physical: gravity is off, nothing collides. Every joint is driven by an
integrated-velocity actuator fed piecewise-constant velocities (0.2 s knots), so the cart
follows the path as straight chords between knots (under 2 mm off on the 150 mm corners).
Use it to check the sequence and clearances, not forces. Geometry follows 3-unit layout v2
(render 20261101-104909-328f): 70 cm loops 2 m tall, loop 10 cm in front of the spine,
pipes 14 cm apart at a handover, unit 3 swung clockwise about pipe E.

Pipes (all vertical sides of the loops): A, B = unit 1; C, D = unit 2; E, F = unit 3.
Cart (OpenPocket #283, the omni cart of docs/plans/cart-roll-redesign-plan.md): two hands 12 cm apart (cad/cart_dims.py PIPE_SPACING) on ONE rigid base, no hinges. Each hand is
the three-lobe sleeve of cad/hand_sleeve.py v5: a thin ring (bore R20, outer R34.5) with a 38 mm omni wheel on the outer lobe (180 deg, drawn at its drive row and its roll row),
two ball cups on the +/-60 deg lobes, and a jaw wedge that carries the +60 deg lobe and swings open 92 deg on a pin at the wedge's far edge. Hand 2 is the true mirror of hand 1.
It always rides on the hand whose partner hangs OUTSIDE the loop, and the hands swap roles at each crossover.

Roll rule (v3, replaces v2's hinge swing): after a hand releases, the WHOLE cart rolls SWING_DEG (90) on the riding pipe, on its roll wheel, so the free hand sits in front of the
pipe plane (-y, the plate side) and its old pipe leaves through the open jaw. Before the next clamp the cart rolls back and the new pipe enters through the jaw. Found with the
control-ui contact search (scripts/search-swing.ts): only the PLATE SIDE can clear, and only if the jaw wedge reaches at least 140 deg (the CAD draws it to 110 and then neither
direction clears: the fixed part of the ring is still round the pipe after 3 degrees of roll). The wedge is drawn to JAW_A1_PROPOSED_DEG (150) here. Same as v2, the clearance of
this path against the units is checked by eye and by the 5 mm figure below, not by contact: nothing collides in this sim.

Sequence (seconds):
  0.0  ride hand 1 up B (unit 1)
  3.0  hand 2 clamps C, 4.0 hand 1 releases B, 5.0 roll the cart 90 deg, hand 1 off to the front
  6.2  up C, round unit 2's top corners, down D (free hand in front)
 13.2  roll back, hand 1 in onto E, 14.4 hand 1 clamps E, 15.4 hand 2 releases D
 16.4  up E sideways, round unit 3's top corner (cart still parallel to units 1-2)
 20.4  swivel 90 deg about the top bar into unit 3's plane
 22.4  along unit 3's top bar, round the far corner, down F; hold from 26.8
"""

import math

from constants import (
    BALL_R, JAW_A1_PROPOSED_DEG, OMNI_R, PIPE_SPACING, SLEEVE_BORE_R, SLEEVE_OUT_R, SWING_DEG,
)

PARAMS = {
    "knot_s": (0.2, "control knot spacing, s (informational; fixed at import)"),
}
TRACK_BODY = "cart"
CAMERAS = ["overview", "chase"]

# ---------------- layout (metres) ----------------
LOOP_W, LOOP_H, LOOP_R = 0.70, 2.00, 0.15
PIPE_R = 0.016
LOOP_OFF = 0.10            # loop in front of spine (-y)
TANK = (0.70, 0.46, 0.30)
Z_BOT = 0.30 + 0.12
Z_TOP = Z_BOT + LOOP_H
SEP = PIPE_SPACING         # pipe spacing at a handover = hand spacing (the cart's two hands, 120 mm)
PITCH = LOOP_W + SEP
YL = -LOOP_OFF
X_B, X_C, X_D = LOOP_W / 2, PITCH - LOOP_W / 2, PITCH + LOOP_W / 2
X_E = X_D + SEP
U3 = (X_E + LOOP_OFF, -LOOP_OFF - LOOP_W / 2)
Y_F = YL - LOOP_W
ZC = Z_BOT + LOOP_H / 2
R = LOOP_R
OPEN = 1.6
SWING = math.radians(SWING_DEG)
UNITS = [(0.0, 0.0, 0.0), (PITCH, 0.0, 0.0), (U3[0], U3[1], -90.0)]
KNOT = 0.2


def lerp(a, b, u):
    return a + (b - a) * u


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def _rx(t):
    c, s = math.cos(t), math.sin(t)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _ry(t):
    c, s = math.cos(t), math.sin(t)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


D = math.radians
# Each phase: (duration s, label, fn(u) -> state overrides). "rp" is the riding hand's centre.
PHASES = [
    (0.5, "start on B", lambda u: {}),
    (2.5, "up B", lambda u: {"rp": (X_B, YL, lerp(0.90, ZC, u))}),
    (1.0, "hand 2 clamps C", lambda u: {"j2": lerp(OPEN, 0, u)}),
    (1.0, "hand 1 releases B", lambda u: {"j1": lerp(0, OPEN, u), "ride": 2, "rp": (X_C, YL, ZC)}),
    (1.2, "roll off B", lambda u: {"a5": SWING * u}),
    (2.0, "up C", lambda u: {"rp": (X_C, YL, lerp(ZC, Z_TOP - R, u))}),
    (1.0, "corner C", lambda u: {"rp": (X_C + R - R * math.cos(D(90 * u)), YL, Z_TOP - R + R * math.sin(D(90 * u))), "a4": D(90 * u)}),
    (1.0, "top bar unit 2", lambda u: {"rp": (lerp(X_C + R, X_D - R, u), YL, Z_TOP)}),
    (1.0, "corner D", lambda u: {"rp": (X_D - R + R * math.sin(D(90 * u)), YL, Z_TOP - R + R * math.cos(D(90 * u))), "a4": D(90 + 90 * u)}),
    (2.0, "down D", lambda u: {"rp": (X_D, YL, lerp(Z_TOP - R, ZC, u))}),
    (1.2, "roll onto E", lambda u: {"a5": SWING * (1 - u)}),
    (1.0, "hand 1 clamps E", lambda u: {"j1": lerp(OPEN, 0, u)}),
    (1.0, "hand 2 releases D", lambda u: {"j2": lerp(0, OPEN, u), "ride": 1, "rp": (X_E, YL, ZC)}),
    (2.0, "up E sideways", lambda u: {"rp": (X_E, YL, lerp(ZC, Z_TOP - R, u))}),
    (1.2, "corner E", lambda u: {"rp": (X_E, YL - R + R * math.cos(D(90 * u)), Z_TOP - R + R * math.sin(D(90 * u))), "a3": D(90 * u)}),
    (0.8, "top bar unit 3", lambda u: {"rp": (X_E, lerp(YL - R, -0.33, u), Z_TOP)}),
    (2.0, "swivel into unit 3", lambda u: {"a2": D(90 * u)}),
    (1.2, "top bar unit 3", lambda u: {"rp": (X_E, lerp(-0.33, Y_F + R, u), Z_TOP)}),
    (1.2, "corner F", lambda u: {"rp": (X_E, Y_F + R - R * math.sin(D(90 * u)), Z_TOP - R + R * math.cos(D(90 * u))), "a1": D(90 * u)}),
    (2.0, "down F", lambda u: {"rp": (X_E, Y_F, lerp(Z_TOP - R, ZC, u))}),
    (1.5, "stop on F", lambda u: {}),
]
DURATION = sum(p[0] for p in PHASES)


def state(t):
    s = {"rp": (X_B, YL, 0.90), "ride": 1, "a1": 0.0, "a2": 0.0, "a3": 0.0, "a4": 0.0, "a5": 0.0,
         "j1": 0.0, "j2": OPEN, "phase": "stop on F"}
    t0 = 0.0
    for dur, name, fn in PHASES:
        if t >= t0 + dur:
            s.update(fn(1.0))
            t0 += dur
            continue
        s.update(fn(ease((t - t0) / dur)))
        s["phase"] = name
        return s
    return s


def rot(s):
    return _mm(_mm(_rx(s["a1"]), _ry(s["a2"])), _mm(_rx(s["a3"]), _ry(s["a4"])))


def pose(t):
    """Root position (cart frame origin, = hand 1 when a5 = 0) and state.

    The roll joint a5 turns the whole cart about local z through hand 2's pipe (x = SEP), which only
    happens while riding hand 2, so hand 2 stays put and the root is rp - SEP * x_local.
    """
    s = state(t)
    Rm = rot(s)
    xl = [Rm[i][0] for i in range(3)]
    rp = s["rp"]
    root = rp if s["ride"] == 1 else tuple(rp[i] - SEP * xl[i] for i in range(3))
    if s["ride"] == 1:
        assert abs(s["a5"]) < 1e-9, "roll only while riding hand 2"
    return root, s


NAMES = ["x", "y", "z", "a1", "a2", "a3", "a4", "a5", "jaw1", "jaw2"]


def _joint_targets(t):
    """Joint positions relative to the start pose (all joints are 0 at t=0)."""
    r, s = pose(t)
    r0, _ = pose(0.0)
    return [r[0] - r0[0], r[1] - r0[1], r[2] - r0[2], s["a1"], s["a2"], s["a3"], s["a4"], s["a5"],
            s["j1"], OPEN - s["j2"]]   # hand 1 (the B-type hand) opens CCW, hand 2 (the mirror) opens CW from its open start pose


def _controls():
    out = {n: [] for n in NAMES}
    n = int(math.ceil(DURATION / KNOT))
    prev = _joint_targets(0.0)
    for i in range(n):
        t0, t1 = i * KNOT, min((i + 1) * KNOT, DURATION)
        nxt = _joint_targets(t1)
        for k, name in enumerate(NAMES):
            out[name].append([round(t0, 3), round((nxt[k] - prev[k]) / (t1 - t0), 4)])
        prev = nxt
    for name in NAMES:
        out[name].append([round(DURATION, 3), 0.0])
    return out


DEFAULT_CONTROLS = _controls()


def _cam_axes(pos, target):
    d = [target[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in d))
    zc = [-c / n for c in d]
    xc = [-zc[1], zc[0], 0.0]  # cross(up, zc) with up = +Z
    m = math.sqrt(xc[0] ** 2 + xc[1] ** 2)
    xc = [c / m for c in xc]
    yc = [zc[1] * xc[2] - zc[2] * xc[1], zc[2] * xc[0] - zc[0] * xc[2], zc[0] * xc[1] - zc[1] * xc[0]]
    f = lambda v: " ".join(f"{c:.4f}" for c in v)
    return f"{f(xc)} {f(yc)}"


def _unit_xml(cx, cy, ang):
    th = math.radians(ang)
    c, s = math.cos(th), math.sin(th)

    def w(lx, ly, lz):
        return (cx + lx * c - ly * s, cy + lx * s + ly * c, lz)

    def ft(p, q):
        return " ".join(f"{v:.4f}" for v in (*p, *q))

    g = []
    pipe = 'rgba="0.72 0.74 0.78 1"'
    W2 = LOOP_W / 2
    segs = [((-W2 + R, YL, Z_BOT), (W2 - R, YL, Z_BOT)), ((W2, YL, Z_BOT + R), (W2, YL, Z_TOP - R)),
            ((W2 - R, YL, Z_TOP), (-W2 + R, YL, Z_TOP)), ((-W2, YL, Z_TOP - R), (-W2, YL, Z_BOT + R))]
    for p, q in segs:
        g.append(f'<geom type="capsule" fromto="{ft(w(*p), w(*q))}" size="{PIPE_R}" {pipe}/>')
    for (ox, oz, a0) in ((W2 - R, Z_BOT + R, -90), (W2 - R, Z_TOP - R, 0), (-W2 + R, Z_TOP - R, 90), (-W2 + R, Z_BOT + R, 180)):
        pts = [(ox + R * math.cos(math.radians(a0 + 15 * k)), YL, oz + R * math.sin(math.radians(a0 + 15 * k))) for k in range(7)]
        for p, q in zip(pts, pts[1:]):
            g.append(f'<geom type="capsule" fromto="{ft(w(*p), w(*q))}" size="{PIPE_R}" {pipe}/>')
    tx, ty, _ = w(0, 0, 0)
    g.append(f'<geom type="box" pos="{tx:.4f} {ty:.4f} {TANK[2]/2:.3f}" size="{TANK[0]/2} {TANK[1]/2} {TANK[2]/2}" '
             f'euler="0 0 {ang}" rgba="0.32 0.34 0.38 1"/>')
    g.append(f'<geom type="cylinder" fromto="{ft(w(0, 0, TANK[2]), w(0, 0, Z_TOP - 0.04))}" size="0.055" rgba="0.92 0.92 0.88 1"/>')
    g.append(f'<geom type="cylinder" fromto="{ft(w(0, 0, Z_TOP - 0.04), w(0, 0, Z_TOP + 0.01))}" size="0.021" rgba="0.6 0.6 0.62 1"/>')
    for z in (Z_BOT, Z_TOP - 0.01):
        g.append(f'<geom type="capsule" fromto="{ft(w(0, -0.055, z), w(0, YL + PIPE_R, z))}" size="0.008" rgba="0.5 0.5 0.55 1"/>')
    z = Z_BOT + 0.2
    while z < Z_TOP - 0.15:
        for sg in (-1, 1):
            g.append(f'<geom type="cylinder" fromto="{ft(w(sg * 0.05, 0, z), w(sg * 0.09, 0, z))}" size="0.025" rgba="0.35 0.72 0.35 1"/>')
        z += 0.2
    return "\n    ".join(g)


def _hand_xml(name, x0, color, jaw_color, jaw0_deg, sg):
    """One hand in the cart frame: pipe along local z at x = x0, the jaw wedge facing the other hand and +y (the spine side).

    Geometry is the three-lobe sleeve of cad/hand_sleeve.py v5, drawn for hand 1 (sg = +1, wedge towards +x) and mirrored in x for hand 2 (sg = -1). Angles are CAD angles from +x
    of hand 1. The jaw wedge is 20 deg (the C gap) to JAW_A1_PROPOSED_DEG, hinged on a pin at its far edge on the tube; opening turns it CCW for hand 1 and CW for hand 2.
    """
    RR = (SLEEVE_BORE_R + SLEEVE_OUT_R) / 2        # mid radius of the tube wall (20 to 34.5)
    HALF_L = 0.062                                  # half the 124 mm sleeve
    SEG = 18.0
    A_JAW0, A_JAW1 = 20.0, JAW_A1_PROPOSED_DEG

    def at(rad, deg, ox=0.0, oy=0.0):
        a = math.radians(deg)
        return (x0 + sg * rad * math.cos(a) - ox, rad * math.sin(a) - oy)

    def seg(a, ox=0.0, oy=0.0, col=color):
        px, py = at(RR, a, ox, oy)
        eu = a if sg > 0 else 180.0 - a
        return (f'<geom type="box" pos="{px:.4f} {py:.4f} 0" size="{(SLEEVE_OUT_R - SLEEVE_BORE_R) / 2:.5f} {RR * math.tan(math.radians(SEG / 2)):.5f} {HALF_L}" '
                f'euler="0 0 {eu:.2f}" rgba="{col}"/>')

    def ball(a, z, ox=0.0, oy=0.0):
        px, py = at(0.016 + BALL_R, a, ox, oy)
        return f'<geom type="sphere" pos="{px:.4f} {py:.4f} {z}" size="{BALL_R}" rgba="0.75 0.75 0.78 1"/>'

    g = []
    a = A_JAW1 + SEG / 2
    while a < 340.0 - SEG / 2 + 1e-6:                      # the fixed part of the tube: from the jaw's far edge round to the C gap
        g.append(seg(a)); a += SEG
    px, py = at(SLEEVE_OUT_R, A_JAW1)                      # the pin sits on the tube surface at the wedge's far edge
    # outer lobe (180 deg): the drive wheel (top row) and the roll wheel (bottom row), 38 mm omni wheels drawn as spheres on their rows (+/-38 mm)
    for z in (0.038, -0.038):
        wx, wy = at(0.016 + OMNI_R, 180.0)
        g.append(f'<geom type="sphere" pos="{wx:.4f} {wy:.4f} {z}" size="{OMNI_R}" rgba="0.12 0.12 0.12 1"/>')
    g.append(f'<geom type="box" pos="{at(0.05, 180.0)[0]:.4f} 0 0" size="0.011 0.015 {HALF_L}" rgba="{color}"/>')   # the lobe
    for z in (0.038, -0.038):
        g.append(ball(-60.0, z))                           # the -60 deg ball cups are fixed
    jaw = []   # the jaw's parts are placed relative to the pin
    for k in range(int((A_JAW1 - A_JAW0) // SEG)):
        aa = A_JAW0 + SEG / 2 + k * SEG
        qx, qy = at(RR, aa)
        eu = aa if sg > 0 else 180.0 - aa
        jaw.append(f'<geom type="box" pos="{qx - px:.4f} {qy - py:.4f} 0" size="{(SLEEVE_OUT_R - SLEEVE_BORE_R) / 2:.5f} {RR * math.tan(math.radians(SEG / 2)):.5f} {HALF_L}" '
                   f'euler="0 0 {eu:.2f}" rgba="{jaw_color}"/>')
    for z in (0.038, -0.038):
        bx, by = at(0.016 + BALL_R, 60.0)
        jaw.append(f'<geom type="sphere" pos="{bx - px:.4f} {by - py:.4f} {z}" size="{BALL_R}" rgba="0.75 0.75 0.78 1"/>')   # the +60 deg ball cups ride the jaw
    qx, qy = at(0.030, 60.0)
    jaw.append(f'<geom type="box" pos="{qx - px:.4f} {qy - py:.4f} 0" size="0.011 0.014 {HALF_L}" rgba="{jaw_color}"/>')     # the +60 deg lobe
    jaw.append(f'<geom type="cylinder" fromto="0 0 {-HALF_L - 0.002} 0 0 {HALF_L + 0.002}" size="0.002" rgba="0.8 0.8 0.82 1"/>')   # the hinge pin
    return ("\n".join(g) +
            f'\n<body name="{name}_jaw" pos="{px:.4f} {py:.4f} 0" euler="0 0 {jaw0_deg:.2f}">'
            f'<joint name="{name}_jaw" type="hinge" axis="0 0 1" armature="0.001" damping="0.09"/>'
            + "\n".join(jaw) + "</body>")


INERT = '<inertial pos="0 0 0" mass="0.01" diaginertia="1e-5 1e-5 1e-5"/>'


def build(**p) -> str:
    units = "\n    ".join(_unit_xml(cx, cy, ang) for (cx, cy, ang) in UNITS)
    r0, _ = pose(0.0)
    ov_pos, ov_tgt = (3.1, -3.6, 3.0), (0.75, -0.35, 1.45)
    ch_pos = (0.75, -0.95, 0.35)
    hands = (_hand_xml("hand1", 0.0, "0.2 0.45 0.85 1", "0.55 0.3 0.85 1", 0.0, 1) + "\n" +
             _hand_xml("hand2", SEP, "0.2 0.45 0.85 1", "0.55 0.3 0.85 1", -math.degrees(OPEN), -1))
    # the rigid base on the sleeve pads (cad/cart_dims.py, omni_cart): plate 168 x 6 x 146 at y -56 .. -50, battery 70 x 50 x 70, arm base block, the arm folded up
    cart_extra = f"""
          <geom type="box" pos="{SEP/2} -0.053 0" size="0.084 0.003 0.073" rgba="1 0.85 0.3 1"/>
          <geom type="box" pos="{SEP/2} -0.081 0" size="0.035 0.025 0.035" rgba="0.3 0.55 0.35 1"/>
          <geom type="box" pos="{SEP/2} -0.116 0" size="0.035 0.010 0.035" rgba="0.9 0.65 0.2 1"/>
          <geom type="cylinder" fromto="{SEP/2} -0.126 0 {SEP/2} -0.149 0" size="0.026" rgba="0.95 0.4 0.1 1"/>
          <geom type="capsule" fromto="{SEP/2} -0.149 0 {SEP/2} -0.164 0.06" size="0.012" rgba="0.95 0.4 0.1 1"/>
          <geom type="capsule" fromto="{SEP/2} -0.164 0.06 {SEP/2} -0.179 0.22" size="0.012" rgba="0.95 0.4 0.1 1"/>
          <geom type="capsule" fromto="{SEP/2} -0.179 0.22 {SEP/2} -0.189 0.06" size="0.012" rgba="0.95 0.4 0.1 1"/>
          <geom type="box" pos="{SEP/2} -0.189 0.05" size="0.015 0.015 0.015" rgba="0.95 0.4 0.1 1"/>"""
    acts = "\n    ".join(
        f'<intvelocity name="{n}" joint="{j}" kp="{kp}" actrange="-6.5 6.5"/>'
        for n, j, kp in (("x", "x", 2000), ("y", "y", 2000), ("z", "z", 2000), ("a1", "a1", 20), ("a2", "a2", 20),
                         ("a3", "a3", 20), ("a4", "a4", 20), ("a5", "a5", 20), ("jaw1", "hand1_jaw", 2),
                         ("jaw2", "hand2_jaw", 2)))
    return f"""<mujoco model="unit_change">
  <compiler angle="degree"/>
  <option timestep="0.004" gravity="0 0 0" integrator="implicitfast"/>
  <visual><global offwidth="800" offheight="450"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.55 0.55 0.55"/></visual>
  <default><geom contype="0" conaffinity="0" mass="0.02"/></default>
  <worldbody>
    <light pos="1.5 -2 5" dir="-0.2 0.3 -1" diffuse="0.5 0.5 0.5" castshadow="false"/>
    <geom name="floor" type="plane" pos="0.7 -0.3 0" size="3 3 0.1" rgba="0.82 0.82 0.8 1"/>
    <camera name="overview" pos="{ov_pos[0]} {ov_pos[1]} {ov_pos[2]}" xyaxes="{_cam_axes(ov_pos, ov_tgt)}" fovy="45"/>
    {units}
    <body name="cart" pos="{r0[0]:.4f} {r0[1]:.4f} {r0[2]:.4f}">
      <joint name="x" type="slide" axis="1 0 0" damping="60"/>
      <joint name="y" type="slide" axis="0 1 0" damping="60"/>
      <joint name="z" type="slide" axis="0 0 1" damping="60"/>
      <geom type="sphere" size="0.004" mass="0.4" rgba="1 1 1 0"/>
      <camera name="chase" mode="track" pos="{ch_pos[0]} {ch_pos[1]} {ch_pos[2]}" xyaxes="{_cam_axes(ch_pos, (0.07, 0, 0))}" fovy="50"/>
      <body name="r1">{INERT}<joint name="a1" type="hinge" axis="1 0 0" armature="0.01" damping="1"/>
        <body name="r2">{INERT}<joint name="a2" type="hinge" axis="0 1 0" armature="0.01" damping="1"/>
          <body name="r3">{INERT}<joint name="a3" type="hinge" axis="1 0 0" armature="0.01" damping="1"/>
            <body name="r4">{INERT}<joint name="a4" type="hinge" axis="0 1 0" armature="0.01" damping="1"/>
              <body name="r5"><joint name="a5" type="hinge" pos="{SEP} 0 0" axis="0 0 1" armature="0.01" damping="1"/>
                {hands}
                {cart_extra}
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    {acts}
  </actuator>
</mujoco>"""
