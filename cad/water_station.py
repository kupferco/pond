# cad/water_station.py: the SHARED WATER TESTING STATION (OpenPocket #330, plan 307 part 2 of 4). docs/water-station/README.md has the story.
# One station on the first unit, on the tank lid next to the dock. The arm pours a water sample into a funnel on its roof; the sample falls into a
# cup that holds ONE good pH probe, ONE cheap EC probe and a DS18B20 temperature probe. After the reading a small pump rinses the cup and the
# cup drains through a standpipe to the ground. The standpipe leaves a "heel" of water so the pH glass never dries out. Powered from the base battery.
# Frame: the unit frame of complete_unit.py / unit_v3_aframe.py (mm, Z up, growing pipe at x = y = 0, tank 700 x 400 x 300, lid top z = 304,
# track bottom run along X at y = -60, z = 450). Station-local numbers are written in that same frame.
# ASSUMED (nothing bought yet; marked ASSUMED where used): dock centre x = 100 on the bottom run; a DFRobot-style pH amp board (42 x 32 x 14),
# an EC board of the same size, an ESP32 dev board (52 x 28 x 14), a 12 V to 5 V buck (20 x 40 x 14), a mini peristaltic pump (rotor 34 mm round x 40),
# a 2 L rinse bottle, 6 mm OD silicone drain tube, 12 mm pH probe 140 mm long, 10 mm EC probe 110 mm long, 6 mm DS18B20 can 60 mm long.
# The arm poses (reach from the cart to the funnel) are a LATER part of the plan (arm sampling poses): this file only keeps the funnel
# 60 mm inboard of the track line, inside where the arm already reaches at the dock, and checks nothing touches the track.
import math
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- unit numbers (mirror complete_unit.py) ----------------
TW, TD, TH = 700.0, 400.0, 300.0
LID = TH + 4                     # lid top
TRACK_Y, TRACK_R, TRACK_Z = -60.0, 16.0, 450.0
GP = 33.7                        # growing pipe OD
DOCK_X = 100.0                   # ASSUMED dock centre on the bottom run; plates 40 mm either side
BAR_Z = LID + 15.0               # the 20 x 15 bar across the lid under the pipe (y +-10)

# ---------------- the station ----------------
CX, CY = 100.0, 0.0              # cup axis (under the dock)
BOX = dict(x0=60.0, x1=260.0, y0=-36.0, y1=58.0, z0=330.0, z1=443.0)     # outer; walls 3 mm; floor 330..333 clears the lid bar
WALL = 3.0
CUP_R, CUP_WALL, CUP_BOT, CUP_H = 30.0, 2.0, 3.0, 80.0
CUP_Z0 = 339.0                   # on a 6 mm stand ring over the floor
STAND_H = 40.0                   # standpipe top above the cup bottom outside face: the heel is this minus the bottom thickness
HEEL = STAND_H - CUP_BOT
PROBE_Z = 358.0                  # probe axes, 19 mm above the cup floor, 21 mm under the heel surface
PROBES = {                       # name: (y, radius, tip x, body length, colour)
    "ph_probe": (0.0, 6.0, 112.0, 125.0, (0.2, 0.35, 0.7, 1)),
    "ec_probe": (14.0, 5.0, 112.0, 100.0, (0.9, 0.7, 0.2, 1)),
    "temp_probe": (-12.0, 3.0, 112.0, 60.0, (0.72, 0.72, 0.75, 1)),
}
BOSS_X0, BOSS_X1, BOSS_Y, BOSS_Z0, BOSS_Z1 = 118.0, 134.0, 22.0, 346.0, 370.0     # flat boss on the cup wall that carries the three grommets
FUNNEL_Z_TOP = 468.0
RINSE_ML_PER_DAY = 100.0         # ASSUMED: two 50 ml flushes
BOTTLE_C, BOTTLE_R, BOTTLE_H = (235.0, 122.0), 50.0, 240.0       # 2 L bottle on the lid behind the box
DRAIN_Y_OUT = 215.0              # the drain tube leaves over the back lid edge (lid edge y = 200)
DRAIN_Z_RUN = 324.0              # the drain tube runs between lid bar top (319) and the floor (330)

