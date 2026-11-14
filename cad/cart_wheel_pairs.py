# cad/cart_wheel_pairs.py: the rigid WHEEL PAIRS of a Pond cart hand (DRAFT, 11 Nov 2026).
# Drawing 4 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Not production geometry: a readable detail drawing to show how one pair is built and how it rides.
#
# Frame: the hand_sleeve.py frame. Track pipe along Z, cart base on the -Y side, C-gap on +X.
# A "pair" is the two wheels at the same angle in the hand's two rows (60 mm apart along the pipe), held by
# one rigid carrier. A hand has three pairs: the DRIVEN pair at 180 deg (-X, outside of the loop) and two
# SPRING IDLER pairs at +/-60 deg (towards the spine): 3 pairs x 2 wheels = the 6 wheels per hand of
# hand_sleeve.py and the decision doc.
#
# Three models are built here:
#   result  : one hand's three pairs on the track pipe, with the driven pair's worm drive and motor.
#   corner  : the same hand going round a 150 mm radius 90 deg loop corner (pipe, sleeve and pairs).
#   context : BOTH hands of the cart, one on each of two parallel pipes (pipe B and pipe C, one from each of two
#             neighbouring units) PIPE_SPACING apart, as in cart_arm.py v2 (base plate across the two pipes).
#             Each hand has its own sleeve, driven pair + worm drive + motor and two spring idler pairs: 12 wheels.
#
# DECIDED (taken from hand_sleeve.py v4.1, cart_assembly.py and docs/decisions/2026-11-02-hand-yaw-control):
#   pipe OD 32, wheel 20 dia x 8 wide, wheel rows 60 mm apart, driven wheel at 180 deg, spring idlers at
#   +/-60 deg, 2.5 mm spring travel, 60 N preload per wheel station, rigid pairs (not free rockers),
#   worm-gear drive so the hand holds when stopped, 150 mm loop corner radius, motor 28 dia x 55 mm
#   (cart_assembly.py placeholder).
#
# ASSUMED (undecided; each is also marked "ASSUMED" where it is used):
#  1. Carrier: two 3 mm side rails (4 mm on the driven pair) either side of each wheel row, tied by a
#     16 mm x 4 mm cross bar between the rows. Printed or cut plate; material not chosen.
#  2. Wheels: 20 x 8 mm tyre on a 10 mm hub. Idler wheels run on two 623ZZ bearings (3 x 10 x 4) in the hub
#     on a FIXED 3 mm axle. The driven wheel is keyed to a ROTATING 3 mm axle that runs in a 623ZZ in each rail.
#  3. Idler spring: two compression springs per pair on the cross bar (60 N each = 60 N per wheel station),
#     8 mm OD, 1.0 mm wire, 10 mm free, 7.5 mm installed, 2.5 mm travel to 5 mm. Rate and wire to be chosen.
#  4. Sleeve change NOT in hand_sleeve.py (which is untouched): each pair slides in a channel cut along the
#     sleeve wall between the rows, closed by a spring cap; the driven pair needs the same channel (no spring).
#  5. Worm drive: worm 3.5 mm pitch radius on a 3 mm shaft along Z at 36.5 mm from the pipe axis, meshing a
#     7 mm pitch radius worm wheel on each driven axle (both driven wheels run in sync from one worm shaft,
#     which also stops the pair yawing). Tooth form, ratio and lead angle are not drawn: plain cylinders.
#     Needs a shallow groove along the sleeve for the worm (cut in the section view, not in hand_sleeve.py).
#  6. Motor: the cart_assembly.py 28 x 55 mm placeholder, here in line with the worm shaft beyond the sleeve end
#     (cart_assembly.py puts it beside the plate; power path from there to this shaft is open).
#  7. Corner: bend in the XZ plane, pipe curving towards +X (spine side inside), 150 mm CENTRELINE radius.
#     The hand sits square on the driven pair at the bend midpoint, wheels as point-contact discs.
#  0. Pipe spacing: 120 mm centre to centre, imported from cart_dims.py (itself ASSUMED; the real spacing between
#     neighbouring units is not decided). Both hands face the same way (driven pairs on the -X side), as in
#     cart_arm.py. The base plate is not drawn here; the hands are shown on bare pipe stubs.
#  8. Corner finding (computed in this file, not simulated): the 90 mm sleeve bore is 4 mm radial
#     clearance on the pipe; at 150 mm radius that is used up at the sleeve ends (see CLEARANCE below).
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_dims as cd   # PIPE_SPACING shared with cart_arm, cart_assembly, cart_base (two-pipe layout)
import cart_assembly as ca   # reuses motor size; importing runs it and also imports hand_sleeve as ca.hs
hs = ca.hs

