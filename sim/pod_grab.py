"""Pod grab reach and collision model: the real SO-101 arm on the upright Pond cart, picking every seedling tray cell and every dry pod store landing.
OpenPocket #531 (owner decision 26 Nov 2026). The layout numbers are NOT in this file: they are read from cad/pod_layout.py, the same file the CAD
(cad/parts/shelf_items.py, cad/parts/tank.py, cad/pond_full_unit.py) reads, so the sim and the drawings cannot drift apart (cad/check_pod_layout.py enforces it).

World = the CAD frame, mm in the code and metres in the XML: X along the bottom track run, Y front(-)/back(+), Z up, tank floor z = 0, growing pipe at x = y = 0.
The cart is UPRIGHT on the track (no roll): a 160 x 146 plate hangs below the track pipe, front face 56 mm out of the pipe axis, the arm base bolted straight on it
(cad/cart_dims.py v4, battery stood on its edge beside the arm, above it). The arm's base axis points out of the plate (-Y) and its pan zero points DOWN, so the pan
swings the arm like a clock hand in the plane of the plate: the claw tilts sideways by about the pan angle on the outer columns.

THE ARM IS THE REAL SO-101. All numbers come from the official SO-101 URDF (TheRobotStudio/SO-ARM100, Simulation/SO101/so101_new_calib.urdf): link offsets, joint limits and link
masses. In the plane of the arm (x out along the arm at zero pose, z up the base axis; base origin on the mounting face):
  pan axis x 38.8, shoulder_lift axis (69.2, 116.6), elbow (97.2, 229.2), wrist_flex (232.1, 234.4), grip point (391.4, 226.5)
  upper arm 116 mm, forearm 135 mm, wrist_flex axis to grip point 159.5 mm. Joint limits (deg): pan +-110, shoulder_lift +-100, elbow +-96.8, wrist_flex +-95, wrist_roll free.
Servos are position servos limited to the STS3215 stall torque (`stall_nm`: 1.9 N m at 7.4 V, about 2.9 N m at 12 V). The pod and its lettuce are a `load_kg` mass at the grip point.

The scene is built from the CAD numbers: the lid is a real plate with the pick slots cut out (so a claw that does not fit a slot HITS the lid), the tray cells, the store lanes
(sloping SLOPE_DEG, flat landing, stop lip, rails), every pod (16 in the tray, 7 x 4 in the store), the growing pipe, the water station, the track pipe and the cart.

Run it: run_sim(model="pod_grab", duration_s=60, record=True) plays the tour (tray A1, C6, then the cart slides to the store: S1, S7).
sim/pod_grab_check.py imports this file and writes the reach / collision table for EVERY tray cell and EVERY store landing (docs/pod-grab/results.json, docs/pod-grab.md).
"""
import importlib.util
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pod_layout", os.path.join(_HERE, "..", "cad", "pod_layout.py"))
PL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PL)

PARAMS = {
    "slope_deg": (PL.SLOPE_DEG, "store lane slope towards the front, degrees (the CAD parameter cad/pod_layout.py SLOPE_DEG; the 15 is a guess pending a real-pot ramp test)"),
    "stall_nm": (1.9, "servo stall torque, N m (STS3215 7.4 V 1.9; 12 V about 2.9)"),
    "load_kg": (0.42, "pod 20 g + lettuce 400 g at the grip point, kg"),
    "kp": (150.0, "servo position gain, N m / rad"),
    "pod_contact": (0, "1: pods are solid to the claw in the played tour; 0: the claw passes through them (it closes round the pod in real life). The check script always counts the other pods"),
    "hover_mm": (50.0, "how far above the grip height the arm hovers between picks"),
    "timestep_s": (0.002, "integrator step"),
    "tour": ("tray", "tray = A1, C6 at the tray park (-130); store = S1, S7 at the store park (+135)"),
    "tilt_tol_deg": (3.0, "the claw counts as vertical within this many degrees"),
    "max_tilt_deg": (45.0, "largest sideways claw tilt the pose search accepts"),
}
TRACK_BODY = "cart"
CAMERAS = ["front", "side", "iso", "top"]
DEFAULT_CONTROLS = {}

# ---------------- the layout (mm), CAD frame: all from cad/pod_layout.py ----------------
PIPE_Y, PIPE_Z, PIPE_R = PL.TRACK_Y, PL.TRACK_Z, PL.TRACK_R
LID_TOP, LID_T = PL.LID_TOP, PL.LID_T
PARK_TRAY, PARK_STORE = PL.PARK_TRAY, PL.PARK_STORE
ROW_NAMES = PL.ROW_NAMES
PILLAR_R = PL.PILLAR_R
STATION = PL.STATION
PLATE_T, PLATE_ALONG, PLATE_DOWN = PL.PLATE_T, PL.PLATE_ALONG, PL.PLATE_DOWN
PLATE_CZ_REL = PL.PLATE_CZ_REL
FACE_REL = PL.PLATE_Y0
BATT = PL.BATT
SAFE = (-1.2, 1.25, 0.49)                       # travel pose (shoulder_lift, elbow_flex, wrist_flex), radians
CELLS_TRAY = list(PL.tray_cells())
CELLS_STORE = list(PL.store_cells())

