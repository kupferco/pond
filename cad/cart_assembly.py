# cad/cart_assembly.py: whole Pond robot cart, assembled (DRAFT, 10 Nov 2026).
# Drawing 1 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable assembly drawing to show how the parts relate.
#
# Frame: the hand_sleeve.py frame. Track pipe runs along Z (a vertical side of the loop), the cart's
# mounting pads face -Y, so the cart base plate and everything on it sits on the -Y side of the pipe.
#
# DECIDED (from cad/hand_sleeve.py v4.1 and the decision docs): 90 mm sleeves, outer R 34, pipe OD 32,
# two wheel rows 60 mm apart, six wheels per hand (driven wheel at 180 deg, spring idlers at +/-60 deg),
# C-gap with funnel on +X, M4 pad on -Y, worm-gear drive so a hand holds when stopped,
# two hands + base + battery + SO-101 follower arm.
#
# ASSUMPTIONS (all marked "ASSUMED" below):
#  1. Hand spacing: hands 220 mm apart centre to centre along the pipe.
#  2. Base plate (v2): open frame, 100 x 332 x 6 mm outline, bolted to both pads (M4 pattern from
#     hand_sleeve.py). 10 mm rim, 36 mm wide bosses round each hand's holes, an 84 mm block under the arm
#     and cross bars between; everything else is cut out as large windows.
#  3. Battery: 70 (along pipe) x 70 (across) x 50 (out from plate) mm block, between the arm and Hand B,
#     resting on the frame's cross bars (v2: narrowed from 80 and moved to make room for the centred arm).
#  4. Drive motors: one worm-gear motor per hand, on the plate beside the hand, shaft along the pipe,
#     as a 28 mm diameter x 55 mm placeholder cylinder. Motor positions are an open roadmap item;
#     power transmission from motor to the driven wheel is not drawn.
#  5. Arm mount (v2): SO-101 base in the middle of the plate (centre of the frame, midway between the
#     hands), arm shown folded over the cart (counterweight idea from the 31 Oct decisions).
#  6. SO-101 arm is an envelope only (boxes sized from cad/so101_servo_layout.py), not real parts.
#  7. Track pipe OD 32 mm (assumed in hand_sleeve.py too). The pipe is shown as a 330 mm stub.
#  8. Both hands are identical and face the same way (no 90 deg swivel between Hand B and the base yet).
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs   # reused, not redrawn; importing runs the model and exposes hs.result and dims

# ---------------- Layout (mm) ----------------
# Shared with cart_base.py: the numbers live in cart_layout.py (all ASSUMED values are marked there).
from cart_layout import *   # noqa: F401,F403
import cart_base
PIPE_STUB_L = 330.0                     # ASSUMED

def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

def zshift(shape, z):
    return shape.translate((0, 0, z))


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

pipe = cyl(hs.R_PIPE, PIPE_STUB_L, "z", (0, 0, 0))

plate = cart_base.base   # the base plate frame, drawn in cart_base.py (drawing 2)

battery = box(BATT[0], BATT[1], BATT[2], (BATT_X, PLATE_Y0 - BATT[1] / 2, BATT_Z))

motors = None
for hz in (HAND_Z, -HAND_Z):
    m = cyl(MOTOR_R, MOTOR_L, "z", (MOTOR_X, PLATE_Y0 - MOTOR_R, hz))
    gearbox = box(26, 2 * MOTOR_R, 20, (MOTOR_X, PLATE_Y0 - MOTOR_R, hz + math.copysign(MOTOR_L / 2 + 10, hz)))  # gearbox on the outer end
    m = m.union(gearbox)
    motors = m if motors is None else motors.union(m)

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

add(pipe, "track_pipe", (0.75, 0.78, 0.8, 1))
add(plate, "base_plate", (0.35, 0.35, 0.38, 1))
for tag, hz in (("A", HAND_Z), ("B", -HAND_Z)):
    add(zshift(hs.result, hz), "hand_%s_sleeve" % tag, (0.95, 0.75, 0.2, 1))
    add(zshift(WHEELS, hz), "hand_%s_wheels" % tag, (0.15, 0.15, 0.15, 1))
add(battery, "battery", (0.2, 0.45, 0.85, 1))
add(motors, "drive_motors", (0.85, 0.25, 0.25, 1))
add(arm, "so101_arm_envelope", (0.88, 0.88, 0.9, 1))

result = assy

if __name__ == "__main__":
    comp = assy.toCompound()
    bb = comp.BoundingBox()
    print("cart_assembly OK, bbox %.0f x %.0f x %.0f mm" % (bb.xlen, bb.ylen, bb.zlen))