# ---------------- Dimensions (mm) ----------------
PIPE_D, R_PIPE = hs.PIPE_D, hs.R_PIPE
WHEEL_R, WHEEL_W = hs.WHEEL_R, hs.WHEEL_W
AXLE_R = hs.AXLE_R_POS              # wheel centre radius from the pipe axis (26)
ROW_Z = hs.RING_Z                   # +/-30: the two rows of the pair
TRAVEL = hs.SPRING_TRAVEL           # 2.5
PRELOAD_N = hs.SPRING_PRELOAD_N     # 60
CORNER_R = 150.0                    # loop corner centreline radius (decision doc, sim/bend_test.py)
HUB_R = 5.0                         # ASSUMED wheel hub radius (10 mm bearing seat)
BRG = dict(od=10.0, id=3.0, w=4.0)  # ASSUMED 623ZZ
AXLE_D_ = 3.0                       # ASSUMED
RAIL_T, RAIL_T_DRIVEN = 3.0, 4.0    # ASSUMED
RAIL_Y0 = WHEEL_W / 2 + 0.5         # rail inner face 0.5 mm clear of the wheel side
RAIL_X0, RAIL_X1 = AXLE_R - 5.0, AXLE_R + 7.0   # ASSUMED rail radial extent: 21 .. 33
RAIL_HL = ROW_Z + 7.0               # rail half length along Z (37)
BAR_X0, BAR_X1, BAR_W, BAR_HL = 22.0, 26.0, 16.0, 16.0   # ASSUMED cross bar: radial 22..26, 16 wide, +/-16 long
SPR_Z = 14.0                        # ASSUMED spring stations on the bar (z = +/-14)
SPR_OD, SPR_WIRE, SPR_FREE, SPR_INST = 8.0, 1.0, 10.0, 7.5   # ASSUMED
CAP_T = 2.5                         # ASSUMED spring cap thickness (x = 33.5 .. 36)
GEAR_R, WORM_R = 7.0, 3.5           # ASSUMED pitch radii
WORM_X = AXLE_R + GEAR_R + WORM_R   # 36.5: worm shaft radial position
GEAR_Y = RAIL_Y0 + RAIL_T_DRIVEN + 1.0 + 2.0   # gear centre plane (y = 11.5) beyond the rail
MOTOR_R, MOTOR_L = ca.MOTOR_R, ca.MOTOR_L
SLEEVE_HL = hs.SLEEVE_L / 2         # 45
PIPE_SPACING = cd.PIPE_SPACING     # 120, ASSUMED in cart_dims.py: pipe B to pipe C

def cyl(r, h, axis, c):
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    start = cq.Vector(*[c[i] - d[i] * h / 2 for i in range(3)])
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, start, cq.Vector(*d)))

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(
        ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))

def spring(cx, cy, z0, length, turns=3.5):
    """Compression spring, axis along +X from x=z0 (a helix swept along X, drawn as a coil)."""
    pitch = (length - SPR_WIRE) / turns
    helix = cq.Wire.makeHelix(pitch, pitch * turns, (SPR_OD - SPR_WIRE) / 2)
    prof = cq.Workplane("XZ", origin=((SPR_OD - SPR_WIRE) / 2, 0, 0)).circle(SPR_WIRE / 2)
    coil = prof.sweep(cq.Workplane("XY").add(helix), isFrenet=True)
    coil = coil.rotate((0, 0, 0), (0, 1, 0), 90)      # helix axis Z -> X
    return coil.translate((z0 + SPR_WIRE / 2 - 0.0, cx, cy))

def rail_pair(driven):
    t = RAIL_T_DRIVEN if driven else RAIL_T
    c = None
    for sgn in (1, -1):
        y0, y1 = sorted((sgn * RAIL_Y0, sgn * (RAIL_Y0 + t)))
        r = box(RAIL_X0, RAIL_X1, y0, y1, -RAIL_HL, RAIL_HL)
        for z in (ROW_Z, -ROW_Z):          # wheel windows are not needed: rails sit beside the wheels
            r = r.cut(cyl(AXLE_D_ / 2, t + 2, "y", (AXLE_R, (y0 + y1) / 2, z)))
        c = r if c is None else c.union(r)
    bar = box(BAR_X0, BAR_X1, -BAR_W / 2, BAR_W / 2, -BAR_HL, BAR_HL)
    return c.union(bar)