# ---------------- the real SO-101, planar (x out, z up the base axis), metres ----------------
PAN_X = 0.0388
S0 = (0.0692, 0.1166)     # shoulder_lift axis
U1 = (0.0280, 0.1126)     # to the elbow
U2 = (0.1349, 0.0052)     # to wrist_flex
U3 = (0.1593, -0.0079)    # to the grip point (gripper_frame_link)
PLANE_Y = -0.0183         # the links' offset beside the pan plane
LIMITS = {                # URDF so101_new_calib.urdf
    "shoulder_pan": (-1.91986, 1.91986),
    "shoulder_lift": (-1.74533, 1.74533),
    "elbow_flex": (-1.69, 1.69),
    "wrist_flex": (-1.65806, 1.65806),
    "wrist_roll": (-2.74385, 2.84121),
}
MASSES = {"shoulder": 0.100006, "upper": 0.103, "lower": 0.104, "wrist": 0.079, "gripper": 0.0991, "base": 0.147}
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]


def rot(v, q):
    """Rotate (x, z) by joint angle q about +y (positive tips the arm forward, towards +x)."""
    c, s = math.cos(q), math.sin(q)
    return (v[0] * c + v[1] * s, -v[0] * s + v[1] * c)


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def fk(q1, q2, q3):
    """Elbow, wrist and grip point in the arm plane (base frame, metres)."""
    e = _add(S0, rot(U1, q1))
    w = _add(e, rot(U2, q1 + q2))
    t = _add(w, rot(U3, q1 + q2 + q3))
    return e, w, t


def _ang(v):
    return math.atan2(v[0], v[1])


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def ik_all(tx, tz, phi):
    """All elbow solutions (q1, q2, q3) that put the grip point at (tx, tz) with the tool at angle phi, limits ignored
    except the elbow scan range. phi = q1 + q2 + q3; 0 = tool straight along +x (straight down once mounted)."""
    t3 = rot(U3, phi)
    w = (tx - t3[0], tz - t3[1])
    d = math.hypot(w[0] - S0[0], w[1] - S0[1])
    lo, hi = LIMITS["elbow_flex"]
    out = []

    def f(q2):
        r = _add(U1, rot(U2, q2))
        return math.hypot(r[0], r[1]) - d

    n = 400
    prev_q, prev_f = lo, f(lo)
    for i in range(1, n + 1):
        q = lo + (hi - lo) * i / n
        fv = f(q)
        if prev_f == 0.0 or prev_f * fv < 0:
            a, b, fa = prev_q, q, prev_f
            for _ in range(50):
                m = 0.5 * (a + b)
                fm = f(m)
                if fa * fm <= 0:
                    b = m
                else:
                    a, fa = m, fm
            q2 = 0.5 * (a + b)
            v = _add(U1, rot(U2, q2))
            q1 = _wrap(_ang((w[0] - S0[0], w[1] - S0[1])) - _ang(v))
            out.append((q1, q2, _wrap(phi - q1 - q2)))
        prev_q, prev_f = q, fv
    return out


def joint_margin(q):
    """Smallest distance to a joint limit over (q1, q2, q3), radians (negative = outside)."""
    names = ("shoulder_lift", "elbow_flex", "wrist_flex")
    return min(min(v - LIMITS[n][0], LIMITS[n][1] - v) for n, v in zip(names, q))


def ik(tx, tz, phi):
    """Best in-limit solution (largest joint margin) or None."""
    best = None
    for q in ik_all(tx, tz, phi):
        m = joint_margin(q)
        if m >= 0 and (best is None or m > best[1]):
            best = (q, m)
    return best



def _smooth(a):
    return 0.5 - 0.5 * math.cos(math.pi * a)



def _f(v):
    return f"{v:.5f}"


def _m(*a):
    return " ".join(_f(x / 1000.0) for x in a)


