# cad/cart_dims.py: the cart's shared layout numbers, in one place (Viber #66).
# cart_assembly.py (whole cart), cart_arm.py (arm on cart) and cart_sleeves.py import these, so the pipe
# spacing, plate size, battery, motors and arm position cannot drift apart between drawings.
# Frame: the hand_sleeve.py frame (pipes along Z, plate on the -Y side). Two parallel pipes, pipe B at
# x = -PIPE_SPACING/2 and pipe C at x = +PIPE_SPACING/2, one hand on each, plate running across (X).
# Everything below is ASSUMED unless a comment says otherwise.
# v2 (Viber #97, 14 Nov 2026): pipes 120 mm apart (was 280); the arm, two drive motors and the battery are re-placed.
# v3 (Pond #279, plan task 265 part 5): the hinges are gone. The plate is rigid on the two sleeve pads (hand_sleeve.py v5); the
# whole cart spins round the static pipe on the omni roll wheel. Reasoning for the 120 mm is in the SPACING BUDGET block below.
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs

# ---------------- Hand envelope (from hand_sleeve.py v5, the three-lobe omni sleeve) ----------------
SLEEVE_R = hs.WALL_OUT_R                # 61: sleeve outer radius (the 180 deg lobe, on the pad side, away from the neighbour)
WHEEL_REACH = hs.WHEEL_REACH            # 54: driven omni wheel's furthest point from the pipe axis
PIPE_R = hs.R_PIPE                      # 16
# Furthest the sleeve reaches towards the NEIGHBOUR pipe (+X for hand B): only the two +/-60 deg ball-cup lobes face it.
# Outer end of the lobe at 60 deg from +X plus half the lobe width across: R_ARM_CUP cos 60 + ARM_W_CUP/2 sin 60 (about 34).
NEIGHBOUR_REACH = hs.R_ARM_CUP * math.cos(math.radians(60.0)) + hs.ARM_W_CUP / 2 * math.sin(math.radians(60.0))

# ---------------- Rigid base on the sleeve pads (Pond #279, plan task 265 part 5) ----------------
# The hinges and worm drives are gone (cart_hinge.py retired). The plate is bolted flat to the front face of both sleeve pads
# (hs.PAD_Y0), so cart and sleeves are one rigid body: the whole base spins round the static pipe on the omni roll wheel.
# Hand C is the true mirror of hand B across x = 0 (Pond #227), so both pads are on the OUTER side of their pipes.
PLATE_T = 6.0                           # ASSUMED, unchanged
PLATE_Y1 = hs.PAD_Y0                    # plate back face on the pad faces: -50
PLATE_Y0 = PLATE_Y1 - PLATE_T           # plate front face -56

