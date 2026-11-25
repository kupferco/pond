"""Pod grab reach: can the real SO-101 arm on the Pond cart reach every tray row and the pod store? (OpenPocket #522)

World = the sim/unit frame, mm in the code and metres in the XML: X along the track, Y front(-)/back(+), Z up.
ONE track pipe (y -60, z 579, r 16). The cart rides it: sleeve, a 168 x 6 x 146 plate (front face y -116, centre z 519), the battery
and the arm. The arm is mounted with its base axis pointing out of the plate (-Y) and its pan zero pointing DOWN, so at pan 0 it works
in the vertical plane through the cart. The tray (4 x 4 pods, pod top z 224) and the pod store (pick z 225) are the targets;
the water station box and its legs are the obstacles. `tray_shift_mm` moves the tray rows towards the arm (-Y): 0 = today, 10 = proposal v3.

THE ARM IS THE REAL SO-101, not an estimate. All numbers below come from the official SO-101 URDF (TheRobotStudio/SO-ARM100,
Simulation/SO101/so101_new_calib.urdf): link offsets, joint limits and link masses. In the plane of the arm (x out along the arm at
zero pose, z up the base axis; base origin on the mounting face):
  pan axis x 38.8, shoulder_lift axis (69.2, 116.6), elbow (97.2, 229.2), wrist_flex (232.1, 234.4), grip point (391.4, 226.5)
  upper arm 116 mm (at 14 deg to the base axis), forearm 135 mm (2.2 deg), wrist_flex axis to grip point 159.5 mm (NOT 100).
  The links sit 18.3 mm beside the pan plane; the gripper comes back to it.
Joint limits (deg): pan +-110, shoulder_lift +-100, elbow +-96.8, wrist_flex +-95, wrist_roll -157..163. Zero pose: upper arm
along the base axis, forearm and gripper along +x. Servos are position servos limited to the STS3215 stall torque (`stall_nm`:
1.9 N m at 7.4 V, about 2.9 N m at 12 V). The pod and its lettuce are a `load_kg` mass at the grip point.

Run it: run_sim(model="pod_grab", duration_s=30, record=True) plays the tour: tray rows A, B, C, D (hover, down to grip height,
hold, up), the cart slides to the store, store pick. A target the arm cannot reach is driven to the nearest pose inside the limits.
sim/pod_grab_check.py imports this file and prints the reach table (joint angles, margins, torques, collisions).
"""
import math

PARAMS = {
    "tray_shift_mm": (0.0, "tray rows moved towards the arm (-Y), mm: 0 today, 10 proposal v3"),
    "tilt_deg": (0.0, "claw tilt from straight down, degrees (+ = claw points towards the plate, wrist further out)"),
    "battery": ("beside", "beside: arm base straight on the plate (brief); under_arm: base on the 50 mm battery (cad/cart_dims.py)"),
    "station_y0_mm": (14.0, "water station box front edge y (cad/water_station.py OFF_Y: 14); -197 puts it over the store pick"),
    "stall_nm": (1.9, "servo stall torque, N m (STS3215 7.4 V 1.9; 12 V about 2.9)"),
    "load_kg": (0.42, "pod 20 g + lettuce 400 g at the grip point, kg"),
    "kp": (150.0, "servo position gain, N m / rad (the STS3215 holds a position much stiffer than a plain P servo)"),
    "pod_contact": (0, "1: pods are solid to the claw (reach checks); 0: the claw passes through them (it closes round the pod in real life)"),
    "hover_mm": (50.0, "how far above the grip height the arm hovers between picks"),
    "timestep_s": (0.002, "integrator step"),
}
TRACK_BODY = "cart"
CAMERAS = ["front", "side", "iso", "top"]
DEFAULT_CONTROLS = {}

# ---------------- the layout (mm) ----------------
PIPE_Y, PIPE_Z, PIPE_R = -60.0, 579.0, 16.0
PLATE_FRONT_Y, PLATE_Z = -116.0, 519.0
PLATE_W, PLATE_T, PLATE_H = 168.0, 6.0, 146.0
BATT = (70.0, 50.0, 70.0)                      # x, y out of the plate, z (cad/cart_dims.py BATT)
TRAY_ROWS_Y = (-155.0, -117.0, -79.0, -41.0)   # rows A..D today
TRAY_POD_TOP = 224.0
TRAY_COL_PITCH = 38.0
TRAY_X = -209.0                                # the tray column the cart stops at
STORE_X, STORE_Y, STORE_Z = 160.0, -147.0, 225.0
STATION = dict(x0=60.0, x1=260.0, depth=100.0, z0=395.0, z1=508.0)   # CAD box 330..443 plus the 64 mm track rise (cad/layout.py)
ROW_NAMES = "ABCD"
SAFE = (-1.2, 1.25, 0.49)                       # travel pose (shoulder_lift, elbow_flex, wrist_flex), radians

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


