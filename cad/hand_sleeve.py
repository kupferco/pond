# cad/hand_sleeve.py: Hand sleeve v5, THREE-LOBE FRAME for omni wheels and ball cups (OpenPocket #278, plan task 265 part 4).
# v4.1 (hinge cart, 20 x 8 mm wheels, full ring R34) is kept unchanged as hand_sleeve_v4.py until plan tasks 5 and 6 retire the hinge.
#
# What v5 is (docs/plans/cart-roll-redesign-plan.md sections 3a, 4, 5, owner answers Q1, Q2, Q4, Q10):
#  - Frame as before: track pipe along Z, plate on the -Y side, C-gap (jaw side) on +X, mounting pad on -X/-Y. Centred on z = 0.
#  - THREE LOBES at the same angles as v4: one outside at 180 deg (-X) and two at +/-60 deg towards the spine. A full ring round the
#    38 mm wheels would be R61 and two of them overlap on pipes 120 mm apart (122 > 120), so the sleeve is a thin tube (bore R20,
#    flared at both ends for the 150 mm bend) with three radial lobes. The 120 mm spacing stays (checked in cart_sleeves.py).
#  - TWO DRIVEN OMNI WHEELS, both on the 180 deg lobe: the DRIVE wheel in the top row (axle tangential, rolls along the pipe) and the
#    ROLL wheel in the bottom row (axle along the pipe, rolls the sleeve round it): 90 deg round from the plate side (-Y).
#  - FOUR PASSIVE BALL CUPS (printed cup + stainless or Delrin ball, cart_omni.py) at +/-60 deg, rows ROW_Z = +/-38 (76 mm apart).
#    Each +/-60 deg lobe holds one rigid PAIR carrier (both cups) on two springs in a channel: 20 N per cup (design value; 40 N
#    in bench tests, owner answer Q4), the cups' drain holes open through the carrier and the cap to the outside of the sleeve.
#  - Length 124 (plan: about 125). Pad on -X/-Y kept (the plate is now bolted rigidly to the pads): pad face moved to y = -50 so
#    the plate clears the +/-60 deg lobe (its corner reaches y = -46).
#  - Bore R20 in the middle, flared at the ends: a straight 124 mm sleeve on the R150 bend has its ends 13.4 mm off the pipe
#    centre line (sagitta). The outer tube grows with the bore (7 mm wall).
#  - C-gap (funnel, 18 mm narrow, 30 mm mouth) kept for the M8 track-joint rod and the spine bracket.
# ASSUMED: everything marked ASSUMED, in particular wall thicknesses, the pad, the carrier and spring sizes.
# Not yet printed or dimension-checked.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_omni as co

# ---------------- Dimensions (mm) ----------------
PIPE_D = co.PIPE_D
R_PIPE = co.R_PIPE
BORE_CLEAR = 4.0                 # radial gap between pipe and bore in the middle of the sleeve
R_BORE = R_PIPE + BORE_CLEAR     # 20
TUBE_WALL = 7.0                  # ASSUMED wall of the tube
TUBE_R_MIN = 34.5                # outer radius of the tube: constant, so the jaw hinge pin sits on the tube surface at every height (the bent-pipe flare of the bore is 27 at most)
ROW_Z = 38.0                     # +/-: the two wheel rows are 76 mm apart (plan section 4)
ROW_SPACING = 2 * ROW_Z
POCKET_CLEAR = 1.0               # ASSUMED clearance all round a wheel in its pocket
POCKET_H = 2 * co.OMNI_R + 2 * POCKET_CLEAR     # 40: pocket height of a wheel standing on its edge
END_WALL = 4.0                   # solid material beyond each pocket
SLEEVE_L = ROW_SPACING + POCKET_H + 2 * END_WALL    # 124
BEND_R = 150.0                   # loop corner radius (cart_wheel_pairs.py)
BEND_CLEAR = 1.5                 # ASSUMED bore clearance beyond the sagitta
OMNI_WALL = 5.0                  # ASSUMED lobe wall beside an omni wheel
ARM_W_OMNI = co.OMNI_W + 2 * POCKET_CLEAR + 2 * OMNI_WALL      # 30.8: width of the 180 deg lobe
SHAFT_HOLE_D = co.SHAFT_D + 0.6  # shaft clearance hole
OUTER_ANG = 180.0                # lobe with both driven omni wheels
INNER_ANGS = (60.0, -60.0)       # lobes with the sprung ball-cup pairs, towards the spine
DRIVE_Z, ROLL_Z = ROW_Z, -ROW_Z  # drive wheel in the top row, roll wheel in the bottom row
OPENING_W = 18.0                 # width of the C gap at its narrow middle (+X); passes the M8 nut
FUNNEL_MOUTH_W = 30.0            # width of the gap at each end
FUNNEL_L = 14.0                  # axial length of each flare
PAD_X0, PAD_X1 = -24.0, 0.0      # base mounting pad extent in X
PAD_Y0, PAD_Y1 = -50.0, -22.0    # pad extent in Y (front = -Y); v4 was -40..-21
PAD_HOLE_D = 4.3                 # M4 clearance holes for the plate
PAD_HOLE_Z = 40.0                # +/- Z spacing of the pad holes from centre (v4: 15, the sleeve is now 124 long)

