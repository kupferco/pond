# cad/cart_arm.py: SO-101 follower arm mounted on the Pond cart (DRAFT, 11 Nov 2026).
# Drawing 5 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable drawing of how the arm sits on the cart and what it can reach.
#
# Frame: the hand_sleeve.py frame (track pipes along Z, plate on the -Y side of the pipes).
# v2 (follow-up): the base plate runs ACROSS two parallel pipes, one hand clamped on each pipe (pipe B and
# pipe C, one pipe from each of two neighbouring units), instead of both hands clamping the same pipe as in
# cart_assembly.py. So the plate's long side is cart X, the two hands sit at x = -/+ PIPE_SPACING/2 and the
# plate is only as tall (Z) as one hand. The arm stays on the plate centre, as in cart_assembly.py.
# The track pipes are VERTICAL in the unit, so cart +Z is world up and the arm points sideways, out of the
# plate (cart -Y), towards the store. Store parts are placed in this frame with store_to_cart() below.
#
# Two scenes are built:
#   result          working scene: arm reaching a dry-store pick hole (D1) and a seedling tray cell (A2),
#                   joints labelled A-F, Waveshare board, cable path, reach envelope.
#   result_stowed   the same cart with the arm folded for travel.
#
# ASSUMED (all marked "ASSUMED" below; nothing here is decided):
#  0. Pipe spacing: the two pipes the cart clamps are 120 mm apart (v3, Viber #97; was 280), centre to centre (ASSUMED; the real
#     spacing between neighbouring units is not decided). One hand per pipe, both facing the same way.
#  1. Arm mount, hands, wheels, sleeves: as cart_assembly.py (itself assumed). Base plate redrawn across the
#     two pipes: 112 mm (Z) x PIPE_SPACING + 100 (X) x 6 mm, same open-frame idea, bosses round each hand's
#     holes and an arm block. Battery 70 x 50 x 70 beside the arm on the pipe-C side, motors one per hand on
#     the +X side of each hand (gearbox up), all ASSUMED positions.
#  2. Link lengths (shoulder to elbow 120, elbow to wrist 130, wrist to gripper tip 100 = 350 mm
#     stretched) taken from the layout in so101_servo_layout.py and the 350 mm REACH of pod_store_reach.py.
#     Servos and links are envelope boxes, not real parts.
#  3. Store, tank, lid, pick holes, rows, seedling tray: pod_store_reach.py v3 numbers (tank 700 x 400 x 400,
#     row pitch 35, pod pitch 28, pipe A at x = -250). The lid is shown only as a patch near the arm.
#  4. Cart height on the pipes: shoulder 550 mm above the tank base, as pod_store_reach.py. The pipes start
#     at z = 480 there (lid 404 + 76); the plate is now short enough (112 mm) that its bottom edge is at 494,
#     clear of both the pipe ends and the lid. The two pipes are drawn as stubs from the pipe end up.
#     The store model has one pipe per x position: the second pipe (neighbouring unit) is not in it.
#  5. The lid has an access opening over the seedling tray (pod_store_reach.py shows no opening).
#  6. Seedling tray: 4 x 4 cells (the grid is an open question: 4 x 4 or 3 x 5), 200 x 380 mm, cell A1 at the
#     tray corner nearest the store and the track end, numbering runs along the tray. Cell A2 is used.
#  7. Pick hole D1: gripper square to the arm axis, i.e. straight down (the hole is in line with the
#     shoulder). Seedling cell A2: the cell is only 34 mm out from the plate face, so with the gripper
#     straight down the wrist would sit inside the battery block; the gripper is leaned 30 deg past square
#     (wrist out and clear). Cells further out than the tray's first column are not reached from this cart
#     position. The solution keeps the elbow on the store side (away from the cart). Wrist flex and roll ranges are not checked against the real servo limits.
#  8. Waveshare bus servo board: 42 x 33 x 12 mm block on four 6 mm standoffs, on a small bracket tab that is
#     bolted to the base-plate arm block and overhangs towards pipe B. Real board size to confirm.
#  9. Cable path: one 6-way servo daisy chain from the board (A at the base up to F at the gripper, clipped
#     to the +arm-Y side of the links), 12 V lead from the battery, USB lead out of the board towards the top
#     edge of the plate (to a laptop now, a Raspberry Pi on the cart battery later). Routes are drawn as
#     straight 4 mm round runs; real cable lengths, clips and strain relief are not designed.
# 10. Stowed pose: upper arm lies along the pipe over the base block, forearm folded back beside it,
#     gripper folded forward beside that (three lanes 26 mm apart). The shoulder pan in this pose is
#     assumed to turn the arm's lanes to the -X side of the cart (towards pipe B; nothing is up there above
#     the plate). Not collision-checked against a real arm.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs          # reused via cart_assembly
import cart_assembly as ca        # reused, not redrawn
import cart_hinge as ch           # plate hinge and worm drive of each hand (Viber #97)

