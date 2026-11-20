# cad/water_station.py: the SHARED WATER TESTING STATION (OpenPocket #330, plan 307 part 2 of 4). docs/water-station/README.md has the story.
# One station on the first unit, on the tank lid next to the dock. v2 (owner redesign, follow-up of 19 Nov 2026): NO rinse bottle, NO rinse pump, NO funnel.
# The cart carries ONE peristaltic pump and a coiled polyurethane recoil tube with a nozzle (cad/water_sampler.py). The tube itself holds the sample.
# The arm plugs the nozzle into a SOCKET on the station roof right above the test cup; the pump runs in REVERSE: the first part of the sample flushes the
# previous sample out over the standpipe, the rest stays in the cup (keeping the pH glass wet) until the next test. The cup holds ONE good pH probe, ONE cheap
# EC probe and a DS18B20 temperature probe and drains through a standpipe to the ground. Each unit has only a passive socket on its lid with a dip tube to the
# tank floor (no pump, no power; a little dripping is accepted). Powered from the base battery.
# Frame: the unit frame of complete_unit.py / unit_v3_aframe.py (mm, Z up, growing pipe at x = y = 0, tank 700 x 400 x 300, lid top z = 304,
# track bottom run along X at y = -60, z = 450). Station-local numbers are written in that same frame.
# ASSUMED (nothing bought yet; marked ASSUMED where used): dock centre x = 100 on the bottom run; a DFRobot-style pH amp board (42 x 32 x 14),
# an EC board of the same size, an ESP32 dev board (52 x 28 x 14), a 12 V to 5 V buck (20 x 40 x 14), 
# 6 mm OD silicone drain tube, 12 mm pH probe 140 mm long, 10 mm EC probe 110 mm long, 6 mm DS18B20 can 60 mm long.
# The arm poses (reach from the cart to the socket) are a LATER part of the plan (arm sampling poses): this file only keeps the socket
# 60 mm inboard of the track line, inside where the arm already reaches at the dock, and checks nothing touches the track.
import math
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts import water_connector as wc
from parts.common import hose, vol, inter   # noqa: F401
from parts.unit import unit_parts
from parts.unit_dims import TW, TD, TH, LID, TR as TRACK_R, LOOP_Y as TRACK_Y, ZB as TRACK_Z, GP   # the unit's numbers, defined once (they were copied here; GP was the spine's 33.7 by mistake)
from parts.lid_items import seedling_storage
from parts.water_volume import COLOR_WATER

# ---------------- unit numbers: imported from cad/parts/unit_dims.py (single source) ----------------
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
OFF_Y = 50.0                     # v2: the whole station is moved 40 mm inboard (+y, away from the track): the cart's omni sleeve is R 61 round the 16 mm track pipe, so the
                                 # box front (was y -36, 24 mm from the track axis) hit it. Now the front is at y +14, 74 mm from the track axis (13 mm clear of R 61). Found by water_assembly.py.
                                 # 19 Nov follow-up: 40 -> 50. Main's #315 bottom support post (x 115..135, y -10..6) and its base plate (x 103..147, y -20..16) clashed with the box and the front legs at 40;
                                 # at 50 the box front is 8 mm clear of the post and the front legs (y 22) 6 mm clear of the base plate. Found by water_station_position.py.
SOCKET_Z_TOP = BOX["z1"]         # 19 Nov follow-up: the female socket is FLUSH with the top of the roof (443). It used to be a raised funnel up to 462. See water_connector.py
SAMPLE_ML = 70.0                 # ASSUMED sample size metered by pump turns (owner: about 50 to 100 ml)
UNIT_SOCKET = (20.0, -105.0)     # the unit's own passive socket on the lid (x, y): 80 mm from the dock centre, 45 mm OUTBOARD of the track axis (y -60), so its 20 mm mouth radius leaves the track's footprint 8 mm clear (it used to sit at y -48, right under the track); clear of the pipe (y +-17), lid bar (y +-10), seedling storage (x >= 70) and the station box (x >= 60)
UNIT_INSERT_D = 8.0              # depth of the round insert let into the lid
DRAIN_Y_OUT = 215.0              # the drain tube leaves over the back lid edge (lid edge y = 200)
DRAIN_Z_RUN = 324.0              # the drain tube runs between lid bar top (319) and the floor (330)