def arm_xml(load_kg):
    """The real SO-101 as a MJCF <body name="arm_base"> in its own base frame (zero pose), metres. Shared by every layout."""
    arm = 'contype="1" conaffinity="2"'          # the arm's own geoms
    nog = 'contype="0" conaffinity="0"'
    # ---- arm: global zero-pose positions in the arm base frame, bodies are relative
    P_pan = (PAN_X, 0.0, 0.0624)
    P_sl = (S0[0], PLANE_Y, S0[1])
    P_el = (S0[0] + U1[0], PLANE_Y, S0[1] + U1[1])
    P_wr = (P_el[0] + U2[0], PLANE_Y, P_el[2] + U2[1])
    P_roll = (P_wr[0] + 0.0611, -0.0002, P_wr[2])
    P_tcp = (P_wr[0] + U3[0], 0.0, P_wr[2] + U3[1])

    def rel(a, b):
        return " ".join(_f(a[i] - b[i]) for i in range(3))

    def com(c, o):
        return " ".join(_f(c[i] - o[i]) for i in range(3))

    def inert(mass):
        return f"{mass:.5f}"

    limr = {n: f'range="{_f(LIMITS[n][0])} {_f(LIMITS[n][1])}" limited="true"' for n in LIMITS}
    elbow_rel = (U1[0], 0.0, U1[1])
    wrist_rel = (U2[0], 0.0, U2[1])
    xml_arm = f"""
        <body name="arm_base" pos="{_m(0, 0, 0)}">
          <geom name="arm_base_foot" type="box" pos="0.0137 0 0.0335" size="0.045 0.035 0.0335" {nog} mass="{MASSES['base']}" rgba="0.15 0.15 0.15 1"/>
          <body name="shoulder_link" pos="{_f(P_pan[0])} {_f(P_pan[1])} {_f(P_pan[2])}">
            <joint name="shoulder_pan" type="hinge" axis="0 0 1" {limr['shoulder_pan']} damping="0.3" armature="0.02"/>
            <inertial pos="{com((0.0696, 0, 0.0877), P_pan)}" mass="{inert(MASSES['shoulder'])}" diaginertia="2e-5 2e-5 2e-5"/>
            <geom name="shoulder_housing" type="box" pos="{com((0.0696, -0.009, 0.0877), P_pan)}" size="0.026 0.033 0.034" {arm} rgba="0.95 0.95 0.95 1"/>
            <body name="upper_arm_link" pos="{rel(P_sl, P_pan)}">
              <joint name="shoulder_lift" type="hinge" axis="0 1 0" {limr['shoulder_lift']} damping="0.3" armature="0.02"/>
              <inertial pos="{com((0.0776, 0.0001, 0.2064), P_sl)}" mass="{inert(MASSES['upper'])}" diaginertia="2e-5 2e-5 2e-5"/>
              <geom name="upper_arm" type="capsule" fromto="0 0 0 {_f(elbow_rel[0])} 0 {_f(elbow_rel[2])}" size="0.02" {arm} rgba="0.95 0.95 0.95 1"/>
              <body name="lower_arm_link" pos="{_f(elbow_rel[0])} 0 {_f(elbow_rel[2])}">
                <joint name="elbow_flex" type="hinge" axis="0 1 0" {limr['elbow_flex']} damping="0.3" armature="0.02"/>
                <inertial pos="{com((0.1953, 0.0, 0.2324), P_el)}" mass="{inert(MASSES['lower'])}" diaginertia="2e-5 2e-5 2e-5"/>
                <geom name="forearm" type="capsule" fromto="0 0 0 {_f(wrist_rel[0])} 0 {_f(wrist_rel[2])}" size="0.02" {arm} rgba="0.95 0.95 0.95 1"/>
                <body name="wrist_link" pos="{_f(wrist_rel[0])} 0 {_f(wrist_rel[2])}">
                  <joint name="wrist_flex" type="hinge" axis="0 1 0" {limr['wrist_flex']} damping="0.2" armature="0.01"/>
                  <inertial pos="{com((0.2707, 0.0098, 0.2345), P_wr)}" mass="{inert(MASSES['wrist'])}" diaginertia="1e-5 1e-5 1e-5"/>
                  <geom name="wrist_housing" type="box" pos="0.03 0.012 0" size="0.035 0.02 0.025" {arm} rgba="0.95 0.95 0.95 1"/>
                  <body name="gripper_link" pos="{rel(P_roll, P_wr)}">
                    <joint name="wrist_roll" type="hinge" axis="-1 0 0" {limr['wrist_roll']} damping="0.2" armature="0.01"/>
                    <inertial pos="{com((0.3185, 0.0001, 0.2346), P_roll)}" mass="{inert(MASSES['gripper'])}" diaginertia="1e-5 1e-5 1e-5"/>
                    <geom name="gripper_body" type="box" pos="0.0275 0 0" size="0.0375 0.022 0.016" {arm} rgba="0.2 0.5 0.9 1"/>
                    <geom name="gripper_tip" type="box" pos="0.0825 0 0" size="0.0175 0.012 0.010" {arm} rgba="0.2 0.5 0.9 1"/>
                    <body name="tcp" pos="{rel(P_tcp, P_roll)}">
                      <site name="tcp" size="0.005" rgba="1 0 0 1"/>
                      <geom name="load" type="sphere" size="0.012" {nog} mass="{float(load_kg):.4f}" rgba="0.3 0.8 0.3 0.8"/>
                    </body>
                  </body>
                </body>
              </body>
            </body>
          </body>
        </body>"""
    return xml_arm



# ======================================================================================================================
# The upright layout: frames, targets and the pose search
# ======================================================================================================================
LIMIT_NAMES = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex")
ARM_GEOMS = ("shoulder_housing", "upper_arm", "forearm", "wrist_housing", "gripper_body", "gripper_tip")
CLAW = ("gripper_body", "gripper_tip", "wrist_housing")     # these go down through the pick slot in the lid
CLEAR_MIN_MM = 1.0                                          # a pose counts as collision-free with at least this much air


def _np():
    import numpy as np
    return np


def cell_target(name):
    """(x, y, grip z, park x) of a grip point, mm. Tray cell 'B3' (row B, column 3) or store landing 'S2'."""
    cells = PL.store_cells() if name[0] == "S" else PL.tray_cells()
    return cells[name]


def base_frame(cart_x):
    """(origin mm, 3 x 3 world<-base rotation) of the arm base: cart at x = cart_x, upright. Base x = down, base y = +X, base z = out of the plate (-Y).
    The base sits straight on the plate, ARM_X from its centre (cad/cart_dims.py v4)."""
    np = _np()
    rb = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], dtype=float)
    b = np.array([-PL.ARM_Z, FACE_REL, PLATE_CZ_REL + PL.ARM_X + PAN_X * 1000.0])
    return np.array([cart_x, PIPE_Y, PIPE_Z]) + b, rb