# ---------------- SPACING BUDGET: why PIPE_SPACING = 120 ----------------
# Limit 1, hands: with the three-lobe sleeve only the two ball-cup lobes face the neighbour, NEIGHBOUR_REACH (about 34) each.
#   Sleeve to sleeve needs 2 x 34 = 68, and a sleeve to the neighbour pipe 34 + 16 = 50. Both are below 120.
#   A full ring of R61 would need 122 (does not fit), which is why the sleeve is a three-lobe frame (owner answer Q2).
# Limit 2, the plate: it runs from the outer edge of pad B to the outer edge of pad C, 168 mm. Pond #280: the drive and roll motors now sit
#   in the sleeves, so the only thing on the plate in X is the 70 mm arm base (and the battery under it): 86 mm needed with gaps, 168 given.
# The battery (70 x 50 x 70) is the same 70 x 70 footprint as the arm base, so it sits flat on the plate centre between
#   the two motors and the arm base is bolted on top of it (Viber #109: stack plate | battery | arm; no shelf tongue).
ARM_BASE_W = 70.0                       # SO-101 base footprint (given, 70 x 70 mm)
MOTOR_R, MOTOR_L = 14.0, 55.0           # ASSUMED worm-gear motor placeholder, 28 x 55 mm. All 4 motors (2 drive, 2 roll) are inside the sleeves (cart_omni.py); none on the plate
PART_GAP, END_GAP = 4.0, 4.0            # ASSUMED gaps: between plate parts, motor to plate end
NEEDED_PLATE_W = ARM_BASE_W + 2 * END_GAP + 2 * PART_GAP    # 86: arm base and battery only (Pond #280: the motors moved into the sleeves)
PIPE_SPACING = 120.0                    # pipe B to pipe C, centre to centre (two tanks touching, pipes 60 from edge)
HX = PIPE_SPACING / 2                   # each pipe's x offset from the cart centre line
PLATE_X0 = -HX + hs.PAD_X0              # -84: outer edge of pad B
PLATE_X1 = HX - hs.PAD_X0               # +84: outer edge of pad C (mirror of PLATE_X0)
assert abs(PLATE_X0 + PLATE_X1) < 1e-9, "plate must be symmetric about x = 0"
assert PLATE_X1 - PLATE_X0 >= NEEDED_PLATE_W, "plate too narrow for the arm base"
assert PIPE_SPACING - 2 * NEIGHBOUR_REACH >= 10.0, "hands too close"
assert PIPE_SPACING - NEIGHBOUR_REACH - PIPE_R >= 10.0, "sleeve too close to the neighbour pipe"
PLATE_ZH = (hs.SLEEVE_L + 22.0) / 2     # ASSUMED half height, 11 mm margin beyond each sleeve end (146 mm for the 124 mm sleeve; as cart_sleeves.py)
assert hs.PAD_HOLE_Z + hs.PAD_HOLE_D / 2 < PLATE_ZH, "pad holes must land on the plate"
RIM, BOSS_HX, BOSS_HZ = 10.0, 18.0, 28.0   # ASSUMED open-frame details
# On the plate: the arm base and the battery under it, at the plate centre. (Pond #280: no motors on the plate any more.)
ARM_X = 0.0                                                                      # arm base centre: the plate centre (symmetric, v4)
LEAD_SLOT_XS = (-53.0, 53.0)                                                     # cable-tie slot centres in the top band (sleeve motor leads), as before
ARM_Z = 0.0
ARM_BLOCK_HX = ARM_BASE_W / 2 + 2.0     # arm block on the plate, 2 mm beyond the arm base each side
BATT = (70.0, 50.0, 70.0)               # ASSUMED: X, Y (out from plate), Z
BATT_X = ARM_X                          # battery sits UNDER the arm base, same x (v3, Viber #109: no shelf tongue)
BATT_Z = ARM_Z                          # ASSUMED: centred on the arm axis, flat on the plate: stack plate | battery | arm base
ARM_Y0 = PLATE_Y0 - BATT[1]             # arm base underside: on the battery's front face (50 mm out from the plate)
PIPE_STUB_L = 330.0                     # ASSUMED: pipe stub length in the assembly

# ---------------- Motor and gravity constants (shared with roll_budget) ----------------
# The hinge worm drive and torque_budget() are gone with the hinges (Pond #279). roll_budget() below replaces them.
# ARM FOLDED POSE (ASSUMED): upper arm vertical and forearm folded back on it, so the arm's centre of mass is 55 mm above its base,
# 105 mm out from the plate (the base sits on the battery), and 20 mm off the arm base centre along the plate.
G = 9.81
MOTOR_RATED_NM = 0.30                   # ASSUMED rated (continuous) torque of the 28 x 55 mm 12 V worm-gear motor, 3 kg cm
MOTOR_RPM = 60.0                        # ASSUMED output speed at rated load


# ---------------- ROLL BUDGET (Pond #277, plan task 265 part 3; numbers only, no drawing uses it yet) ----------------
# New design (docs/plans/cart-roll-redesign-plan.md): no hinges. The whole cart (base) spins round the STATIC hand's pipe on
# a driven omni wheel (the roll wheel, axle along the pipe), and one driven omni wheel per sleeve drives the cart along the
# pipe. Both are rubber-roller omni wheels pressed on the 32 mm PVC pipe, so every number here is limited by friction.
# Everything is ASSUMED until the bench test (grip on real PVC, preload, hold on a tilt) measures it.
ROLL_WHEEL_R = 19.0                     # 38 mm omni wheel (plan: a common 48 or 58 mm size is possible, pass wheel_r to roll_budget)
WHEEL_RATING_N = 20.0                   # a 38 mm omni wheel is rated about 2 kg
PRELOAD_TARGET_N = (20.0, 40.0)         # plan section 5: aim for 20 N, test to 40 N, never today's 60 N
MU_WET = 0.3                            # rubber on wet PVC (sim pipe_climb.py: 30 N wet slid, 60 N held)
CART_MASS_KG = 3.0                      # whole cart, plan section 3
# Roll load items: (name, mass kg, x from the cart centre line mm, y out from the pipe plane mm). Worst case as in
# torque_budget(): pipe axis HORIZONTAL (every mass counts at its full lever), all added as if aligned, arm folded.
# y: the plate's front face is at PLATE_Y0 (-56), battery and arm stack on it. No hinge, so the lever is from the pipe axis.
ROLL_LOAD_ITEMS = (("plate 168x146x6", 0.30, ARM_X, PLATE_Y0 + PLATE_T / 2),
                   ("battery 70x50x70 under the arm", 0.35, BATT_X, PLATE_Y0 - BATT[1] / 2),
                   ("arm SO-101, folded pose", 0.80, ARM_X + 20.0, PLATE_Y0 - BATT[1] - 55.0))