def nearest_pose(tx, tz, phi):
    """No solution inside the limits: the in-limit pose whose grip point is closest, tool angle as close to phi as the limits allow."""
    best, bd = None, 1e9
    l1, l2, l3 = (LIMITS[n] for n in ("shoulder_lift", "elbow_flex", "wrist_flex"))
    steps = 70
    for i in range(steps + 1):
        q1 = l1[0] + (l1[1] - l1[0]) * i / steps
        for j in range(steps + 1):
            q2 = l2[0] + (l2[1] - l2[0]) * j / steps
            q3 = min(max(phi - q1 - q2, l3[0]), l3[1])
            t = fk(q1, q2, q3)[2]
            d = math.hypot(t[0] - tx, t[1] - tz) + 0.05 * abs(q1 + q2 + q3 - phi)
            if d < bd:
                best, bd = (q1, q2, q3), d
    return best


def layout(p):
    """Frame numbers shared by build() and the check script (mm)."""
    out = 0.0 if p["battery"] == "beside" else BATT[1]
    shift = float(p["tray_shift_mm"])
    return {
        "base_y": PLATE_FRONT_Y - out,                  # arm base mounting face
        "base_z": PLATE_Z + PAN_X * 1000.0,             # base origin height (pan axis on the plate centre; base x points down)
        "batt_out": out,
        "rows_y": [y - shift for y in TRAY_ROWS_Y],
    }


def target_plane(p, y, z):
    """World (y, z) of a grip point -> arm plane (x, z) in metres."""
    L = layout(p)
    return ((L["base_z"] - z) / 1000.0, (L["base_y"] - y) / 1000.0)


def targets(p):
    """Named grip points: name -> (x, y, z) mm. Rows A..D at the tray column, S = the store pick."""
    L = layout(p)
    t = {ROW_NAMES[i]: (TRAY_X, L["rows_y"][i], TRAY_POD_TOP) for i in range(4)}
    t["S"] = (STORE_X, STORE_Y, STORE_Z)
    return t


def pose_for(p, y, z, dz=0.0):
    """Joint angles (q1, q2, q3) for a grip point at (y, z + dz) with the claw tilt of the params; (q, ok)."""
    tx, tz = target_plane(p, y, z + dz)
    phi = math.radians(float(p["tilt_deg"]))
    r = ik(tx, tz, phi)
    if r:
        return r[0], True
    return nearest_pose(tx, tz, phi), False


def _smooth(a):
    return 0.5 - 0.5 * math.cos(math.pi * a)


def make_controls(p):
    """The tour as piecewise-constant position targets at 20 Hz."""
    hover = float(p["hover_mm"])
    tg = targets(p)
    home = (0.0, 0.0, 0.0)
    keys = []      # (seconds, (q1, q2, q3), cart x relative to the tray stop, mm)
    cart = 0.0
    safe = SAFE   # arm folded up in front of the plate, clear of the trays: it travels through here
    keys.append((1.0, home, cart))
    keys.append((1.2, safe, cart))
    for name in ("A", "B", "C", "D", "S"):
        x, y, z = tg[name]
        if name == "S":
            keys.append((1.4, safe, cart))
            cart = STORE_X - TRAY_X
            keys.append((2.5, safe, cart))
        up, _ = pose_for(p, y, z, hover)
        dn, _ = pose_for(p, y, z, 0.0)
        keys += [(1.6, up, cart), (1.4, dn, cart), (1.2, dn, cart), (1.4, up, cart)]
    keys.append((1.6, safe, cart))
    keys.append((1.6, home, cart))
    steps = {j: [] for j in ("shoulder_lift", "elbow_flex", "wrist_flex", "cart")}
    t = 0.0
    cur = (home, 0.0)
    for dur, q, c in keys:
        n = max(1, int(round(dur * 20)))
        for i in range(1, n + 1):
            a = _smooth(i / n)
            tt = t + dur * i / n
            qs = [cur[0][k] + (q[k] - cur[0][k]) * a for k in range(3)]
            cc = cur[1] + (c - cur[1]) * a
            for name, v in zip(("shoulder_lift", "elbow_flex", "wrist_flex"), qs):
                steps[name].append([round(tt, 3), round(v, 5)])
            steps["cart"].append([round(tt, 3), round(cc / 1000.0, 5)])
        t += dur
        cur = (q, c)
    ctrl = {f"{n}_servo": [[0.0, 0.0]] + v for n, v in steps.items() if n != "cart"}
    ctrl["cart_servo"] = [[0.0, 0.0]] + steps["cart"]
    return ctrl, t


def _f(v):
    return f"{v:.5f}"


