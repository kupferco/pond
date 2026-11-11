# cad/cart_base.py: Pond robot cart BASE on its own (DRAFT, 11 Nov 2026).
# Drawing 2 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable drawing of the base frame and everything that mounts to it.
#
# Frame: the hand_sleeve.py frame. Track pipe runs along Z, the hands' M4 pads face -Y, the base plate
# sits on the pads' -Y face and everything else hangs further out (-Y). Outline dimensions, hand spacing,
# battery, motor and arm positions come from cad/cart_layout.py, shared with cart_assembly.py.
#
# DECIDED (from hand_sleeve.py v4.1): M4 pad pattern (2 holes, 30 mm apart along the pipe, 4.3 mm clearance,
# on the pad centre x = -12), worm-gear drive per hand, two hands + base + battery + SO-101 arm.
#
# ASSUMED (each is also marked "ASSUMED" where it is set; the first group lives in cart_layout.py):
#  1. Hand spacing 220 mm; plate 100 x 332 x 6 mm; open-frame cut-outs (10 mm rim, 36 mm bosses).
#  2. Battery 70 x 50 x 70 mm at x = -27, z = -75 (between the arm and Hand B).
#  3. Drive motor: 28 mm dia x 55 mm worm-gear motor with a 26 x 28 x 20 mm gearbox on the outer end,
#     axis along the pipe, at x = 24, one per hand. Motor-to-wheel transmission is not drawn.
#  4. Arm mount at the plate centre (x = -12, z = 0).
#  5. SO-101 base bolt pattern: 4 x M4 on a 50 x 50 mm square (the real pattern is not checked yet).
#  6. Battery cradle: 3 mm walls, 12 mm high, on the two ends and the +X side of the footprint is left open;
#     two strap slots (4 x 20 mm) per end wall. Real battery case is not chosen.
#  7. Motor clamps: two 7 mm rings per motor (bore 28 mm, 3 mm wall), one M3 grub screw each. Wall overhangs
#     the plate edge by 3 mm on +X.
#  8. Cable routing: 3 x 8 mm zip-tie slots through the -X rim (z = +/-20, 62, 100, 145) and the +X rim
#     (z = +/-62); 12 mm cable notches in the battery end walls; 8 mm lead hole in the arm block. Which
#     cables exist (motor, battery, arm USB, dock brushes) is not decided.
#  9. Frame webs: 12 mm wide on the pad centre line, joining each hand boss to the arm block and end rim
#     (v2 in cart_assembly.py left the bosses floating; fixed here, cart_assembly follows).
# 10. Plate thickness 6 mm in a printed plastic; no material or print orientation chosen.
# 11. Hand pads and mounting holes sit on the plate centre line of the hand (shared via hand_sleeve.py).
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs
from cart_layout import *   # noqa: F401,F403  (HAND_Z, PLATE_*, BATT*, MOTOR*, ARM_*, RIM, BOSS_*, ...)

# ---------------- Features (mm), all ASSUMED unless noted ----------------
WEB_W = 12.0                  # ASSUMED: web joining each hand boss to the arm block and the end rim
ARM_BOLT_SQ = 50.0            # ASSUMED: SO-101 base 4 x M4 square pattern
ARM_BOLT_D = 4.3              # M4 clearance
ARM_LEAD_D = 8.0              # ASSUMED: arm lead (USB + power) hole in the arm block
CRADLE_WALL, CRADLE_H = 3.0, 12.0     # ASSUMED
STRAP_SLOT = (20.0, 4.0)      # ASSUMED: X length, Y height of battery strap slots
NOTCH_W = 12.0                # ASSUMED: cable notch width in cradle end walls
CLAMP_T, CLAMP_WALL = 7.0, 3.0        # ASSUMED motor clamp ring thickness (along pipe) and wall
CLAMP_Z = (134.0, 122.0)      # ASSUMED: |z| of the two clamp ring centres per motor
GRUB_D = 3.2                  # ASSUMED: M3 grub screw clearance
TIE_SLOT = (3.0, 8.0)         # ASSUMED: zip-tie slot X, Z
TIE_Z_NEG_X = (20.0, 62.0, 100.0, 145.0)   # ASSUMED, mirrored to +/-z
TIE_Z_POS_X = (62.0,)                       # ASSUMED, mirrored to +/-z

def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

def window(x0, x1, z0, z1):
    return box(x1 - x0, PLATE_T + 2, z1 - z0, ((x0 + x1) / 2, PLATE_CY, (z0 + z1) / 2))

def through_y(r, x, z):
    return cyl(r, PLATE_T + 2, "y", (x, PLATE_CY, z))

# ---------------- Plate frame (same open frame as cart_assembly v2) ----------------
plate = box(PLATE_W, PLATE_T, PLATE_L, (PLATE_X0 + PLATE_W / 2, PLATE_CY, 0))
XL, XR = PLATE_X0 + RIM, PLATE_X0 + PLATE_W - RIM
ZE = PLATE_L / 2 - RIM
for sgn in (1, -1):
    for za, zb in ((ARM_BLOCK_HL, HAND_Z - BOSS_HL), (HAND_Z + BOSS_HL, ZE)):
        lo, hi = sorted((sgn * za, sgn * zb))
        # a WEB_W wide web is left on the pad centre line so the hand bosses stay joined to the frame
        plate = plate.cut(window(XL, PAD_CX - WEB_W / 2, lo, hi)).cut(window(PAD_CX + WEB_W / 2, XR, lo, hi))
    lo, hi = sorted((sgn * (HAND_Z - BOSS_HL), sgn * (HAND_Z + BOSS_HL)))
    plate = plate.cut(window(XL, PAD_CX - BOSS_HW, lo, hi)).cut(window(PAD_CX + BOSS_HW, XR, lo, hi))

