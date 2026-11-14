# cad/cart_base.py: Pond cart BASE plate hung on a hinge at each hand (DRAFT v2, 14 Nov 2026, Viber #97).
# Drawing 2 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable drawing of the plate, its hinges, rotation servos and where the parts sit.
#
# DRAFT v2 (14 Nov 2026), changes from v1 (11 Nov):
#   - Pipes 120 mm apart (was 280): neighbouring units' pipes B and C, tanks touching, pipes 60 mm in from the tank
#     edge (unit drawings TX 250 -> 290). Spacing set in cart_dims.py, with the budget that limits it (see there).
#   - HINGE on each hand: on the sleeve's pad edge, axis parallel to the pipe. Sleeve leaf + 2 knuckles on the
#     sleeve, plate leaf + 1 knuckle on the plate, 4 mm pin, countersunk M4 screws to the pad (2) and to the plate
#     (2). The sleeve stays clamped on the pipe; the plate swings out to -Y like a door. Hand B's hinge is on the
#     pad's -X edge, hand C's on its +X edge, so the plate hangs BETWEEN the two hinge axes. Parts: cart_hinge.py.
#   - ROTATION SERVO per hand, bolted to the plate (in a window of a tongue above the plate), output on the hinge
#     axis, horn bolted to the top sleeve knuckle: it turns the plate against the sleeve. Nothing round the pipe.
#   - The plate is now 142 x 112 x 6 mm, solid: there is no room left to open frames up. The arm base (70) and the
#     two drive motors (28 each) are in a row on it; the battery moved ABOVE the arm on a shelf tongue; the
#     Waveshare board moved onto the battery's front face (cart_arm.py).
#
# KNOWN OPEN POINT (kinematics): with ONE rigid plate and two hinges whose axes are 120 + 36 - ... mm apart (not
# the same line), the plate cannot swing while BOTH hands are clamped on their parallel pipes: the two hinge axes
# are not coaxial, so the plate is locked. It can swing only with one hand released from its pipe, or if the plate
# is split into two half-doors (one per hand) that meet at a latch. Decide before the transfer scene (#81).
#
# Frame: hand_sleeve.py (pipes along Z, plate on the -Y side of the pads). Plate outline, hand positions, pipe
# spacing, battery, motor and arm positions come from cart_dims.py, not redefined here.
#
# ASSUMED (nothing below is decided; all marked "ASSUMED" in the code):
#  1. Pipe spacing 120 mm, pipe B to pipe C (cart_dims.py; limited by arm 70 + two 28 mm motors on the plate).
#  2. Plate 142 (X) x 112 (Z) x 6 mm solid (aluminium or steel not chosen), shown as a single solid, with a
#     notch at each hinge end for the servo horn, a battery shelf tongue and two servo tongues above the top edge.
#  3. Hinge and servo sizes: listed in cart_hinge.py (barrel 10 mm, pin 4 mm, leaves 3 mm, servo 45.2 x 24.7 x 35.5).
#  4. Arm mount: four M4 holes on a 50 mm square plus a 20 mm cable hole, at x = -12 (SO-101 base footprint 70 x 70;
#     the real SO-101 base hole pattern is to confirm).
#  5. Battery 70 x 50 x 70 mm on the shelf tongue above the arm: four corner stops, two strap slots, 20 mm strap.
#     Real battery size and fixing not decided.
#  6. Drive motors: one per hand, 28 x 55 mm, gearbox up, on the plate at x = -65 and +41 (between the hinge
#     barrels and the arm), each in two saddles with M3 clamp holes. Real motor and clamp not decided. The
#     transmission from motor to the driven wheels is not drawn (see cart_sleeves.py: worm shaft).
#  7. Cable routing: the 12 V lead, motor leads and USB lead use 3 x 8 mm tie slots in the plate's top and bottom
#     10 mm band; the servo bus goes up through the 20 mm arm hole. Cable lengths and strain relief not designed.
#  8. Cart height: plate centre at the arm shoulder level used by cart_arm.py (pipes end 70 below it).
# Not drawn: drive transmission, wheel pairs, board bracket (board now velcro-ed to the battery), servo wiring
# and the gear stage the hinge servo would need to lift the plate with arm and battery on it.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs
import cart_assembly as ca
import cart_arm as arm            # shared layout numbers; importing builds the arm drawing too
import cart_hinge as ch

# ---------------- Shared layout (imported) ----------------
from cart_dims import (PIPE_SPACING, HX, PLATE_X0, PLATE_X1, PLATE_ZH, PLATE_T, PLATE_Y0, PLATE_Y1,
                       ARM_X, ARM_Z, BATT, MOTOR_R, MOTOR_L, MOTOR_XS, ARM_BLOCK_HX, RIM, BATT_X, BATT_Z)