def to_plane(R, origin, target):
    """World grip point (mm) -> (pan angle, planar x, planar z in metres) in the arm's own plane."""
    np = _np()
    pb = R.T @ (np.array(target, dtype=float) - origin) / 1000.0
    dx, dy = pb[0] - PAN_X, pb[1]
    return math.atan2(dy, dx), PAN_X + math.hypot(dx, dy), float(pb[2])


def plane_to_world(R, origin, pan, px, pz):
    """Arm-plane point (planar x, z in metres) at this pan -> world mm."""
    np = _np()
    r = px - PAN_X
    return origin + R @ (np.array([PAN_X + r * math.cos(pan), r * math.sin(pan), pz]) * 1000.0)


def chain_world(cart_x, pose):
    """World mm of the arm joints for a pose (pan, q1, q2, q3): shoulder_lift axis, elbow, wrist_flex axis, grip point. The CAD arm is drawn from these."""
    origin, R = base_frame(cart_x)
    pan, q1, q2, q3 = pose
    e, w, t = fk(q1, q2, q3)
    pts = [S0, e, w, t]
    return [plane_to_world(R, origin, pan, p[0], p[1]) for p in pts], origin, R


def tool_tilt(R, pan, phi):
    """Angle between the claw axis and straight down, degrees (phi = shoulder_lift + elbow_flex + wrist_flex)."""
    np = _np()
    t = R @ np.array([math.cos(phi) * math.cos(pan), math.cos(phi) * math.sin(pan), -math.sin(phi)])
    return math.degrees(math.acos(max(-1.0, min(1.0, -float(t[2])))))


def candidates(R, pan, tx, tz, cap):
    """Every in-limit arm pose that puts the grip point at (tx, tz) with the claw within `cap` degrees of vertical: [(tilt, margin rad, phi, (q1, q2, q3))]."""
    out = []
    if abs(pan) > LIMITS["shoulder_pan"][1]:
        return out
    for d in range(-150, 151):
        phi = math.radians(d)
        tilt = tool_tilt(R, pan, phi)
        if tilt > cap:
            continue
        r = ik(tx, tz, phi)
        if r:
            out.append((tilt, min(r[1], LIMITS["shoulder_pan"][1] - abs(pan)), phi, r[0]))
    return out


def candidates_for(cart_x, target, cap):
    origin, R = base_frame(cart_x)
    pan, tx, tz = to_plane(R, origin, target)
    return pan, candidates(R, pan, tx, tz, cap)


def reach_mm(cart_x, target):
    """(distance from the shoulder_lift axis to the wrist_flex axis for the vertical claw, limit L1 + L2 along the real links): the 'N / 251' of the brief."""
    origin, R = base_frame(cart_x)
    pan, tx, tz = to_plane(R, origin, target)
    w = (tx, tz + U3[1] * 0 + 0.0)
    return pan, tx, tz


# ---------------- the scene ----------------
def lid_pieces():
    """The lid as solid boxes (x0, x1, y0, y1) with every pick slot cut out: raster on the slot edges, runs along x merged."""
    rects = list(PL.slot_rects().values())
    xs = sorted({-350.0, 350.0} | {c for r in rects for c in r[:2] if -350 < c < 350})
    ys = sorted({-200.0, 200.0} | {c for r in rects for c in r[2:] if -200 < c < 200})
    out = []
    for j in range(len(ys) - 1):
        y0, y1 = ys[j], ys[j + 1]
        run = None
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            slot = any(r[0] < cx < r[1] and r[2] < cy < r[3] for r in rects)
            if slot:
                if run:
                    out.append((run[0], run[1], y0, y1))
                    run = None
            else:
                run = (run[0], x1) if run else (x0, x1)
        if run:
            out.append((run[0], run[1], y0, y1))
    return out


