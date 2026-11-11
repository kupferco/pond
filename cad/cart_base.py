# cad/cart_base.py: Pond cart BASE plate across two parallel pipes (DRAFT v1, 11 Nov 2026).
# Drawing 2 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Replaces the closed one-pipe base task (#62). Not production geometry: a readable drawing of the plate, its
# mounting points and where the parts sit.
#
# Layout (decided in the 11 Nov two-pipe design, spacing ASSUMED): the cart's two hands clamp two DIFFERENT
# parallel pipes side by side, pipe B and pipe C, one from each of two neighbouring units. The plate runs
# across between them (cart X), one hand sleeve bolted at each end (M4 pads of hand_sleeve.py), the SO-101 arm
# at the plate centre. Frame: hand_sleeve.py (pipes along Z, plate on the -Y side of the pads).
# Plate outline, hand positions, pipe spacing, battery, motor and arm positions are imported from
# cart_arm.py / cart_assembly.py, not redefined here.
#
# ASSUMED (nothing below is decided; all marked "ASSUMED" in the code):
#  1. Pipe spacing 280 mm, pipe B to pipe C (from cart_arm.py).
#  2. Plate 112 (Z) x 380 (X) x 6 mm open frame, 10 mm rim, bosses round each hand's holes, arm block
#     (from cart_arm.py); steel or 6 mm aluminium not chosen, shown as a single solid.
#  3. Arm mount: four M4 holes on a 50 mm square plus a 20 mm cable hole, at the plate centre (SO-101 base
#     footprint 70 x 70 from cart_assembly.py; the real SO-101 base hole pattern is to confirm).
#  4. Battery 70 x 50 x 70 mm at x = 70 (cart_arm.py): two cross bars of the frame carry it, four corner
#     stops hold it, two strap slots per bar take a 20 mm strap. Real battery size and fixing not decided.
#  5. Drive motors: one per hand on its +X side, gearbox up (cart_arm.py). Mount = two cross bars with a
#     saddle each (cradle for the 28 mm motor body) and M3 clamp holes. Real motor and clamp not decided.
#  6. Servo board bracket: two M3 holes in the arm block on the pipe-B side for the tab drawn in cart_arm.py.
#  7. Cable routing: the 12 V lead and the motor leads run in the rim, held by 3 x 8 mm tie slots; the servo
#     bus goes up through the 20 mm arm hole; a notch in the top rim lets the USB lead out. Cable lengths,
#     clips and strain relief are not designed.
#  8. Cart height: plate centre at the arm shoulder level used by cart_arm.py (pipes end 70 below it).
# Not drawn: the hands' drive transmission, wheel pairs, the board itself (see cart_arm.py).
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs
import cart_assembly as ca
import cart_arm as arm            # shared layout numbers; importing builds the arm drawing too

# ---------------- Shared layout (imported) ----------------
PIPE_SPACING = arm.PIPE_SPACING   # ASSUMED 280
HX = arm.HX
PLATE_X0, PLATE_X1 = arm.PLATE_X0, arm.PLATE_X1
PLATE_ZH = arm.PLATE_ZH
PLATE_T = ca.PLATE_T
PLATE_Y0, PLATE_Y1, PLATE_CY = ca.PLATE_Y0, ca.PLATE_Y1, arm.PLATE_CY
ARM_X, ARM_Z = ca.ARM_X, ca.ARM_Z
BATT, BATT_C = ca.BATT, arm.BATT_C
MOTOR_R, MOTOR_L, MOTOR_DX = ca.MOTOR_R, ca.MOTOR_L, arm.MOTOR_DX
PIPE_Z0, PIPE_Z1 = arm.PIPE_Z0, arm.PIPE_Z1
BOSS_HX, BOSS_HZ, ARM_BLOCK_HX, RIM = arm.BOSS_HX, arm.BOSS_HZ, arm.ARM_BLOCK_HX, arm.RIM
PAD_CX = ca.pad_cx
box, cyl, fuse, xshift = arm.box, arm.cyl, arm.fuse, arm.xshift

# ---------------- Numbers added here (ASSUMED) ----------------
ARM_HOLE_SQ = 50.0        # ASSUMED: arm base M4 square
ARM_HOLE_D = 4.3
ARM_CABLE_D = 20.0        # ASSUMED: servo bus pass-through
BATT_BAR_Z, BATT_BAR_W = 29.0, 10.0   # ASSUMED: battery cross bars centred at z = +/-29, 10 wide (battery 70 long)
BATT_STOP_H, BATT_STOP_T = 18.0, 3.0  # corner stops: 18 out from the plate, 3 thick
STRAP_SLOT = (3.0, 20.0)  # ASSUMED strap slot: 3 along Z, 20 across X
MOTOR_BAR_Z, MOTOR_BAR_W = 20.0, 8.0  # ASSUMED motor saddle bars at z = +/-20
SADDLE_W = 28.0           # saddle width in X (= motor diameter)
M3_D = 3.4
TIE_SLOT = (8.0, 3.0)     # ASSUMED cable-tie slot: 8 along X, 3 along Z
BOARD_HOLE_X = ARM_X - ARM_BLOCK_HX + 2.5     # ASSUMED: board-tab bolts, just inside the arm block's -X end
BOARD_HOLE_DZ = 10.0

