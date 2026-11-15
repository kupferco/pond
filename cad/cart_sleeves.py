# cad/cart_sleeves.py: the two SLEEVE (hand) systems of the Pond cart (DRAFT v3, 15 Nov 2026, Viber #109 / #97).
# Drawing 3 of 5 planned cart drawings (whole cart, base, sleeve/hand systems, wheel pairs, arm on cart).
# Reuses cad/hand_sleeve.py v4.1 (the sleeve body) and cad/cart_assembly.py (hand spacing, wheel helper);
# neither is redrawn or changed. Not production geometry: a readable drawing of how the parts relate.
#
# v3 (Viber #109, bringing the drawing up to date with Viber #97): each hand now carries its plate HINGE and the base
# rotation worm drive, imported from cart_hinge.py v3 (sleeve leaf + knuckles, plate leaf, pin, brass worm wheel on the
# hinge axis, worm, bracket, worm motor); the base plate comes from cart_assembly.py. Nothing is redrawn and no number
# is duplicated: layout numbers are in cart_dims.py, hinge numbers in cart_hinge.py (cart_hinge.py wins on any conflict).
# The old note "no 90 deg swivel yet" is gone: the swivel is the hinge drive. NEW scene `transfer`: one hand is the
# STATIC hand (the one that is not moving during a transfer): its six wheels sit in their sleeve wheel pockets (sockets),
# clamped on its pipe by the spring idlers, exactly as in the other views, drawn in blue so it can be told apart. Its
# worm drive turns the plate round its hinge; the OTHER hand is released from its pipe and rides on the plate.
# Which hand is static comes from cart_dims.torque_budget() (its "driving_hand": the worst-case hand for the hinge torque). Swing angle
# is an illustration only (TRANSFER_ANGLE).
#
# v2 (follow-up): each hand (each set of wheels) clamps its OWN pipe. The two pipes run parallel, side by side
# (as in cart_arm.py v2), not both hands on one pipe as in cart_assembly.py v1.
#
# Frame: the hand_sleeve.py frame. Track pipes run along Z, base pads face -Y, the C-gap with funnel faces +X.
#
# DECIDED (hand_sleeve.py v4.1, decisions 31 Oct, 1 Nov, 2 Nov):
#   90 mm sleeve, outer R 34, two wheel rows 60 mm apart, six wheels per hand (driven wheel at 180 deg,
#   spring idlers at +/-60 deg, 2.5 mm travel, 60 N preload each), double-ended funnel C-gap (18 mm narrow,
#   30 mm mouth), worm-gear drive so a hand holds when stopped, M4 pad on -Y.
#
# ASSUMED (undecided; every one is marked "ASSUMED" below):
#  1. Pipe OD 32 mm (also assumed in hand_sleeve.py), shown as a 330 mm stub.
#  2. Pipe spacing 120 mm centre to centre (Viber #97; was 280, now from cart_dims.py), one hand per pipe (same assumed value as cart_arm.py v2; the
#     real spacing between neighbouring units is not decided). Both hands at the same height along the pipes.
#     Hinge and plate (v3): cart_hinge.py / cart_assembly.py as they are (hinge on the pad edge at -Y, plate 142 x 112 x 6).
#     The plate's own motors, arm and battery are not drawn here (see cart_base.py, cart_arm.py).
#  3. Drive layout: ONE worm shaft per hand, along the pipe, beside the sleeve on -X, meshing with a worm
#     wheel on each driven axle (both 180 deg wheels, one per row). Worm wheel R 7 mm, worm R 3 mm, worm 80 mm
#     long. The real ratio, tooth form and motor torque are not sized.
#  4. Motor: 28 mm diameter x 55 mm worm-gear motor placeholder (same size as cart_assembly.py), on the
#     outer end of each hand's worm shaft, with a 20 mm gearbox block. Real part not chosen.
#  5. Axle pins: 3.2 mm pins through the wheels; the driven pins stick out 14 mm on +Y to carry the worm wheel.
#     Bearings, circlips and the way the spring idlers are pushed (spring type, retainer) are not drawn.
#  6. Gear housing: two 4 mm bearing blocks at the ends of the worm; how they attach to the sleeve is not drawn.
#  7. Clamp: only the spring idlers clamp (arrows show the 60 N preload). v4.1 has NO jaw, so the hand has no
#     open and closed state to draw. The "open" jaw seen in sim/unit_change.py (hand shell opening widened
#     122 deg) and the jaw motor in the 1 Nov notes are not in the CAD. So there is no open/closed view; the
#     release is shown as the idler travel only (exploded view, top view). ASSUMED: release = jaw to be designed.
#  8. Both hands identical and the same way round (C-gap facing +X), drive on the +Z end of each hand.
#  9. Exploded view offsets are for readability only.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs        # reused, not redrawn
import cart_hinge as ch         # plate hinge + worm rotation drive of each hand (Viber #97), reused
import cart_assembly as ca      # reused: HAND_SPACING, PIPE_STUB_L, box/cyl helpers

