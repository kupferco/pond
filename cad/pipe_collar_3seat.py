# cad/pipe_collar_3seat.py: pipe collar with THREE pod seats, built as THREE IDENTICAL 120 degree pieces held by magnets, NO hinge
# (OpenPocket #563). Owner decision 27 Nov 2026, approved drawing = option B of Viber sketch SUPhkmDEjmXn (docs/pipe-collar-3seat-reference.png).
# Everything about one seat comes UNCHANGED from cad/pipe_collar.py (imported, not copied; that file is not touched, task 537 uses it):
#   pipe 75 / 3 mm, collar RI 37.6 / RO 42.6, H 108, 45 mm hole, hole centre ZH 68, 26 mm seat bore angled 45 degrees up, spigot, gasket ring,
#   seat O-ring groove, straight plug holder 44 mm below the seat, 10 x 3 mm N52 magnets in 30 x 16 mm tabs (pockets 10.2 x 3.2).
# Plan view, angles round the pipe axis, seat 1 at 0 degrees (+X):
#   seats at 0, 120, 240 (all at z = ZH); joints at 60, 180, 300 (in the gaps between seats); about 46 degrees of pipe wall stay intact between holes.
#   ONE piece wraps -60 .. +60 degrees round its seat; printed three times (piece k = piece rotated by 120 k degrees). No hinge, no pin, no knuckles.
#   At each end of a piece a magnet tab straddles the joint plane (15 mm each side, radius 39.6 .. 55.6, z 31 .. 61, two magnets at z 38 and 54).
#   The tab at the -60 degree end is the "front" tab (N out at z 38, S out at z 54), the one at +60 the mirror ("back" tab): at every joint the
#   back tab of one piece faces the front tab of the next, so each facing pair attracts. The spigot in each drilled hole already stops the collar
#   sliding or turning; the magnets only keep the three pieces closed and aligned. Like the real collar the pieces stand SPLIT = 1 mm apart.
# ASSUMED (the brief says so): one plug holder per seat (three per collar), as in the real collar. Not in the repo yet: how many collars per unit,
#   the pitch between them, the real hole positions (docs/pipe-collar-3seat.md, open questions).
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadquery as cq
import numpy as np
import pipe_collar as pc
from pipe_collar import (RP, RI, RO, H, ZH, ZP, SPLIT, BOSS_D, X_TOP, U_FACE, SPIGOT_OD, SPIGOT_IN_R, GASKET_R0, GASKET_R1, GASKET_DEPTH,
                         HOLDER_FLOOR_X, DRILL_D, TAB_X, TAB_Z0, TAB_Z1, YB, MAG_ZS, MAG_Y, MAG_POCKET_D, MAG_POCKET_T, SPINE_R,
                         cylx, cylz, boxc, tilt, tubex, OR_GROOVE_D, OR_GROOVE_W, OR_GROOVE_X, BORE_D, U_FACE)

SEATS = (0.0, 120.0, 240.0)             # seat angles, degrees round the pipe axis
HALF = 60.0                              # a piece reaches 60 degrees each side of its seat
EXPLODE = 60.0                           # exploded view: pieces moved this far out along their seat direction (readability only)


def rotz(wp, deg):
    return wp.rotate((0, 0, 0), (0, 0, 1), deg)


# The joint frame is the real collar's closure frame (joint plane = YZ plane, tab on the -Y side, +X = "front" side); rotating it by
# 30 degrees puts the front side on the piece's -60 degree end, rotating it by 150 degrees puts the back side on its +60 degree end.
ROT_FRONT, ROT_BACK = 30.0, 150.0


def _tab(side):
    """Tab (box) of one end in the joint frame. side +1 = front, -1 = back."""
    if side > 0:
        return boxc(SPLIT / 2, TAB_X, YB - 6.5, -RO + 3, TAB_Z0, TAB_Z1)
    return boxc(-TAB_X, -SPLIT / 2, YB - 6.5, -RO + 3, TAB_Z0, TAB_Z1)


def _pocket(side, z):
    if side > 0:
        return cylx(MAG_POCKET_D / 2, SPLIT / 2 - 0.1, SPLIT / 2 + MAG_POCKET_T, MAG_Y, z)
    return cylx(MAG_POCKET_D / 2, -SPLIT / 2 - MAG_POCKET_T, -SPLIT / 2 + 0.1, MAG_Y, z)