def build(**p) -> str:
    p = {**{k: v[0] for k, v in PARAMS.items()}, **p}
    stall, kp = float(p["stall_nm"]), float(p["kp"])
    th = math.radians(float(p["slope_deg"]))
    if not p.get("_scene_only"):                  # the pose search builds the bare scene (no tour): the tour itself needs the pose search
        ctrl, total = make_controls(p)
        DEFAULT_CONTROLS.clear()
        DEFAULT_CONTROLS.update(ctrl)
    env = 'contype="2" conaffinity="1"'
    nog = 'contype="0" conaffinity="0"'
    podc = env if int(p["pod_contact"]) else nog
    pod_r, pod_hh = PL.POD_D / 2, PL.POD_H / 2

    def box(name, x0, x1, y0, y1, z0, z1, rgba, extra=""):
        return (f'<geom name="{name}" type="box" pos="{_m((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)}" size="{_m((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)}" '
                f'{env} rgba="{rgba}" {extra}/>')

    sc = [f'<geom name="track_pipe" type="cylinder" pos="0 {_f(PIPE_Y / 1000)} {_f(PIPE_Z / 1000)}" euler="0 1.5708 0" size="{_f(PIPE_R / 1000)} 0.30" {env} rgba="0.7 0.7 0.72 1"/>']
    for k, (x0, x1, y0, y1) in enumerate(lid_pieces()):
        sc.append(box(f"lid_{k}", x0, x1, y0, y1, LID_TOP - LID_T, LID_TOP, "0.6 0.7 0.8 0.35"))
    for tag, (x0_, x1_, y0_, y1_) in {"front": (-350, 350, -200, -196), "back": (-350, 350, 196, 200), "left": (-350, -346, -196, 196), "right": (346, 350, -196, 196)}.items():
        sc.append(box(f"lid_wall_{tag}", x0_, x1_, y0_, y1_, 0.0, LID_TOP - LID_T, "0.75 0.75 0.8 0.3"))      # the tank walls (4 mm), part of the "lid" group for the clearance check
    sc.append(box("shelf", -346, 346, -196, 196, PL.SHELF_TOP - PL.SHELF_T, PL.SHELF_TOP, "0.5 0.5 0.55 0.5"))
    # tray: base plate and a 35 x 34 x 24 block per cell (the round pocket is not modelled: the pod stands in it)
    c0, c1 = PL.tray_cell_x(PL.TRAY_COLS - 1) - PL.CELL_X / 2, PL.tray_cell_x(0) + PL.CELL_X / 2
    sc.append(box("tray", c0, c1, PL.TRAY_ROWS_Y[0] - PL.CELL_Y / 2, PL.TRAY_ROWS_Y[-1] + PL.CELL_Y / 2, PL.SHELF_TOP, PL.POD_BOTTOM_TRAY, "0.59 0.43 0.27 1"))
    for name, (x, y, _, _) in PL.tray_cells().items():
        sc.append(box(f"cell_{name}", x - PL.CELL_X / 2, x + PL.CELL_X / 2, y - PL.CELL_Y / 2, y + PL.CELL_Y / 2, PL.POD_BOTTOM_TRAY, PL.POD_BOTTOM_TRAY + PL.CELL_H, "0.59 0.43 0.27 1"))
        sc.append(f'<geom name="pod_{name}" type="cylinder" pos="{_m(x, y, PL.POD_BOTTOM_TRAY + PL.POD_H / 2)}" size="{_f(pod_r / 1000)} {_f(pod_hh / 1000)}" {podc} rgba="0.95 0.6 0.2 1"/>')
        sc.append(f'<geom name="lettuce_{name}" type="sphere" pos="{_m(x, y, PL.POD_BOTTOM_TRAY + PL.POD_H + 22)}" size="0.02" {nog} rgba="0.3 0.8 0.3 0.5"/>')
    # store: base, landing, lip, a plate on the ramp, rails, pods
    x0, x1 = PL.lane_x(0) - PL.LANE_PITCH / 2, PL.lane_x(PL.LANES - 1) + PL.LANE_PITCH / 2
    sc.append(box("store_base", x0, x1, PL.LAND_Y[0] - PL.LIP_T, PL.RAMP_Y1, PL.SHELF_TOP, PL.ZL, "0.35 0.5 0.75 1"))
    sc.append(box("store_lip", x0, x1, PL.LAND_Y[0] - PL.LIP_T, PL.LAND_Y[0], PL.ZL, PL.ZL + PL.LIP_H, "0.35 0.5 0.75 1"))
    ramp_len = (PL.RAMP_Y1 - PL.LAND_Y[1]) / math.cos(th)
    n = (0.0, -math.sin(th), math.cos(th))                                 # ramp normal (tilts towards the front)
    mid = (0.0, (PL.LAND_Y[1] + PL.RAMP_Y1) / 2, PL.ZL + (PL.RAMP_Y1 - PL.LAND_Y[1]) / 2 * math.tan(th))
    sc.append(f'<geom name="store_ramp" type="box" pos="{_m((x0 + x1) / 2, mid[1] - 1.5 * n[1], mid[2] - 1.5 * n[2])}" size="{_m((x1 - x0) / 2, ramp_len / 2, 1.5)}" euler="{_f(th)} 0 0" {env} rgba="0.35 0.5 0.75 1"/>')
    for i in range(PL.LANES + 1):
        xr = x0 + i * PL.LANE_PITCH
        sc.append(box(f"rail_land_{i}", xr - PL.RAIL_T / 2, xr + PL.RAIL_T / 2, PL.LAND_Y[0], PL.LAND_Y[1], PL.ZL, PL.ZL + PL.RAIL_H, "0.45 0.6 0.85 1"))
        sc.append(f'<geom name="rail_ramp_{i}" type="box" pos="{_m(xr, mid[1] + n[1] * PL.RAIL_H / 2, mid[2] + n[2] * PL.RAIL_H / 2)}" size="{_m(PL.RAIL_T / 2, ramp_len / 2, PL.RAIL_H / 2)}" euler="{_f(th)} 0 0" {env} rgba="0.45 0.6 0.85 1"/>')
    for i in range(PL.LANES):
        x = PL.lane_x(i)
        sc.append(f'<geom name="pod_S{i + 1}" type="cylinder" pos="{_m(x, PL.LAND_CY, PL.ZL + PL.POD_H / 2)}" size="{_f(pod_r / 1000)} {_f(pod_hh / 1000)}" {podc} rgba="0.95 0.6 0.2 1"/>')
        for k in range(1, PL.LANE_PODS):
            yc = PL.LAND_Y[1] + pod_r + 2 + (k - 1) * PL.POD_PITCH_ON_RAMP
            zf = PL.ZL + (yc - PL.LAND_Y[1]) * math.tan(th)
            sc.append(f'<geom name="store_pod_{i + 1}_{k}" type="cylinder" pos="{_m(x, yc + n[1] * PL.POD_H / 2, zf + n[2] * PL.POD_H / 2)}" size="{_f(pod_r / 1000)} {_f(pod_hh / 1000)}" euler="{_f(th)} 0 0" {podc} rgba="0.95 0.6 0.2 1"/>')
    st = STATION
    sc.append(box("station_box", st["x0"], st["x1"], st["y0"], st["y1"], st["z0"], st["z1"], "0.82 0.82 0.78 1"))
    for lx in (st["x0"] + 10, st["x1"] - 30):
        for ly in (st["y0"] + 8, st["y1"] - 28):
            sc.append(box(f"station_leg_{int(lx)}_{int(ly)}", lx, lx + 20, ly, ly + 20, LID_TOP, st["z0"], "0.7 0.7 0.7 1"))
    sc.append(f'<geom name="pillar" type="cylinder" pos="{_m(0, 0, LID_TOP + 300)}" size="{_f(PILLAR_R / 1000)} 0.3" {env} rgba="0.93 0.93 0.95 1"/>')
    sc.append('<geom name="floor" type="plane" size="1.5 1 0.1" pos="0 0 0" rgba="0.3 0.32 0.35 1"/>')

    # the cart: upright, coordinates relative to the pipe axis. Hand C rides the track; hand B (the free one) hangs 120 mm below it; the deepest part is 165 mm under the axis (cad/layout.json)
    cart = f"""
        <geom name="sleeve" type="cylinder" pos="0 0 0" euler="0 1.5708 0" size="0.045 0.062" {nog} mass="0.9" rgba="0.5 0.5 0.55 1"/>
        <geom name="sleeve_b" type="cylinder" pos="{_m(0, 0, -120)}" euler="0 1.5708 0" size="0.045 0.062" {nog} mass="0.9" rgba="0.5 0.5 0.55 1"/>
        <geom name="hand_arm" type="box" pos="{_m(0, FACE_REL / 2, -60)}" size="{_m(30, -FACE_REL / 2 - 4, 40)}" {nog} mass="0.2" rgba="0.5 0.5 0.55 1"/>
        <geom name="plate" type="box" pos="{_m(0, FACE_REL + PLATE_T / 2, PLATE_CZ_REL)}" size="{_m(PLATE_ALONG / 2, PLATE_T / 2, PLATE_DOWN / 2)}" {env} mass="0.3" rgba="0.8 0.8 0.85 1"/>
        <geom name="battery" type="box" pos="{_m(0, FACE_REL - BATT[1] / 2, PLATE_CZ_REL + PL.BATT_X)}" size="{_m(BATT[2] / 2, BATT[1] / 2, BATT[0] / 2)}" {env} mass="0.35" rgba="0.2 0.25 0.6 1"/>"""
    base_pos = _m(-PL.ARM_Z, FACE_REL, PLATE_CZ_REL + PL.ARM_X + PAN_X * 1000.0)
    arm_in_cart = arm_xml(p["load_kg"]).replace(f'<body name="arm_base" pos="{_m(0, 0, 0)}">', f'<body name="arm_base" pos="{base_pos}" xyaxes="0 0 -1 1 0 0">', 1)

    def cam(name, pos, xy):
        return f'<camera name="{name}" pos="{pos}" xyaxes="{xy}" fovy="40"/>'
    cams = "\n        ".join([cam("front", _m(0, -900 - PIPE_Y, -150), "1 0 0 0 0 1"), cam("side", _m(800, -150 - PIPE_Y, -150), "0 1 0 0 0 1"),
                              cam("iso", _m(600, -700 - PIPE_Y, 50), "0.76 0.65 0 -0.23 0.27 0.93"), cam("top", _m(0, -150 - PIPE_Y, 500), "1 0 0 0 1 0")])
    rng = (PARK_STORE - PARK_TRAY) / 1000.0
    names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
    acts = "".join(f'<position name="{k}_servo" joint="{k}" kp="{kp}" kv="2.0" forcerange="-{stall} {stall}" forcelimited="true" '
                   f'ctrlrange="{_f(LIMITS[k][0])} {_f(LIMITS[k][1])}" ctrllimited="true"/>' for k in names)
    acts += f'<position name="cart_servo" joint="cart_x" kp="3000" kv="300" forcerange="-60 60" forcelimited="true" ctrlrange="-0.05 {_f(rng + 0.05)}" ctrllimited="true"/>'
    return f"""<mujoco model="pod_grab">
  <compiler angle="radian"/>
  <option timestep="{float(p['timestep_s'])}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <visual><global offwidth="1280" offheight="720"/><headlight ambient="0.45 0.45 0.45" diffuse="0.6 0.6 0.6"/></visual>
  <worldbody>
    <light pos="0 -0.8 1.6" dir="0 0.4 -1"/>
    {chr(10).join(sc)}
    <body name="cart" pos="{_m(PARK_TRAY, PIPE_Y, PIPE_Z)}">
      <joint name="cart_x" type="slide" axis="1 0 0" range="-0.05 {_f(rng + 0.05)}" damping="5"/>
      <inertial pos="0 {_f(FACE_REL / 2000)} {_f(PLATE_CZ_REL / 1000)}" mass="0.5" diaginertia="0.01 0.01 0.01"/>
      {cams}{cart}
      {arm_in_cart}
    </body>
  </worldbody>
  <actuator>{acts}</actuator>
  <sensor><framepos name="tcp_pos" objtype="site" objname="tcp"/></sensor>
</mujoco>"""