# Hand mounting points: M4 holes matching each hand's pad holes (hand_sleeve.py)
HAND_HOLES = [(PAD_CX, hz + dz) for hz in (HAND_Z, -HAND_Z) for dz in (hs.PAD_HOLE_Z, -hs.PAD_HOLE_Z)]
for x, z in HAND_HOLES:
    plate = plate.cut(through_y(hs.PAD_HOLE_D / 2, x, z))

# Arm mount: 4 x M4 on a square round the arm axis, and a lead hole
ARM_HOLES = [(ARM_X + sx * ARM_BOLT_SQ / 2, ARM_Z + sz * ARM_BOLT_SQ / 2) for sx in (1, -1) for sz in (1, -1)]
for x, z in ARM_HOLES:
    plate = plate.cut(through_y(ARM_BOLT_D / 2, x, z))
plate = plate.cut(through_y(ARM_LEAD_D / 2, ARM_X, ARM_Z))

# Cable routing: zip-tie slots through the rims
TIE_SLOTS = []
for z in TIE_Z_NEG_X:
    TIE_SLOTS += [(PLATE_X0 + RIM / 2, z), (PLATE_X0 + RIM / 2, -z)]
for z in TIE_Z_POS_X:
    TIE_SLOTS += [(PLATE_X0 + PLATE_W - RIM / 2, z), (PLATE_X0 + PLATE_W - RIM / 2, -z)]
for x, z in TIE_SLOTS:
    plate = plate.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (x, PLATE_CY, z)))

# ---------------- Battery cradle: end walls with strap slots and cable notches ----------------
bx0, bx1 = BATT_X - BATT[0] / 2, BATT_X + BATT[0] / 2
bz0, bz1 = BATT_Z - BATT[2] / 2, BATT_Z + BATT[2] / 2
cradle = None
for zc in (bz0 - CRADLE_WALL / 2, bz1 + CRADLE_WALL / 2):
    wall = box(BATT[0], CRADLE_H, CRADLE_WALL, (BATT_X, PLATE_Y0 - CRADLE_H / 2, zc))
    wall = wall.cut(box(STRAP_SLOT[0], STRAP_SLOT[1], CRADLE_WALL + 2, (BATT_X, PLATE_Y0 - CRADLE_H / 2 - 1, zc)))
    # cable notch from the free (outer) edge of the wall, at the +X end
    wall = wall.cut(box(NOTCH_W, 5, CRADLE_WALL + 2, (bx1 - NOTCH_W / 2 - 2, PLATE_Y0 - CRADLE_H + 2.5 - 0.01, zc)))
    cradle = wall if cradle is None else cradle.union(wall)

# ---------------- Drive motor clamps: closed rings the motor slides into ----------------
clamps = None
cy = PLATE_Y0 - MOTOR_R
for sgn in (1, -1):
    for zc in CLAMP_Z:
        ring = cyl(MOTOR_R + CLAMP_WALL, CLAMP_T, "z", (MOTOR_X, cy, sgn * zc))
        ring = ring.union(box(2 * (MOTOR_R + CLAMP_WALL), MOTOR_R, CLAMP_T, (MOTOR_X, PLATE_Y0 - MOTOR_R / 2, sgn * zc)))
        ring = ring.cut(cyl(MOTOR_R, CLAMP_T + 2, "z", (MOTOR_X, cy, sgn * zc)))
        ring = ring.cut(cyl(GRUB_D / 2, MOTOR_R + CLAMP_WALL + 1, "y",
                            (MOTOR_X, cy - (MOTOR_R + CLAMP_WALL) / 2 - MOTOR_R / 2 + 0.5, sgn * zc)))
        clamps = ring if clamps is None else clamps.union(ring)

base = plate.union(cradle).union(clamps)

# ---------------- Reference parts (not part of the base; for the drawing only) ----------------
battery = box(BATT[0], BATT[1], BATT[2], (BATT_X, PLATE_Y0 - BATT[1] / 2, BATT_Z))
motors = None
for hz in (HAND_Z, -HAND_Z):
    m = cyl(MOTOR_R, MOTOR_L, "z", (MOTOR_X, cy, hz))
    m = m.union(box(26, 2 * MOTOR_R, 20, (MOTOR_X, cy, hz + (1 if hz > 0 else -1) * (MOTOR_L / 2 + 10))))
    motors = m if motors is None else motors.union(m)
arm_base = box(70, 8, 70, (ARM_X, PLATE_Y0 - 4, ARM_Z))   # footprint of the SO-101 base (ASSUMED 70 x 70)

assy = cq.Assembly()
assy.add(base, name="cart_base", color=cq.Color(0.35, 0.35, 0.38, 1))
assy.add(battery, name="battery_ref", color=cq.Color(0.2, 0.45, 0.85, 1))
assy.add(motors, name="drive_motors_ref", color=cq.Color(0.85, 0.25, 0.25, 1))
assy.add(arm_base, name="arm_base_ref", color=cq.Color(0.88, 0.88, 0.9, 1))
result = assy

if __name__ == "__main__":
    bb = base.val().BoundingBox()
    print("cart_base OK, bbox %.0f x %.0f x %.0f mm, solids %d, valid %s" % (
        bb.xlen, bb.ylen, bb.zlen, len(base.val().Solids()), base.val().isValid()))
