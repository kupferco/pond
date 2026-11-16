# cad/pipe_collar.py: clamp-on pod collar for the central (growing) pipe, pod plug, plug holder (DRAFT v1, 16 Nov 2026,
# OpenPocket #229). Parts only: no sim scene is touched. Dimensions that are ASSUMED are marked so.
#
# DESIGN (decided with Dani): the holes are simply DRILLED through the 75 mm pipe (no heat-forming). A 3D-printed
# clamshell collar clips round the pipe at each hole: front half (carries the pod seat and the plug holder, ONE piece),
# back half, a hinge on one side (pin through three knuckles), a magnetic closure on the other side (4 disc magnets 10 x 3 mm
# N52, 2 in each tab, no screw: the spigot in the drilled hole already stops the collar sliding or turning and only a
# trickle runs down inside the pipe, so the closure only has to keep the halves shut and aligned; it does not clamp).
#   - SEAL: a 2.5 mm cord/O-ring in a groove on the collar's inner face rings the hole (light + water); a short
#     spigot on the collar goes into the drilled hole (the KEY: the collar cannot rotate or slide on the pipe).
#   - SEAT: the outer face is a round socket, bore 26 mm, with an O-ring (24 x 2) for the pod body and a 2 mm
#     recess for the pod cap. The pod plug has the same body/cap shape as a pod, so it fits the same seat and the
#     robot hand uses the same grip on both (the 6 mm of cap that stands proud of the seat).
#   - PLUG HOLDER: a second, blind socket of the same shape, STRAIGHT (not angled), 44 mm below the hole. A plug
#     parked there stands 5 mm further out than a seated plug (blind floor), so you can see it is parked. The
#     robot pulls the plug out of the hole along the 45 degree axis, tilts it 45 degrees down to horizontal while moving
#     it 44 mm down, and pushes it into the holder; back the same way.
# FOLLOW-UP 16 Nov 2026 (Dani): the POD SEAT IS ANGLED 45 degrees UP (pod's outer end higher than its inner end, so the
#   seedling grows upward). The plug holder stays STRAIGHT (axis +X), now BELOW the hole (the tilted pod cap would hit a
#   holder above it), 44 mm lower. CHOICE: the hole is still drilled SQUARE to the pipe (a plain hole saw, simplest by
#   hand) but is 45 mm, not 29: a 25 mm pod at 45 degrees needs a 25 x 35.4 mm oval plus the 3 mm wall slant. The printed
#   spigot (44.6 mm, flush with the inner wall) fills the hole and carries the 26 mm bore at 45 degrees, so the light seal
#   (spigot overlap + gasket ring round the hole + seat O-ring) is kept. The plug sits in the same angled seat, so the
#   robot now TILTS the plug 45 degrees between the hole (45 deg up) and the parking socket (straight, horizontal).
#   POD DEPTH (see checks()): the pod's inner end is set as far in as the spine allows (3.0 mm gap to the 33.7 mm
#   spine tube); its lower end edges then sit about 3 mm inside the wall surface, in the water running down the inner wall.
# Frame: pipe axis = Z, hole axis = +X, collar bottom at z = 0, hole centre z = ZH (upper), holder centre z = ZP (lower).
# ASSUMED (no decision in the repo): pod = 25 mm body x 32 + 34 mm cap x 8 (overall 40, as pod_store.py: 25 x 40);
#   pipe 75 mm OD, 3 mm wall (pod_store_reach.py, unit_v3_*.py); spine tube 33.7 mm in the pipe (unit_v3_dimensioned.py);
#   holes 100 mm apart along the pipe (one collar of 92 mm per hole). Real hole positions are not in the repo yet.
# PRINT: ASA (or PETG) only, outdoors / UV, NOT PLA. Print the halves lying on the split face, boss pointing up,
#   0.2 mm layers, 4 perimeters, 40 % infill. Plug: ASA, black (light-tight), print standing on the cap. Gaskets: EPDM.
# DRILL: 45 mm through ONE wall of the pipe (a 45 mm hole saw, square to the pipe), deburr. Hole centres 68 mm above the
#   collar's bottom edge, 100 mm pitch (ASSUMED).
import os
import sys
import math
import cadquery as cq

