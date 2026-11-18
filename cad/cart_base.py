# cad/cart_base.py: Pond cart BASE plate hung on a hinge at each hand (DRAFT v4, 15 Nov 2026, Viber #97 / #109).
#
# Pond #280: motor saddles and the plate-mounted motor drawing removed (motors are in the sleeves); the rest is as in #279.
# v4 (Viber #109 follow-up, decided by Dani): the battery is now UNDER the arm: stack plate | battery | SO-101 arm base. The
# battery shelf tongue above the arm is gone (the plate is a plain rectangle plus the two worm-bracket tongues). The four
# M4 holes on the 50 mm square now mount the battery (housing); the arm base bolts to the battery's front face. The strap
# slots and the 20 mm servo-bus hole are gone (the bus leaves over the battery's top edge to the board, which moved onto the
# battery's top face, cart_arm.py). The four corner stops stay and hold the battery sideways. Torque margin 1.66 (was 1.85).
# Drawing 2 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable drawing of the plate, its hinges, worm-gear rotation drives and where the parts sit.
#
# DRAFT v3 (14 Nov 2026), changes from v2 (same day):
#   - HINGE DRIVE: the direct-drive servo per hand is replaced by a WORM GEAR: brass wheel (module 1, 38 teeth) on the
#     hinge axis fixed to the sleeve, steel worm (single start, self-locking) in a bracket on a plate tongue, driven
#     by a 28 x 55 mm worm-gear motor, the same part as the hand drives. Ratio 38:1. Parts: cart_hinge.py.
#   - Rotation happens only during a transfer: one hand releases its pipe, the plate swings on the other hand's
#     hinge, one rigid plate (decided by Dani). This closes the kinematic open point of v2 (see below).
#   - The arm folds in close to the plate before rotating (folded pose ASSUMED in cart_dims.py).
#   - TORQUE BUDGET in cart_dims.py (torque_budget(), printed below by `python cart_base.py`): about 2.2 N m needed
#     at the hinge, 4.0 N m available, margin 1.85 (v4: 2.4 N m, margin 1.66, arm 50 mm further out). Every mass is ASSUMED. No spring needed.
#
# Changes of v2 from v1 (11 Nov):
#   - Pipes 120 mm apart (was 280): neighbouring units' pipes B and C, tanks touching, pipes 60 mm in from the tank
#     edge (unit drawings TX 250 -> 290). Spacing set in cart_dims.py, with the budget that limits it (see there).
#   - HINGE on each hand: on the sleeve's pad edge, axis parallel to the pipe. Sleeve leaf + 2 knuckles on the
#     sleeve, plate leaf + 1 knuckle on the plate, 4 mm pin, countersunk M4 screws to the pad (2) and to the plate
#     (2). The sleeve stays clamped on the pipe; the plate swings out to -Y like a door. Hand B's hinge is on the
#     pad's -X edge, hand C's on its +X edge, so the plate hangs BETWEEN the two hinge axes. Parts: cart_hinge.py.
#   - ROTATION SERVO per hand, bolted to the plate (in a window of a tongue above the plate), output on the hinge
#     axis, horn bolted to the top sleeve knuckle: it turns the plate against the sleeve. Nothing round the pipe.
#   - The plate is now 166 x 112 x 6 mm (mirrored hands, Pond #227; was 142), solid: there is no room left to open frames up. The arm base (70) and the
#     two drive motors (28 each) are in a row on it; the battery moved ABOVE the arm on a shelf tongue; the
#     Waveshare board moved onto the battery's front face (cart_arm.py). (Both superseded by v4 above.)
#
# SOLVED IN v3 (was: KNOWN OPEN POINT, kinematics): with ONE rigid plate and two hinges whose axes are 120 + 36 - ... mm apart (not
# the same line), the plate cannot swing while BOTH hands are clamped on their parallel pipes: the two hinge axes
# are not coaxial, so the plate is locked. It can swing only with one hand released from its pipe, or if the plate
# is split into two half-doors (one per hand) that meet at a latch. Decide before the transfer scene (#81).
#
# Frame: hand_sleeve.py (pipes along Z, plate on the -Y side of the pads). Plate outline, hand positions, pipe
# spacing, battery, motor and arm positions come from cart_dims.py, not redefined here.
#
# ASSUMED (nothing below is decided; all marked "ASSUMED" in the code):
#  1. Pipe spacing 120 mm, pipe B to pipe C (cart_dims.py; limited by arm 70 + two 28 mm motors on the plate).
#  2. Plate 166 (X) x 112 (Z) x 6 mm solid (aluminium or steel not chosen), shown as a single solid, with a
#     notch at each hinge end for the wheel flange, and two worm-bracket tongues above the top edge (no battery shelf since v4).
#  3. Hinge and worm drive sizes: listed in cart_hinge.py (barrel 10 mm, pin 4 mm, leaves 3 mm, M1 38T wheel, 10 mm worm).
#  4. Battery mount: four M4 holes on a 50 mm square at x = -12 (SO-101 base footprint 70 x 70, same as the battery;
#     the real SO-101 base hole pattern is to confirm); the arm base bolts on the battery, 50 mm out from the plate.
#  5. Battery 70 x 50 x 70 mm flat on the plate under the arm base: four corner stops.
#     Real battery size and fixing not decided.
#  6. (Pond #280) No motors on the plate: the drive and roll motors are in the sleeves (cart_omni.py), so the motor saddles are gone.
#  7. Cable routing: the 12 V lead, motor leads and USB lead use 3 x 8 mm tie slots in the plate's top and bottom
#     10 mm band; the servo bus leaves over the battery's top edge. Cable lengths and strain relief not designed.
#  8. Cart height: plate centre at the arm shoulder level used by cart_arm.py (pipes end 70 below it).
# Not drawn: drive transmission, wheel pairs, board bracket (board now on foam pads on the battery's top face), motor wiring,
# worm bearings and coupling, limit switches for the swing end positions.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs
import cart_assembly as ca
import cart_arm as arm            # shared layout numbers; importing builds the arm drawing too