COL = dict(shell=(0.93, 0.93, 0.9, 1), roof=(0.82, 0.82, 0.78, 1), cup=(0.62, 0.8, 0.95, 1), water=(0.35, 0.65, 0.95, 1),
           stand=(0.2, 0.5, 0.8, 1), grom=(0.1, 0.1, 0.1, 1), pcb=(0.1, 0.5, 0.25, 1), esp=(0.1, 0.1, 0.16, 1), buck=(0.15, 0.3, 0.7, 1),
           pump=(0.92, 0.5, 0.15, 1), drain=(0.3, 0.3, 0.35, 1), rinse=(0.8, 0.8, 0.9, 1), bottle=(0.75, 0.87, 0.97, 1),
           funnel=(0.9, 0.9, 0.9, 1), tank=(0.75, 0.78, 0.82, 1), frame=(0.55, 0.57, 0.6, 1), track=(0.7, 0.7, 0.72, 1),
           copper=(0.85, 0.5, 0.2, 1), bnc=(0.8, 0.8, 0.82, 1), ground=(0.55, 0.42, 0.3, 1), board=(0.78, 0.65, 0.45, 1))


# ---------------- helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(r, p0, p1):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))


def tube(ro, ri, p0, p1):
    return cyl(ro, p0, p1).cut(cyl(ri, tuple(a - 1e-3 * (b - a) for a, b in zip(p0, p1)), tuple(b + 1e-3 * (b - a) for a, b in zip(p0, p1))))


def hose(r, pts):
    """Solid hose of radius r along a polyline of points, with a ball at each bend."""
    out = None
    for a, b in zip(pts, pts[1:]):
        s = cyl(r, a, b)
        out = s if out is None else out.union(s)
    for p in pts[1:-1]:
        out = out.union(cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(*p), cq.Vector(0, 0, 1), -90, 90, 360)))
    return out


def vol(w):
    return sum(s.Volume() for s in w.solids().vals()) if w.solids().vals() else 0.0


def inter(a, b):
    bb, cc = a.val().BoundingBox(), b.val().BoundingBox()
    if bb.xmax < cc.xmin or cc.xmax < bb.xmin or bb.ymax < cc.ymin or cc.ymax < bb.ymin or bb.zmax < cc.zmin or cc.zmax < bb.zmin:
        return 0.0
    return vol(a.intersect(b))


# ---------------- the parts ----------------
def cup():
    """Sample cup: round, 80 mm tall, ~200 ml, bottom outlet (drain hole 7 mm), flat boss on the +x wall with three probe holes, rim cover with funnel + nozzle holes."""
    outer = cyl(CUP_R, (CX, CY, CUP_Z0), (CX, CY, CUP_Z0 + CUP_H)).union(box(CX + BOSS_X0 - 100, CX + BOSS_X1 - 100, -BOSS_Y, BOSS_Y, BOSS_Z0, BOSS_Z1))
    c = outer.cut(cyl(CUP_R - CUP_WALL, (CX, CY, CUP_Z0 + CUP_BOT), (CX, CY, CUP_Z0 + CUP_H + 1)))
    c = c.cut(cyl(3.5, (CX, CY, CUP_Z0 - 1), (CX, CY, CUP_Z0 + CUP_BOT + 1)))                       # drain outlet under the standpipe
    for name, (y, r, tipx, ln, _) in PROBES.items():
        c = c.cut(cyl(r + 0.2, (CX + 15, y, PROBE_Z), (CX + 40, y, PROBE_Z)))                          # probe hole through the wall and the boss (the grommet fills the gap)
    return c


def cup_cover():
    return (cyl(CUP_R + 2, (CX, CY, CUP_Z0 + CUP_H), (CX, CY, CUP_Z0 + CUP_H + 3))
            .cut(cyl(11, (CX, CY, CUP_Z0 + CUP_H - 1), (CX, CY, CUP_Z0 + CUP_H + 4)))
            .cut(cyl(2.2, (CX + 18, CY + 18, CUP_Z0 + CUP_H - 1), (CX + 18, CY + 18, CUP_Z0 + CUP_H + 4))))   # nozzle hole


def standpipe():
    return tube(4.5, 3.0, (CX, CY, CUP_Z0 - 3.0), (CX, CY, CUP_Z0 + STAND_H))       # pulled out by hand to empty the cup fully (calibration, cleaning)


def heel_water(cut_front=True):
    w = cyl(CUP_R - CUP_WALL - 0.3, (CX, CY, CUP_Z0 + CUP_BOT), (CX, CY, CUP_Z0 + STAND_H)).cut(cyl(4.6, (CX, CY, CUP_Z0), (CX, CY, CUP_Z0 + STAND_H + 1)))
    for name in PROBES:
        w = w.cut(probes()[name][0])
    return w.cut(grommets())