def _ends():
    """(side, rotation) of the two ends of a piece: the front tab at -60 degrees, the back tab at +60 degrees."""
    return ((1, ROT_FRONT), (-1, ROT_BACK))


def piece():
    """The ONE piece: seat at 0 degrees, wrapping -60 .. +60 degrees, tabs at both ends. Print it three times."""
    ring = cylz(RO, 0, H).cut(cylz(RI, -1, H + 1))
    keep_minus = rotz(boxc(SPLIT / 2, 200, -200, 200, -1, H + 1), ROT_FRONT)       # side of the -60 degree joint that holds the piece
    keep_plus = rotz(boxc(-200, -SPLIT / 2, -200, 200, -1, H + 1), ROT_BACK)        # side of the +60 degree joint that holds the piece
    body = ring.intersect(keep_minus).intersect(keep_plus)
    # one seat, exactly as the front half of pipe_collar.py: plug-holder boss, angled pod boss, web, spigot, gasket groove, angled seat, holder
    body = body.union(cylx(BOSS_D / 2, 28, X_TOP, 0, ZP))
    body = body.union(tilt(cylx(BOSS_D / 2, -25.0, U_FACE)))
    body = body.union(boxc(30, X_TOP - 8, -18, 18, ZP, ZH))
    body = body.cut(cylz(RI, -1, H + 1))
    spigot = cylx(SPIGOT_OD / 2, 0, RI + 1.0, 0, ZH).intersect(cylz(RI + 1.0, -1, H + 1).cut(cylz(SPIGOT_IN_R, -2, H + 2)))
    body = body.union(spigot, clean=False)
    body = body.cut(cylx(GASKET_R1, 0, RO, 0, ZH).cut(cylx(GASKET_R0, -1, RO + 1, 0, ZH))
                    .intersect(cylz(RI + GASKET_DEPTH, -1, H + 1).cut(cylz(RI - 0.5, -2, H + 2))), clean=False)
    body = pc._angled_seat_cuts(body)
    body = pc._seat_cuts(body, ZP, HOLDER_FLOOR_X)
    # the two magnet tabs
    for side, rot in _ends():
        body = body.union(rotz(_tab(side), rot), clean=False)
    for side, rot in _ends():
        for z in MAG_ZS:
            body = body.cut(rotz(_pocket(side, z), rot), clean=False)
    return body


def tab_magnets():
    """The four magnets of one piece: (name, shape, colour, polarity out of the joint face). Front: N-out at z 38, S-out at z 54; back: mirror."""
    out = []
    for side, rot in _ends():
        for i, z in enumerate(MAG_ZS):
            north_out = (i == 0) == (side > 0)
            out.append(("magnet_%s_%d_%s" % ("front" if side > 0 else "back", i + 1, "N" if north_out else "S"),
                        rotz(pc.magnet(side, z), rot), pc.C_MAG_N if north_out else pc.C_MAG_S, side, z))
    return out


def place(wp, k, out=0.0):
    """Put something built for seat 1 (0 degrees) on seat k, optionally moved out along the seat direction."""
    a = math.radians(SEATS[k])
    return rotz(wp, SEATS[k]).translate((out * math.cos(a), out * math.sin(a), 0))


def pipe3():
    """The 75 mm pipe with three 45 mm holes drilled at 0, 120 and 240 degrees."""
    p = pc.pipe()
    for k in (1, 2):
        p = p.cut(rotz(cylx(DRILL_D / 2, 0, RP + 5, 0, ZH), SEATS[k]))
    return p


def seat_orings_3seat():
    """The two seat O-rings, each IN its groove: one in the angled pod seat's groove (on the 45 degree axis, u = U_FACE - 12 .. +2.6) and one in
    the straight plug holder's groove at height ZP. (pipe_collar.seat_orings() puts its first ring on a straight axis at ZH, where this collar has
    no straight seat, so it floated loose in the bore: not used here; pipe_collar.py itself is unchanged.)"""
    u0 = U_FACE - 12.0
    angled = tilt(tubex(OR_GROOVE_D / 2 - 0.05, BORE_D / 2 - 1, u0 + 0.3, u0 + OR_GROOVE_W - 0.3))
    straight = tubex(OR_GROOVE_D / 2 - 0.05, BORE_D / 2 - 1, OR_GROOVE_X + 0.3, OR_GROOVE_X + OR_GROOVE_W - 0.3, 0, ZP)
    return angled.union(straight)