box, cyl = ca.box, ca.cyl
from cart_dims import PIPE_SPACING, torque_budget   # 120, ASSUMED in cart_dims.py: pipe-to-pipe
HAND_X = PIPE_SPACING / 2                         # hands at x = -/+ 60, one per pipe

# ---------------- Drive (all ASSUMED) ----------------
AXLE_PIN_R = hs.AXLE_D / 2
AXLE_Y0 = -(math.sqrt(hs.WALL_OUT_R**2 - hs.AXLE_R_POS**2) + hs.AXLE_OVERRUN)   # -24.9, flush with the holes
DRIVEN_Y1 = 36.0                          # ASSUMED: driven pins run out to y = 36 for the worm wheel
WORM_WHEEL_R, WORM_WHEEL_T = 7.0, 4.0     # ASSUMED
WORM_WHEEL_Y = 32.0                       # ASSUMED: centre plane of the worm wheels (clear of the sleeve body)
WORM_R, WORM_L = 3.0, 80.0                # ASSUMED
WORM_X = -hs.AXLE_R_POS - WORM_WHEEL_R - WORM_R + 1.0    # ASSUMED: -35 mm, meshing with the worm wheel rim
MOTOR_R, MOTOR_L = ca.MOTOR_R, ca.MOTOR_L           # ASSUMED 28 x 55 mm, as in cart_assembly.py
GEARBOX = (26.0, 2 * MOTOR_R, 20.0)       # ASSUMED
BLOCK_T = 4.0                             # ASSUMED bearing blocks
ARROW_L = 14.0                            # preload arrow length (drawing aid only)

def rot(shape, ang):
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)

def wheel_stations():
    """(row z, angle deg, driven?) for the six wheels of a hand, the two rows being ROW_SPACING apart."""
    out = []
    for z in (hs.RING_Z, -hs.RING_Z):
        out.append((z, hs.OUTER_WHEEL_ANG, True))
        for a in hs.INNER_WHEEL_ANGS:
            out.append((z, a, False))
    return out