# ---------------- Ball cup lobes ----------------
CUP = co.ball_cup(co.BALL_D)
BORE_CUP_D = 2 * (CUP["cup_r"] + 0.3)            # cup bore in the lobe
CARRIER_T = 3.0                  # ASSUMED carrier plate thickness
CARRIER_W = 2 * CUP["cup_r"] + 1.0               # carrier width (tangential)
CARRIER_HL = ROW_Z + CUP["cup_r"]                # carrier half length along Z (47)
CARRIER_R0 = CUP["centre_r"] + CUP["back_x"]     # carrier inner face from the pipe axis (30.65): the cup backs rest on it
SPRING_TRAVEL = co.SPRING_TRAVEL                 # 2.5
SPRING_FREE, SPRING_INST = 10.0, 7.5             # ASSUMED spring lengths, installed 7.5, 5 at full travel
SPRING_OD = 8.0
SPRING_Z = 14.0                  # ASSUMED: two springs per carrier at z = +/-14, between the rows
SPRING_PRELOAD_N = co.OMNI_RATING_N      # design preload per wheel station 20 N (v4: 60 N). Test up to 40 N (owner answer Q4)
SPRING_TEST_N = 40.0
# Two springs per carrier, each 20 N at the installed 7.5 mm (= 20 N per cup). At full travel (5 mm) a spring rate k gives 20 + 2.5 k per
# spring, so k up to 8 N/mm keeps the test case (40 N per cup) inside the same spring. ASSUMED: to be chosen with the bench test.
SPRING_RATE_MAX_N_MM = (SPRING_TEST_N - SPRING_PRELOAD_N) / SPRING_TRAVEL
CAP_T = 2.5                      # ASSUMED spring cap (screwed to the lobe, screws not drawn)
CARRIER_R1 = CARRIER_R0 + CARRIER_T              # 33.65
CAP_R0 = CARRIER_R1 + SPRING_INST                  # 41.15: the cap sits on the installed spring
CAP_R1 = CAP_R0 + CAP_T                            # 43.65
ARM_W_CUP = 28.0                 # width of a +/-60 deg lobe
R_ARM_CUP = CAP_R1               # outer end of the +/-60 deg lobes
R_ARM_OMNI = co.OMNI_REACH + 3.0 + END_WALL      # 61: outer end of the 180 deg lobe (plan: about 61)
CHAN_W = CARRIER_W + 0.6         # channel width in a +/-60 deg lobe
CHAN_HL = CARRIER_HL + 0.3

# ---------------- Derived ----------------
RING_Z = ROW_Z
WHEEL_REACH = co.OMNI_REACH      # 54
WALL_OUT_R = R_ARM_OMNI          # outermost radius of the sleeve (the 180 deg lobe)
AXLE_R_POS = co.OMNI_AXLE_R      # 35