# ---------------- Numbers ----------------
L1, L2, L3 = 120.0, 130.0, 100.0        # ASSUMED: shoulder-elbow, elbow-wrist, wrist-gripper tip (350 total)
SHOULDER_H = 88.0                       # shoulder axis height above the arm base plate (same as cart_assembly)
REACH = L1 + L2 + L3                    # 350, as pod_store_reach.py

# Store numbers from pod_store_reach.py (world frame: z up, pipe A at x = -250)
TH = 400.0; LID_T = 4.0
LID_TOP = TH + LID_T
PIPE_XW = -290.0
STORE_X0 = -140.0; ROW_P = 35.0; POD_D = 25.0
FRONT_Y = -200.0
SEED_X0, SEED_X1, SEED_Y = -345.0, -145.0, 190.0     # seedling tray 200 x 380
SEED_TOP = TH - 20.0
SHOULDER_Z = 550.0                                    # as pod_store_reach.py (plate bottom then at 494, pipes start 480)
PIPE_BOTTOM_W = 480.0                                  # pipe ends at z = TH + 80 in pod_store_reach.py
PIPE_SPACING, HX, PLATE_ZH = ca.PIPE_SPACING, ca.HX, ca.PLATE_ZH     # shared with cart_assembly via cart_dims.py
ARM_YW = 0.0                                          # world y of the arm axis (cart parked above row line y = 0)
YC = ARM_YW - ca.ARM_X                                # world y of the cart's own Y axis origin

def store_to_cart(x, y, z):
    """World (store) point -> cart frame. Pipe A axis is cart (0, 0, *); out of the plate = -Y = world +x."""
    return (y - YC, -(x - PIPE_XW), z - SHOULDER_Z)

# Pick hole D1 (row 1, hole at y = 0) and seedling cell A2
D1_W = (STORE_X0 + ROW_P / 2, 0.0, LID_TOP)
CELL_W = (SEED_X1 - 25.0, -47.5, SEED_TOP)             # ASSUMED 4 x 4 grid: 50 mm columns, 95 mm rows; A2

# ---------------- Helpers ----------------
def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

def cyl_dir(r, p0, p1):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v))

def fuse(items):
    out = None
    for i in items:
        out = i if out is None else out.union(i)
    return out

# Arm frame -> cart frame. Arm Z = out of the plate (cart -Y); arm X = cart +Z at pan 0; arm Y = cart -X.
ARM_ORIGIN = (ca.ARM_X, ca.PLATE_Y0, ca.ARM_Z)
def a2c_pt(p):
    return (ARM_ORIGIN[0] - p[1], ARM_ORIGIN[1] - p[2], ARM_ORIGIN[2] + p[0])
def to_cart(wp):
    # same rotation chain as cart_assembly.arm_envelope: X -> Y (about Z), then Y -> Z, Z -> -Y (about X)
    return (wp.rotate((0, 0, 0), (0, 0, 1), 90).rotate((0, 0, 0), (1, 0, 0), 90).translate(ARM_ORIGIN))

def d_in_plane(a):
    return (math.sin(math.radians(a)), 0.0, math.cos(math.radians(a)))

def lerp(p, d, t):
    return tuple(p[i] + d[i] * t for i in range(3))

# ---------------- Arm builder ----------------
COL = {
    "A": (0.9, 0.2, 0.2, 1), "B": (1.0, 0.55, 0.1, 1), "C": (0.95, 0.85, 0.1, 1),
    "D": (0.2, 0.7, 0.3, 1), "E": (0.2, 0.45, 0.95, 1), "F": (0.6, 0.25, 0.85, 1),
}
NAMES = {"A": "shoulder pan", "B": "shoulder lift", "C": "elbow flex", "D": "wrist flex",
         "E": "wrist roll", "F": "gripper"}

