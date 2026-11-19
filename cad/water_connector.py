# cad/water_connector.py: the sampling connector pair (OpenPocket #330 follow-up, 19 Nov 2026), after the owner's photo of the Omron blood pressure monitor connector.
# MALE (on the end of the soft tube): a thin rigid straight spigot (about 4.4 mm across, 1.5 mm bore) on a wider collar with ring grooves at its base that the arm (or a hand) grips.
# FEMALE (on the tank lids, the test station box, the cart): a plain round hole with a slight recess (counterbore), FLUSH with the surface, nothing sticking up.
# It pushes straight in and holds by friction (ASSUMED: a soft liner or O-ring in the hole gives the grip; here the hole is 0.1 mm bigger than the spigot so the CAD parts do not overlap).
# Pulled straight out. No twist, no clip. Frame-free: every function takes the axis position and an axis direction along Z.
import cadquery as cq

SPIGOT_R, BORE_R, SPIGOT_L = 2.2, 0.75, 14.0       # spigot 4.4 mm OD, 1.5 mm bore, 14 mm long
COLLAR_R, COLLAR_L = 6.5, 10.0                       # collar 13 mm OD, 10 mm long
GROOVES = (2.5, 5.0, 7.5)                            # groove centres from the spigot end of the collar, 1.2 mm wide, 0.8 mm deep
GROOVE_W, GROOVE_D = 1.2, 0.8
HOLE_R, RECESS_R, RECESS_D = 2.3, 3.4, 1.0           # female: hole 4.6 mm across (0.1 mm clearance), recess 6.8 mm across, 1 mm deep
HOLE_DEPTH = 16.0                                    # deeper than the 14 mm spigot


def _cyl(r, z0, z1, cx, cy):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(cx, cy, z0), cq.Vector(0, 0, 1)))


def male(cx, cy, zf, d):
    """Male nozzle. zf = height of the face it plugs against. d = +1: spigot goes up from zf, collar below; d = -1: spigot goes down from zf, collar above."""
    if d > 0:
        sp0, sp1, c0, c1 = zf, zf + SPIGOT_L, zf - COLLAR_L, zf
    else:
        sp0, sp1, c0, c1 = zf - SPIGOT_L, zf, zf, zf + COLLAR_L
    n = _cyl(COLLAR_R, c0, c1, cx, cy).union(_cyl(SPIGOT_R, sp0, sp1, cx, cy))
    for g in GROOVES:                                                    # grooves counted from the spigot end of the collar
        zc = (c1 - g) if d > 0 else (c0 + g)
        ring = _cyl(COLLAR_R + 1, zc - GROOVE_W / 2, zc + GROOVE_W / 2, cx, cy).cut(_cyl(COLLAR_R - GROOVE_D, zc - GROOVE_W / 2 - 1, zc + GROOVE_W / 2 + 1, cx, cy))
        n = n.cut(ring)
    return n.cut(_cyl(BORE_R, c0 - 1, sp1 + 1, cx, cy) if d > 0 else _cyl(BORE_R, sp0 - 1, c1 + 1, cx, cy))


def female_cut(cx, cy, zf, s):
    """The volume to cut out of a body to make the female socket: round hole + slight recess. zf = height of the flush face.
    s = +1: the face looks up (+Z), the hole goes down into the body; s = -1: the face looks down (-Z), the hole goes up into the body."""
    if s > 0:
        return _cyl(HOLE_R, zf - HOLE_DEPTH, zf + 1, cx, cy).union(_cyl(RECESS_R, zf - RECESS_D, zf + 1, cx, cy))
    return _cyl(HOLE_R, zf - 1, zf + HOLE_DEPTH, cx, cy).union(_cyl(RECESS_R, zf - 1, zf + RECESS_D, cx, cy))
