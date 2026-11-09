# cad/hand_sleeve.py @ claude/drafts
# Hand sleeve, draft v4.1 (3 Nov 2026). v4.1: jaw OPENING_W widened 14 -> 18 mm and
# FUNNEL_MOUTH_W 26 -> 30 mm so the track joint's M8 rod + standard lock nut (15 mm across
# corners) pass with ~1.5 mm a side (cad/track_joint.py). Wheel pockets at +/-60 deg still clear.
# Changes in v4 from v3 (31 Oct, render 20261031-232037-eaa2):
#   - Wheel rows set to exactly ROW_SPACING = 60 mm apart (v3 was 64 mm by accident of
#     sleeve length). Sim: 60 mm holds yaw to ~4 deg on straights and still passes the
#     150 mm loop corners (sim/guide_test.py, sim/bend_test.py).
#   - The bracket gap (C opening, +X) is now a double-ended funnel: narrow OPENING_W in the
#     middle, flaring to FUNNEL_MOUTH_W at both ends over FUNNEL_L. Track rods / brackets
#     entering from either direction push the hand back square.
#   - Spring idlers sized for SPRING_PRELOAD_N = 60 N per wheel station (30 N could not
#     climb a wet pipe in sim; 60 N climbs wet with ~3% slip). Spring pockets unchanged;
#     choose a stiffer spring for the same 2.5 mm travel.
#   - Drive: specify a worm-gear motor so the hand holds position when stopped (back-drive
#     resistance). Motor mount not yet drawn.
# Not yet printed or dimension-checked; see the "assumed" comments.
import cadquery as cq
import math

# ---------------- Dimensions (mm) ----------------
PIPE_D = 32.0          # outer diameter of the track pipe (assumed)
BORE_CLEAR = 4.0       # radial gap between pipe and sleeve bore
WALL_OUT_R = 34.0      # outer radius of the sleeve body
ROW_SPACING = 60.0     # axial distance between the two wheel rows (centre to centre)
WHEEL_D = 20.0         # wheel diameter
WHEEL_W = 8.0          # wheel width
WHEEL_CLEAR = 1.0      # clearance round each wheel in its pocket
END_WALL = 4.0         # solid material above/below each pocket
AXLE_D = 3.2           # axle hole (M3 / 3 mm shaft)
AXLE_OVERRUN = 3.0     # how far each axle hole runs past the outer wall
SPRING_TRAVEL = 2.5    # radial slot travel for spring-loaded wheels
SPRING_PRELOAD_N = 60.0  # target clamp force per idler station (for spring choice; not geometry)
OUTER_WHEEL_ANG = 180.0          # driven wheel, outside of the loop (-X)
INNER_WHEEL_ANGS = (60.0, -60.0) # spring wheels, back and front, towards spine
OPENING_W = 18.0       # width of the C gap at its narrow middle (+X); passes M8 nut
FUNNEL_MOUTH_W = 30.0  # width of the gap at each end of the sleeve
FUNNEL_L = 14.0        # axial length of each flare
PAD_X0, PAD_X1 = -24.0, 0.0      # base mounting pad extent in X
PAD_Y0, PAD_Y1 = -40.0, -21.0    # pad extent in Y (front = -Y)
PAD_HOLE_D = 4.3       # M4 clearance holes for the cart base
PAD_HOLE_Z = 15.0      # +/- Z spacing of the pad holes from centre

# ---------------- Derived ----------------
R_PIPE = PIPE_D / 2
R_BORE = R_PIPE + BORE_CLEAR
WHEEL_R = WHEEL_D / 2
AXLE_R_POS = R_PIPE + WHEEL_R            # wheel centre radius (touches pipe)
POCKET_H = WHEEL_D + 2 * WHEEL_CLEAR
POCKET_W = WHEEL_W + 2 * WHEEL_CLEAR
RING_Z = ROW_SPACING / 2
SLEEVE_L = ROW_SPACING + POCKET_H + 2 * END_WALL   # 90 mm
AXLE_LEN = 2 * (math.sqrt(WALL_OUT_R**2 - AXLE_R_POS**2) + AXLE_OVERRUN)

# ---------------- Body ----------------
body = (cq.Workplane("XY").circle(WALL_OUT_R).circle(R_BORE)
        .extrude(SLEEVE_L).translate((0, 0, -SLEEVE_L / 2)))

pad = cq.Workplane("XY").box(PAD_X1 - PAD_X0, PAD_Y1 - PAD_Y0, SLEEVE_L).translate(
    ((PAD_X0 + PAD_X1) / 2, (PAD_Y0 + PAD_Y1) / 2, 0))
body = body.union(pad)

def rot(shape, ang):
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)

for z in (RING_Z, -RING_Z):
    for ang, sprung in [(OUTER_WHEEL_ANG, False)] + [(a, True) for a in INNER_WHEEL_ANGS]:
        rad_len = WALL_OUT_R - R_BORE + 6
        pocket = cq.Workplane("XY").box(rad_len, POCKET_W, POCKET_H).translate(
            ((R_BORE + WALL_OUT_R) / 2, 0, z))
        body = body.cut(rot(pocket, ang))
        axle = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            AXLE_D / 2, AXLE_LEN, cq.Vector(AXLE_R_POS, -AXLE_LEN / 2, z), cq.Vector(0, 1, 0)))
        if sprung:
            axle2 = cq.Workplane("XY").add(cq.Solid.makeCylinder(
                AXLE_D / 2, AXLE_LEN, cq.Vector(AXLE_R_POS + SPRING_TRAVEL, -AXLE_LEN / 2, z), cq.Vector(0, 1, 0)))
            bridge = cq.Workplane("XY").box(SPRING_TRAVEL, AXLE_LEN, AXLE_D).translate(
                (AXLE_R_POS + SPRING_TRAVEL / 2, 0, z))
            axle = axle.union(axle2).union(bridge)
        body = body.cut(rot(axle, ang))

# Bracket gap: a double-ended funnel. Profile in the YZ plane (y = width, z = along pipe),
# extruded outward along +X from x = 15 mm to past the outer wall.
X0 = 15.0
H = SLEEVE_L / 2 + 1.0
wm, wn = FUNNEL_MOUTH_W / 2, OPENING_W / 2
zf = SLEEVE_L / 2 - FUNNEL_L
profile = [(-wm, H), (wm, H), (wn, zf), (wn, -zf), (wm, -H), (-wm, -H), (-wn, -zf), (-wn, zf)]
gap = (cq.Workplane("YZ", origin=(X0, 0, 0)).polyline(profile).close()
       .extrude(WALL_OUT_R + 10 - X0))
body = body.cut(gap)

for z in (PAD_HOLE_Z, -PAD_HOLE_Z):
    hole = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        PAD_HOLE_D / 2, PAD_Y1 - PAD_Y0 + 2, cq.Vector((PAD_X0 + PAD_X1) / 2, PAD_Y0 - 1, z), cq.Vector(0, 1, 0)))
    body = body.cut(hole)

result = body