# ---------------- pipe ----------------
RP, PIPE_WALL = 37.5, 3.0              # 75 mm OD, 3 mm wall (repo)
SPINE_R = 33.7 / 2                      # spine tube inside the pipe (repo)
DRILL_D = 45.0                          # drilled hole in the pipe
# ---------------- collar ----------------
FIT = 0.1                               # bore clearance on the pipe
RI = RP + FIT
WALL = 5.0
RO = RI + WALL
H = 108.0
ZH, ZP = 68.0, 24.0                     # hole centre (upper), plug-holder centre (lower), 44 mm apart
TILT = 45.0                             # pod seat angle, degrees up from horizontal (+X toward +Z)
P0 = (RP - 1.5, 0.0, ZH)                # seat axis passes here (mid pipe wall)
U_CAP = 21.7                            # cap underside, along the seat axis from P0 (sets how far in the pod sits)
U_FACE = U_CAP + 2.0                    # seat face
SPLIT = 1.0                             # gap between the halves at the YZ plane; the magnets pull it closed to about 1.2 mm
BOSS_D = 40.0
X_TOP = 54.0                            # seat face
BORE_D = 26.0
RECESS_D, RECESS_T = 35.2, 2.0
OR_GROOVE_D, OR_GROOVE_W, OR_GROOVE_X = 28.6, 2.6, 42.0   # seat O-ring 24 x 2: groove x 42..44.6
SPIGOT_OD, SPIGOT_ID = DRILL_D - 0.4, BORE_D     # in the 45 mm hole: 0.2 mm clearance each side
SPIGOT_IN_R = RP - PIPE_WALL + 0.1      # spigot tip flush with the inner wall (34.5; 0.1 mm recessed)
GASKET_R0, GASKET_R1 = 25.5, 28.0       # gasket cord ring round the hole (mean dia 53.5, 2.5 cord)
GASKET_DEPTH = 1.8                      # groove depth beyond the bore
HOLDER_FLOOR_X = 40.0
# hinge and closure
YH = RO + 3.5
KR = 5.0
PIN_D = 3.0
TAB_X, TAB_Z0, TAB_Z1 = 15.0, 31.0, 61.0
YB = -(RO + 6.5)                        # tab centre line (-Y side)
MAG_D, MAG_T = 10.0, 3.0                # N52 neodymium disc 10 x 3 mm
MAG_POCKET_D, MAG_POCKET_T = 10.2, 3.2  # press-fit / glue pocket: +0.2 mm dia for print tolerance, +0.2 mm deep
MAG_ZS = (38.0, 54.0)                   # two magnets per tab, 16 mm apart, inside the 31..61 tab
MAG_Y = YB + 1.5                       # centre of the tab in Y (tab spans YB-6.5 .. -RO+3)
# ---------------- pod and plug ----------------
POD_BODY_D, POD_BODY_L = 25.0, 32.0
CAP_D, CAP_T = 34.0, 8.0
PLUG_BODY_D, PLUG_BODY_L = 25.5, 17.0
PARK_DX = HOLDER_FLOOR_X + PLUG_BODY_L - (X_TOP - RECESS_T)     # 5: parked plug stands this much further out

