# cad/cart_assembly.py: whole Pond robot cart, assembled (DRAFT v3, 11 Nov 2026).
# Drawing 1 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable assembly drawing to show how the parts relate.
#
# v3 (Viber #66): design correction. The two hands do NOT clamp the same pipe. Each hand clamps a different
# pipe: two parallel pipes side by side (pipe B and pipe C, one from each of two neighbouring units), the base
# plate runs across between them and the SO-101 arm sits at the plate centre. Shared numbers (pipe spacing,
# plate, battery, motors, arm position) live in cart_dims.py, also used by cart_arm.py and cart_sleeves.py.
#
# Frame: the hand_sleeve.py frame. Track pipes run along Z (vertical sides of the loop), the cart's
# mounting pads face -Y, so the cart base plate and everything on it sits on the -Y side of the pipes.
# Pipe B at x = -140, pipe C at x = +140.
#
# DECIDED (from cad/hand_sleeve.py v4.1 and the decision docs): 90 mm sleeves, outer R 34, pipe OD 32,
# two wheel rows 60 mm apart, six wheels per hand (driven wheel at 180 deg, spring idlers at +/-60 deg),
# C-gap with funnel on +X, M4 pad on -Y, worm-gear drive so a hand holds when stopped,
# two hands + base + battery + SO-101 follower arm.
#
# ASSUMPTIONS (all marked "ASSUMED" in cart_dims.py or below):
#  1. Pipe spacing: 280 mm, centre to centre (the real spacing between neighbouring units is not decided).
#     One hand per pipe, both facing the same way (no 90 deg swivel yet).
#  2. Base plate: open frame, 112 (Z) x 380 (X) x 6 mm, bolted to both pads (M4 pattern from hand_sleeve.py).
#     10 mm rim, 36 mm wide bosses round each hand's holes, an 84 mm block under the arm; the rest is cut out.
#  3. Battery: 70 (X) x 50 (out from plate) x 70 (Z) mm block, between the arm block and pipe C's hand.
#  4. Drive motors: one worm-gear motor per hand, on the plate beside the hand (+X of each pipe), shaft along
#     the pipe, 28 mm diameter x 55 mm placeholder cylinder with a gearbox block. Positions are an open
#     roadmap item; power transmission from motor to the driven wheel is not drawn.
#  5. Arm mount: SO-101 base on the plate centre (x = -12, midway between the pads), arm shown folded over
#     the cart (counterweight idea from the 31 Oct decisions).
#  6. SO-101 arm is an envelope only (boxes sized from cad/so101_servo_layout.py), not real parts.
#  7. Track pipe OD 32 mm (assumed in hand_sleeve.py too). Each pipe is shown as a 330 mm stub.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs   # reused, not redrawn; importing runs the model and exposes hs.result and dims

# ---------------- Layout (mm): all shared numbers come from cart_dims.py ----------------
from cart_dims import *   # noqa: F401,F403  (PIPE_SPACING, HX, PLATE_*, BATT*, MOTOR_*, ARM_*, PIPE_STUB_L, ...)
PLATE_CY = (PLATE_Y0 + PLATE_Y1) / 2

def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

pad_cx = (hs.PAD_X0 + hs.PAD_X1) / 2

# ---------------- Parts ----------------
def hand_wheels():
    """The 12 wheels of one hand (6 per ring pair), sitting in the pockets of hs.result."""
    w = None
    for z in (hs.RING_Z, -hs.RING_Z):
        for ang in (hs.OUTER_WHEEL_ANG,) + tuple(hs.INNER_WHEEL_ANGS):
            wheel = cyl(hs.WHEEL_R, hs.WHEEL_W, "y", (hs.AXLE_R_POS, 0, z))
            wheel = wheel.rotate((0, 0, 0), (0, 0, 1), ang)
            w = wheel if w is None else w.union(wheel)
    return w

WHEELS = hand_wheels()

def xshift(shape, x):
    return shape.translate((x, 0, 0))

def window(x0, x1, z0, z1):
    return box(x1 - x0, PLATE_T + 2, z1 - z0, ((x0 + x1) / 2, PLATE_CY, (z0 + z1) / 2))