# Corner geometry (bend in the XZ plane, spine side inside): the two outer omni wheels (180 deg, rows +/-ROW_Z) touch the OUTSIDE of the
# pipe, so their centres lie on a circle R_OUT round the bend centre C, and that sets where the rigid sleeve sits (cart_wheel_pairs.py
# corner model uses the same numbers).
R_OUT = BEND_R + R_PIPE + co.OMNI_R                          # 185
HAND_AXIS_D = R_OUT * math.cos(math.asin(ROW_Z / R_OUT)) - co.OMNI_AXLE_R    # sleeve axis distance from C (146.1)


def pipe_offset(z):
    """Where the bent pipe's centre line is, in the sleeve frame, at height z along the sleeve (x, towards the bend centre)."""
    return HAND_AXIS_D - math.sqrt(BEND_R ** 2 - z ** 2)


def bore_r(z):
    """Bore radius at height z: R20, larger where the bent pipe's centre line (offset pipe_offset(z) from the sleeve axis) needs room."""
    return max(R_BORE, R_PIPE + BEND_CLEAR + abs(pipe_offset(z)))


def _tube():
    zs = [-SLEEVE_L / 2 + i * SLEEVE_L / 31 for i in range(32)]
    outer = [(max(TUBE_R_MIN, bore_r(z) + TUBE_WALL), z) for z in zs]
    inner = [(bore_r(z), z) for z in reversed(zs)]
    return cq.Workplane("XZ").polyline(outer + inner).close().revolve(360, (0, 0, 0), (0, 1, 0))


def _arm(ang, r0, r1, w, length=SLEEVE_L):
    return cq.Workplane("XY").box(r1 - r0, w, length).translate(((r0 + r1) / 2, 0, 0)).rotate((0, 0, 0), (0, 0, 1), ang)


def rot(shape, ang):
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)