def pair(driven):
    """One rigid pair at angle 0 (radial = +X). Returns dict name -> (shape, colour)."""
    parts = {}
    rails = rail_pair(driven)
    wheels = axles = brgs = None
    for z in (ROW_Z, -ROW_Z):
        w = cyl(WHEEL_R, WHEEL_W, "y", (AXLE_R, 0, z))
        if not driven:
            w = w.cut(cyl(BRG["od"] / 2, WHEEL_W + 2, "y", (AXLE_R, 0, z)))   # hub bore for two bearings
            for yy in (-BRG["w"] / 2, BRG["w"] / 2):
                b = cyl(BRG["od"] / 2, BRG["w"], "y", (AXLE_R, yy, z)).cut(
                    cyl(BRG["id"] / 2, BRG["w"] + 2, "y", (AXLE_R, yy, z)))
                brgs = b if brgs is None else brgs.union(b)
            ax = cyl(AXLE_D_ / 2, 2 * (RAIL_Y0 + RAIL_T) + 1, "y", (AXLE_R, 0, z))
        else:
            for sgn in (1, -1):      # one 623ZZ in each rail
                yy = sgn * (RAIL_Y0 + RAIL_T_DRIVEN / 2)
                b = cyl(BRG["od"] / 2, BRG["w"], "y", (AXLE_R, yy, z)).cut(
                    cyl(BRG["id"] / 2, BRG["w"] + 2, "y", (AXLE_R, yy, z)))
                brgs = b if brgs is None else brgs.union(b)
                rails = rails.cut(cyl(BRG["od"] / 2, BRG["w"], "y", (AXLE_R, yy, z)))
            ax_len = (GEAR_Y + 2.5) + (RAIL_Y0 + RAIL_T_DRIVEN + 1)
            ax = cyl(AXLE_D_ / 2, ax_len, "y", (AXLE_R, (GEAR_Y + 2.5 - RAIL_Y0 - RAIL_T_DRIVEN - 1) / 2, z))
        wheels = w if wheels is None else wheels.union(w)
        axles = ax if axles is None else axles.union(ax)
    parts["wheels"] = (wheels, (0.12, 0.12, 0.12, 1))
    parts["axles"] = (axles, (0.75, 0.75, 0.78, 1))
    parts["bearings"] = (brgs, (0.85, 0.7, 0.2, 1))
    parts["carrier"] = (rails, (0.2, 0.55, 0.85, 1))
    return parts

def rot(shape, ang, about=(0, 0, 1)):
    return shape.rotate((0, 0, 0), about, ang)

def driven_drive():
    """Worm shaft, worms, worm wheels and motor for the driven pair, in the pair frame (radial +X)."""
    gears = None
    worms = None
    for z in (ROW_Z, -ROW_Z):
        g = cyl(GEAR_R + 1.0, 4.0, "y", (AXLE_R, GEAR_Y, z))
        gears = g if gears is None else gears.union(g)
        w = cyl(WORM_R + 1.0, 8.0, "z", (WORM_X, GEAR_Y, z))
        worms = w if worms is None else worms.union(w)
    shaft = cyl(1.5, SLEEVE_HL + 5 + ROW_Z + 12, "z", (WORM_X, GEAR_Y, (SLEEVE_HL + 5 - ROW_Z - 12) / 2 + 0.0)).union(worms)
    mz0 = SLEEVE_HL + 8
    motor = cyl(MOTOR_R, MOTOR_L, "z", (WORM_X, GEAR_Y, mz0 + MOTOR_L / 2))
    return gears, shaft, motor

# ---------------- Detail model: one hand's three pairs on the pipe ----------------
PIPE_L = 200.0
pipe = cyl(R_PIPE, PIPE_L, "z", (0, 0, 0))

assy = cq.Assembly()
def add(obj, name, color):
    assy.add(obj, name=name, color=cq.Color(*color))

add(pipe, "track_pipe", (0.75, 0.78, 0.8, 1))

# driven pair at 180 deg
dp = pair(True)
gears, shaft, motor = driven_drive()
for k, (s, col) in dp.items():
    add(rot(s, 180), "driven_pair_" + k, col)
add(rot(gears, 180), "driven_worm_wheels", (0.9, 0.55, 0.15, 1))
add(rot(shaft, 180), "worm_shaft", (0.9, 0.55, 0.15, 1))
add(rot(motor, 180), "drive_motor", (0.85, 0.25, 0.25, 1))