# ---------------- One hand: parts in the hand's own frame (centred at z = 0) ----------------
def hand_parts():
    """Dict name -> (shape, colour). Frame: sleeve centred on z = 0. Motor sits on the +Z end;
    the same hand is placed on each pipe (see build_pair)."""
    parts = {}
    parts["sleeve"] = (hs.result, (0.95, 0.75, 0.2, 1))
    wheels, axles, wwheels, arrows = None, None, None, None
    for z, ang, driven in wheel_stations():
        w = rot(cyl(hs.WHEEL_R, hs.WHEEL_W, "y", (hs.AXLE_R_POS, 0, z)), ang)
        y1 = DRIVEN_Y1 if driven else -AXLE_Y0
        pin = rot(cq.Workplane("XY").add(cq.Solid.makeCylinder(
            AXLE_PIN_R, y1 - AXLE_Y0, cq.Vector(hs.AXLE_R_POS, AXLE_Y0, z), cq.Vector(0, 1, 0))), ang)
        wheels = w if wheels is None else wheels.union(w)
        axles = pin if axles is None else axles.union(pin)
        if driven:
            ww = cyl(WORM_WHEEL_R, WORM_WHEEL_T, "y", (-hs.AXLE_R_POS, WORM_WHEEL_Y, z))
            wwheels = ww if wwheels is None else wwheels.union(ww)
        else:
            # spring preload arrow: from outside the wheel, pointing at the pipe axis (inward)
            r0 = hs.AXLE_R_POS + hs.WHEEL_R + 4 + ARROW_L
            a = cq.Workplane("XY").add(cq.Solid.makeCylinder(1.2, ARROW_L - 5, cq.Vector(r0, 0, z), cq.Vector(-1, 0, 0)))
            a = a.union(cq.Workplane("XY").add(cq.Solid.makeCone(3.0, 0, 5, cq.Vector(r0 - ARROW_L + 5, 0, z), cq.Vector(-1, 0, 0))))
            a = rot(a, ang)
            arrows = a if arrows is None else arrows.union(a)
    parts["wheels"] = (wheels, (0.15, 0.15, 0.15, 1))
    parts["axle_pins"] = (axles, (0.8, 0.8, 0.82, 1))
    parts["worm_wheels"] = (wwheels, (0.8, 0.5, 0.15, 1))
    parts["spring_preload_arrows"] = (arrows, (0.85, 0.1, 0.1, 1))
    # worm along Z, bearing blocks at both ends, then gearbox + motor beyond the +Z end of the sleeve
    worm = cyl(WORM_R, WORM_L, "z", (WORM_X, WORM_WHEEL_Y, 0))
    parts["worm"] = (worm, (0.6, 0.6, 0.65, 1))
    blocks = None
    for z in (WORM_L / 2 - BLOCK_T / 2, -WORM_L / 2 + BLOCK_T / 2):
        b = box(14, 14, BLOCK_T, (WORM_X, WORM_WHEEL_Y, z))
        blocks = b if blocks is None else blocks.union(b)
    parts["bearing_blocks"] = (blocks, (0.5, 0.5, 0.55, 1))
    zg = WORM_L / 2 + GEARBOX[2] / 2
    gearbox = box(GEARBOX[0], GEARBOX[1], GEARBOX[2], (WORM_X, WORM_WHEEL_Y, zg))
    motor = cyl(MOTOR_R, MOTOR_L, "z", (WORM_X, WORM_WHEEL_Y, WORM_L / 2 + GEARBOX[2] + MOTOR_L / 2))
    parts["gearbox"] = (gearbox, (0.85, 0.25, 0.25, 1))
    parts["drive_motor"] = (motor, (0.85, 0.25, 0.25, 1))
    return parts

# ---------------- Pair: one hand on each of two parallel pipes ----------------
WHEEL_COL, STATIC_WHEEL_COL = (0.15, 0.15, 0.15, 1), (0.1, 0.35, 0.8, 1)
TAGS = (("B", -1), ("C", 1))                      # (tag, sgn): pipe B at -x, pipe C at +x, as cart_assembly.py

def build_pair(static=None, angle=0.0, with_plate=True):
    """Both hands, each on its own pipe, each with its hinge and worm drive (cart_hinge.py) and the plate.
    static: None (plain pair) or "B"/"C": that hand is the STATIC hand (wheels blue, clamped on its pipe) and the plate
    swings by `angle` degrees on its hinge, carrying the other (released) hand; the pipes stay where they are."""
    a = cq.Assembly()
    swing = static is not None and angle != 0.0
    sgn_s = dict(TAGS).get(static, 0)
    # rotation about the static hinge axis, towards -Y (out from the pads), as the plate swings "like a door"
    ax_pt = (ch.hinge_x(sgn_s), 0, 0) if sgn_s else (0, 0, 0)
    def moved(shape):
        return shape.rotate(ax_pt, (ax_pt[0], 0, 1), -sgn_s * angle) if swing else shape
    for tag, sgn in TAGS:
        hx = sgn * HAND_X
        a.add(cyl(hs.R_PIPE, ca.PIPE_STUB_L, "z", (hx, 0, 0)), name="track_pipe_%s" % tag, color=cq.Color(0.75, 0.78, 0.8, 1))
        is_static = static == tag
        riding = swing and not is_static          # the released hand rides with the plate
        role = "static" if is_static else ("released" if static else "hand")
        for name, (shp, col) in hand_parts().items():
            if is_static and name in ("wheels", "axle_pins"):
                col = STATIC_WHEEL_COL if name == "wheels" else col
                name = "static_" + name
            shp = shp.translate((hx, 0, 0))
            a.add(moved(shp) if riding else shp, name="%s_%s_%s" % (role, tag, name), color=cq.Color(*col))
        for nm, shp, col in ch.hinge_parts(sgn):
            # on the plate side (turns with the plate when it swings) or on the sleeve side (stays with its sleeve)
            on_plate = nm in ("plate_leaf_knuckle", "plate_leaf_screws", "worm", "worm_bracket", "bracket_screws", "worm_motor")
            turns = riding or (swing and is_static and on_plate)
            a.add(moved(shp) if turns else shp, name="hinge_%s_%s" % (tag, nm), color=cq.Color(*col))
    if with_plate:
        a.add(moved(ca.plate) if swing else ca.plate, name="base_plate", color=cq.Color(0.35, 0.35, 0.38, 1))
    return a