def probes():
    out = {}
    for name, (y, r, tipx, ln, col) in PROBES.items():
        body = cyl(r, (tipx, y, PROBE_Z), (tipx + ln, y, PROBE_Z))
        if name == "ph_probe":                                              # glass bulb on the tip
            body = body.union(cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(tipx, y, PROBE_Z), cq.Vector(1, 0, 0), -90, 90, 360)))
        out[name] = (body, col)
    out["ph_bnc"] = (cyl(5.0, (112 + 125, 0, PROBE_Z), (112 + 125 + 15, 0, PROBE_Z)), COL["bnc"])
    out["ec_cable"] = (cyl(2.0, (112 + 100, 14, PROBE_Z), (112 + 100 + 25, 14, PROBE_Z)), (0.1, 0.1, 0.1, 1))
    out["temp_cable"] = (cyl(1.5, (112 + 60, -12, PROBE_Z), (112 + 60 + 60, -12, PROBE_Z)), (0.1, 0.1, 0.1, 1))
    return out


def grommets():
    g = None
    for name, (y, r, tipx, ln, _) in PROBES.items():
        s = tube(r + 3.0, r, (CX + 24, y, PROBE_Z), (BOSS_X1 + CX - 100, y, PROBE_Z))      # silicone grommet through the boss
        g = s if g is None else g.union(s)
    return g


def shell():
    b = BOX
    outer = box(b["x0"], b["x1"], b["y0"], b["y1"], b["z0"], b["z1"] - 3)                    # roof is a separate plate
    inner = box(b["x0"] + WALL, b["x1"] - WALL, b["y0"] + WALL, b["y1"] - WALL, b["z0"] + WALL, b["z1"] - 3 + 1)
    s = outer.cut(inner)
    s = s.cut(cyl(4.0, (CX, CY, b["z0"] - 1), (CX, CY, b["z0"] + WALL + 1)))                 # drain tube hole
    s = s.cut(cyl(3.0, (BOTTLE_C[0], b["y1"] - WALL - 1, 345), (BOTTLE_C[0], b["y1"] + 1, 345)))   # rinse inlet hole in the back wall
    s = s.cut(box(b["x0"] + WALL, b["x1"] - WALL, b["y0"] - 1, b["y0"] + WALL + 0.5, b["z0"] + WALL, b["z1"] - 4))      # the front is a separate door; without it the box is open (pictures)
    return s


def door():
    b = BOX
    return box(b["x0"] + WALL, b["x1"] - WALL, b["y0"], b["y0"] + WALL, b["z0"] + WALL, b["z1"] - 4)


def roof():
    b = BOX
    r = box(b["x0"] - 8, b["x1"] + 8, b["y0"], b["y1"] + 8, b["z1"] - 3, b["z1"])         # sun shade: 8 mm overhang left, right and back; none to the front (track line is 8 mm away)
    return r.cut(cyl(13.0, (CX, CY, b["z1"] - 4), (CX, CY, b["z1"] + 1)))


def funnel():
    neck = tube(13.0, 11.0, (CX, CY, CUP_Z0 + CUP_H + 3), (CX, CY, BOX["z1"] + 3))
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(26.0, 11.0, FUNNEL_Z_TOP - (BOX["z1"] + 3), cq.Vector(CX, CY, BOX["z1"] + 3), cq.Vector(0, 0, 1)))
    inner = cq.Workplane("XY").add(cq.Solid.makeCone(24.0, 11.0, FUNNEL_Z_TOP - (BOX["z1"] + 3) + 1e-3, cq.Vector(CX, CY, BOX["z1"] + 3), cq.Vector(0, 0, 1)))
    return neck.union(cone.cut(inner))


def electronics():
    """Boards stand on the back wall (y 38..52), probe tails run under them. Returns dict name -> (shape, colour)."""
    y0, y1 = 38.0, 52.0
    return {
        "ph_board": (box(205, 247, y0, y1, 380, 412), COL["pcb"]),          # the pH amp is next to the BNC end of the pH probe
        "ec_board": (box(160, 200, y0, y1, 380, 410), COL["pcb"]),
        "esp32": (box(140, 192, y0, y1, 340, 368), COL["esp"]),
        "buck_12v_5v": (box(196, 216, y0, y1, 340, 380), COL["buck"]),
        "rinse_pump": (cyl(17.0, (BOTTLE_C[0], 36.0, 352), (BOTTLE_C[0], 52.0, 352)).union(box(BOTTLE_C[0] - 17, BOTTLE_C[0] + 17, 36.0, 52.0, 335, 352)), COL["pump"]),
    }