PLATE_CY = ca.PLATE_CY
BATT_C = BATT_X
PIPE_Z0, PIPE_Z1 = arm.PIPE_Z0, arm.PIPE_Z1
box, cyl, fuse, xshift = arm.box, arm.cyl, arm.fuse, arm.xshift

# ---------------- Numbers added here (ASSUMED) ----------------
ARM_HOLE_SQ = 50.0        # ASSUMED: arm base M4 square
ARM_HOLE_D = 4.3
ARM_CABLE_D = 20.0        # ASSUMED: servo bus pass-through
BATT_STOP_H, BATT_STOP_T = 18.0, 3.0  # corner stops: 18 out from the plate, 3 thick
STRAP_SLOT = (3.0, 20.0)  # ASSUMED strap slot: 3 along Z, 20 across X
MOTOR_BAR_Z, MOTOR_BAR_W = 20.0, 8.0  # ASSUMED motor saddle bars at z = +/-20
SADDLE_W = 28.0           # saddle width in X (= motor diameter)
M3_D = 3.4
TIE_SLOT = (8.0, 3.0)     # ASSUMED cable-tie slot: 8 along X, 3 along Z

# ---------------- Plate ----------------
def hole(d, x, z, y=PLATE_CY, depth=PLATE_T + 2):
    return cyl(d / 2, depth, "y", (x, y, z))

def slot(w, l, x, z):                       # rectangular slot through the plate, w along X, l along Z
    return box(w, PLATE_T + 2, l, (x, PLATE_CY, z))

def build_plate():
    p = ca.plate                            # solid plate + battery shelf + servo tongues + horn notches (cart_assembly.py)
    # ---- arm mount (centre) ----
    h = ARM_HOLE_SQ / 2
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = p.cut(hole(ARM_HOLE_D, ARM_X + sx * h, ARM_Z + sz * h))
    p = p.cut(hole(ARM_CABLE_D, ARM_X, ARM_Z))
    # ---- hinge: two M4 holes per hand for the plate-leaf screws (countersunk on the plate's front face) ----
    for sgn in (-1, 1):
        xh, d = ca.hinge_x(sgn), -sgn
        for dz in (ch.PLATE_SCREW_DZ, -ch.PLATE_SCREW_DZ):
            p = p.cut(hole(ARM_HOLE_D, xh + d * ch.PLATE_SCREW_DX, dz)).cut(ch.csk_cut(xh + d * ch.PLATE_SCREW_DX, PLATE_Y0, dz))
    # ---- servo tongue ear screws (M3 through the frame) ----
    for ex, z in ch.tongue_holes():
        p = p.cut(hole(M3_D, ex, z))
    # ---- battery shelf: strap slots either side of the battery ----
    for dz in (-BATT[2] / 4, BATT[2] / 4):
        for dx in (-22.0, 22.0):
            p = p.cut(slot(STRAP_SLOT[1] / 2, STRAP_SLOT[0], BATT_C + dx, BATT_Z + dz))
    # ---- drive motors: saddle M3 clamp holes beside each motor are cut in saddles() ----
    # ---- cable routing: tie slots in the top band (motor leads, USB) and bottom band (12 V lead) ----
    zr = PLATE_ZH - RIM / 2
    for x in (ARM_X - 10.0, ARM_X + 10.0):                                  # 12 V lead, bottom band
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (x, PLATE_CY, -zr)))
    for sgn in (-1, 1):                                                     # motor leads, top band, by each motor
        mx = MOTOR_XS[sgn]
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (mx - 8.0, PLATE_CY, zr - 4.0)))
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (mx + 8.0, PLATE_CY, zr - 4.0)))
    return p

plate = build_plate()

# ---------------- Things bolted on the plate ----------------
def corner_stops():
    out = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = (BATT_C + sx * (BATT[0] / 2 + BATT_STOP_T / 2), PLATE_Y0 - BATT_STOP_H / 2, BATT_Z + sz * (BATT[2] / 2 - 6.0))
            out.append(box(BATT_STOP_T, BATT_STOP_H, 12.0, c))
    return fuse(out)
batt_stops = corner_stops()
battery = box(BATT[0], BATT[1], BATT[2], (BATT_C, PLATE_Y0 - BATT[1] / 2, BATT_Z))

