# cad/cart_dims.py: the cart's shared layout numbers, in one place (Viber #66).
# cart_assembly.py (whole cart), cart_arm.py (arm on cart) and cart_sleeves.py import these, so the pipe
# spacing, plate size, battery, motors and arm position cannot drift apart between drawings.
# Frame: the hand_sleeve.py frame (pipes along Z, plate on the -Y side). Two parallel pipes, pipe B at
# x = -PIPE_SPACING/2 and pipe C at x = +PIPE_SPACING/2, one hand on each, plate running across (X).
# Everything below is ASSUMED unless a comment says otherwise.
# v2 (Viber #97, 14 Nov 2026): pipes 120 mm apart (was 280); the plate now hangs on a hinge at each hand
# (see cart_base.py), so the plate runs between the two hinge axes and the arm, two drive motors and the battery
# are re-placed. Reasoning for the 120 mm is in the SPACING BUDGET block below.
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs

# ---------------- Hand envelope (from hand_sleeve.py, DECIDED numbers) ----------------
SLEEVE_R = hs.WALL_OUT_R                # 34: sleeve outer radius
WHEEL_REACH = hs.AXLE_R_POS + hs.WHEEL_R    # 36: outer (driven) wheel's outer edge from the pipe axis, on -X
PIPE_R = hs.R_PIPE                      # 16

# ---------------- Hinge (ASSUMED sizes; drawn in cart_base.py) ----------------
# One hinge per hand on the pad edge, axis parallel to the pipe. Hand B's hinge is on the pad's -X edge, hand
# C's on its +X edge, so the plate sits BETWEEN the two hinge axes (a door hung between two posts).
HINGE_R = 5.0                           # ASSUMED: knuckle barrel radius (10 mm OD)
HINGE_LEAF_T = 3.0                      # ASSUMED: leaf thickness
HINGE_OFF_B = hs.PAD_X0 - 6.0           # hinge axis, relative to pipe B: -30 (pad -X edge - 6)
HINGE_OFF_C = hs.PAD_X1 + 6.0           # hinge axis, relative to pipe C: +6 (pad +X edge + 6)
LEAF_Y1 = hs.PAD_Y0 - HINGE_LEAF_T      # sleeve leaf front face: -43
PLATE_T = 6.0                           # ASSUMED
PLATE_Y1 = LEAF_Y1 - HINGE_LEAF_T       # closed stack, out from the pad: pad | sleeve leaf | plate leaf | plate
PLATE_Y0 = PLATE_Y1 - PLATE_T           # plate front face -52
HINGE_Y = LEAF_Y1                       # hinge axis y = -43, on the face between the two leaves
HINGE_CLEAR = 2.0                       # plate edge to barrel gap beyond the barrel radius