def tubes():
    z_n = CUP_Z0 + CUP_H + 8
    b = BOX
    ex = BOTTLE_C[0]
    return {
        "drain_tube": (hose(3.0, [(CX, CY, CUP_Z0 - 3.0), (CX, CY, DRAIN_Z_RUN), (CX, DRAIN_Y_OUT, DRAIN_Z_RUN), (CX, DRAIN_Y_OUT, 5.0)]), COL["drain"]),
        "rinse_nozzle_tube": (hose(2.0, [(ex + 15, 44.0, 352.0), (ex + 15, 44.0, z_n), (CX + 18, CY + 18, z_n), (CX + 18, CY + 18, CUP_Z0 + CUP_H - 12)]), COL["rinse"]),
        "rinse_inlet_tube": (hose(2.0, [(ex, BOTTLE_C[1] - BOTTLE_R - 2, 345.0), (ex, 44.0, 345.0)]), COL["rinse"]),
    }


def bottle():
    ex, ey = BOTTLE_C
    body = cyl(BOTTLE_R, (ex, ey, LID), (ex, ey, LID + BOTTLE_H))
    return body.union(cyl(18.0, (ex, ey, LID + BOTTLE_H), (ex, ey, LID + BOTTLE_H + 15)))


def station_parts(door_on=False, cutaway=True):
    """dict name -> (shape, colour). door_on=False draws the box with the front door off so the inside shows; cutaway=True cuts the front of the cup away."""
    p = {}
    p["ws_shell"] = (shell(), COL["shell"])
    if door_on:
        p["ws_door"] = (door(), COL["shell"])
    p["ws_roof"] = (roof(), COL["roof"])
    c, cv, w = cup(), cup_cover(), heel_water()
    gr = grommets()
    if cutaway:
        keep = box(CX - 60, CX + 60, -8.0, 60.0, CUP_Z0 - 10, CUP_Z0 + CUP_H + 10)             # front part of the cup (y < -8) cut away
        c = c.intersect(keep)
        w = w.intersect(keep)
    p["ws_cup"] = (c, COL["cup"])
    p["ws_heel_water"] = (w, COL["water"])
    p["ws_cup_cover"] = (cv, COL["cup"])
    p["ws_standpipe"] = (standpipe(), COL["stand"])
    p["ws_grommets"] = (gr, COL["grom"])
    p["ws_funnel"] = (funnel(), COL["funnel"])
    for n, v in probes().items():
        p["ws_" + n] = v
    for n, v in electronics().items():
        p["ws_" + n] = v
    for n, v in tubes().items():
        p["ws_" + n] = v
    p["ws_rinse_bottle"] = (bottle(), COL["bottle"])
    return p


# ---------------- the unit around it (cropped, simplified) ----------------
WIN = box(-60, 340, -150, 270, -10, 560)


def context_parts():
    """Lid corner of the first unit around the station: tank and lid, growing pipe, lid bar, back strut, tray stand-in, braces, track bottom run, dock plates, the ground."""
    p = {}
    p["tank"] = (box(-TW / 2, TW / 2, -TD / 2, TD / 2, 0, TH + 4), COL["tank"])
    p["growing_pipe"] = (cyl(GP / 2, (0, 0, LID), (0, 0, 700)), (0.9, 0.9, 0.9, 1))
    p["lid_bar"] = (box(-340, 340, -10, 10, LID, BAR_Z), COL["frame"])
    p["lid_back_strut"] = (box(-15, 15, 0, 190, LID, LID + 5), COL["frame"])
    p["seedling_storage"] = (box(70, 310, -180, -70, LID, LID + 16), (0.35, 0.5, 0.75, 1))
    for sx in (1, -1):
        p["brace_%s" % ("r" if sx > 0 else "l")] = (cyl(8.0, (sx * 340, 0, LID), (sx * 21, 0, 1215)), COL["frame"])
    p["track_bottom_run"] = (cyl(TRACK_R, (-140, TRACK_Y, TRACK_Z), (140, TRACK_Y, TRACK_Z)), COL["track"])
    arc = (cq.Workplane("XZ", origin=(0, TRACK_Y, 0)).moveTo(140, TRACK_Z).radiusArc((290, TRACK_Z + 150), -150))
    prof = cq.Workplane("YZ", origin=(140, TRACK_Y, TRACK_Z)).circle(TRACK_R)
    p["track_corner"] = (prof.sweep(arc), COL["track"])
    for dx in (-40, 40):
        p["dock_plate_%s" % ("minus" if dx > 0 else "plus")] = (
            cq.Workplane("YZ").circle(TRACK_R + 3).circle(TRACK_R).extrude(40).translate((DOCK_X + dx - 20, TRACK_Y, TRACK_Z)), COL["copper"])
    p["ground"] = (box(-60, 340, -150, 270, -4, 0), COL["ground"])
    out = {}
    for n, (s, c) in p.items():
        t = s.intersect(WIN)
        if t.solids().vals():
            out[n] = (t, c)
    return out