def build_arm(pan, a1, a2, a3, lane=(0.0, 0.0, 0.0), roll=0.0):
    """Arm in the arm frame, returned in cart coordinates.
    pan: turn about the arm Z axis (deg). a1, a2, a3: direction of upper arm, forearm and wrist/gripper,
    measured from the arm Z axis towards +X in the arm's own plane (deg). lane: arm-Y offset (mm) of the
    upper arm, forearm and wrist/gripper (all 0 in a working pose; used to fold side by side).
    Returns (dict name -> Workplane, dict joint letter -> (centre, axis) in cart coords, cable points)."""
    parts, joints = {}, {}

    def spin(wp):                       # pan about the arm Z axis, then to cart
        return to_cart(wp.rotate((0, 0, 0), (0, 0, 1), pan))

    def pt(p):                          # point in the panned arm frame -> cart
        c, s = math.cos(math.radians(pan)), math.sin(math.radians(pan))
        return a2c_pt((p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]))

    def ax(v):                          # direction in the panned arm frame -> cart (a vector)
        o, e = pt((0, 0, 0)), pt(v)
        return tuple(e[i] - o[i] for i in range(3))

    def link(p0, p1, w, t, y):          # box between two points of the arm plane, rotated into place
        d = tuple(p1[i] - p0[i] for i in range(3))
        n = math.hypot(d[0], d[2])
        ang = math.degrees(math.atan2(d[0], d[2]))
        b = box(w, t, n, (0, 0, 0)).rotate((0, 0, 0), (0, 1, 0), ang)
        m = tuple((p0[i] + p1[i]) / 2 for i in range(3))
        return b.translate((m[0], m[1] + y, m[2]))

    def servo(c, ang, y, axis_len=35.0, size=(45.0, 35.0, 24.0)):
        # box with its long side (45) along the link direction (angle ang), joint axis along arm Y
        b = box(size[2], size[1], size[0], (0, 0, 0)).rotate((0, 0, 0), (0, 1, 0), ang)
        return b.translate((c[0], c[1] + y, c[2]))

    S = (0.0, 0.0, SHOULDER_H)
    E = lerp(S, d_in_plane(a1), L1)
    W = lerp(E, d_in_plane(a2), L2)
    d3 = d_in_plane(a3)
    T = lerp(W, d3, L3)
    y1, y2, y3 = lane

    # static base (does not pan)
    parts["base_plate"] = to_cart(box(70, 70, 8, (0, 0, 4)))
    parts["servo_A_base"] = to_cart(box(45, 24, 35, (0, 0, 26)))
    # turret: everything above servo A pans with it
    parts["shoulder_bracket"] = spin(box(50, 40, 30, (0, 0, 62)))
    parts["servo_B_shoulder"] = spin(servo(S, a1, y1))
    parts["upper_arm"] = spin(link(S, E, 26, 20, y1))
    parts["servo_C_elbow"] = spin(servo(E, a1, y2))
    parts["forearm"] = spin(link(E, W, 26, 20, y2))
    parts["servo_D_wrist_flex"] = spin(servo(W, a2, y3))
    roll_c, grip_c = lerp(W, d3, 30.0), lerp(W, d3, 64.0)
    parts["servo_E_wrist_roll"] = spin(box(24, 24, 36, (0, 0, 0)).rotate((0, 0, 0), (0, 1, 0), a3)
                                       .translate((roll_c[0], roll_c[1] + y3, roll_c[2])))
    parts["servo_F_gripper"] = spin(box(24, 35, 36, (0, 0, 0)).rotate((0, 0, 0), (0, 1, 0), a3)
                                    .translate((grip_c[0], grip_c[1] + y3, grip_c[2])))
    for k, off in (("fixed", 7.0), ("moving", -7.0)):
        jc = lerp(lerp(W, d3, 88.0), (d3[2], 0, -d3[0]), off)
        parts["jaw_" + k] = spin(box(6, 8, 24, (0, 0, 0)).rotate((0, 0, 0), (0, 1, 0), a3)
                                 .translate((jc[0], jc[1] + y3, jc[2])))
    # joint markers: short round discs along each joint axis
    def marker(letter, c, axis_dir, y):
        cc = (c[0], c[1] + y, c[2])
        if axis_dir == "y":
            return spin(cyl(9, 44, "y", cc))
        # roll axis: along the gripper direction
        return spin(cyl_dir(9, lerp(cc, d3, -5), lerp(cc, d3, 5)))
    A_c = (0, 0, 46.0)
    parts["joint_A"] = spin(cyl(14, 8, "z", A_c))
    parts["joint_B"] = marker("B", S, "y", y1)
    parts["joint_C"] = marker("C", E, "y", y2)
    parts["joint_D"] = marker("D", W, "y", y3)
    parts["joint_E"] = marker("E", lerp(W, d3, 14.0), "roll", y3)
    parts["joint_F"] = marker("F", lerp(W, d3, 50.0), "y", y3)

    joints = {"A": pt(A_c), "B": pt((S[0], S[1] + y1, S[2])), "C": pt((E[0], E[1] + y2, E[2])),
              "D": pt((W[0], W[1] + y3, W[2])), "E": pt(lerp((W[0], W[1] + y3, W[2]), d3, 14.0)),
              "F": pt(lerp((W[0], W[1] + y3, W[2]), d3, 50.0))}
    tip = pt((T[0], T[1] + y3, T[2]))

    # cable path: servo bus daisy chain, clipped along the +arm-Y side of the links
    CY = 17.0
    chain = [(0, CY, 26), (0, CY, 62), (S[0], S[1] + y1 + CY, S[2]),
             (E[0], E[1] + y2 + CY, E[2]), (W[0], W[1] + y3 + CY, W[2]),
             lerp((W[0], W[1] + y3 + CY, W[2]), d3, 30.0), lerp((W[0], W[1] + y3 + CY, W[2]), d3, 64.0)]
    cable = [a2c_pt(chain[0]), a2c_pt(chain[1])] + [pt(p) for p in chain[2:]]
    return parts, joints, cable, tip