def spine():
    return cylz(SPINE_R, -10, H + 10).cut(cylz(SPINE_R - 1.5, -11, H + 11))


C_PIECES = (pc.C_COLLAR, (0.36, 0.42, 0.46, 1), (0.22, 0.34, 0.3, 1))   # three tints so the three copies can be told apart; they are the same part


def scene(content="empty", explode=0.0, with_pipe=True, with_spine=True):
    """content: 'empty', 'piece' (seat 1 only), 'pods' (a pod in every seat + a plug parked in holder 1), 'plugs' (a plug in every hole)."""
    a = cq.Assembly()
    add = lambda o, n, c: a.add(o, name=n, color=cq.Color(*c))
    ks = (0,) if content == "piece" else (0, 1, 2)
    p0 = piece()
    for k in ks:
        add(place(p0, k, explode), "collar_piece_%d" % (k + 1), C_PIECES[k])
        for (n, m, c, _s, _z) in tab_magnets():
            add(place(m, k, explode), "%s_piece_%d" % (n, k + 1), c)
        add(place(pc.gasket(), k, explode), "gasket_EPDM_%d" % (k + 1), pc.C_SEAL)
        add(place(seat_orings_3seat(), k, explode), "seat_orings_%d" % (k + 1), pc.C_SEAL)
        if content == "pods":
            add(place(pc.pod(), k, explode), "pod_%d" % (k + 1), pc.C_POD)
        elif content == "plugs":
            add(place(pc.plug(), k, explode), "plug_%d" % (k + 1), pc.C_PLUG)
    if content == "pods":
        add(place(pc.plug(park=True), 0, explode), "plug_parked_seat_1", pc.C_PLUG)
    if with_pipe:
        add(pipe3(), "pipe_75", pc.C_PIPE)
    if with_spine:
        add(spine(), "spine_tube_33.7", (0.75, 0.55, 0.3, 1))
    return a


# ---------------- checks ----------------
def _vol(a, b):
    i = a.intersect(b)
    return sum(s.Volume() for s in i.vals()) if i.vals() else 0.0


def _footprint(wp):
    """Convex plan-view outline (XY points of the hull) of a convex solid."""
    from scipy.spatial import ConvexHull
    pts = []
    for s in wp.vals():
        v, _t = s.tessellate(0.3, 0.3)
        pts += [(p.x, p.y) for p in v]
    pts = np.array(pts)
    h = pts[ConvexHull(pts).vertices]
    out = []
    for i in range(len(h)):         # sample the edges densely
        p, q = h[i], h[(i + 1) % len(h)]
        out += [p + (q - p) * t for t in np.linspace(0, 1, 60)]
    return np.array(out)


def plan_gap(a, b):
    from scipy.spatial import cKDTree
    return float(cKDTree(_footprint(a)).query(_footprint(b))[0].min())


def seat_bosses():
    """The seat's own bosses as plain convex solids: angled pod boss, plug-holder boss, web between them."""
    return (tilt(cylx(BOSS_D / 2, -25.0, U_FACE)), cylx(BOSS_D / 2, 28, X_TOP, 0, ZP), boxc(30, X_TOP - 8, -18, 18, ZP, ZH))


