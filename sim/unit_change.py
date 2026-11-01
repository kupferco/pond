"""Unit change animation: the cart crosses unit 1 -> unit 2 -> unit 3 (corner unit) and lands on F.

Scripted, not physical: gravity is off, nothing collides, and every motion is driven by stiff
position actuators following a precomputed path (DEFAULT_CONTROLS). Use it to check the
sequence and clearances, not forces. Geometry follows 3-unit layout v2 (render
20261101-104909-328f): 70 cm loops 2 m tall, loop 10 cm in front of the spine, pipes 14 cm
apart at a handover, unit 3 swung clockwise about pipe E.

Pipes (all vertical sides of the loops): A, B = unit 1; C, D = unit 2; E, F = unit 3.
Cart: two hands 14 cm apart on a yellow base plate, arm folded. It always rides on the hand
whose partner hangs OUTSIDE the loop, and the hands swap roles at each crossover.

Sequence (seconds):
  0.0  ride hand 1 up B (unit 1)
  3.0  hand 2 clamps C (unit 2), 4.0 hand 1 releases B   -> now riding hand 2 on unit 2
  5.0  up C, round unit 2's top corners, down D
 12.0  hand 1 clamps E (unit 3), 13.0 hand 2 releases D  -> now riding hand 1 on E
 14.0  up E sideways, round unit 3's top corner (cart still parallel to units 1-2)
 18.0  swivel 90 deg about the top bar into unit 3's plane
 20.0  along unit 3's top bar, round the far corner, down F; hold from 24.4
"""

import math