def solve_pose(target_c, elbow_store_side=True, a3_deg=90.0):
    """Planar solution for the arm reaching `target_c` (cart frame) with its gripper along a3.
    Pan turns the arm plane about the arm Z axis (cart -Y through the base) towards the target. The gripper
    direction a3 = 90 deg is perpendicular to that axis, i.e. along the line from the axis to the target,
    so it points straight at the target (straight down when the target is in line with the shoulder)."""
    ox, oy, oz = ARM_ORIGIN
    dx, dz = target_c[0] - ox, target_c[2] - oz
    u = oy - target_c[1]                            # distance out of the plate along the arm axis
    r = math.hypot(dx, dz)
    pan = math.degrees(math.atan2(-dx, dz))         # arm X at pan p points to cart (X = -sin p, Z = cos p)
    d3 = d_in_plane(a3_deg)
    wx, wz = r - d3[0] * L3, u - d3[2] * L3         # wrist position in the arm plane (x radial, z along axis)
    rx, rz = wx - 0.0, wz - SHOULDER_H
    d = math.hypot(rx, rz)
    if d > L1 + L2 or d < abs(L1 - L2):
        raise ValueError("target out of reach (wrist %.0f mm from the shoulder)" % d)
    psi = math.degrees(math.atan2(rx, rz))
    g = math.degrees(math.acos((L1 ** 2 + d ** 2 - L2 ** 2) / (2 * L1 * d)))
    a1 = psi - g if elbow_store_side else psi + g
    e = (L1 * math.sin(math.radians(a1)), SHOULDER_H + L1 * math.cos(math.radians(a1)))
    a2 = math.degrees(math.atan2(wx - e[0], wz - e[1]))
    return pan, a1, a2, a3_deg, d

# ---------------- Cart: two hands on two parallel pipes, one plate across them ----------------
PIPE_Z0, PIPE_Z1 = PIPE_BOTTOM_W - SHOULDER_Z, 165.0     # pipe stubs: from the pipe end (z -70) up to z +165
def xshift(shape, x):
    return shape.translate((x, 0, 0))

PLATE_X0, PLATE_X1, PLATE_CY = ca.PLATE_X0, ca.PLATE_X1, ca.PLATE_CY
plate, battery, motors = ca.plate, ca.battery, ca.motors    # the same parts as the whole-cart drawing
BATT_C = ca.BATT_X
BATT, BATT_Y = ca.BATT, ca.BATT[1]

cart = [("base_plate", plate, (0.35, 0.35, 0.38, 1)),
        ("battery", battery, (0.2, 0.45, 0.85, 1)),
        ("drive_motors", motors, (0.85, 0.25, 0.25, 1))]