def cylx(r, x0, x1, y=0.0, z=0.0):
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(r).extrude(x1 - x0)
def tubex(ro, ri, x0, x1, y=0.0, z=0.0):
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(ro).circle(ri).extrude(x1 - x0)
def cylz(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)
def boxc(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def tilt(wp):
    """Move a solid built along +X from the origin onto the angled seat axis (through P0, 45 degrees up)."""
    return wp.rotate((0, 0, 0), (0, 1, 0), -TILT).translate(P0)

def pipe():
    p = cylz(RP, -20, H + 20).cut(cylz(RP - PIPE_WALL, -21, H + 21))
    return p.cut(cylx(DRILL_D / 2, 0, RP + 5, 0, ZH))

def _seat_cuts(w, z, x_floor):
    """Straight seat (the plug holder): axis +X at height z, floor at x_floor."""
    w = w.cut(cylx(BORE_D / 2, x_floor, X_TOP + 1, 0, z), clean=False)
    w = w.cut(cylx(RECESS_D / 2, X_TOP - RECESS_T, X_TOP + 1, 0, z), clean=False)
    w = w.cut(tubex(OR_GROOVE_D / 2, BORE_D / 2 - 1, OR_GROOVE_X, OR_GROOVE_X + OR_GROOVE_W, 0, z), clean=False)
    return w

def _angled_seat_cuts(w):
    """The pod seat: same shape, on the 45 degree axis. Local u runs along the axis from P0; bore goes right through."""
    w = w.cut(tilt(cylx(BORE_D / 2, -40.0, U_FACE + 1)), clean=False)
    w = w.cut(tilt(cylx(RECESS_D / 2, U_CAP, U_CAP + 30.0)), clean=False)   # long: also clears the cap where it crosses the collar ring top
    w = w.cut(tilt(tubex(OR_GROOVE_D / 2, BORE_D / 2 - 1, U_FACE - 12.0, U_FACE - 12.0 + OR_GROOVE_W)), clean=False)
    return w

def gasket_band():
    """Region of the gasket ring on the curved inner face: ring about the hole axis, radial band RP .. RI + GASKET_DEPTH."""
    ring = tubex(GASKET_R1, GASKET_R0, 0, RO, 0, ZH)
    band = cylz(RI + GASKET_DEPTH, -1, H + 1).cut(cylz(RP, -2, H + 2))
    return ring.intersect(band)

def collar_halves():
    ring = cylz(RO, 0, H).cut(cylz(RI, -1, H + 1))
    front = ring.intersect(boxc(SPLIT / 2, 200, -200, 200, -1, H + 1))
    back = ring.intersect(boxc(-200, -SPLIT / 2, -200, 200, -1, H + 1))
    # boss x 2, web between them, hinge knuckles, closure tabs
    front = front.union(cylx(BOSS_D / 2, 28, X_TOP, 0, ZP))                       # straight plug-holder boss
    front = front.union(tilt(cylx(BOSS_D / 2, -25.0, U_FACE)))                     # angled pod boss
    front = front.union(boxc(30, X_TOP - 8, -18, 18, ZP, ZH))
    front = front.cut(cylz(RI, -1, H + 1))
    spigot = cylx(SPIGOT_OD / 2, 0, RI + 1.0, 0, ZH).intersect(
        cylz(RI + 1.0, -1, H + 1).cut(cylz(SPIGOT_IN_R, -2, H + 2)))
    front = front.union(spigot, clean=False)         # clean=True makes OCC return an invalid solid here
    front = front.cut(cylx(GASKET_R1, 0, RO, 0, ZH).cut(cylx(GASKET_R0, -1, RO + 1, 0, ZH))
                      .intersect(cylz(RI + GASKET_DEPTH, -1, H + 1).cut(cylz(RI - 0.5, -2, H + 2))), clean=False)
    front = _angled_seat_cuts(front)                # through the pipe wall at 45 degrees: the pod seat
    front = _seat_cuts(front, ZP, HOLDER_FLOOR_X)   # blind: the plug holder
    # hinge: front gets knuckles z 0..30 and 62..92, back the middle one 30.5..61.5
    kf = cylz(KR, 0, 30, 0, YH).union(cylz(KR, 62, H, 0, YH))
    kb = cylz(KR, 30.5, 61.5, 0, YH)
    kf_big = cylz(KR + 0.3, -0.3, 30.3, 0, YH).union(cylz(KR + 0.3, 61.7, H + 0.3, 0, YH))
    kb_big = cylz(KR + 0.3, 30.2, 61.8, 0, YH)
    front_k = front.union(kf, clean=False).cut(back, clean=False).cut(kb_big, clean=False)
    back_k = back.union(kb, clean=False).cut(front, clean=False).cut(kf_big, clean=False)
    # closure tabs on the -Y side, one on each half, magnets along X
    ft = boxc(SPLIT / 2, TAB_X, YB - 6.5, -RO + 3, TAB_Z0, TAB_Z1)
    bt = boxc(-TAB_X, -SPLIT / 2, YB - 6.5, -RO + 3, TAB_Z0, TAB_Z1)
    front_k = front_k.union(ft, clean=False)
    back_k = back_k.union(bt, clean=False)
    # magnet pockets open on the closing faces. Front tab: N-out at the first position, S-out at the second;
    # back tab is the mirror, so each facing pair attracts and the two pairs together also stop the halves sliding.
    for z in MAG_ZS:
        front_k = front_k.cut(cylx(MAG_POCKET_D / 2, SPLIT / 2 - 0.1, SPLIT / 2 + MAG_POCKET_T, MAG_Y, z), clean=False)
        back_k = back_k.cut(cylx(MAG_POCKET_D / 2, -SPLIT / 2 - MAG_POCKET_T, -SPLIT / 2 + 0.1, MAG_Y, z), clean=False)
    pin_hole = cylz(PIN_D / 2 + 0.2, -1, H + 1, 0, YH)
    return front_k.cut(pin_hole, clean=False), back_k.cut(pin_hole, clean=False)

def pin():
    return cylz(PIN_D / 2, 1, H - 1, 0, YH)

def magnet(side, z):
    """side +1 = in the front tab, -1 = in the back tab; glued to the pocket floor, 0.1 mm below the closing face."""
    x0 = SPLIT / 2 + MAG_POCKET_T - MAG_T
    return cylx(MAG_D / 2, x0, x0 + MAG_T, MAG_Y, z) if side > 0 else cylx(MAG_D / 2, -x0 - MAG_T, -x0, MAG_Y, z)

def gasket():
    ring = tubex(GASKET_R1 - 0.1, GASKET_R0 + 0.1, 0, RO, 0, ZH)
    return ring.intersect(cylz(RI + GASKET_DEPTH, -1, H + 1).cut(cylz(RP, -2, H + 2)))

def seat_orings():
    out = None
    for z in (ZH, ZP):
        r = tubex(OR_GROOVE_D / 2 - 0.05, 12.0, OR_GROOVE_X + 0.3, OR_GROOVE_X + 2.3, 0, z)
        out = r if out is None else out.union(r)
    return out

def _cap_and_body(xcap, body_d, body_l, dimple):
    """Pod or plug along +X from the origin: cap underside at xcap."""
    s = cylx(body_d / 2, xcap - body_l, xcap, 0, 0).union(cylx(CAP_D / 2, xcap, xcap + CAP_T, 0, 0))
    if dimple:
        s = s.cut(cylx(8.0, xcap + CAP_T - 1.2, xcap + CAP_T + 1, 0, 0))
    return s

def plug(angled=True, park=False):
    """Plug in the angled hole seat (default), or parked in the straight holder (park=True)."""
    if park:
        x = X_TOP - RECESS_T + PARK_DX
        return _cap_and_body(x, PLUG_BODY_D, PLUG_BODY_L, True).translate((0, 0, ZP))
    return tilt(_cap_and_body(U_CAP, PLUG_BODY_D, PLUG_BODY_L, True))

def pod():
    return tilt(_cap_and_body(U_CAP, POD_BODY_D, POD_BODY_L, False))

def plug_alone():
    """Plug on its own, axis +Z (cap up), for the single-part render."""
    return _cap_and_body(0.0, PLUG_BODY_D, PLUG_BODY_L, True).rotate((0, 0, 0), (0, 1, 0), -90).translate((0, 0, PLUG_BODY_L))

def water_film():
    """Render-only: the film of water on the inner wall (r 33.0 .. 34.5), +X half, around the hole. Not a part."""
    return cylz(RP - PIPE_WALL, ZH - 50, ZH + 50).cut(cylz(RP - PIPE_WALL - 1.5, ZH - 51, ZH + 51)).intersect(boxc(0, 60, -60, 60, ZH - 50, ZH + 50))

# ---------------- colours ----------------
C_COLLAR, C_BACK = (0.25, 0.28, 0.3, 1), (0.34, 0.37, 0.4, 1)
C_PLUG, C_POD = (0.2, 0.2, 0.22, 1), (0.85, 0.65, 0.3, 1)
C_MAG_N, C_MAG_S = (0.8, 0.15, 0.15, 1), (0.15, 0.3, 0.8, 1)
C_PIPE, C_SEAL, C_METAL = (0.95, 0.95, 0.95, 0.30), (0.1, 0.5, 0.2, 1), (0.7, 0.7, 0.72, 1)

def scene(content="empty", with_pipe=True, water=False, spine=False):
    """content: 'empty' (hole open), 'pod', 'plug' (plug in the hole), 'parked' (plug parked in the holder, hole open)."""
    front, back = collar_halves()
    a = cq.Assembly()
    add = lambda o, n, c: a.add(o, name=n, color=cq.Color(*c))
    add(front, "collar_front_half", C_COLLAR)
    add(back, "collar_back_half", C_BACK)
    add(pin(), "hinge_pin", C_METAL)
    # polarity: front tab pocket 1 N-out (red), pocket 2 S-out (blue); back tab opposite, so facing pairs attract
    for i, z in enumerate(MAG_ZS):
        add(magnet(1, z), "magnet_front_%d_%s" % (i + 1, "N" if i == 0 else "S"), C_MAG_N if i == 0 else C_MAG_S)
        add(magnet(-1, z), "magnet_back_%d_%s" % (i + 1, "S" if i == 0 else "N"), C_MAG_S if i == 0 else C_MAG_N)
    add(gasket(), "gasket_EPDM", C_SEAL)
    add(seat_orings(), "seat_oring_24x2", C_SEAL)
    if with_pipe:
        add(pipe(), "pipe_75", C_PIPE)
    if content == "pod":
        add(pod(), "pod", C_POD)
    elif content == "plug":
        add(plug(), "plug", C_PLUG)
    elif content == "parked":
        add(plug(park=True), "plug_parked", C_PLUG)
    if spine:
        add(cylz(SPINE_R, -10, H + 10).cut(cylz(SPINE_R - 1.5, -11, H + 11)), "spine_tube_33.7", (0.75, 0.55, 0.3, 1))
    if water:
        add(water_film(), "water_film_on_inner_wall", (0.2, 0.5, 0.95, 0.55))
    return a

def checks():
    f, b = collar_halves()
    # collar halves must not collide with each other, the pipe, or the pins; pod and plug must not hit the spine
    out = {}
    out["front_vs_back"] = f.intersect(b).val().Volume()
    out["collar_vs_pipe"] = (f.intersect(pipe()).val().Volume() if f.intersect(pipe()).vals() else 0.0) + \
                            (b.intersect(pipe()).val().Volume() if b.intersect(pipe()).vals() else 0.0)
    spine = cylz(SPINE_R, -10, H + 10)
    for n, o in (("pod_vs_spine", pod()), ("plug_vs_spine", plug())):
        i = o.intersect(spine)
        out[n] = i.val().Volume() if i.vals() else 0.0
    for n, o, zz in (("plug_vs_collar", plug(), ZH), ("pod_vs_collar", pod(), ZH), ("plug_parked_vs_collar", plug(park=True), ZP)):
        i = o.intersect(f)
        out[n] = i.val().Volume() if i.vals() else 0.0
    for i, z in enumerate(MAG_ZS):
        for sd, h in ((1, f), (-1, b)):
            x = magnet(sd, z).intersect(h)
            out["magnet%d_%s_overlap" % (i + 1, "front" if sd > 0 else "back")] = x.val().Volume() if x.vals() else 0.0
    # pod vs the drilled pipe (must pass the 45 mm hole without touching the pipe wall)
    pv = pod().intersect(pipe())
    out["pod_vs_pipe"] = pv.val().Volume() if pv.vals() else 0.0
    c, sn = math.cos(math.radians(TILT)), math.sin(math.radians(TILT))
    cx = P0[0] + (U_CAP - POD_BODY_L) * c                  # pod inner end face centre x
    r = POD_BODY_D / 2
    out["pod_tip_centre_x"] = cx
    out["pod_tip_min_x"] = cx - r * sn                     # point of the pod closest to the spine axis (y = 0)
    out["spine_gap_mm"] = cx - r * sn - SPINE_R
    r_in = RP - PIPE_WALL
    out["tip_edge_radius"] = math.hypot(cx, r)             # side edges (y = +-12.5) of the end face, from the pipe axis
    out["tip_edge_inside_wall_mm"] = r_in - math.hypot(cx, r)
    out["wall_x_at_pod_edge_y"] = math.sqrt(r_in ** 2 - r ** 2)   # inner wall x at y = +-12.5
    out["tip_below_wall_at_edge_mm"] = math.sqrt(r_in ** 2 - r ** 2) - cx
    out["side_edge_crosses_wall_mm_from_tip"] = (math.sqrt(r_in ** 2 - r ** 2) - cx) / c   # along the axis
    out["tip_centre_below_wall_mm"] = r_in - cx
    return out

result = scene("empty")

if __name__ == "__main__":
    for k, v in checks().items():
        print("%-24s %.3f" % (k, v))