COL = dict(shell=(0.93, 0.93, 0.9, 1), roof=(0.82, 0.82, 0.78, 1), cup=(0.62, 0.8, 0.95, 1), water=(0.35, 0.65, 0.95, 1),
           stand=(0.2, 0.5, 0.8, 1), grom=(0.1, 0.1, 0.1, 1), pcb=(0.1, 0.5, 0.25, 1), esp=(0.1, 0.1, 0.16, 1), buck=(0.15, 0.3, 0.7, 1),
           drain=(0.3, 0.3, 0.35, 1), sock=(0.95, 0.95, 0.95, 1), dip=(0.3, 0.3, 0.35, 1),
           tank=(0.75, 0.78, 0.82, 1), frame=(0.55, 0.57, 0.6, 1), track=(0.7, 0.7, 0.72, 1),
           copper=(0.85, 0.5, 0.2, 1), bnc=(0.8, 0.8, 0.82, 1), ground=(0.55, 0.42, 0.3, 1), board=(0.78, 0.65, 0.45, 1))


# ---------------- helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(r, p0, p1):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))


def tube(ro, ri, p0, p1):
    return cyl(ro, p0, p1).cut(cyl(ri, tuple(a - 1e-3 * (b - a) for a, b in zip(p0, p1)), tuple(b + 1e-3 * (b - a) for a, b in zip(p0, p1))))


def cup():
    """Sample cup: round, 80 mm tall, ~200 ml, bottom outlet (drain hole 7 mm), flat boss on the +x wall with three probe holes, rim cover with the socket hole."""
    outer = cyl(CUP_R, (CX, CY, CUP_Z0), (CX, CY, CUP_Z0 + CUP_H)).union(box(CX + BOSS_X0 - 100, CX + BOSS_X1 - 100, -BOSS_Y, BOSS_Y, BOSS_Z0, BOSS_Z1))
    c = outer.cut(cyl(CUP_R - CUP_WALL, (CX, CY, CUP_Z0 + CUP_BOT), (CX, CY, CUP_Z0 + CUP_H + 1)))
    c = c.cut(cyl(3.5, (CX, CY, CUP_Z0 - 1), (CX, CY, CUP_Z0 + CUP_BOT + 1)))                       # drain outlet under the standpipe
    for name, (y, r, tipx, ln, _) in PROBES.items():
        c = c.cut(cyl(r + 0.2, (CX + 15, y, PROBE_Z), (CX + 40, y, PROBE_Z)))                          # probe hole through the wall and the boss (the grommet fills the gap)
    return c


def cup_cover():
    return (cyl(CUP_R + 2, (CX, CY, CUP_Z0 + CUP_H), (CX, CY, CUP_Z0 + CUP_H + 3))
            .cut(cyl(11, (CX, CY, CUP_Z0 + CUP_H - 1), (CX, CY, CUP_Z0 + CUP_H + 4))))      # hole under the socket (the nozzle tip drips through it)


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
    s = s.cut(box(b["x0"] + WALL, b["x1"] - WALL, b["y0"] - 1, b["y0"] + WALL + 0.5, b["z0"] + WALL, b["z1"] - 4))      # the front is a separate door; without it the box is open (pictures)
    return s


def door():
    b = BOX
    return box(b["x0"] + WALL, b["x1"] - WALL, b["y0"], b["y0"] + WALL, b["z0"] + WALL, b["z1"] - 4)


LEG = 20.0                       # v3: four printed 20 x 20 legs carry the box from the lid up to its floor (no gap, no floating); the drain tube runs between them
LEG_XS = (60.0, 240.0)           # leg x0 (leg is LEG wide); the drain tube is at x = 100, so it passes between the legs
LEG_YS = (-28.0, 30.0)           # station-local y0; after OFF_Y the front legs stand at y 22..42, clear of the lid bar (y +-10)


def legs():
    """Four printed legs from the tank lid (z 304) to the box floor underside (z 330). Union of 4 boxes; they touch the lid and the floor (face contact)."""
    out = None
    for x0 in LEG_XS:
        for y0 in LEG_YS:
            b = box(x0, x0 + LEG, y0, y0 + LEG, LID, BOX["z0"])
            out = b if out is None else out.union(b)
    return out


def roof():
    b = BOX
    r = box(b["x0"] - 8, b["x1"] + 8, b["y0"], b["y1"] + 8, b["z1"] - 3, b["z1"])         # sun shade: 8 mm overhang left, right and back; none to the front (track line is 8 mm away)
    return r.cut(cyl(13.0, (CX, CY, b["z1"] - 4), (CX, CY, b["z1"] + 1)))