for tag, sgn in (("pipe_C", 1), ("pipe_B", -1)):
    cart.append(("track_%s" % tag, xshift(ca.cyl(hs.R_PIPE, PIPE_Z1 - PIPE_Z0, "z", (0, 0, (PIPE_Z0 + PIPE_Z1) / 2)), sgn * HX),
                 (0.75, 0.78, 0.8, 1)))
    cart.append(("hand_on_%s_sleeve" % tag, xshift(hs.result, sgn * HX), (0.95, 0.75, 0.2, 1)))
    cart.append(("hand_on_%s_wheels" % tag, xshift(ca.WHEELS, sgn * HX), (0.15, 0.15, 0.15, 1)))
    for nm, shp, col in ch.hinge_parts(sgn):
        cart.append(("hinge_%s_%s" % (tag, nm), shp, col))

# ---------------- Waveshare board and bracket ----------------
BOARD = (42.0, 12.0, 33.0)                       # ASSUMED: X (along plate), out from plate, Z
BOARD_X = ca.BATT_X                              # ASSUMED (v3, Viber #97): on the battery's front face on 6 mm foam pads
STAND = 6.0                                      # (the plate no longer has room for a board beside the arm)
board_c = (BOARD_X, ca.PLATE_Y0 - BATT_Y - STAND - BOARD[1] / 2, ca.BATT_Z)
foam = fuse([box(8.0, STAND, 8.0, (BOARD_X + sx * 16.0, ca.PLATE_Y0 - BATT_Y - STAND / 2, ca.BATT_Z + sz * 11.0))
             for sx in (-1, 1) for sz in (-1, 1)])
board = box(BOARD[0], BOARD[1], BOARD[2], board_c)
# 12 V lead: board -> battery's front-bottom edge (a 20 mm run)
power_pts = [(BOARD_X + 10.0, board_c[1], ca.BATT_Z - BOARD[2] / 2),
             (BOARD_X + 10.0, ca.PLATE_Y0 - BATT_Y, ca.BATT_Z - BATT[2] / 2 + 6.0)]
usb_pts = [(BOARD_X, board_c[1], ca.BATT_Z + BOARD[2] / 2), (BOARD_X, board_c[1], ca.BATT_Z + BATT[2] / 2 + 10.0)]

def polyline(pts, r=2.0):
    out = []
    for p0, p1 in zip(pts, pts[1:]):
        out.append(cyl_dir(r, p0, p1))
        out.append(cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(*p1), cq.Vector(0, 0, 1), -90, 90, 360)))
    return fuse(out)

# ---------------- Store parts (placed in the cart frame) ----------------
def lid_patch():
    # lid top is at world z LID_TOP; patch from the tray end to just past D4, full row length
    x0, x1, y0, y1 = SEED_X0, 5.0, -210.0, 210.0
    p0, p1 = store_to_cart(x0, y0, LID_TOP), store_to_cart(x1, y1, LID_TOP - LID_T)
    c = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
    lid = box(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]), abs(p1[2] - p0[2]), c)
    # ASSUMED tray access opening, 8 mm bigger than the tray all round
    q0, q1 = store_to_cart(SEED_X0 - 8, -SEED_Y - 8, LID_TOP), store_to_cart(SEED_X1 + 8, SEED_Y + 8, LID_TOP - LID_T)
    qc = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2, (q0[2] + q1[2]) / 2)
    lid = lid.cut(box(abs(q1[0] - q0[0]), abs(q1[1] - q0[1]), abs(q1[2] - q0[2]) + 2, qc))
    for i in range(4):                               # pick holes of rows D1..D4 (all at y = 0)
        hc = store_to_cart(STORE_X0 + ROW_P / 2 + i * ROW_P, 0.0, LID_TOP + 1.0)
        lid = lid.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(POD_D / 2 + 2, LID_T + 2, cq.Vector(*hc),
                                                                  cq.Vector(0, 0, -1))))
    return lid

def seed_tray():
    p0, p1 = store_to_cart(SEED_X0, -SEED_Y, SEED_TOP), store_to_cart(SEED_X1, SEED_Y, SEED_TOP - 40.0)
    c = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
    tray = box(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]), abs(p1[2] - p0[2]), c)
    # 4 x 4 cell pockets, 12 mm deep (ASSUMED grid)
    for i in range(4):
        for j in range(4):
            wx = SEED_X0 + 25.0 + 50.0 * i
            wy = -SEED_Y + 47.5 + 95.0 * j
            pc = store_to_cart(wx, wy, SEED_TOP - 6.0)
            tray = tray.cut(box(85.0, 40.0, 14.0, (pc[0], pc[1], pc[2])))
    return tray

