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
#   - PLUG HOLDER: a second, blind socket of the same shape 44 mm straight above the hole, on the same boss axis. A plug
#     parked there stands 5 mm further out than a seated plug (blind floor), so you can see it is parked. The
#     robot takes the plug from the hole and moves it straight up 44 mm (no turning), and back.
# Frame: pipe axis = Z, hole axis = +X, collar bottom at z = 0, hole centre z = ZH, holder centre z = ZP.
# ASSUMED (no decision in the repo): pod = 25 mm body x 32 + 34 mm cap x 8 (overall 40, as pod_store.py: 25 x 40);
#   pipe 75 mm OD, 3 mm wall (pod_store_reach.py, unit_v3_*.py); spine tube 33.7 mm in the pipe (unit_v3_dimensioned.py);
#   holes 100 mm apart along the pipe (one collar of 92 mm per hole). Real hole positions are not in the repo yet.
# PRINT: ASA (or PETG) only, outdoors / UV, NOT PLA. Print the halves lying on the split face, boss pointing up,
#   0.2 mm layers, 4 perimeters, 40 % infill. Plug: ASA, black (light-tight), print standing on the cap. Gaskets: EPDM.
# DRILL: 29 mm through ONE wall of the pipe (a 29 mm hole saw / step drill), deburr. Hole centres 24 mm above the
#   collar's bottom edge, 100 mm pitch (ASSUMED).
import os
import sys
import math
import cadquery as cq

# ---------------- pipe ----------------
RP, PIPE_WALL = 37.5, 3.0              # 75 mm OD, 3 mm wall (repo)
SPINE_R = 33.7 / 2                      # spine tube inside the pipe (repo)
DRILL_D = 29.0                          # drilled hole in the pipe
# ---------------- collar ----------------
FIT = 0.1                               # bore clearance on the pipe
RI = RP + FIT
WALL = 5.0
RO = RI + WALL
H = 92.0
ZH, ZP = 24.0, 68.0                     # hole centre, plug-holder centre (44 mm apart)
SPLIT = 1.0                             # gap between the halves at the YZ plane; the magnets pull it closed to about 1.2 mm
BOSS_D = 40.0
X_TOP = 54.0                            # seat face
BORE_D = 26.0
RECESS_D, RECESS_T = 35.2, 2.0
OR_GROOVE_D, OR_GROOVE_W, OR_GROOVE_X = 28.6, 2.6, 42.0   # seat O-ring 24 x 2: groove x 42..44.6
SPIGOT_OD, SPIGOT_ID = 28.6, BORE_D     # in the 29 mm hole: 0.2 mm clearance
SPIGOT_IN_R = RP - 2.5                  # spigot tip radius (35): 2.5 mm into the 3 mm wall
GASKET_R0, GASKET_R1 = 16.5, 19.0       # gasket cord ring (mean dia 35.5, 2.5 cord)
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

def pipe():
    p = cylz(RP, -20, H + 20).cut(cylz(RP - PIPE_WALL, -21, H + 21))
    return p.cut(cylx(DRILL_D / 2, 0, RP + 5, 0, ZH))

def _seat_cuts(w, z, x_floor):
    w = w.cut(cylx(BORE_D / 2, x_floor, X_TOP + 1, 0, z), clean=False)
    w = w.cut(cylx(RECESS_D / 2, X_TOP - RECESS_T, X_TOP + 1, 0, z), clean=False)
    w = w.cut(tubex(OR_GROOVE_D / 2, BORE_D / 2 - 1, OR_GROOVE_X, OR_GROOVE_X + OR_GROOVE_W, 0, z), clean=False)
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
    for z in (ZH, ZP):
        front = front.union(cylx(BOSS_D / 2, 28, X_TOP, 0, z))
    front = front.union(boxc(30, X_TOP - 8, -16, 16, ZH, ZP))
    front = front.cut(cylz(RI, -1, H + 1))
    spigot = cylx(SPIGOT_OD / 2, 0, RI + 1.0, 0, ZH).intersect(
        cylz(RI + 1.0, -1, H + 1).cut(cylz(SPIGOT_IN_R, -2, H + 2)))
    front = front.union(spigot, clean=False)         # clean=True makes OCC return an invalid solid here
    front = front.cut(cylx(GASKET_R1, 0, RO, 0, ZH).cut(cylx(GASKET_R0, -1, RO + 1, 0, ZH))
                      .intersect(cylz(RI + GASKET_DEPTH, -1, H + 1).cut(cylz(RI - 0.5, -2, H + 2))), clean=False)
    front = _seat_cuts(front, ZH, 20.0)             # through the pipe wall: the pod seat
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

def _cap_and_body(xcap, z, body_d, body_l, dimple):
    s = cylx(body_d / 2, xcap - body_l, xcap, 0, z).union(cylx(CAP_D / 2, xcap, xcap + CAP_T, 0, z))
    if dimple:
        s = s.cut(cylx(8.0, xcap + CAP_T - 1.2, xcap + CAP_T + 1, 0, z))
    return s

def plug(xcap=X_TOP - RECESS_T, z=ZH):
    return _cap_and_body(xcap, z, PLUG_BODY_D, PLUG_BODY_L, True)

def pod(xcap=X_TOP - RECESS_T, z=ZH):
    return _cap_and_body(xcap, z, POD_BODY_D, POD_BODY_L, False)

def plug_alone():
    """Plug on its own, axis +Z (cap up), for the single-part render."""
    return plug(0.0, 0.0).rotate((0, 0, 0), (0, 1, 0), -90).translate((0, 0, PLUG_BODY_L))

# ---------------- colours ----------------
C_COLLAR, C_BACK = (0.25, 0.28, 0.3, 1), (0.34, 0.37, 0.4, 1)
C_PLUG, C_POD = (0.2, 0.2, 0.22, 1), (0.85, 0.65, 0.3, 1)
C_MAG_N, C_MAG_S = (0.8, 0.15, 0.15, 1), (0.15, 0.3, 0.8, 1)
C_PIPE, C_SEAL, C_METAL = (0.95, 0.95, 0.95, 0.30), (0.1, 0.5, 0.2, 1), (0.7, 0.7, 0.72, 1)

def scene(content="empty", with_pipe=True):
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
        add(plug(X_TOP - RECESS_T + PARK_DX, ZP), "plug_parked", C_PLUG)
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
    for n, o, zz in (("plug_vs_collar", plug(), ZH), ("pod_vs_collar", pod(), ZH), ("plug_parked_vs_collar", plug(X_TOP - RECESS_T + PARK_DX, ZP), ZP)):
        i = o.intersect(f)
        out[n] = i.val().Volume() if i.vals() else 0.0
    for i, z in enumerate(MAG_ZS):
        for sd, h in ((1, f), (-1, b)):
            x = magnet(sd, z).intersect(h)
            out["magnet%d_%s_overlap" % (i + 1, "front" if sd > 0 else "back")] = x.val().Volume() if x.vals() else 0.0
    out["spine_gap_mm"] = (X_TOP - RECESS_T - POD_BODY_L) - SPINE_R
    return out

result = scene("empty")

if __name__ == "__main__":
    for k, v in checks().items():
        print("%-24s %.3f" % (k, v))