# (Pond #280: the two plate motors are gone from this list: all four motors are in the sleeves, on or beside the pipe axis, so they add
#  no roll lever; the released hand's motors are in ROLL_OTHER_HAND_KG below.)
ROLL_OTHER_HAND_KG = 0.30               # the released hand: sleeve, wheels, motors, at its pipe (PIPE_SPACING away), on the axis plane


def roll_budget(wheel_r=ROLL_WHEEL_R, pipe_r=PIPE_R, mu=MU_WET, motor_nm=MOTOR_RATED_NM, motor_rpm=MOTOR_RPM,
                preload_n=PRELOAD_TARGET_N[0], rating_n=WHEEL_RATING_N, mass_kg=CART_MASS_KG):
    """Roll and drive budget of the omni-wheel cart: torque, traction and speed. Returns a dict.
    The wheel rolls on the pipe without slipping, so the contact is the instant centre: the wheel axle is 'lever' = pipe_r + wheel_r
    from the pipe axis, the sleeve turns at wheel_rpm * wheel_r / lever, and torque is multiplied by lever / wheel_r (power is kept).
    Friction limits what the contact can push: F_max = mu * preload."""
    import math
    lever = pipe_r + wheel_r                     # pipe axis to wheel axle, mm (35 for a 38 mm wheel on 32 mm pipe)
    ratio = lever / wheel_r                      # roll torque multiplier (1.84)
    f_motor = motor_nm / (wheel_r / 1000.0)      # tangential force the motor can make at the wheel edge, N
    # --- speed ---
    drive_mm_s = motor_rpm / 60.0 * 2 * math.pi * wheel_r                   # along the pipe
    roll_rpm = motor_rpm * wheel_r / lever                                  # sleeve round the pipe
    # --- torque to roll: pipe horizontal (worst case), masses at their full lever from the pipe axis ---
    rows, req = [], 0.0
    for static_x in (-HX, HX):                   # the static hand on pipe B or on pipe C
        tot, r_rows = 0.0, []
        for n, m, x, y in ROLL_LOAD_ITEMS + (("released hand + motors", ROLL_OTHER_HAND_KG, -static_x, 0.0),):
            r = math.hypot(x - static_x, y) / 1000.0
            r_rows.append((n, m, r * 1000.0, m * G * r))
            tot += m * G * r
        if tot > req:
            req, rows = tot, r_rows
    avail_motor = motor_nm * ratio               # roll torque the motor can make, before friction
    # --- traction (the roll wheel's contact is the only thing that holds the cart rolled on a tilted pipe) ---
    f_fric = mu * preload_n                      # friction limit at the contact, N
    hold_nm = min(f_motor, f_fric) * lever / 1000.0                    # roll torque actually available / holdable
    need_preload_roll = req / (mu * lever / 1000.0)                    # N, to hold the worst-case roll load
    # --- along the pipe: cart weight on a vertical pipe held by the driven wheel's contact alone ---
    weight_n = mass_kg * G
    need_preload_along = weight_n / mu
    return {"lever_mm": lever, "ratio": ratio, "drive_speed_mm_s": drive_mm_s, "roll_rpm": roll_rpm,
            "roll_deg_s": roll_rpm * 6.0, "t180_s": 30.0 / roll_rpm,
            "rows": rows, "required_Nm": req, "motor_force_N": f_motor, "available_motor_Nm": avail_motor,
            "friction_force_N": f_fric, "hold_Nm": hold_nm, "margin_motor": avail_motor / req, "margin_hold": hold_nm / req,
            "preload_needed_roll_N": need_preload_roll, "wheel_rating_N": rating_n, "preload_N": preload_n,
            "preload_over_rating": need_preload_roll / rating_n,
            "weight_N": weight_n, "preload_needed_along_N": need_preload_along, "drive_force_N": f_motor,
            "along_margin": min(f_motor, f_fric) / weight_n,
            "worm_hold_ok": f_fric * lever / 1000.0 >= req}


if __name__ == "__main__":
    b = roll_budget()
    for k, v in b.items():
        print(k, v if k != "rows" else "")
        if k == "rows":
            for r in v:
                print("   %-34s %.2f kg  lever %5.1f mm  %.3f N m" % r)