def targets():
    d1 = store_to_cart(*D1_W)
    cell = store_to_cart(*CELL_W)
    pod = cq.Workplane("XY").add(cq.Solid.makeCylinder(POD_D / 2, 30.0, cq.Vector(d1[0], d1[1], d1[2] - 6.0),
                                                       cq.Vector(0, 0, -1)))        # pod just below the lid
    seedling = cq.Workplane("XY").add(cq.Solid.makeCylinder(8.0, 30.0, cq.Vector(cell[0], cell[1], cell[2] - 6.0),
                                                            cq.Vector(0, 0, 1)))    # seedling in its cell
    return pod, seedling

# ---------------- Reach envelope ----------------
S_CART = a2c_pt((0, 0, SHOULDER_H))               # shoulder axis position in the cart frame

def ring(radius, plane):
    """A thin ring (3 x 3 mm section) of the given radius about the shoulder, half of it kept.
    plane 'XZ': in the cart X-Z plane (store y-z, vertical, across the track), lower half (Z < shoulder);
    'YZ': in the cart Y-Z plane (store x-z, vertical, towards the store), lower and outer half;
    'XY': horizontal on the lid plane, outer half (towards the store)."""
    t = 3.0
    if plane == "XZ":
        r = cq.Workplane("XZ").circle(radius + t / 2).circle(radius - t / 2).extrude(t / 2, both=True)
        r = r.intersect(box(2 * radius + 20, 20, radius + 10, (0, 0, -(radius + 10) / 2)))
        return r.translate(S_CART)
    if plane == "YZ":
        r = cq.Workplane("YZ").circle(radius + t / 2).circle(radius - t / 2).extrude(t / 2, both=True)
        r = r.intersect(box(20, radius + 10, radius + 10, (0, -(radius + 10) / 2, -(radius + 10) / 2)))
        return r.translate(S_CART)
    r = cq.Workplane("XY").circle(radius + t / 2).circle(radius - t / 2).extrude(t / 2, both=True)
    r = r.intersect(box(2 * radius + 20, radius + 10, 20, (0, -(radius + 10) / 2, 0)))
    return r

LID_PLANE_Z = store_to_cart(0, 0, LID_TOP)[2]
LID_R = math.sqrt(REACH ** 2 - (S_CART[2] - LID_PLANE_Z) ** 2)       # reach footprint on the lid plane
def reach_rings():
    rs = [ring(REACH, "XZ"), ring(REACH, "YZ")]
    hz = ring(LID_R, "XY").translate((S_CART[0], S_CART[1], LID_PLANE_Z))
    return rs[0], rs[1], hz

def reach_dome():
    """Translucent lower-outer eighth-sphere set (GLB only, hidden-line drawings leave it out)."""
    sph = cq.Workplane("XY").add(cq.Solid.makeSphere(REACH, cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -90, 90, 360))
    keep = box(2 * REACH, REACH, REACH, (0, -REACH / 2, -REACH / 2))
    return sph.intersect(keep).translate(S_CART)

# ---------------- Poses ----------------
D1_C, CELL_C = store_to_cart(*D1_W), store_to_cart(*CELL_W)
POSE_PICK = solve_pose(D1_C)
POSE_CELL = solve_pose(CELL_C, True, 120.0)   # ASSUMED: gripper leaned 30 deg past square so the wrist clears the battery

# Stowed: pan so the arm plane runs along the pipe (arm X = cart +Z, pan 0); upper arm lies along +arm X
# (a1 = 90), forearm folded back (a2 = 270), gripper folded forward (a3 = 90), in three lanes.
STOW = dict(pan=0.0, a1=90.0, a2=270.0, a3=90.0, lane=(0.0, 26.0, 52.0))
# the arm plane lanes extend to the arm +Y side = cart -X side, towards the battery side of the plate

# ---------------- Scenes ----------------
def build_board_and_cable(arm_cable_pts):
    arm_cable = polyline([(board_c[0] + BOARD[0] / 2, board_c[1], board_c[2])] + [p for p in arm_cable_pts], 2.0)
    return arm_cable, polyline(power_pts, 2.0), polyline(usb_pts, 2.0)