TRANSFER_ANGLE = 45.0                             # ASSUMED illustration angle (deg) of the plate swing
STATIC_HAND = torque_budget()["driving_hand"]     # the hand whose hinge drives the transfer (cart_dims.py)

# ---------------- Exploded view of one hand ----------------
EXPLODE = {                                  # ASSUMED offsets (mm), readability only
    "sleeve": (0, 0, 0),
    "wheels": (0, 0, 0),
    "axle_pins": (0, 0, 0),
    "worm_wheels": (0, 28, 0),
    "worm": (-30, 40, 0),
    "bearing_blocks": (-30, 40, 0),
    "gearbox": (-30, 40, 30),
    "drive_motor": (-30, 40, 60),
    "spring_preload_arrows": (0, 0, 0),
}
def build_exploded():
    """One hand pulled apart: sleeve at the centre; each wheel pulled radially out of its pocket along its own
    axis direction and each axle pin drawn out along Y; drive parts stacked away on -X / +Y / +Z."""
    a = cq.Assembly()
    a.add(cyl(hs.R_PIPE, 200.0, "z", (0, 0, 0)), name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    a.add(hs.result, name="sleeve", color=cq.Color(0.95, 0.75, 0.2, 1))
    for i, (z, ang, driven) in enumerate(wheel_stations()):
        d = 38.0
        dx, dy = d * math.cos(math.radians(ang)), d * math.sin(math.radians(ang))
        w = rot(cyl(hs.WHEEL_R, hs.WHEEL_W, "y", (hs.AXLE_R_POS, 0, z)), ang).translate((dx, dy, 0))
        a.add(w, name="wheel_%d" % i, color=cq.Color(0.15, 0.15, 0.15, 1))
        y1 = DRIVEN_Y1 if driven else -AXLE_Y0
        pin = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            AXLE_PIN_R, y1 - AXLE_Y0, cq.Vector(hs.AXLE_R_POS, AXLE_Y0, z), cq.Vector(0, 1, 0)))
        pin = rot(pin, ang).translate((dx * 1.9, dy * 1.9, 0))
        a.add(pin, name="axle_pin_%d" % i, color=cq.Color(0.8, 0.8, 0.82, 1))
    for name, (shp, col) in hand_parts().items():
        if name in ("sleeve", "wheels", "axle_pins"):
            continue
        a.add(shp.translate(EXPLODE[name]), name=name, color=cq.Color(*col))
    return a

pair = build_pair()
transfer = build_pair(STATIC_HAND, TRANSFER_ANGLE)
exploded = build_exploded()
result = pair

# Key dimensions (mm), reused by the render script for the drawing annotations.
DIMS = {
    "pipe_spacing": PIPE_SPACING,
    "sleeve_length": hs.SLEEVE_L,
    "row_spacing": hs.ROW_SPACING,
    "sleeve_od": 2 * hs.WALL_OUT_R,
    "pipe_od": hs.PIPE_D,
    "gap_narrow": hs.OPENING_W,
    "gap_mouth": hs.FUNNEL_MOUTH_W,
}

if __name__ == "__main__":
    for tag, obj in (("pair", pair), ("transfer (static hand %s)" % STATIC_HAND, transfer), ("exploded hand", exploded)):
        bb = obj.toCompound().BoundingBox()
        print("cart_sleeves %s OK, bbox %.0f x %.0f x %.0f mm" % (tag, bb.xlen, bb.ylen, bb.zlen))