# spring idler pairs at +/-60 deg, each with two springs and a spring cap on the sleeve channel
def idler_extras():
    sp = None
    cap = None
    for z in (SPR_Z, -SPR_Z):
        s = spring(0, z, BAR_X1, SPR_INST)
        sp = s if sp is None else sp.union(s)
    cap = box(BAR_X1 + SPR_INST, BAR_X1 + SPR_INST + CAP_T, -BAR_W / 2 - 3, BAR_W / 2 + 3, -BAR_HL - 4, BAR_HL + 4)
    return sp, cap

for ang in hs.INNER_WHEEL_ANGS:
    tag = "p60" if ang > 0 else "m60"
    ip = pair(False)
    for k, (s, col) in ip.items():
        add(rot(s, ang), "idler_%s_%s" % (tag, k), col)
    sp, cap = idler_extras()
    add(rot(sp, ang), "idler_%s_springs" % tag, (0.9, 0.2, 0.2, 1))
    add(rot(cap, ang), "idler_%s_spring_cap" % tag, (0.6, 0.6, 0.62, 1))

result = assy

# ---------------- Context model: both hands, one on each of two parallel pipes ----------------
def two_hand_model():
    c = cq.Assembly()
    def cadd(obj, name, color):
        c.add(obj, name=name, color=cq.Color(*color))
    sleeve = hs.result
    for tag, dx in (("B", -PIPE_SPACING / 2), ("C", PIPE_SPACING / 2)):
        def mv(s_):
            return s_.translate((dx, 0, 0))
        cadd(mv(cyl(R_PIPE, PIPE_L, "z", (0, 0, 0))), "pipe_%s" % tag, (0.75, 0.78, 0.8, 1))
        cadd(mv(sleeve), "sleeve_%s" % tag, (0.95, 0.75, 0.2, 1))
        g, sh, mo = driven_drive()
        for k, (s_, col) in pair(True).items():
            cadd(mv(rot(s_, 180)), "%s_driven_pair_%s" % (tag, k), col)
        cadd(mv(rot(g, 180)), "%s_worm_wheels" % tag, (0.9, 0.55, 0.15, 1))
        cadd(mv(rot(sh, 180)), "%s_worm_shaft" % tag, (0.9, 0.55, 0.15, 1))
        cadd(mv(rot(mo, 180)), "%s_drive_motor" % tag, (0.85, 0.25, 0.25, 1))
        for ang in hs.INNER_WHEEL_ANGS:
            t = "p60" if ang > 0 else "m60"
            for k, (s_, col) in pair(False).items():
                cadd(mv(rot(s_, ang)), "%s_idler_%s_%s" % (tag, t, k), col)
            sp, cap = idler_extras()
            cadd(mv(rot(sp, ang)), "%s_idler_%s_springs" % (tag, t), (0.9, 0.2, 0.2, 1))
            cadd(mv(rot(cap, ang)), "%s_idler_%s_spring_cap" % (tag, t), (0.6, 0.6, 0.62, 1))
    return c

context = two_hand_model()

# ---------------- Corner model: the hand on a 150 mm radius loop corner ----------------
# Bend in the XZ plane. C = bend centre. The hand frame: Z along the chord through the two driven wheels,
# X towards C. The driven wheels (centres on a circle of radius R+r_pipe+r_wheel round C) set where the hand sits.
R_OUT = CORNER_R + R_PIPE + WHEEL_R
HALF_ANG = math.asin(ROW_Z / R_OUT)                         # wheel centres +/-HALF_ANG either side of the mid angle
HAND_AXIS_D = R_OUT * math.cos(HALF_ANG) - AXLE_R           # hand axis distance from C (147.4)

def idler_travel(ang):
    """Radial shift (mm, + = away from the pipe axis, compressing the spring) of an idler pair so both wheels
    keep contact with the bent pipe. Point-contact wheels, bend centreline radius CORNER_R."""
    ca_, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    def dist(s, z):
        x, y = (AXLE_R + s) * ca_, (AXLE_R + s) * sa
        rr = math.hypot(HAND_AXIS_D - x, z)
        return math.hypot(rr - CORNER_R, y)
    worst = 0.0
    for z in (ROW_Z, -ROW_Z):
        lo, hi = -10.0, 10.0
        for _ in range(60):
            m = (lo + hi) / 2
            if dist(m, z) - (R_PIPE + WHEEL_R) > 0:
                hi = m
            else:
                lo = m
        if abs(m) > abs(worst):
            worst = m
    return worst