# ---------------- Plate ----------------
def hole(d, x, z, y=PLATE_CY, depth=PLATE_T + 2):
    return cyl(d / 2, depth, "y", (x, y, z))

def slot(w, l, x, z):                       # rectangular slot through the plate, w along X, l along Z
    return box(w, PLATE_T + 2, l, (x, PLATE_CY, z))

def build_plate():
    p = arm.plate                           # open frame from cart_arm.py: rim, bosses, arm block, M4 pad holes
    # ---- arm mount (centre) ----
    h = ARM_HOLE_SQ / 2
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = p.cut(hole(ARM_HOLE_D, ARM_X + sx * h, ARM_Z + sz * h))
    p = p.cut(hole(ARM_CABLE_D, ARM_X, ARM_Z))
    # ---- servo board tab bolts (pipe-B side of the arm block) ----
    for sz in (-1, 1):
        p = p.cut(hole(M3_D, BOARD_HOLE_X, sz * BOARD_HOLE_DZ))
    # ---- battery: two cross bars carry it between the arm block and the pipe-C boss ----
    bx0, bx1 = ARM_X + ARM_BLOCK_HX, HX + PAD_CX - BOSS_HX
    for sz in (-1, 1):
        bar = box(bx1 - bx0 + 2, PLATE_T, BATT_BAR_W, ((bx0 + bx1) / 2, PLATE_CY, sz * BATT_BAR_Z))
        p = p.union(bar)
        for dx in (-22.0, 22.0):
            p = p.cut(slot(STRAP_SLOT[1] / 2, STRAP_SLOT[0], BATT_C + dx, sz * BATT_BAR_Z))
    # ---- drive motors: one per hand, +X side of its boss ----
    for sgn in (-1, 1):
        mx = sgn * HX + MOTOR_DX
        # bars run from the boss edge to the next solid (arm block for B, rim for C)
        a = sgn * HX + PAD_CX + BOSS_HX
        b = (ARM_X - ARM_BLOCK_HX) if sgn < 0 else (PLATE_X1 - RIM / 2)
        x0, x1 = (min(a, b), max(a, b))
        for sz in (-1, 1):
            p = p.union(box(x1 - x0 + 2, PLATE_T, MOTOR_BAR_W, ((x0 + x1) / 2, PLATE_CY, sz * MOTOR_BAR_Z)))
    # ---- cable routing in the rim: tie slots, 12 V lead along the bottom rim, motor leads at the top ----
    zr = PLATE_ZH - RIM / 2
    for x in (ARM_X - 40.0, ARM_X - 6.0, ARM_X + 28.0, BATT_C):          # 12 V lead, bottom rim (as cart_arm.py)
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (x, PLATE_CY, -zr)))
    for sgn in (-1, 1):                                                     # motor leads, top rim, by each motor
        mx = sgn * HX + MOTOR_DX
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (mx - 10.0, PLATE_CY, zr)))
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (mx + 10.0, PLATE_CY, zr)))
    for x in (ARM_X - 66.0,):                                               # USB lead, top rim (cart_arm.py: x -70)
        p = p.cut(box(TIE_SLOT[0], PLATE_T + 2, TIE_SLOT[1], (x, PLATE_CY, zr)))
    return p

plate = build_plate()

# ---------------- Things bolted on the plate ----------------
def corner_stops():
    out = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = (BATT_C + sx * (BATT[0] / 2 + BATT_STOP_T / 2), PLATE_Y0 - BATT_STOP_H / 2, sz * (BATT[2] / 2 - 6.0))
            out.append(box(BATT_STOP_T, BATT_STOP_H, 12.0, c))
    return fuse(out)
batt_stops = corner_stops()
battery = box(BATT[0], BATT[1], BATT[2], (BATT_C, PLATE_Y0 - BATT[1] / 2, 0.0))

def saddles():
    out = []
    for sgn in (-1, 1):
        mx = sgn * HX + MOTOR_DX
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
        mx = sgn * HX + MOTOR_DX
        top = PLATE_ZH - RIM / 2
        leads.append(arm.polyline([(mx - 10.0, PLATE_Y0 - 2.0, MOTOR_L / 2 + 10.0),
                                   (mx - 10.0, PLATE_Y0 - 2.0, top)], 1.5))
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