def _m(*a):
    return " ".join(_f(x / 1000.0) for x in a)


def build(**p) -> str:
    L = layout(p)
    stall, kp = float(p["stall_nm"]), float(p["kp"])
    ctrl, total = make_controls(p)
    DEFAULT_CONTROLS.clear()
    DEFAULT_CONTROLS.update(ctrl)

    env = 'contype="2" conaffinity="1"'          # things the arm can hit
    arm = 'contype="1" conaffinity="2"'          # the arm's own geoms
    nog = 'contype="0" conaffinity="0"'
    podc = env if int(p["pod_contact"]) else nog
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
                      <geom name="load" type="sphere" size="0.012" {nog} mass="{float(p['load_kg']):.4f}" rgba="0.3 0.8 0.3 0.8"/>
                    </body>
                  </body>
                </body>
              </body>
            </body>
          </body>
        </body>"""

    # ---- cart (all geoms collide with the arm). Body origin = world origin at the tray stop, slides along X.
    cx = TRAY_X
    cart_geoms = f"""
        <geom name="sleeve" type="cylinder" pos="0 {_f(PIPE_Y/1000)} {_f(PIPE_Z/1000)}" euler="0 1.5708 0" size="0.0345 0.062" {nog} mass="0.9" rgba="0.5 0.5 0.55 1"/>
        <geom name="hand_arm" type="box" pos="0 {_f((PIPE_Y + PLATE_FRONT_Y)/2000)} {_f((PIPE_Z + 10)/1000)}" size="0.03 {_f((PLATE_FRONT_Y - PIPE_Y)/-2000)} 0.02" {nog} mass="0.2" rgba="0.5 0.5 0.55 1"/>
        <geom name="plate" type="box" pos="0 {_f((PLATE_FRONT_Y + PLATE_T/2)/1000)} {_f(PLATE_Z/1000)}" size="{_m(PLATE_W/2, PLATE_T/2, PLATE_H/2)}" {env} mass="0.3" rgba="0.8 0.8 0.85 1"/>"""
    if p["battery"] == "beside":
        bx = 78.0   # beside the arm base, on the plate (position assumed: the brief gives none)
        cart_geoms += f"""
        <geom name="battery" type="box" pos="{_m(bx, PLATE_FRONT_Y - BATT[1] / 2, PLATE_Z)}" size="{_m(BATT[0]/2, BATT[1]/2, BATT[2]/2)}" {env} mass="0.35" rgba="0.2 0.25 0.6 1"/>"""
    else:
        cart_geoms += f"""
        <geom name="battery" type="box" pos="{_m(0, PLATE_FRONT_Y - BATT[1] / 2, PLATE_Z)}" size="{_m(BATT[0]/2, BATT[1]/2, BATT[2]/2)}" {env} mass="0.35" rgba="0.2 0.25 0.6 1"/>"""
    # arm base: mounting face at base_y, base x down, base y +X, base z out of the plate (-Y); pan axis on the plate centre line
    base_pos = _m(0, L["base_y"], L["base_z"])
    arm_in_cart = xml_arm.replace(f'<body name="arm_base" pos="{_m(0, 0, 0)}">',
                                  f'<body name="arm_base" pos="{base_pos}" xyaxes="0 0 -1 1 0 0">', 1)

    # ---- fixed scene
    scene = [f'<geom name="track_pipe" type="cylinder" pos="0 {_f(PIPE_Y/1000)} {_f(PIPE_Z/1000)}" euler="0 1.5708 0" size="{_f(PIPE_R/1000)} 0.45" {env} rgba="0.7 0.7 0.72 1"/>']
    rows_y = L["rows_y"]
    tray_y0, tray_y1 = min(rows_y) - 25, max(rows_y) + 25
    tray_x0, tray_x1 = TRAY_X - 1.5 * TRAY_COL_PITCH - 25 - TRAY_COL_PITCH, TRAY_X + 2.5 * TRAY_COL_PITCH + 25 - TRAY_COL_PITCH
    scene.append(f'<geom name="tray" type="box" pos="{_m((tray_x0+tray_x1)/2, (tray_y0+tray_y1)/2, TRAY_POD_TOP - 24)}" size="{_m((tray_x1-tray_x0)/2, (tray_y1-tray_y0)/2, 3)}" {env} rgba="0.59 0.43 0.27 1"/>')
    for i, ry in enumerate(rows_y):
        for j in range(4):
            px = TRAY_X + (j - 1) * TRAY_COL_PITCH
            nm = f"pod_{ROW_NAMES[i]}{j}"
            scene.append(f'<geom name="{nm}" type="cylinder" pos="{_m(px, ry, TRAY_POD_TOP - 11)}" size="0.0125 0.011" {podc} rgba="0.95 0.6 0.2 1"/>')
            scene.append(f'<geom name="lettuce_{ROW_NAMES[i]}{j}" type="sphere" pos="{_m(px, ry, TRAY_POD_TOP + 25)}" size="0.02" {nog} rgba="0.3 0.8 0.3 0.5"/>')
    # store: shelf and three rows of pods, the pick pod at (STORE_X, STORE_Y)
    scene.append(f'<geom name="store_shelf" type="box" pos="{_m(160, -147, STORE_Z - 31)}" size="{_m(110, 62, 3)}" {env} rgba="0.59 0.43 0.27 1"/>')
    for r, sy in enumerate((STORE_Y - 35, STORE_Y, STORE_Y + 35)):
        for k in range(-3, 4):
            nm = "pod_S" if (r == 1 and k == 0) else f"store_pod_{r}_{k + 3}"
            scene.append(f'<geom name="{nm}" type="cylinder" pos="{_m(STORE_X + k * 28, sy, STORE_Z - 11)}" size="0.0125 0.011" {podc} rgba="0.95 0.6 0.2 1"/>')
    # water station: box on four 20 x 20 legs down to the lid (top 304 + 64 rise)
    sx0, sx1, sy0 = STATION["x0"], STATION["x1"], float(p["station_y0_mm"])
    sy1 = sy0 + STATION["depth"]
    scene.append(f'<geom name="station_box" type="box" pos="{_m((sx0+sx1)/2, (sy0+sy1)/2, (STATION["z0"]+STATION["z1"])/2)}" size="{_m((sx1-sx0)/2, (sy1-sy0)/2, (STATION["z1"]-STATION["z0"])/2)}" {env} rgba="0.82 0.82 0.78 1"/>')
    for lx in (sx0 + 10, sx1 - 10):
        for ly in (sy0 + 10, sy1 - 10):
            scene.append(f'<geom name="station_leg_{int(lx)}_{int(ly)}" type="box" pos="{_m(lx, ly, (368 + STATION["z0"])/2)}" size="{_m(10, 10, (STATION["z0"]-368)/2)}" {env} rgba="0.7 0.7 0.7 1"/>')
    scene.append(f'<geom name="lid" type="box" pos="{_m(0, 0, 366)}" size="{_m(330, 210, 2)}" {nog} rgba="0.6 0.7 0.8 0.15"/>')
    scene.append('<geom name="floor" type="plane" size="1.5 1 0.1" pos="0 0 0" rgba="0.3 0.32 0.35 1"/>')

    def cam(name, pos, xy):
        return f'<camera name="{name}" pos="{pos}" xyaxes="{xy}" fovy="40"/>'

    cams = "\n        ".join([
        cam("front", _m(0, -1000, 400), "1 0 0 0 0 1"),
        cam("side", _m(1000, -150, 400), "0 1 0 0 0 1"),
        cam("iso", _m(650, -750, 700), "0.76 0.65 0 -0.23 0.27 0.93"),
        cam("top", _m(0, -150, 1100), "1 0 0 0 1 0"),
    ])
    rng = float(STORE_X - TRAY_X) / 1000.0
    names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
    acts = "".join(
        f'<position name="{n}_servo" joint="{n}" kp="{kp}" kv="2.0" forcerange="-{stall} {stall}" forcelimited="true" '
        f'ctrlrange="{_f(LIMITS[n][0])} {_f(LIMITS[n][1])}" ctrllimited="true"/>' for n in names)
    acts += f'<position name="cart_servo" joint="cart_x" kp="3000" kv="300" forcerange="-60 60" forcelimited="true" ctrlrange="-0.1 {_f(rng + 0.1)}" ctrllimited="true"/>'
    sc = "\n    ".join(scene)
    return f"""<mujoco model="pod_grab">
  <compiler angle="radian"/>
  <option timestep="{float(p['timestep_s'])}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <visual><global offwidth="1280" offheight="720"/><headlight ambient="0.45 0.45 0.45" diffuse="0.6 0.6 0.6"/></visual>
  <worldbody>
    <light pos="0 -0.8 1.6" dir="0 0.4 -1"/>
    {sc}
    <body name="cart" pos="{_m(cx, 0, 0)}">
      <joint name="cart_x" type="slide" axis="1 0 0" range="-0.05 {_f(rng + 0.05)}" damping="5"/>
      <inertial pos="0 {_f(-0.1)} {_f(PLATE_Z/1000)}" mass="2.0" diaginertia="0.05 0.05 0.05"/>{cart_geoms}
      {cams}
      {arm_in_cart}
    </body>
  </worldbody>
  <actuator>{acts}</actuator>
  <sensor><framepos name="tcp_pos" objtype="site" objname="tcp"/></sensor>
</mujoco>"""