def _cyl(r, h, d, c):
    """Cylinder radius r, length h, axis direction d, starting at c."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*c), cq.Vector(*d)))


# ---------------- Body ----------------
body = _tube()
body = body.union(_arm(OUTER_ANG, R_BORE - 2, R_ARM_OMNI, ARM_W_OMNI))
for a in INNER_ANGS:
    body = body.union(_arm(a, R_BORE - 2, R_ARM_CUP, ARM_W_CUP))
pad = cq.Workplane("XY").box(PAD_X1 - PAD_X0, PAD_Y1 - PAD_Y0, SLEEVE_L).translate(
    ((PAD_X0 + PAD_X1) / 2, (PAD_Y0 + PAD_Y1) / 2, 0))
body = body.union(pad)

# bore (the arms were added over it)
bore = cq.Workplane("XZ").polyline([(bore_r(z), z) for z in [-SLEEVE_L / 2 - 1 + i * (SLEEVE_L + 2) / 31 for i in range(32)]]
                                   + [(0, SLEEVE_L / 2 + 1), (0, -SLEEVE_L / 2 - 1)]).close().revolve(360, (0, 0, 0), (0, 1, 0))
body = body.cut(bore)

# drive wheel pocket (wheel on its edge, axle along Y) and shaft holes
pk = cq.Workplane("XY").box(R_ARM_OMNI + 2 - 12, co.OMNI_W + 2 * POCKET_CLEAR, POCKET_H).translate(((R_ARM_OMNI + 2 + 12) / 2, 0, DRIVE_Z))
sh = _cyl(SHAFT_HOLE_D / 2, ARM_W_OMNI, (0, 1, 0), (co.OMNI_AXLE_R, -ARM_W_OMNI / 2 + 2.5, DRIVE_Z))   # +Y through, -Y blind (2.5 skin)
body = body.cut(rot(pk, OUTER_ANG)).cut(rot(sh, OUTER_ANG))
# roll wheel pocket (wheel flat, axle along Z)
rp = _cyl(co.OMNI_R + POCKET_CLEAR, co.OMNI_W + 2 * POCKET_CLEAR, (0, 0, 1), (co.OMNI_AXLE_R, 0, ROLL_Z - co.OMNI_W / 2 - POCKET_CLEAR))
rs = _cyl(SHAFT_HOLE_D / 2, (ROLL_Z + co.OMNI_W / 2 + 3) + SLEEVE_L / 2 + 1, (0, 0, 1), (co.OMNI_AXLE_R, 0, -SLEEVE_L / 2 - 1))   # up to the pocket, then blind
body = body.cut(rot(rp, OUTER_ANG)).cut(rot(rs, OUTER_ANG))

# ball cup lobes: a bore for each cup, a channel for the carrier and springs, open at the outer end (the cap closes it)
for a in INNER_ANGS:
    chan = cq.Workplane("XY").box(R_ARM_CUP + 1 - (CARRIER_R0 - 0.2), CHAN_W, 2 * CHAN_HL).translate(((R_ARM_CUP + 1 + CARRIER_R0 - 0.2) / 2, 0, 0))
    body = body.cut(rot(chan, a))
    for z in (ROW_Z, -ROW_Z):
        cb = _cyl(BORE_CUP_D / 2, CARRIER_R0 - 0.2 - 12.0 + 0.5, (1, 0, 0), (12.0, 0, z))
        body = body.cut(rot(cb, a))

# Bracket gap: a double-ended funnel, as v4. Profile in the YZ plane, extruded outward along +X from x = 15 mm.
X0 = 15.0
H = SLEEVE_L / 2 + 1.0
wm, wn = FUNNEL_MOUTH_W / 2, OPENING_W / 2
zf = SLEEVE_L / 2 - FUNNEL_L
profile = [(-wm, H), (wm, H), (wn, zf), (wn, -zf), (wm, -H), (-wm, -H), (-wn, -zf), (-wn, zf)]
body = body.cut(cq.Workplane("YZ", origin=(X0, 0, 0)).polyline(profile).close().extrude(60.0 - X0))

for z in (PAD_HOLE_Z, -PAD_HOLE_Z):
    body = body.cut(_cyl(PAD_HOLE_D / 2, PAD_Y1 - PAD_Y0 + 2, (0, 1, 0), ((PAD_X0 + PAD_X1) / 2, PAD_Y0 - 1, z)))

result = body


def reach():
    """Largest distance of the sleeve body from the pipe axis, in the XY plane (from the tessellation)."""
    v, _ = body.val().tessellate(0.5, 0.5)
    return max(math.hypot(p.x, p.y) for p in v)


def checks():
    """Asserted numbers of the cups and the sleeve. Returns a dict."""
    assert CUP["ball_retained"], "ball would fall out of the seat"
    assert CUP["lip_gap_ball"] >= 0.3, "lip touches the ball"
    assert CUP["lip_gap_pipe"] >= 0.5, "lip would touch the pipe"
    assert PIPE_BUMP_OK
    return {"length": SLEEVE_L, "bore_end": bore_r(SLEEVE_L / 2), "lip_gap_ball": CUP["lip_gap_ball"], "lip_gap_pipe": CUP["lip_gap_pipe"]}


PIPE_BUMP_OK = CUP["lip_gap_pipe"] + SPRING_TRAVEL >= co.PIPE_BUMP     # a 1.5 mm joint ring passes: the spring gives 2.5 mm

if __name__ == "__main__":
    c = checks()
    print("hand_sleeve v5 OK: %d solid(s), length %.0f mm, bore %.1f mm at the ends, lip %.2f mm off the pipe and %.2f mm off the ball"
          % (len(body.solids().vals()), c["length"], c["bore_end"], c["lip_gap_pipe"], c["lip_gap_ball"]))
    print("outer reach %.1f mm from the pipe axis (180 deg lobe %.0f), volume %.0f cm3" % (reach(), R_ARM_OMNI, body.val().Volume() / 1000))