# ---------------- SPACING BUDGET: why PIPE_SPACING = 120 ----------------
# Limit 1, hands (sleeve + wheels + neighbour pipe): hand B reaches 34 mm towards C (sleeve wall; spring wheels
#   reach 24), hand C's driven wheel reaches 36 mm towards B. Sleeve to sleeve needs only 34 + 36 = 70, and a
#   hand to the neighbour pipe 34 + 16 = 50. Both are far below 120 (50 mm sleeve-to-wheel gap at 120).
# Limit 2, the plate between the hinge axes (THIS decides it): everything that sits on the plate in X is
#   motor 28 + arm base 70 + motor 28 = 126 mm, plus 4 mm between parts and 4 mm to each plate end = 142 mm.
#   Plate width between the hinge axes = PIPE_SPACING + (HINGE_OFF_C - HINGE_OFF_B) - 2 (R + CLEAR)
#                                      = PIPE_SPACING + 36 - 14 = PIPE_SPACING + 22.
#   So PIPE_SPACING >= 142 - 22 = 120. At 115 the plate is 137 wide and the arm or a motor would overlap.
# The battery (70 x 50 x 70) does NOT fit between the hands at any spacing near this: it goes above the arm
#   (BATT_Z) on a shelf tongue of the plate. The two hinge worm drives also go above the sleeves (z > 60).
ARM_BASE_W = 70.0                       # SO-101 base footprint (given, 70 x 70 mm)
MOTOR_R, MOTOR_L = 14.0, 55.0           # ASSUMED worm-gear motor placeholder, 28 x 55 mm
PART_GAP, END_GAP = 4.0, 4.0            # ASSUMED gaps: between plate parts, motor to plate end
NEEDED_PLATE_W = 2 * (2 * MOTOR_R) + ARM_BASE_W + 2 * PART_GAP + 2 * END_GAP    # 142
PIPE_SPACING = 120.0                    # pipe B to pipe C, centre to centre (two tanks touching, pipes 60 from edge)
HX = PIPE_SPACING / 2                   # each pipe's x offset from the cart centre line
PLATE_X0 = -HX + HINGE_OFF_B + HINGE_R + HINGE_CLEAR      # -83: just clear of hand B's hinge barrel
PLATE_X1 = HX + HINGE_OFF_C - HINGE_R - HINGE_CLEAR       # +59: just clear of hand C's hinge barrel
assert PLATE_X1 - PLATE_X0 >= NEEDED_PLATE_W, "plate too narrow for motor + arm + motor at this PIPE_SPACING"
assert PIPE_SPACING - SLEEVE_R - WHEEL_REACH >= 10.0, "hands too close"
assert PIPE_SPACING - SLEEVE_R - PIPE_R >= 10.0, "sleeve too close to the neighbour pipe"
PLATE_ZH = (hs.SLEEVE_L + 22.0) / 2     # ASSUMED half height, 11 mm margin beyond each sleeve end (112 mm)
RIM, BOSS_HX, BOSS_HZ = 10.0, 18.0, 28.0   # ASSUMED open-frame details
# Parts on the plate, left to right (x): motor B, arm, motor C
MOTOR_XS = {-1: PLATE_X0 + END_GAP + MOTOR_R}                                    # motor B centre, -65
ARM_X = MOTOR_XS[-1] + MOTOR_R + PART_GAP + ARM_BASE_W / 2                       # -12: arm base centre
MOTOR_XS[1] = ARM_X + ARM_BASE_W / 2 + PART_GAP + MOTOR_R                        # +41: motor C centre
ARM_Z = 0.0
ARM_BLOCK_HX = ARM_BASE_W / 2 + 2.0     # arm block on the plate, 2 mm beyond the arm base each side
BATT = (70.0, 50.0, 70.0)               # ASSUMED: X, Y (out from plate), Z
BATT_X = ARM_X                          # battery sits above the arm, same x
BATT_Z = PLATE_ZH + 6.0 + BATT[2] / 2   # ASSUMED: on a shelf tongue above the plate's top rim (centre z)
PIPE_STUB_L = 330.0                     # ASSUMED: pipe stub length in the assembly

# ---------------- Hinge worm drive (v3, ASSUMED sizes, drawn in cart_hinge.py) ----------------
# v3 (Viber #97, 14 Nov 2026): the direct-drive servo is gone. Each hinge has a worm WHEEL fixed on the hinge axis
# (bolted to the sleeve's top knuckle) and a WORM carried by the plate, driven by the same 28 x 55 mm worm-gear
# motor as the hand drives. Turning the worm walks the plate round the wheel. Single-start worm: it self-locks.
WORM_M = 1.0                            # ASSUMED: module 1 brass wheel and steel worm (standard M1 hobby set)
WHEEL_Z = 38                            # ASSUMED: wheel teeth -> ratio 38:1
WHEEL_PD = WORM_M * WHEEL_Z             # 38 mm pitch diameter
WHEEL_OD = WHEEL_PD + 2 * WORM_M        # 40
WORM_PD = 10.0                          # ASSUMED worm pitch diameter (lead angle 5.7 deg: self-locking)
WORM_OD = WORM_PD + 2 * WORM_M          # 12
WORM_L = 24.0                           # ASSUMED worm length
WHEEL_T = 8.0                           # ASSUMED wheel face width
CENTRE_DIST = (WHEEL_PD + WORM_PD) / 2  # 24: worm axis this far in front (-Y) of the hinge axis
WHEEL_Z0 = 62.0                         # ASSUMED wheel underside (above the plate's top rim 56; hub from the knuckle at 45)
WORM_ZC = WHEEL_Z0 + WHEEL_T / 2        # 66: worm axis height
HORN_R, HORN_T = 10.0, 3.0              # ASSUMED: hub flange bolted to the top of the sleeve knuckle
KNUCKLE_Z = 45.0                        # sleeve knuckles run to the sleeve end
BATT_SHELF_T = 3.0                      # battery corner stops
TONGUE_DX0, TONGUE_W = 21.0, 30.0       # worm-bracket tongue on the plate: starts 21 mm from the hinge axis (beyond the wheel), 30 wide
TONGUE_Z1 = 86.0                        # tongue top