# ---------------- collision-aware pose choice ----------------
_MODELS = {}


def model_for(**p):
    import mujoco
    key = tuple(sorted(p.items()))
    if key not in _MODELS:
        _MODELS[key] = mujoco.MjModel.from_xml_string(build(_scene_only=True, **p))
    return _MODELS[key]


def groups(model):
    """Geom ids: arm, cart, and the environment split by what it is."""
    g = {k: [] for k in ("arm", "plate", "battery", "cart", "pillar", "station", "lid", "tank", "pipe", "tray", "store", "pods")}
    for i in range(model.ngeom):
        n = model.geom(i).name
        if n in ARM_GEOMS:
            g["arm"].append(i)
        elif n == "plate":
            g["plate"].append(i)
            g["cart"].append(i)
        elif n == "battery":
            g["battery"].append(i)
            g["cart"].append(i)
        elif n in ("sleeve", "sleeve_b"):
            g["cart"].append(i)
        elif n == "pillar":
            g["pillar"].append(i)
        elif n.startswith("station"):
            g["station"].append(i)
        elif n.startswith("lid_wall_"):
            g["tank"].append(i)
        elif n.startswith("lid_"):
            g["lid"].append(i)
        elif n == "track_pipe":
            g["pipe"].append(i)
        elif n == "tray" or n.startswith("cell_") or n == "shelf":
            g["tray"].append(i)
        elif n.startswith(("store_", "rail_")):
            g["store"].append(i)
        elif n.startswith("pod_") or n.startswith("store_pod"):
            g["pods"].append(i)
    return g