PARAMS = {
    "dt_s": (0.02, "control sample spacing, s"),
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
SEP = 0.14                 # pipe spacing at a handover = hand spacing
PITCH = LOOP_W + SEP
YL = -LOOP_OFF
X_B, X_C, X_D = LOOP_W / 2, PITCH - LOOP_W / 2, PITCH + LOOP_W / 2
X_E = X_D + SEP
U3 = (X_E + LOOP_OFF, -LOOP_OFF - LOOP_W / 2)
Y_F = YL - LOOP_W
ZC = Z_BOT + LOOP_H / 2
R = LOOP_R
OPEN = 1.6
UNITS = [(0.0, 0.0, 0.0), (PITCH, 0.0, 0.0), (U3[0], U3[1], -90.0)]


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
PHASES = [
    (0.5, lambda u: {}),
    (2.5, lambda u: {"rp": (X_B, YL, lerp(0.90, ZC, u))}),
    (1.0, lambda u: {"j2": lerp(OPEN, 0, u)}),
    (1.0, lambda u: {"j1": lerp(0, OPEN, u), "ride": 2, "rp": (X_C, YL, ZC)}),
    (2.0, lambda u: {"rp": (X_C, YL, lerp(ZC, Z_TOP - R, u))}),
    (1.0, lambda u: {"rp": (X_C + R - R * math.cos(D(90 * u)), YL, Z_TOP - R + R * math.sin(D(90 * u))), "a4": D(90 * u)}),
    (1.0, lambda u: {"rp": (lerp(X_C + R, X_D - R, u), YL, Z_TOP)}),
    (1.0, lambda u: {"rp": (X_D - R + R * math.sin(D(90 * u)), YL, Z_TOP - R + R * math.cos(D(90 * u))), "a4": D(90 + 90 * u)}),
    (2.0, lambda u: {"rp": (X_D, YL, lerp(Z_TOP - R, ZC, u))}),
    (1.0, lambda u: {"j1": lerp(OPEN, 0, u)}),
    (1.0, lambda u: {"j2": lerp(0, OPEN, u), "ride": 1, "rp": (X_E, YL, ZC)}),
    (2.0, lambda u: {"rp": (X_E, YL, lerp(ZC, Z_TOP - R, u))}),
    (1.2, lambda u: {"rp": (X_E, YL - R + R * math.cos(D(90 * u)), Z_TOP - R + R * math.sin(D(90 * u))), "a3": D(90 * u)}),
    (0.8, lambda u: {"rp": (X_E, lerp(YL - R, -0.33, u), Z_TOP)}),
    (2.0, lambda u: {"a2": D(90 * u)}),
    (1.2, lambda u: {"rp": (X_E, lerp(-0.33, Y_F + R, u), Z_TOP)}),
    (1.2, lambda u: {"rp": (X_E, Y_F + R - R * math.sin(D(90 * u)), Z_TOP - R + R * math.cos(D(90 * u))), "a1": D(90 * u)}),
    (2.0, lambda u: {"rp": (X_E, Y_F, lerp(Z_TOP - R, ZC, u))}),
    (1.5, lambda u: {}),
]
DURATION = sum(p[0] for p in PHASES)


def _state(t):
    s = {"rp": (X_B, YL, 0.90), "ride": 1, "a1": 0.0, "a2": 0.0, "a3": 0.0, "a4": 0.0, "j1": 0.0, "j2": OPEN}
    t0 = 0.0
    for dur, fn in PHASES:
        if t >= t0 + dur:
            s.update(fn(1.0))
            t0 += dur
            continue
        s.update(fn(ease((t - t0) / dur)))
        return s
    return s


def _pose(t):
    s = _state(t)
    Rm = _mm(_mm(_rx(s["a1"]), _ry(s["a2"])), _mm(_rx(s["a3"]), _ry(s["a4"])))
    xl = [Rm[i][0] for i in range(3)]
    rp = s["rp"]
    h1 = rp if s["ride"] == 1 else tuple(rp[i] - SEP * xl[i] for i in range(3))
    return h1, s


def _controls(dt):
    names = ["x", "y", "z", "a1", "a2", "a3", "a4", "jaw1", "jaw2"]
    out = {n: [] for n in names}
    n = int(DURATION / dt) + 1
    for i in range(n):
        t = round(i * dt, 4)
        h1, s = _pose(t)
        vals = [h1[0], h1[1], h1[2], s["a1"], s["a2"], s["a3"], s["a4"], -s["j1"], -s["j2"]]
        for k, v in zip(names, vals):
            out[k].append([t, round(v, 5)])
    return out


DEFAULT_CONTROLS = _controls(0.02)


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


def _unit_xml(cx, cy, ang, idx):
    th = math.radians(ang)
    c, s = math.cos(th), math.sin(th)

    def w(lx, ly, lz):
        return (cx + lx * c - ly * s, cy + lx * s + ly * c, lz)

    def ft(p, q):
        return " ".join(f"{v:.4f}" for v in (*p, *q))

    g = []
    pipe = 'rgba="0.72 0.74 0.78 1"'
    W2 = LOOP_W / 2
    # straight runs of the loop
    segs = [((-W2 + R, YL, Z_BOT), (W2 - R, YL, Z_BOT)), ((W2, YL, Z_BOT + R), (W2, YL, Z_TOP - R)),
            ((W2 - R, YL, Z_TOP), (-W2 + R, YL, Z_TOP)), ((-W2, YL, Z_TOP - R), (-W2, YL, Z_BOT + R))]
    for p, q in segs:
        g.append(f'<geom type="capsule" fromto="{ft(w(*p), w(*q))}" size="{PIPE_R}" {pipe}/>')
    # rounded corners
    for (ox, oz, a0) in ((W2 - R, Z_BOT + R, -90), (W2 - R, Z_TOP - R, 0), (-W2 + R, Z_TOP - R, 90), (-W2 + R, Z_BOT + R, 180)):
        pts = [(ox + R * math.cos(math.radians(a0 + 15 * k)), YL, oz + R * math.sin(math.radians(a0 + 15 * k))) for k in range(7)]
        for p, q in zip(pts, pts[1:]):
            g.append(f'<geom type="capsule" fromto="{ft(w(*p), w(*q))}" size="{PIPE_R}" {pipe}/>')
    # tank, spine, plant pipe, brackets, pods
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


def _hand_xml(name, x0, color, jaw_color):
    """One hand in the cart frame: pipe along local z, opening facing +y (spine side)."""
    RR = 0.042
    g = []
    for a in range(110, 341, 23):
        r = math.radians(a)
        g.append(f'<geom type="box" pos="{x0 + RR*math.cos(r):.4f} {RR*math.sin(r):.4f} 0" size="0.004 0.0095 0.02" '
                 f'euler="0 0 {a}" rgba="{color}"/>')
    for a in (270, 150):
        r = math.radians(a)
        for z in (-0.012, 0.012):
            g.append(f'<geom type="sphere" pos="{x0 + 0.024*math.cos(r):.4f} {0.024*math.sin(r):.4f} {z}" size="0.008" rgba="0.1 0.1 0.1 1"/>')
    hx, hy = RR * math.cos(math.radians(346)), RR * math.sin(math.radians(346))
    jaw = []
    for a in range(352, 431, 13):
        r = math.radians(a)
        jaw.append(f'<geom type="box" pos="{RR*math.cos(r) - hx:.4f} {RR*math.sin(r) - hy:.4f} 0" size="0.004 0.0075 0.02" '
                   f'euler="0 0 {a}" rgba="{jaw_color}"/>')
    r = math.radians(30)
    for z in (-0.012, 0.012):
        jaw.append(f'<geom type="sphere" pos="{0.024*math.cos(r) - hx:.4f} {0.024*math.sin(r) - hy:.4f} {z}" size="0.008" rgba="0.1 0.1 0.1 1"/>')
    jaw.append('<geom type="box" pos="0.012 -0.02 0.034" size="0.012 0.02 0.016" rgba="0.15 0.15 0.15 1"/>')
    return ("\n".join(g) +
            f'\n<body name="{name}_jaw" pos="{x0 + hx:.4f} {hy:.4f} 0">'
            f'<joint name="{name}_jaw" type="hinge" axis="0 0 1" range="-1.8 0.1" armature="0.001" damping="0.09"/>'
            + "\n".join(jaw) + "</body>")


def build(**p) -> str:
    units = "\n    ".join(_unit_xml(cx, cy, ang, i) for i, (cx, cy, ang) in enumerate(UNITS))
    ov_pos, ov_tgt = (3.1, -3.6, 3.0), (0.75, -0.35, 1.45)
    ch_pos = (0.75, -0.95, 0.35)
    hands = _hand_xml("hand1", 0.0, "0.2 0.45 0.85 1", "0.55 0.3 0.85 1") + "\n" + \
            _hand_xml("hand2", SEP, "0.2 0.45 0.85 1", "0.55 0.3 0.85 1")
    cart_extra = f"""
          <geom type="box" pos="{SEP/2} -0.057 0" size="{SEP/2 + 0.02} 0.005 0.04" rgba="1 0.85 0.3 1"/>
          <geom type="cylinder" fromto="0 -0.062 -0.04 0 -0.062 0.04" size="0.016" rgba="0.2 0.7 0.4 1"/>
          <geom type="cylinder" fromto="{SEP} -0.062 -0.04 {SEP} -0.062 0.04" size="0.016" rgba="0.2 0.7 0.4 1"/>
          <geom type="cylinder" fromto="{SEP/2} -0.062 0 {SEP/2} -0.085 0" size="0.026" rgba="0.95 0.4 0.1 1"/>
          <geom type="capsule" fromto="{SEP/2} -0.085 0 {SEP/2} -0.10 0.06" size="0.012" rgba="0.95 0.4 0.1 1"/>
          <geom type="capsule" fromto="{SEP/2} -0.10 0.06 {SEP/2} -0.115 0.22" size="0.012" rgba="0.95 0.4 0.1 1"/>
          <geom type="capsule" fromto="{SEP/2} -0.115 0.22 {SEP/2} -0.125 0.06" size="0.012" rgba="0.95 0.4 0.1 1"/>
          <geom type="box" pos="{SEP/2} -0.125 0.05" size="0.015 0.015 0.015" rgba="0.95 0.4 0.1 1"/>"""
    h0, _ = _pose(0.0)
    return f"""<mujoco model="unit_change">
  <compiler angle="degree"/>
  <option timestep="0.002" gravity="0 0 0" integrator="implicitfast"/>
  <visual><global offwidth="1280" offheight="720"/><quality shadowsize="4096"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.55 0.55 0.55"/></visual>
  <default><geom contype="0" conaffinity="0" mass="0.02"/></default>
  <worldbody>
    <light pos="1.5 -2 5" dir="-0.2 0.3 -1" diffuse="0.5 0.5 0.5"/>
    <geom name="floor" type="plane" pos="0.7 -0.3 0" size="3 3 0.1" rgba="0.82 0.82 0.8 1"/>
    <camera name="overview" pos="{ov_pos[0]} {ov_pos[1]} {ov_pos[2]}" xyaxes="{_cam_axes(ov_pos, ov_tgt)}" fovy="45"/>
    {units}
    <body name="cart" pos="0 0 0">
      <joint name="x" type="slide" axis="1 0 0" damping="60" ref="0"/>
      <joint name="y" type="slide" axis="0 1 0" damping="60"/>
      <joint name="z" type="slide" axis="0 0 1" damping="60"/>
      <geom type="sphere" size="0.004" mass="0.4" rgba="1 1 1 0"/>
      <camera name="chase" mode="track" pos="{ch_pos[0]} {ch_pos[1]} {ch_pos[2]}" xyaxes="{_cam_axes(ch_pos, (0.07, 0, 0))}" fovy="50"/>
      <body name="r1"><joint name="a1" type="hinge" axis="1 0 0" armature="0.01" damping="1"/>
        <body name="r2"><joint name="a2" type="hinge" axis="0 1 0" armature="0.01" damping="1"/>
          <body name="r3"><joint name="a3" type="hinge" axis="1 0 0" armature="0.01" damping="1"/>
            <body name="r4"><joint name="a4" type="hinge" axis="0 1 0" armature="0.01" damping="1"/>
              {hands}
              {cart_extra}
            </body>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="x" joint="x" kp="2000"/>
    <position name="y" joint="y" kp="2000"/>
    <position name="z" joint="z" kp="2000"/>
    <position name="a1" joint="a1" kp="20"/>
    <position name="a2" joint="a2" kp="20"/>
    <position name="a3" joint="a3" kp="20"/>
    <position name="a4" joint="a4" kp="20"/>
    <position name="jaw1" joint="hand1_jaw" kp="2"/>
    <position name="jaw2" joint="hand2_jaw" kp="2"/>
  </actuator>
  <keyframe><key name="start" qpos="{h0[0]:.4f} {h0[1]:.4f} {h0[2]:.4f} 0 0 0 0 0 {-OPEN}"/></keyframe>
</mujoco>"""