def scene(kind="unit", door_on=False, cutaway=True):
    """kind: 'unit' (station in the unit), 'close' (station only, on the lid, same frame), 'bench' (bench rig: no box, on a plywood board)."""
    a = cq.Assembly()
    if kind == "unit":
        for n, (s, c) in context_parts().items():
            a.add(s, name=n, color=cq.Color(*c))
    if kind == "close":
        a.add(box(20, 300, -60, 160, LID - 4, LID), name="lid_stand_in", color=cq.Color(*COL["tank"]))
    if kind == "bench":
        return bench()
    for n, (s, c) in station_parts(door_on, cutaway).items():
        a.add(s, name=n, color=cq.Color(*c))
    return a


# ---------------- bench rig ----------------
def bench():
    """The same cup, probes, boards, pump and bottle on a 450 x 300 ply board, no box, no unit. A person pours the sample by hand through the funnel.
    The drain tube runs into a bucket on the floor. Same coordinates as the station, so the same numbers apply."""
    a = cq.Assembly()
    sp = station_parts(door_on=False, cutaway=True)
    for n, (s, c) in sp.items():
        if n in ("ws_shell", "ws_roof", "ws_door"):
            continue
        a.add(s, name="bench_" + n[3:], color=cq.Color(*c))
    a.add(box(40, 400, -80, 150, 318, 330), name="bench_ply_board", color=cq.Color(*COL["board"]))
    a.add(box(CX - 33, CX + 33, -36, 36, 330, 339), name="bench_cup_stand", color=cq.Color(*COL["board"]))
    # clip-on stands for the boards (the box wall is not there): one upright plate at y 52..55
    a.add(box(135, 262, 52, 55, 333, 415), name="bench_back_plate", color=cq.Color(*COL["board"]))
    # funnel support: a ring clip on a post so the funnel sits on the cup like in the box (the roof is not there)
    a.add(box(CX - 36, CX - 30, -40, -34, 330, 440), name="bench_funnel_post", color=cq.Color(*COL["board"]))
    a.add(box(CX - 36, CX + 6, -40, -34, 436, 440), name="bench_funnel_arm", color=cq.Color(*COL["board"]))
    # the drain goes to a bucket (bench only; on the unit it goes to the soil)
    bucket = cyl(110.0, (CX, DRAIN_Y_OUT - 120, 0), (CX, DRAIN_Y_OUT - 120, 260)).cut(cyl(106.0, (CX, DRAIN_Y_OUT - 120, 4), (CX, DRAIN_Y_OUT - 120, 261)))
    a.add(bucket, name="bench_bucket", color=cq.Color(0.2, 0.45, 0.2, 1))
    a.add(box(-60, 460, -150, 270, -4, 0), name="bench_floor", color=cq.Color(*COL["ground"]))
    a.add(box(-60, 470, -90, 160, 300, 318), name="bench_table_top", color=cq.Color(0.65, 0.5, 0.35, 1))
    return a