def dist(model, data, a, b, far=0.15):
    import mujoco
    np = _np()
    return float(mujoco.mj_geomDistance(model, data, a, b, far, np.zeros(6))) * 1000.0


def set_pose(model, data, cart_x, pose):
    import mujoco
    data.qpos[:] = 0
    data.qpos[model.joint("cart_x").qposadr[0]] = (cart_x - PARK_TRAY) / 1000.0
    for n, v in zip(LIMIT_NAMES, pose):
        data.qpos[model.joint(n).qposadr[0]] = v
    mujoco.mj_forward(model, data)


def clearances(model, data, target, grp):
    """Smallest distance (mm; negative = inside) per pair of groups, with the two geoms. The pod being picked is left out (the claw closes on it)."""
    skip = model.geom(f"pod_{target}").id
    res = {}

    def best(A, B, label, drop=()):
        b = (1e9, "")
        for a in A:
            if model.geom(a).name in drop:
                continue
            for e in B:
                if e == skip:
                    continue
                v = dist(model, data, a, e)
                if v < b[0]:
                    b = (v, f"{model.geom(a).name} / {model.geom(e).name}")
        res[label] = {"mm": round(b[0], 1), "between": b[1]}
    best(grp["arm"], grp["plate"] + grp["pipe"], "arm_to_plate_and_pipe", drop=("shoulder_housing",))   # the shoulder housing sits on the plate by design
    best(grp["arm"], grp["battery"], "arm_to_battery")
    best(grp["arm"], grp["lid"], "arm_to_lid")
    best(grp["arm"], grp["tank"], "arm_to_tank_wall")
    best(grp["arm"], grp["pillar"], "arm_to_pillar")
    best(grp["arm"], grp["station"], "arm_to_station")
    best(grp["arm"], grp["tray"] + grp["store"], "arm_to_tray_and_store")
    best(grp["arm"], grp["pods"], "arm_to_other_pods")
    best(grp["cart"], grp["lid"] + grp["tank"], "cart_to_lid")
    best(grp["cart"], grp["pillar"], "cart_to_pillar")
    best(grp["cart"], grp["station"], "cart_to_station")
    best(grp["cart"], grp["tray"] + grp["store"] + grp["pods"], "cart_to_tray_store_pods")
    return res


def worst_mm(cl, lid=True):
    return min(v["mm"] for k, v in cl.items() if k.startswith("arm_to") and (lid or k != "arm_to_lid"))