IDLER_SHIFT = idler_travel(60.0)                 # same for -60 by symmetry

def pipe_gap_in_bore(z):
    """Radial room left between the straight sleeve bore and the bent pipe at height z along the hand
    (negative = the pipe would hit the bore). The pipe centreline is offset from the hand axis by x."""
    xc = HAND_AXIS_D - math.sqrt(CORNER_R ** 2 - z ** 2)
    return hs.R_BORE - R_PIPE - abs(xc)

CLEARANCE = {z: pipe_gap_in_bore(z) for z in (0.0, ROW_Z, SLEEVE_HL)}   # mid, wheel rows, sleeve end

def bent_pipe():
    """90 deg pipe bend, centreline radius CORNER_R, plus 80 mm straight stubs, in the world XZ plane.
    Bend centre C at world (CORNER_R, 0, 0): pipe comes up the +Z side... built so the hand mid-angle is 45 deg."""
    r = CORNER_R
    path = (cq.Workplane("XZ").moveTo(0, -80).lineTo(0, 0)
            .radiusArc((r, r), r).lineTo(r + 80, r))     # up the Z axis, then turn towards +X
    prof = cq.Workplane("XY").circle(R_PIPE)
    return prof.sweep(path)

def corner_model():
    c = cq.Assembly()
    def cadd(obj, name, color):
        c.add(obj, name=name, color=cq.Color(*color))
    cadd(bent_pipe(), "track_pipe", (0.75, 0.78, 0.8, 1))
    # hand parts built in the hand frame (axis = Z through the origin, X towards C), then moved to the world:
    # world C = (CORNER_R, 0, 0)... the hand frame origin is placed HAND_AXIS_D from C, at mid angle 45 deg.
    mid = math.radians(45.0)
    # hand frame -> world: Z_h = tangent at 45 deg, X_h = towards C, Y_h = Y_world (out of the bend plane)
    cx, cz = CORNER_R, 0.0
    ux, uz = -math.cos(mid), math.sin(mid)             # from C outward to the pipe at mid angle
    ox, oz = cx + HAND_AXIS_D * ux, cz + HAND_AXIS_D * uz
    tx, tz = math.sin(mid), math.cos(mid)              # tangent direction (+Z_h)
    # rotation about Y that takes (X_h=(1,0,0), Z_h=(0,0,1)) to (-ux,-uz) and (tx,tz):
    ang = math.degrees(math.atan2(-uz, -ux))           # direction of X_h in the XZ plane, angle from +X towards -Z? see below
    def place(shape):
        # rotate about +Y by phi so that +X_h -> (-ux, 0, -uz)  [rotation about +Y maps X to (cos, 0, -sin)]
        phi = math.degrees(math.atan2(uz, -ux))
        return shape.rotate((0, 0, 0), (0, 1, 0), phi).translate((ox, 0, oz))
    sleeve = hs.result
    wheels_shapes = []
    cadd(place(sleeve), "hand_sleeve", (0.95, 0.75, 0.2, 1))
    dp_ = pair(True)
    for k, (s, col) in dp_.items():
        cadd(place(rot(s, 180)), "driven_pair_" + k, col)
    for a in hs.INNER_WHEEL_ANGS:
        ip_ = pair(False)
        shift = cq.Vector(1, 0, 0)
        for k, (s, col) in ip_.items():
            cadd(place(rot(s.translate((IDLER_SHIFT, 0, 0)), a)), "idler_%s_%s" % ("p60" if a > 0 else "m60", k), col)
    return c

corner = corner_model()

if __name__ == "__main__":
    bb = assy.toCompound().BoundingBox()
    print("cart_wheel_pairs OK, detail bbox %.0f x %.0f x %.0f mm" % (bb.xlen, bb.ylen, bb.zlen))
    bc = context.toCompound().BoundingBox()
    print("context (two hands, pipes %.0f apart) bbox %.0f x %.0f x %.0f mm" % (PIPE_SPACING, bc.xlen, bc.ylen, bc.zlen))
    print("corner R %.0f: idler pair shift %.2f mm of %.1f mm travel" % (CORNER_R, IDLER_SHIFT, TRAVEL))
    for z, g in CLEARANCE.items():
        print("  bore gap at z=%4.1f mm from hand centre: %+.2f mm" % (z, g))