def saddles():
    out = []
    for sgn in (-1, 1):
        mx = MOTOR_XS[sgn]
        for sz in (-1, 1):
            s = box(SADDLE_W, MOTOR_R, MOTOR_BAR_W, (mx, PLATE_Y0 - MOTOR_R / 2, sz * MOTOR_BAR_Z))
            cradle = cyl(MOTOR_R, 2 * MOTOR_BAR_W, "z", (mx, PLATE_Y0 - MOTOR_R, sz * MOTOR_BAR_Z))
            s = s.cut(cradle)
            for dx in (-MOTOR_R + 1.5, MOTOR_R - 1.5):                      # M3 clamp holes beside the cradle
                s = s.cut(cyl(M3_D / 2, MOTOR_R + 2, "y", (mx + dx, PLATE_Y0 - MOTOR_R / 2, sz * MOTOR_BAR_Z)))
            out.append(s)
    return fuse(out)
motor_saddles = saddles()
motors = arm.motors

# cable runs (drawn as 4 mm round runs like cart_arm.py): 12 V board -> battery, motor leads to the top rim, USB
def cable_runs():
    p12 = arm.polyline(arm.power_pts, 2.0)
    leads = []
    for sgn in (-1, 1):
        mx = MOTOR_XS[sgn]
        top = PLATE_ZH - RIM / 2
        leads.append(arm.polyline([(mx - 8.0, PLATE_Y0 - 2.0, MOTOR_L / 2 + 10.0),
                                   (mx - 8.0, PLATE_Y0 - 2.0, top - 4.0)], 1.5))
    bus = arm.polyline([(ARM_X, PLATE_Y0 - 2.0, ARM_Z), (arm.board_c[0] + arm.BOARD[0] / 2, arm.board_c[1], arm.board_c[2])], 2.0)
    usb = arm.polyline(arm.usb_pts, 2.0)
    return p12, fuse(leads), bus, usb

# ---------------- Assembly ----------------
def build(show_context=True):
    assy = cq.Assembly()
    add = lambda o, n, c: assy.add(o, name=n, color=cq.Color(*c))
    add(plate, "base_plate", (0.35, 0.35, 0.38, 1))
    add(batt_stops, "battery_corner_stops", (0.35, 0.35, 0.38, 1))
    add(motor_saddles, "motor_saddles", (0.35, 0.35, 0.38, 1))
    add(battery, "battery", (0.2, 0.45, 0.85, 1))
    add(motors, "drive_motors", (0.85, 0.25, 0.25, 1))
    # arm base footprint on the plate (the arm itself is drawn in cart_arm.py)
    add(arm.to_cart(box(70, 70, 8, (0, 0, 4))), "arm_base_footprint", (0.88, 0.88, 0.9, 1))
    if show_context:
        for tag, sgn in (("pipe_C", 1), ("pipe_B", -1)):
            add(xshift(cyl(hs.R_PIPE, PIPE_Z1 - PIPE_Z0, "z", (0, 0, (PIPE_Z0 + PIPE_Z1) / 2)), sgn * HX),
                "track_%s" % tag, (0.75, 0.78, 0.8, 1))
            add(xshift(hs.result, sgn * HX), "hand_on_%s_sleeve" % tag, (0.95, 0.75, 0.2, 1))
            add(xshift(ca.WHEELS, sgn * HX), "hand_on_%s_wheels" % tag, (0.15, 0.15, 0.15, 1))
    for tag, sgn in (("pipe_C", 1), ("pipe_B", -1)):      # the hinge and its rotation servo are the point of v2: always shown
        for nm, shp, col in ch.hinge_parts(sgn):
            add(shp, "hinge_%s_%s" % (tag, nm), col)
    add(arm.foam, "board_foam_pads", (0.8, 0.8, 0.8, 1))
    add(arm.board, "waveshare_board", (0.1, 0.5, 0.25, 1))
    p12, leads, bus, usb = cable_runs()
    add(p12, "cable_12V", (0.8, 0.1, 0.1, 1))
    add(leads, "cable_motor_leads", (0.8, 0.1, 0.1, 1))
    add(bus, "cable_servo_bus", (0.05, 0.05, 0.05, 1))
    add(usb, "cable_usb", (0.3, 0.3, 0.9, 1))
    return assy

result = build()

if __name__ == "__main__":
    bb = plate.val().BoundingBox()
    print("plate %.0f x %.0f x %.0f mm (X x Y x Z), pipes %.0f mm apart" % (bb.xlen, bb.ylen, bb.zlen, PIPE_SPACING))
    print("cart_base OK, bbox %.0f x %.0f x %.0f mm"
          % tuple(getattr(result.toCompound().BoundingBox(), k) for k in ("xlen", "ylen", "zlen")))