def pick_pose(name, dz=0.0, p=None, collide=True, lid=True):
    """The pose for a cell: the least claw tilt (within `tilt_tol_deg` counts as vertical, then the widest joint margin) among the poses that
    clear everything by CLEAR_MIN_MM. dz raises the grip point (the hover). Returns a dict: pose (pan, q1, q2, q3), tilt, reachable, collision_free, clearance, margin, ..."""
    import mujoco
    p = {**{k: v[0] for k, v in PARAMS.items()}, **(p or {})}
    x, y, z, park = cell_target(name)
    pan, cands = candidates_for(park, (x, y, z + dz), float(p["max_tilt_deg"]))
    out = {"cell": name, "target_mm": [x, y, z + dz], "park_x_mm": park, "pan_deg": round(math.degrees(pan), 1), "reachable": bool(cands), "collision_free": False}
    if not cands:
        return out
    tol = float(p["tilt_tol_deg"])
    order = sorted(cands, key=lambda c: (0 if c[0] <= tol else round(c[0], 1), -c[1]))
    model = model_for(**{k: p[k] for k in ("slope_deg", "stall_nm", "load_kg", "kp", "pod_contact", "hover_mm", "timestep_s", "tour", "tilt_tol_deg", "max_tilt_deg")}) if collide else None
    data = mujoco.MjData(model) if collide else None
    grp = groups(model) if collide else None
    pan_c = max(-LIMITS["shoulder_pan"][1], min(LIMITS["shoulder_pan"][1], pan))
    first = None
    for tilt, margin, phi, q in order[:40]:
        pose = (pan_c,) + tuple(q)
        if collide:
            set_pose(model, data, park, pose)
            cl = clearances(model, data, name, grp)
            free = worst_mm(cl, lid) >= CLEAR_MIN_MM
        else:
            cl, free = None, True
        rec = dict(out, pose=pose, tilt=tilt, margin_rad=margin, clearance=cl, collision_free=free)
        if first is None:
            first = rec
        if free:
            return rec
    return dict(first, collision_free=False)


# ---------------- the tour ----------------
def make_controls(p):
    """The tour: tray A1, C6 at the tray park, then the cart slides to the store park: S1, S7. Piecewise-constant targets at 20 Hz."""
    hover = float(p["hover_mm"])
    home, safe = (0.0, 0.0, 0.0, 0.0), (0.0,) + SAFE
    keys = []                                  # (seconds, pose (pan, q1, q2, q3), cart x relative to the tray park, mm)
    cart = (PARK_STORE - PARK_TRAY) if p["tour"] == "store" else 0.0       # cart x relative to the tray park, mm

    def visit(name):
        c = cell_target(name)[3] + cart
        up, dn = pick_pose(name, hover, p, collide=False), pick_pose(name, 0.0, p, collide=False)
        a = up.get("pose", safe)
        b = dn.get("pose", safe)
        return [(1.6, a, cart), (1.4, b, cart), (1.2, b, cart), (1.4, a, cart), (1.4, safe, cart)]

    keys += [(1.0, home, cart), (1.2, safe, cart)]
    for n in (("S1", "S7") if p["tour"] == "store" else ("A1", "C6")):
        keys += visit(n)
    keys += [(1.6, home, cart)]
    chans = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "cart"]
    steps = {c: [] for c in chans}
    t, cur = 0.0, (home, cart)
    for dur, q, c in keys:
        n = max(1, int(round(dur * 20)))
        for i in range(1, n + 1):
            a, tt = _smooth(i / n), t + dur * i / n
            for k, nm in enumerate(chans[:4]):
                steps[nm].append([round(tt, 3), round(cur[0][k] + (q[k] - cur[0][k]) * a, 5)])
            steps["cart"].append([round(tt, 3), round((cur[1] + (c - cur[1]) * a) / 1000.0, 5)])
        t += dur
        cur = (q, c)
    return {f"{n}_servo": [[0.0, 0.0]] + v for n, v in steps.items()}, t


def claw_footprint(model, data, band=(PL.LID_TOP - PL.LID_T - 1.0, PL.LID_TOP + 1.0)):
    """(x0, x1, y0, y1) mm of the claw and wrist housing where they cross the lid (z band), for the pose currently set in `data`; None if they do not reach the lid."""
    np = _np()
    pts = []
    for gn in CLAW:
        g = model.geom(gn)
        R, c, sz = data.geom_xmat[g.id].reshape(3, 3), data.geom_xpos[g.id], model.geom_size[g.id]
        for a in np.linspace(-1, 1, 15):
            for b in np.linspace(-1, 1, 9):
                for e in np.linspace(-1, 1, 9):
                    q = (c + R @ (np.array([a, b, e]) * sz)) * 1000.0
                    if band[0] <= q[2] <= band[1]:
                        pts.append(q)
    if not pts:
        return None
    P = np.array(pts)
    return float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max())


def slot_for(name, p=None):
    """The lid slot of a target: a rectangle round the minimum slot over the pod (SLOT_X x SLOT_Y, the pod leaves straight up) and the claw and wrist footprint of its pick pose at the lid (+ margin), rounded out to 1 mm."""
    rec = pick_pose(name, 0.0, p, lid=False)
    x, y, _, _ = cell_target(name)
    if not rec.get("pose"):
        return None
    mdl = model_for(**{k: v[0] for k, v in PARAMS.items()})
    import mujoco
    dat = mujoco.MjData(mdl)
    set_pose(mdl, dat, cell_target(name)[3], rec["pose"])
    f = claw_footprint(mdl, dat) or (x, x, y, y)
    # the slot = the minimum slot centred on the pod (the pod comes out straight up through it) joined with the claw's footprint at the lid (+ margin): a rectangle round both
    m = PL.SLOT_MARGIN
    x0 = min(x - PL.SLOT_X / 2, f[0] - m)
    x1 = max(x + PL.SLOT_X / 2, f[1] + m)
    y0 = min(y - PL.SLOT_Y / 2, f[2] - m)
    y1 = max(y + PL.SLOT_Y / 2, f[3] + m)
    return (math.floor(x0), math.ceil(x1), math.floor(y0), math.ceil(y1))