def socket():
    """Female socket FLUSH with the roof top (z 443): a plug in the roof hole from the cup cover up to the roof top, a plain round hole through it with a slight recess at the top,
    right above the cup. Nothing sticks up. The cart's male nozzle (water_connector.py) pushes straight in from above, friction holds it, the sample drips into the cup."""
    z0 = CUP_Z0 + CUP_H + 3
    plug = cyl(13.0, (CX, CY, z0), (CX, CY, SOCKET_Z_TOP))
    return plug.cut(wc.female_cut(CX, CY, SOCKET_Z_TOP, +1).union(wc._cyl(wc.HOLE_R, z0 - 1, SOCKET_Z_TOP, CX, CY)))


def unit_socket():
    """The unit's own passive female socket, FLUSH with the top of the tank lid (z 304): a round insert let into the lid (the lid is cut for it in context_parts), a plain hole with a slight
    recess, and a 6 mm dip tube down to 8 mm over the tank floor. No pump, no power. The nozzle pushes straight in from above, the cart pump draws the sample up through the dip tube.
    A little dripping is accepted. (Frame: the unit frame.)"""
    x, y = UNIT_SOCKET
    body = cyl(13.0, (x, y, LID - UNIT_INSERT_D), (x, y, LID)).cut(wc.female_cut(x, y, LID, +1).union(wc._cyl(wc.HOLE_R, LID - UNIT_INSERT_D - 1, LID, x, y)))
    dip = tube(3.0, 2.0, (x, y, 8.0), (x, y, LID - UNIT_INSERT_D - 8.0))      # stops 8 mm under the insert: that 8 mm of open bore takes the end of the spigot
    return {"unit_socket": (body, COL["sock"]), "unit_dip_tube": (dip, COL["dip"])}


def electronics():
    """Boards stand on the back wall (y 38..52), probe tails run under them. Returns dict name -> (shape, colour)."""
    y0, y1 = 38.0, 52.0
    return {
        "ph_board": (box(205, 247, y0, y1, 380, 412), COL["pcb"]),          # the pH amp is next to the BNC end of the pH probe
        "ec_board": (box(160, 200, y0, y1, 380, 410), COL["pcb"]),
        "esp32": (box(140, 192, y0, y1, 340, 368), COL["esp"]),
        "buck_12v_5v": (box(196, 216, y0, y1, 340, 380), COL["buck"]),
    }


def tubes():
    b = BOX
    return {
        "drain_tube": (hose(3.0, [(CX, CY, CUP_Z0 - 3.0), (CX, CY, DRAIN_Z_RUN), (CX, DRAIN_Y_OUT, DRAIN_Z_RUN), (CX, DRAIN_Y_OUT, 5.0)]), COL["drain"]),
    }


def station_parts(door_on=False, cutaway=True, dy=None):
    """dict name -> (shape, colour). door_on=False draws the box with the front door off so the inside shows; cutaway=True cuts the front of the cup away."""
    p = {}
    p["ws_shell"] = (shell(), COL["shell"])
    if door_on:
        p["ws_door"] = (door(), COL["shell"])
    p["ws_roof"] = (roof(), COL["roof"])
    p["ws_legs"] = (legs(), COL["frame"])
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
    p["ws_socket"] = (socket(), COL["sock"])
    for n, v in probes().items():
        p["ws_" + n] = v
    for n, v in electronics().items():
        p["ws_" + n] = v
    for n, v in tubes().items():
        p["ws_" + n] = v
    dy = OFF_Y if dy is None else dy
    return {n: (sh.translate((0, dy, 0)), c) for n, (sh, c) in p.items()}


# ---------------- the unit around it (cropped, simplified) ----------------
WIN = box(-60, 340, -150, 270, -10, 560)