# ---------------- checks ----------------
def check():
    out = {}
    sp = station_parts(door_on=True, cutaway=False)
    ctx = context_parts()
    # cup volumes (ml)
    inner_r = CUP_R - CUP_WALL
    out["cup_volume_ml"] = math.pi * inner_r ** 2 * (CUP_H - CUP_BOT) / 1000.0
    out["heel_volume_ml"] = math.pi * inner_r ** 2 * HEEL / 1000.0
    out["heel_depth_mm"] = HEEL
    out["probe_depth_under_heel_surface_mm"] = {n: (CUP_Z0 + STAND_H) - (PROBE_Z + r) for n, (y, r, tx, ln, c) in PROBES.items()}
    out["probe_height_over_cup_floor_mm"] = {n: PROBE_Z - r - (CUP_Z0 + CUP_BOT) for n, (y, r, tx, ln, c) in PROBES.items()}
    out["probe_gap_to_each_other_mm"] = {"ph-ec": 14.0 - 6.0 - 5.0, "ph-temp": 12.0 - 6.0 - 3.0}
    out["rinse_bottle_ml"] = math.pi * (BOTTLE_R - 2) ** 2 * (BOTTLE_H - 10) / 1000.0
    out["rinse_bottle_days_at_%dml_per_day" % RINSE_ML_PER_DAY] = out["rinse_bottle_ml"] / RINSE_ML_PER_DAY
    # fit
    b = BOX
    out["box_mm"] = (b["x1"] - b["x0"], b["y1"] - b["y0"], b["z1"] - b["z0"])
    out["box_front_gap_to_track_mm"] = (b["y0"] - (TRACK_Y + TRACK_R))
    out["funnel_gap_to_track_edge_mm"] = (CY - 26.0) - (TRACK_Y + TRACK_R)
    out["funnel_distance_from_track_axis_mm"] = CY - TRACK_Y
    out["roof_top_below_track_top_mm"] = (TRACK_Z + TRACK_R) - (b["z1"])
    out["funnel_top_above_track_axis_mm"] = FUNNEL_Z_TOP - TRACK_Z
    out["funnel_x_from_dock_centre_mm"] = CX - DOCK_X
    out["box_floor_over_lid_bar_mm"] = b["z0"] - BAR_Z
    out["drain_tube_run_over_lid_bar_mm"] = (DRAIN_Z_RUN - 3.0) - BAR_Z
    out["drain_tube_outside_tank_mm"] = DRAIN_Y_OUT - TD / 2
    out["drain_tube_length_mm"] = (CUP_Z0 - 3.0 - DRAIN_Z_RUN) + (DRAIN_Y_OUT - CY) + (DRAIN_Z_RUN - 5.0)
    out["drain_tube_hits_tank_mm3"] = inter(sp["ws_drain_tube"][0], ctx["tank"][0])
    out["bottle_over_back_strut_mm3"] = inter(sp["ws_rinse_bottle"][0], ctx["lid_back_strut"][0])
    # nothing in the unit is touched except what the box stands on (the lid bar is cleared by 11 mm, the lid by 26 mm)
    hit = {}
    for n, (s, c) in sp.items():
        for m, (o, _) in ctx.items():
            if m in ("ground",):
                continue
            v = inter(s, o)
            if v > 1e-3:
                hit["%s vs %s" % (n, m)] = round(v, 2)
    out["station_vs_unit_clashes_mm3"] = hit
    # parts of the station that must not overlap each other (allowed: probe through grommet through boss through cup wall; funnel through roof and cover; tubes through walls/pump/bottle; standpipe through cup floor)
    ok_pairs = {("ws_cup", "ws_grommets"), ("ws_cup", "ws_standpipe"), ("ws_cup", "ws_cup_cover"), ("ws_funnel", "ws_cup_cover"), ("ws_funnel", "ws_roof"),
                ("ws_grommets", "ws_ph_probe"), ("ws_grommets", "ws_ec_probe"), ("ws_grommets", "ws_temp_probe"), ("ws_heel_water", "ws_standpipe"),
                ("ws_drain_tube", "ws_standpipe"), ("ws_drain_tube", "ws_cup"), ("ws_drain_tube", "ws_shell"), ("ws_rinse_inlet_tube", "ws_shell"), ("ws_rinse_inlet_tube", "ws_rinse_pump"),
                ("ws_rinse_nozzle_tube", "ws_rinse_pump"), ("ws_rinse_nozzle_tube", "ws_cup_cover"), ("ws_rinse_nozzle_tube", "ws_cup"), ("ws_rinse_inlet_tube", "ws_rinse_bottle"),
                ("ws_cup", "ws_heel_water"), ("ws_cup_cover", "ws_roof"), ("ws_standpipe", "ws_cup_cover")}
    names = list(sp)
    clash = {}
    for i, n in enumerate(names):
        for m in names[i + 1:]:
            if (n, m) in ok_pairs or (m, n) in ok_pairs:
                continue
            v = inter(sp[n][0], sp[m][0])
            if v > 1e-3:
                clash["%s vs %s" % (n, m)] = round(v, 2)
    out["station_internal_clashes_mm3"] = clash
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(check(), indent=1, default=str))