def build_plate():
    """Open-frame plate across both pipes: rim, a boss round each hand's M4 holes, an arm block, big windows."""
    plate = box(PLATE_X1 - PLATE_X0, PLATE_T, 2 * PLATE_ZH, ((PLATE_X0 + PLATE_X1) / 2, PLATE_CY, 0))
    ZE = PLATE_ZH - RIM
    for sgn in (1, -1):
        bc = sgn * HX + pad_cx                              # boss centre x (pad centre of that hand)
        inner = ARM_X + sgn * ARM_BLOCK_HX
        outer_end = (PLATE_X1 - RIM) if sgn > 0 else (PLATE_X0 + RIM)
        for xa, xb in ((inner, bc - sgn * BOSS_HX), (bc + sgn * BOSS_HX, outer_end)):
            plate = plate.cut(window(min(xa, xb), max(xa, xb), -ZE, ZE))
        for za, zb in ((BOSS_HZ, ZE), (-ZE, -BOSS_HZ)):     # windows above and below each boss
            plate = plate.cut(window(bc - BOSS_HX, bc + BOSS_HX, za, zb))
        for dz in (hs.PAD_HOLE_Z, -hs.PAD_HOLE_Z):          # M4 holes matching the pad
            plate = plate.cut(cyl(hs.PAD_HOLE_D / 2, PLATE_T + 2, "y", (bc, PLATE_CY, dz)))
    return plate

def build_motors():
    motors = None
    for sgn in (1, -1):
        mx = sgn * HX + MOTOR_DX
        m = cyl(MOTOR_R, MOTOR_L, "z", (mx, PLATE_Y0 - MOTOR_R, 0.0))
        m = m.union(box(26, 2 * MOTOR_R, 20, (mx, PLATE_Y0 - MOTOR_R, MOTOR_L / 2 + 10)))   # gearbox up (ASSUMED)
        motors = m if motors is None else motors.union(m)
    return motors

plate = build_plate()
battery = box(BATT[0], BATT[1], BATT[2], (BATT_X, PLATE_Y0 - BATT[1] / 2, 0.0))
motors = build_motors()

def arm_envelope():
    """Simplified SO-101 envelope in the arm frame (Z up, X forward), folded over the cart.
    Sizes follow cad/so101_servo_layout.py. Returned in cart coordinates."""
    parts = []
    parts.append(box(70, 70, 8, (0, 0, 4)))              # arm base plate (ASSUMED footprint)
    parts.append(box(45, 24, 35, (0, 0, 26)))            # servo 1, base rotation
    parts.append(box(50, 40, 30, (0, 0, 60)))            # shoulder bracket
    parts.append(box(45, 35, 24, (0, 0, 88)))            # servo 2, shoulder
    parts.append(box(30, 20, 115, (0, 0, 150)))          # upper arm, vertical
    parts.append(box(45, 35, 24, (0, 0, 212)))           # servo 3, elbow
    parts.append(box(135, 20, 25, (60, 0, 224)))         # forearm, folded forward over the cart
    parts.append(box(24, 35, 45, (130, 0, 224)))         # servo 4, wrist flex
    parts.append(box(35, 24, 45, (160, 0, 224)))         # servo 5, wrist roll
    parts.append(box(45, 24, 35, (200, 0, 224)))         # servo 6, gripper
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    # arm frame -> cart frame: up (arm Z) -> -Y (out from plate), forward (arm X) -> +Z (along pipe)
    out = out.rotate((0, 0, 0), (0, 0, 1), 90)           # X -> Y
    out = out.rotate((0, 0, 0), (1, 0, 0), 90)           # Y -> Z, Z -> -Y
    return out.translate((ARM_X, PLATE_Y0, ARM_Z))

arm = arm_envelope()

# ---------------- Assembly ----------------
assy = cq.Assembly()
def add(obj, name, color):
    assy.add(obj, name=name, color=cq.Color(*color))

add(plate, "base_plate", (0.35, 0.35, 0.38, 1))
for tag, sgn in (("C", 1), ("B", -1)):
    add(xshift(cyl(hs.R_PIPE, PIPE_STUB_L, "z", (0, 0, 0)), sgn * HX), "track_pipe_%s" % tag, (0.75, 0.78, 0.8, 1))
    add(xshift(hs.result, sgn * HX), "hand_on_pipe_%s_sleeve" % tag, (0.95, 0.75, 0.2, 1))
    add(xshift(WHEELS, sgn * HX), "hand_on_pipe_%s_wheels" % tag, (0.15, 0.15, 0.15, 1))
add(battery, "battery", (0.2, 0.45, 0.85, 1))
add(motors, "drive_motors", (0.85, 0.25, 0.25, 1))
add(arm, "so101_arm_envelope", (0.88, 0.88, 0.9, 1))

result = assy

if __name__ == "__main__":
    comp = assy.toCompound()
    bb = comp.BoundingBox()
    print("cart_assembly OK, bbox %.0f x %.0f x %.0f mm" % (bb.xlen, bb.ylen, bb.zlen))