def context_parts():
    """Lid corner of the first unit around the station, cropped to WIN. Every unit part comes from cad/parts/ (parts.unit.unit_parts): tank, water volume, lid,
    growing pipe, lid bars, A-frame legs, track loop, seedling storage. Only the dock plates and the ground are the station's own."""
    keep = ("tank", "water_volume", "lid", "growing_pipe", "base_bar_and_lid_plates", "lower_aframe_and_back_strut_16mm", "track_loop")
    p = {}
    for n, s, c in unit_parts():
        if n in keep:
            if n == "lid":     # pocket in the lid for the flush socket insert
                s = s.cut(cyl(13.0, (UNIT_SOCKET[0], UNIT_SOCKET[1], LID - UNIT_INSERT_D), (UNIT_SOCKET[0], UNIT_SOCKET[1], LID + 1))).cut(cyl(3.0, (UNIT_SOCKET[0], UNIT_SOCKET[1], 8.0), (UNIT_SOCKET[0], UNIT_SOCKET[1], LID)))
            p[n] = (s, c)
    p["seedling_storage"] = (seedling_storage(), (0.35, 0.5, 0.75, 1))
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
        for n, (s, c) in unit_socket().items():
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
    """The same cup, probes, boards and socket on a 450 x 300 ply board, no box, no unit, no cart. A person plugs a 100 ml syringe with the nozzle tip into the
    socket and pushes the sample in by hand (the cart pump and coil tube are tested on their own, see docs/water-station/README.md). The drain tube runs into a bucket.
    Same coordinates as the station, so the same numbers apply."""
    a = cq.Assembly()
    sp = station_parts(door_on=False, cutaway=True, dy=0.0)
    for n, (s, c) in sp.items():
        if n in ("ws_shell", "ws_roof", "ws_door", "ws_legs"):
            continue
        a.add(s, name="bench_" + n[3:], color=cq.Color(*c))
    a.add(box(40, 400, -80, 150, 318, 330), name="bench_ply_board", color=cq.Color(*COL["board"]))
    a.add(box(CX - 33, CX + 33, -36, 36, 330, 339), name="bench_cup_stand", color=cq.Color(*COL["board"]))
    # clip-on stands for the boards (the box wall is not there): one upright plate at y 52..55
    a.add(box(135, 262, 52, 55, 333, 415), name="bench_back_plate", color=cq.Color(*COL["board"]))
    # socket support: a ring clip on a post so the socket sits on the cup like in the box (the roof is not there)
    a.add(box(CX - 36, CX - 30, -40, -34, 330, 440), name="bench_socket_post", color=cq.Color(*COL["board"]))
    a.add(box(CX - 36, CX + 6, -40, -34, 436, 440), name="bench_socket_arm", color=cq.Color(*COL["board"]))
    # hand-held syringe with the nozzle tip plugged into the socket (bench only; on the unit it is the cart tube)
    a.add(wc.male(CX, CY, SOCKET_Z_TOP, -1), name="bench_syringe_nozzle", color=cq.Color(0.9, 0.9, 0.5, 1))
    a.add(cyl(16.0, (CX, CY, SOCKET_Z_TOP + wc.COLLAR_L), (CX, CY, SOCKET_Z_TOP + wc.COLLAR_L + 110)), name="bench_syringe_barrel", color=cq.Color(0.9, 0.9, 0.5, 0.6))
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
    # sample and flush (owner redesign): the cart pump pushes SAMPLE_ML into the cup; the first part washes out the old heel over the standpipe, the heel left is the new sample
    out["sample_ml"] = SAMPLE_ML
    out["sample_over_heel_volume"] = SAMPLE_ML / out["heel_volume_ml"]
    out["old_sample_left_in_heel_percent_if_well_mixed"] = 100.0 * math.exp(-SAMPLE_ML / out["heel_volume_ml"])   # ideal mixing: a worst-case guide, bench test measures it
    out["sample_fits_cup_ml"] = out["cup_volume_ml"]
    out["rinse_bottle_and_pump"] = "removed"
    # fit
    b = BOX
    out["box_mm"] = (b["x1"] - b["x0"], b["y1"] - b["y0"], b["z1"] - b["z0"])
    out["box_front_gap_to_track_pipe_mm"] = (b["y0"] + OFF_Y - (TRACK_Y + TRACK_R))
    out["box_front_gap_to_cart_sleeve_R61_mm"] = (b["y0"] + OFF_Y - TRACK_Y) - 61.0     # cart omni sleeve outer radius (hand_sleeve.WALL_OUT_R); the cart can roll so the full radius counts
    out["socket_distance_from_track_axis_mm"] = CY + OFF_Y - TRACK_Y
    out["roof_top_below_track_top_mm"] = (TRACK_Z + TRACK_R) - (b["z1"])
    out["socket_top_above_track_axis_mm"] = SOCKET_Z_TOP - TRACK_Z
    # 19 Nov follow-up: FLUSH female sockets, nothing sticking up, and the male nozzle plugs in without touching the walls
    sb = sp["ws_socket"][0].val().BoundingBox()
    rb = sp["ws_roof"][0].val().BoundingBox()
    out["station_socket_top_minus_roof_top_mm (0 = flush)"] = round(sb.zmax - rb.zmax, 6)
    us = unit_socket()
    ub = us["unit_socket"][0].val().BoundingBox()
    lidb = ctx["lid"][0].val().BoundingBox()
    out["unit_socket_top_minus_lid_top_mm (0 = flush)"] = round(ub.zmax - lidb.zmax, 6)
    out["highest_thing_over_roof_top_mm (socket neighbourhood, 0 = nothing sticks up)"] = round(max(0.0, sb.zmax - rb.zmax), 6)
    nz = wc.male(CX, CY + OFF_Y, SOCKET_Z_TOP, -1)
    out["nozzle_in_station_socket_clash_mm3 (0 = fits)"] = round(sum(inter(nz, sp[n][0]) for n in ("ws_socket", "ws_roof", "ws_cup_cover", "ws_cup")), 4)
    nb = nz.val().BoundingBox()
    out["nozzle_spigot_depth_in_station_socket_mm"] = round(SOCKET_Z_TOP - nb.zmin, 3)
    out["nozzle_tip_over_cup_cover_mm (drips into the cup)"] = round(nb.zmin - (CUP_Z0 + CUP_H + 3), 3)
    nu = wc.male(UNIT_SOCKET[0], UNIT_SOCKET[1], LID, -1)
    out["nozzle_in_unit_socket_clash_mm3 (0 = fits)"] = round(inter(nu, us["unit_socket"][0]) + inter(nu, ctx["lid"][0]), 4)
    out["connector_spigot_od_mm"] = 2 * wc.SPIGOT_R
    out["connector_hole_od_mm"] = 2 * wc.HOLE_R
    out["connector_collar_od_mm"] = 2 * wc.COLLAR_R
    out["socket_x_from_dock_centre_mm"] = CX - DOCK_X
    us = unit_socket()
    out["unit_socket_x_from_dock_centre_mm"] = UNIT_SOCKET[0] - DOCK_X
    out["unit_dip_tube_bottom_over_tank_floor_mm"] = 8.0
    out["unit_dip_tube_inner_volume_ml"] = math.pi * 2.0 ** 2 * (LID + 2.0 - 8.0) / 1000.0
    out["unit_socket_clashes_mm3"] = {m: round(inter(us["unit_socket"][0], o), 2) for m, (o, _) in ctx.items() if m != "ground" and inter(us["unit_socket"][0], o) > 1e-3}
    out["unit_socket_vs_station_mm3"] = round(sum(inter(us["unit_socket"][0], s_[0]) for s_ in sp.values()), 2)
    out["box_floor_over_lid_bar_mm"] = b["z0"] - BAR_Z
    # v3: the box must sit on something. Legs stand on the lid (z = LID) and carry the floor (z = box z0): no gap at either end.
    lg = sp["ws_legs"][0].val().BoundingBox()
    out["legs_bottom_minus_lid_top_mm"] = lg.zmin - LID
    out["legs_top_minus_box_floor_mm"] = lg.zmax - b["z0"]
    out["box_floor_gap_to_support_mm"] = max(abs(lg.zmin - LID), abs(lg.zmax - b["z0"]))
    out["legs_footprint_inside_box_footprint"] = (lg.xmin >= b["x0"] and lg.xmax <= b["x1"] and lg.ymin >= b["y0"] + OFF_Y and lg.ymax <= b["y1"] + OFF_Y)
    out["legs_vs_drain_tube_mm3"] = round(inter(sp["ws_legs"][0], sp["ws_drain_tube"][0]), 3)
    out["legs_vs_lid_bar_mm3"] = round(inter(sp["ws_legs"][0], ctx["base_bar_and_lid_plates"][0]), 3)
    assert out["box_floor_gap_to_support_mm"] < 1e-6, "box is floating"
    out["drain_tube_run_over_lid_bar_mm"] = (DRAIN_Z_RUN - 3.0) - BAR_Z
    out["drain_tube_outside_tank_mm"] = DRAIN_Y_OUT + OFF_Y - TD / 2
    out["drain_tube_length_mm"] = (CUP_Z0 - 3.0 - DRAIN_Z_RUN) + (DRAIN_Y_OUT - CY) + (DRAIN_Z_RUN - 5.0)   # on the unit the cup axis and the drain are both moved OFF_Y, so the run is unchanged
    out["drain_tube_hits_tank_mm3"] = inter(sp["ws_drain_tube"][0], ctx["lid"][0]) + inter(sp["ws_drain_tube"][0], ctx["tank"][0])
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
    # parts of the station that must not overlap each other (allowed: probe through grommet through boss through cup wall; socket through roof and cover; tubes through walls; standpipe through cup floor)
    ok_pairs = {("ws_cup", "ws_grommets"), ("ws_cup", "ws_standpipe"), ("ws_cup", "ws_cup_cover"), ("ws_socket", "ws_cup_cover"), ("ws_socket", "ws_roof"),
                ("ws_grommets", "ws_ph_probe"), ("ws_grommets", "ws_ec_probe"), ("ws_grommets", "ws_temp_probe"), ("ws_heel_water", "ws_standpipe"),
                ("ws_drain_tube", "ws_standpipe"), ("ws_drain_tube", "ws_cup"), ("ws_drain_tube", "ws_shell"),
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