def checks():
    out = {}
    p0 = piece()
    pieces = [place(p0, k) for k in range(3)]
    pipe = pipe3()
    sp = cylz(SPINE_R, -10, H + 10)
    out["pieces_identical_volume_mm3"] = p0.val().Volume()
    out["piece_solid_valid"] = float(p0.val().isValid())
    for i in range(3):
        j = (i + 1) % 3
        out["piece%d_vs_piece%d" % (i + 1, j + 1)] = _vol(pieces[i], pieces[j])
    out["pieces_vs_pipe"] = sum(_vol(p, pipe) for p in pieces)
    out["pieces_vs_spine"] = sum(_vol(p, sp) for p in pieces)
    pods = [place(pc.pod(), k) for k in range(3)]
    plugs = [place(pc.plug(), k) for k in range(3)]
    parked = [place(pc.plug(park=True), k) for k in range(3)]
    allp = pieces[0].union(pieces[1]).union(pieces[2])
    for nm, objs in (("pod", pods), ("plug", plugs), ("plug_parked", parked)):
        out[nm + "_vs_spine"] = sum(_vol(o, sp) for o in objs)
        out[nm + "_vs_pieces"] = sum(_vol(o, allp) for o in objs)
        out[nm + "_vs_pipe"] = sum(_vol(o, pipe) for o in objs)
    # seat O-rings: sit in their grooves (inside the piece's groove void, so no overlap with the plastic and no overlap with the pipe),
    # and do not overlap a seated pod / plug or a parked plug
    orings = [place(seat_orings_3seat(), k) for k in range(3)]
    out["oring_vs_pieces"] = sum(_vol(o, pieces[k]) for k, o in enumerate(orings))
    out["oring_vs_pipe"] = sum(_vol(o, pipe) for o in orings)
    # an O-ring squeezes the pod / plug body of ITS OWN seat (24 mm ring on a 25 / 25.5 mm body: the intended seal, as in the single collar);
    # it must touch nothing of any other seat, and in its own seat it only touches the part that belongs in that groove
    out["oring_vs_other_seats_pods_plugs"] = sum(_vol(o, x) for i, o in enumerate(orings) for j in range(3) if j != i for x in (pods[j], plugs[j], parked[j]))
    out["oring_squeeze_own_pod_mm3"] = sum(_vol(o, pods[i]) for i, o in enumerate(orings)) / 3
    out["oring_vs_gasket"] = sum(_vol(orings[k], place(pc.gasket(), k)) for k in range(3))
    # seated pods / plugs and parked plugs must not touch each other (every combination that can occur together)
    groups = {"pods+parked": pods + parked, "plugs+parked": plugs + parked}
    for gn, g in groups.items():
        worst = 0.0
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                worst = max(worst, _vol(g[i], g[j]))
        out["%s_mutual_overlap" % gn] = worst
    # magnets: fully inside their pocket (nothing sticks out) and not in the material of any piece
    bad_out, bad_in, fac = 0.0, 0.0, []
    for (n, m, c, side, z), rot in zip(tab_magnets(), (ROT_FRONT, ROT_FRONT, ROT_BACK, ROT_BACK)):
        pocket = rotz(_pocket(side, z), rot)
        for k in range(3):
            mk = place(m, k)
            pk = place(pocket, k)
            bad_out = max(bad_out, mk.val().Volume() - _vol(mk, pk))      # volume of the magnet outside its pocket
            bad_in = max(bad_in, _vol(mk, pieces[k]))                       # magnet in the plastic
    out["magnet_outside_pocket_mm3"] = bad_out
    out["magnet_in_plastic_mm3"] = bad_in
    out["magnet_face_gap_across_joint_mm"] = SPLIT + 2 * 0.1                # each magnet is 0.1 mm below its closing face
    # plan view: magnet tabs to the seat bosses (the brief wants at least 5 mm)
    tabs = []
    for k in range(3):
        for side, rot in _ends():
            tabs.append(place(rotz(_tab(side), rot), k))
    gap = 1e9
    for t in tabs:
        for k in range(3):
            for b in seat_bosses():
                gap = min(gap, plan_gap(t, place(b, k)))
    out["tab_to_seat_boss_plan_gap_mm"] = gap
    # and to the spigot (round the hole)
    spg = cylx(SPIGOT_OD / 2, 0, RI + 1.0, 0, ZH)
    out["tab_to_spigot_plan_gap_mm"] = min(plan_gap(t, place(spg, k)) for t in tabs for k in range(3))
    # wall left between the holes (angle round the pipe axis, outer surface): 120 - 2 asin(22.5 / 37.5)
    out["intact_wall_between_holes_deg"] = 120.0 - 2 * math.degrees(math.asin(DRILL_D / 2 / RP))
    out["joint_angles_deg"] = 60.0
    # the single collar's own geometry numbers (pod depth, gap to the spine, ...) are the same for every seat: take them from pipe_collar.checks()
    single = pc.checks()
    for k in ("pod_tip_centre_x", "pod_tip_min_x", "spine_gap_mm", "tip_edge_inside_wall_mm", "tip_below_wall_at_edge_mm", "tip_centre_below_wall_mm"):
        out["single_" + k] = single[k]
    return out


result = scene("empty")

if __name__ == "__main__":
    for k, v in checks().items():
        print("%-38s %.3f" % (k, v))