def add_arm(assy, tag, pose, color_override=None, labelled=True, prefix=""):
    parts, joints, cable, tip = build_arm(*pose[:4]) if isinstance(pose, tuple) else build_arm(**pose)
    for name, wp in parts.items():
        col = (0.88, 0.88, 0.9, 1)
        if name.startswith("servo_") and name[6] in COL:
            col = COL[name[6]]
        if name.startswith("joint_"):
            col = (0.12, 0.12, 0.12, 1)
        if color_override and not name.startswith("joint_"):
            col = color_override
        assy.add(wp, name="%s%s_%s" % (prefix, tag, name), color=cq.Color(*col))
    return joints, cable, tip

def scene(working=True):
    assy = cq.Assembly()
    for name, obj, col in cart:
        assy.add(obj, name=name, color=cq.Color(*col))
    assy.add(foam, name="board_foam_pads", color=cq.Color(0.8, 0.8, 0.8, 1))
    assy.add(board, name="waveshare_board", color=cq.Color(0.1, 0.5, 0.25, 1))
    info = {}
    if working:
        joints, cable, tip = add_arm(assy, "arm_pick_D1", POSE_PICK)
        j2, cable2, tip2 = add_arm(assy, "arm_cell_A2", POSE_CELL, color_override=(0.6, 0.8, 0.95, 1), prefix="ghost_")
        info = dict(joints=joints, tip=tip, tip2=tip2, joints2=j2)
        arm_cable, power, usb = build_board_and_cable(cable)
        assy.add(lid_patch(), name="store_lid_patch", color=cq.Color(0.6, 0.6, 0.65, 0.5))
        assy.add(seed_tray(), name="seedling_tray", color=cq.Color(0.3, 0.7, 0.4, 1))
        pod, seedling = targets()
        assy.add(pod, name="pod_D1", color=cq.Color(0.9, 0.2, 0.2, 1))
        assy.add(seedling, name="seedling_A2", color=cq.Color(0.2, 0.6, 0.2, 1))
        r1, r2, r3 = reach_rings()
        assy.add(r1, name="reach_ring_across", color=cq.Color(0.95, 0.4, 0.4, 1))
        assy.add(r2, name="reach_ring_towards_store", color=cq.Color(0.95, 0.4, 0.4, 1))
        assy.add(r3, name="reach_ring_on_lid", color=cq.Color(0.95, 0.4, 0.4, 1))
        assy.add(reach_dome(), name="reach_envelope", color=cq.Color(0.95, 0.4, 0.4, 0.15))
    else:
        joints, cable, tip = add_arm(assy, "arm_stowed", STOW)
        info = dict(joints=joints, tip=tip)
        arm_cable, power, usb = build_board_and_cable(cable)
    assy.add(arm_cable, name="cable_servo_bus", color=cq.Color(0.05, 0.05, 0.05, 1))
    assy.add(power, name="cable_12V", color=cq.Color(0.8, 0.1, 0.1, 1))
    assy.add(usb, name="cable_usb", color=cq.Color(0.3, 0.3, 0.9, 1))
    return assy, info

result, INFO = scene(True)
result_stowed, INFO_STOWED = scene(False)

def outline_parts(assy):
    """Parts that go into the black-and-white drawings (the translucent dome is left out)."""
    out = cq.Assembly()
    for ch in assy.children:
        if ch.name != "reach_envelope":
            out.add(ch.obj, name=ch.name, loc=ch.loc, color=ch.color)
    return out

if __name__ == "__main__":
    for tag, pose, tgt in (("D1 pick hole", POSE_PICK, D1_C), ("cell A2", POSE_CELL, CELL_C)):
        pan, a1, a2, a3, d = pose
        print("%s: pan %.0f, shoulder %.0f, elbow %.0f deg from the arm axis; wrist %.0f mm from shoulder"
              % (tag, pan, a1, a2, d))
    for tag, tgt in (("D1", D1_C), ("A2", CELL_C)):
        d = math.dist(tgt, S_CART)
        print("%s: %.0f mm from the shoulder vs reach %.0f" % (tag, d, REACH))
    print("lid-plane reach footprint radius %.0f mm (shoulder %.0f above the lid)" % (LID_R, S_CART[2] - LID_PLANE_Z))
    for name, a in (("working", result), ("stowed", result_stowed)):
        bb = a.toCompound().BoundingBox()
        print("cart_arm %s OK, bbox %.0f x %.0f x %.0f mm" % (name, bb.xlen, bb.ylen, bb.zlen))