# ---------------- Shared layout (imported) ----------------
from cart_dims import (PIPE_SPACING, HX, PLATE_X0, PLATE_X1, PLATE_ZH, PLATE_T, PLATE_Y0, PLATE_Y1,
                       ARM_X, ARM_Z, BATT, LEAD_SLOT_XS, ARM_BLOCK_HX, RIM, BATT_X, BATT_Z)
PLATE_CY = ca.PLATE_CY
BATT_C = BATT_X
PIPE_Z0, PIPE_Z1 = arm.PIPE_Z0, arm.PIPE_Z1
box, cyl, fuse, xshift = arm.box, arm.cyl, arm.fuse, arm.xshift

# ---------------- Numbers added here (ASSUMED) ----------------
ARM_HOLE_SQ = 50.0        # ASSUMED: arm base M4 square
ARM_HOLE_D = 4.3
BATT_STOP_H, BATT_STOP_T = 18.0, 3.0  # corner stops: 18 out from the plate, 3 thick
M3_D = 3.4
TIE_SLOT = (8.0, 3.0)     # ASSUMED cable-tie slot: 8 along X, 3 along Z

# ---------------- Plate ----------------
def hole(d, x, z, y=PLATE_CY, depth=PLATE_T + 2):
    return cyl(d / 2, depth, "y", (x, y, z))

def slot(w, l, x, z):                       # rectangular slot through the plate, w along X, l along Z
    return box(w, PLATE_T + 2, l, (x, PLATE_CY, z))

def build_plate():
    p = ca.plate                            # plain rigid plate with the pad bolt holes (cart_geom.py)
    # ---- battery mount (centre; v4: the battery sits on the plate, the arm base on the battery) ----
    h = ARM_HOLE_SQ / 2
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = p.cut(hole(ARM_HOLE_D, ARM_X + sx * h, ARM_Z + sz * h))
    # ---- the pad bolts (two M4 per hand, hs.PAD_HOLE_Z) are already cut in cart_geom.py; no hinge screws, no tongue holes ----
    # ---- cable routing: tie slots in the top band (motor leads, USB) and bottom band (12 V lead) ----
    zr = PLATE_ZH - RIM / 2
    for x in (ARM_X - 10.0, ARM_X + 10.0):                                  # 12 V lead, bottom band
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (x, PLATE_CY, -zr)))
    for mx in LEAD_SLOT_XS:                                                 # sleeve motor leads, top band, one pair above each hand's side
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


# cable runs (drawn as 4 mm round runs like cart_arm.py): 12 V board -> battery, motor leads to the top rim, USB
def cable_runs():
    p12 = arm.polyline(arm.power_pts, 2.0)
    leads = []
    for mx in LEAD_SLOT_XS:
        top = PLATE_ZH - RIM / 2
        leads.append(arm.polyline([(mx - 8.0, PLATE_Y0 - 2.0, 40.0),
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
    add(battery, "battery", (0.2, 0.45, 0.85, 1))
    # arm base footprint on the plate (the arm itself is drawn in cart_arm.py)
    add(arm.to_cart(box(70, 70, 8, (0, 0, 4))), "arm_base_footprint", (0.88, 0.88, 0.9, 1))
    if show_context:
        for tag, sgn in (("pipe_C", 1), ("pipe_B", -1)):
            add(xshift(cyl(hs.R_PIPE, PIPE_Z1 - PIPE_Z0, "z", (0, 0, (PIPE_Z0 + PIPE_Z1) / 2)), sgn * HX),
                "track_%s" % tag, (0.75, 0.78, 0.8, 1))
            for nm, shp, col in ca.clamp_hand_parts():     # clamp/jaw sleeve, clamped (cart_sleeves.py)
                add(ca.csl.place_hand(shp, sgn), "hand_on_%s_%s" % (tag, nm), col)
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
    import cart_dims as _cd
    _r = _cd.roll_budget()
    print("ROLL BUDGET (ASSUMED masses), whole base rolled round the static pipe, arm folded (cart_dims.py roll_budget()):")
    for n, m, r, tq in _r["rows"]:
        print("  %-36s %.2f kg at r %3.0f mm -> %.3f N m" % (n, m, r, tq))
    print("  required %.2f N m, motor %.2f N m (margin %.2f), friction hold %.2f N m (margin %.2f), 180 deg in %.1f s"
          % (_r["required_Nm"], _r["available_motor_Nm"], _r["margin_motor"], _r["hold_Nm"], _r["margin_hold"], _r["t180_s"]))
    bb = plate.val().BoundingBox()
    print("plate %.0f x %.0f x %.0f mm (X x Y x Z), pipes %.0f mm apart" % (bb.xlen, bb.ylen, bb.zlen, PIPE_SPACING))
    print("cart_base OK, bbox %.0f x %.0f x %.0f mm"
          % tuple(getattr(result.toCompound().BoundingBox(), k) for k in ("xlen", "ylen", "zlen")))