# ---------------- TORQUE BUDGET (ASSUMED masses; rotation only during a transfer) ----------------
# Decided: one hand lets go of its pipe, the plate (one rigid piece) swings on the OTHER hand's hinge; that hand's worm
# motor drives. Worst case: hinge axis horizontal, so every mass counts at its full distance r from the axis
# (r = in-plane lever and out-of-plane offset combined, the max over the swing angle), all summed as if aligned.
# ARM FOLDED POSE (ASSUMED): upper arm vertical and forearm folded back on it, wrist and gripper tucked, so the arm's centre
# of mass is 55 mm out from the plate (dy) and 20 mm off the arm base centre along the plate (dx). Unfolded
# (centre of mass about 300 mm out) the same arm would need about 3x the torque.
G = 9.81
WORM_EFF = 0.35                         # ASSUMED worm efficiency (steel on brass, lead angle 5.7 deg, mu 0.15)
MOTOR_RATED_NM = 0.30                   # ASSUMED rated (continuous) torque of the 28 x 55 mm 12 V worm-gear motor, 3 kg cm
MOTOR_RPM = 60.0                        # ASSUMED output speed at rated load


def hinge_x(sgn):
    """x of the hinge axis of the hand on pipe B (sgn -1) or pipe C (sgn +1)."""
    return sgn * HX + (HINGE_OFF_B if sgn < 0 else HINGE_OFF_C)


def torque_budget():
    """Return dict: required torque (N m) at the driving hinge, available torque, margin, swing time for 90 deg."""
    import math
    arm_x = -12.0
    xb, xc = hinge_x(-1), hinge_x(1)
    best = None
    for drv, x_ax, other_x in (("B", xb, xc), ("C", xc, xb)):
        tot, rows = 0.0, []
        items = [("plate 142x112x6 + hinge leaves", 0.30, arm_x, 6.0, 1.0),
                 ("battery 70x50x70", 0.35, arm_x, 34.0, 1.0),
                 ("arm SO-101, folded pose", 0.80, arm_x + 20.0 * (1 if drv == "B" else -1), 64.0, 1.0),
                 ("drive motor B", 0.15, -65.0, 23.0, 1.0),
                 ("drive motor C", 0.15, 41.0, 23.0, 1.0),
                 ("other hand's worm motor + bracket", 0.30, other_x, 30.0, 1.0)]
        for n, m, x, dy, _ in items:
            r = math.hypot(abs(x - x_ax), dy) / 1000.0
            t = m * G * r
            rows.append((n, m, r * 1000.0, t))
            tot += t
        if best is None or tot > best[0]:
            best = (tot, drv, rows)
    req, drv, rows = best
    ratio = WHEEL_Z
    avail = MOTOR_RATED_NM * ratio * WORM_EFF
    return {"driving_hand": drv, "rows": rows, "required_Nm": req, "available_Nm": avail,
            "margin": avail / req, "ratio": ratio, "motor_torque_needed_Nm": req / (ratio * WORM_EFF),
            "t90_s": 0.25 * 60.0 / (MOTOR_RPM / ratio),
            "tooth_force_N": req / (WHEEL_PD / 2000.0)}
