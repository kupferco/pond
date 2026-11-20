# cad/complete_unit.py: SIMPLIFIED "complete unit" model (OpenPocket #311). Not detailed: boxes, cylinders and tubes only, to show
# everything together in one picture: frame and braces, solar panel, growing pipe with a pod/cup in every hole (4 per level), water tank,
# seedling tray, seedling storage and the cart on the track. Numbers come from unit_v3_aframe.py (mm, Z up); holes 100 mm apart (assumed).
# v2 (OpenPocket #364, brought up to date): tank, lid and bottom track height come from the shared layout (cad/layout.json), so the cart (hanging under the bottom run at the
# dock) clears the lid; water in the tank (translucent blue, its own part "tank_water", 150 mm level); the cart is the motors-inward cart of #312 (cart_assembly.py numbers, simplified)
# with the water sampler of #330 (pump, blue sample tubing coil, nozzle parked in its block); the water testing station of #330 on the lid, with its flush socket and drain tube.
# Needs numpy + trimesh only (not CadQuery). Writes docs/drawings/renders/complete-unit-v2.glb (Y up, as the other GLBs).
#   python cad/complete_unit.py
import math
import os

import numpy as np
import trimesh
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as LAY   # the ONE shared layout: tank, lid, bottom track and cart heights (cad/layout.json)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "drawings", "renders", "complete-unit-v2.glb")
TW, TD, TH = 700.0, 400.0, LAY.TANK_H
GP, SP, TR, R = 75.0, 33.7, 16.0, 150.0
TX, LOOP_Y = 290.0, -60.0
LID = LAY.LID_TOP
ZB, ZT = LAY.TRACK_BOTTOM_Z, 1900.0 - TR
ZC1, ZC2, FOOT_X, ZBAR, BAR_X = 1215.0, 1547.5, 340.0, 1900.0, 200.0
HOLE_PITCH, POD_D = 100.0, 25.0
COLORS = {"tank": (190, 195, 205, 90), "tank_water": (50, 120, 240, 120), "cart": (220, 50, 50), "cart_plate": (225, 225, 230), "cart_motors": (240, 190, 40), "cart_arm": (60, 60, 70),
          "sampler_pump": (235, 128, 38), "sampler_tubing": (40, 120, 255), "sampler_nozzle": (240, 240, 100), "station": (238, 238, 230), "station_cup": (160, 205, 242),
          "station_roof": (210, 210, 200), "station_drain": (80, 80, 90), "lid_socket": (245, 245, 245), "frame": (140, 145, 150), "legs": (240, 150, 50), "pipe": (235, 235, 235), "track": (180, 180, 185),
          "panel": (20, 30, 90), "pods": (60, 170, 80), "caps": (30, 30, 30), "tray": (150, 110, 70), "store": (90, 130, 190),
          "cart": (220, 50, 50), "feet": (50, 50, 50), "bags": (205, 180, 115)}
parts = {}


def add(name, m):
    parts.setdefault(name, []).append(m)


def box(sx, sy, sz, cx, cy, z0):
    m = trimesh.creation.box((sx, sy, sz))
    m.apply_translation((cx, cy, z0 + sz / 2))
    return m


def rod(p, q, r, sections=14):
    p, q = np.asarray(p, float), np.asarray(q, float)
    m = trimesh.creation.cylinder(radius=r, segment=np.array([p, q]), sections=sections)
    return m


def tube(ro, ri, z0, z1, sections=40):
    return trimesh.creation.annulus(r_min=ri, r_max=ro, height=z1 - z0, sections=sections).apply_translation((0, 0, (z0 + z1) / 2))


# tank (open box), lid, socket
# tank: HOLLOW and see-through (4 mm walls, floor and lid) with the water in it as its own part at the normal level (OpenPocket #364)
add("tank", box(TW, 4, TH, 0, -TD / 2 + 2, 0)); add("tank", box(TW, 4, TH, 0, TD / 2 - 2, 0))
add("tank", box(4, TD - 8, TH, -TW / 2 + 2, 0, 0)); add("tank", box(4, TD - 8, TH, TW / 2 - 2, 0, 0))
add("tank", box(TW - 8, TD - 8, 4, 0, 0, 0))
add("tank", box(TW, TD, 4, 0, 0, TH))
add("tank_water", box(TW - 8, TD - 8, LAY.WATER_LEVEL - 4, 0, 0, 4))
# growing pipe, spine inside, collars
add("pipe", tube(GP / 2, GP / 2 - 3, LID, ZT))
add("frame", tube(GP / 2 + 3, GP / 2, ZC1 - 25, ZC1 + 25))
add("frame", tube(GP / 2 + 3, GP / 2, ZC2 - 25, ZC2 + 25))
add("frame", tube(GP / 2 + 10, GP / 2 + 1, LID, LID + 25))
# braces: lower A-frame legs + back strut from the lower collar, top triangle legs from the upper collar
for zc, ends in ((ZC1, [(-FOOT_X, 0, LID), (FOOT_X, 0, LID), (0, 180, LID)]), (ZC2, [(-BAR_X, 0, ZBAR), (BAR_X, 0, ZBAR)])):
    for e in ends:
        h = math.hypot(e[0], e[1])
        start = (e[0] / h * (GP / 2 + 3 - 4), e[1] / h * (GP / 2 + 3 - 4), zc)
        add("legs", rod(start, e, 8))
add("frame", box(2 * FOOT_X, 20, 15, 0, 0, LID))
add("frame", box(30, 190, 5, 0, 90, LID))
add("frame", box(2 * BAR_X + 20, 20, 15, 0, 0, ZBAR))
# feet and sandbags
for sx in (-1, 1):
    for sy in (-1, 1):
        add("feet", box(50, 220, 6, sx * 325, sy * 310, 0))
        add("bags", box(110, 120, 55, sx * 325, sy * 315, 6))
# solar panel 450 x 350, 23 degrees, on rails
tilt = math.radians(23)
panel = trimesh.creation.box((450, 350, 25))
panel.apply_transform(trimesh.transformations.rotation_matrix(tilt, (1, 0, 0)))
panel.apply_translation((0, 0, 2000))
add("panel", panel)
for x in (-150.0, 150.0):
    add("frame", box(20, 260, 15, x, 0, ZBAR + 15))
    for y in (-110.0, 110.0):
        zu = 2000 + y * math.tan(tilt) - 12.5 / math.cos(tilt)
        add("frame", box(15, 15, max(zu - (ZBAR + 30) + 2, 4), x, y, ZBAR + 30))
# track loop (rounded rectangle in the XZ plane at y = -60) as short rods, plus two spine brackets to the pipe
pts = []
for cx, cz, a0 in ((TX - R, ZT - R, 0), (-TX + R, ZT - R, 90), (-TX + R, ZB + R, 180), (TX - R, ZB + R, 270)):
    for k in range(13):
        a = math.radians(a0 + 90 * k / 12)
        pts.append((cx + R * math.cos(a), LOOP_Y, cz + R * math.sin(a)))
pts.append(pts[0])
for p, q in zip(pts, pts[1:]):
    add("track", rod(p, q, TR, 12))
    add("track", trimesh.creation.uv_sphere(TR, count=(8, 8)).apply_translation(q))
add("frame", box(16, 30, 30, 0, -45, ZT - 15))
add("frame", box(16, 30, 30, 0, -45, ZB - 15))
# pods in the holes: 4 faces, 100 mm apart up the pipe, turning 90 degrees each level, skipping the collar zones.
# Each pod is a cup tilted 45 degrees up out of the hole with a dark cap on its end.
zs = [z for z in np.arange(400.0, 1840.0, HOLE_PITCH) if abs(z - ZC1) > 60 and abs(z - ZC2) > 60]
n_holes = 0
for i, z in enumerate(zs):
    for k in range(4):
        az = math.radians(90 * k + 45 * (i % 2) + 45)
        radial = np.array([math.cos(az), math.sin(az), 0.0])
        d = radial * math.cos(math.radians(45)) + np.array([0, 0, math.sin(math.radians(45))])
        p0 = radial * (GP / 2 - 6) + np.array([0, 0, z])
        add("pods", rod(p0, p0 + d * 50, POD_D / 2, 12))
        add("caps", rod(p0 + d * 50, p0 + d * 66, POD_D / 2 + 4, 12))
        n_holes += 1
# seedling tray (shallow tray with cells) and seedling storage (box with five pod sticks) on the lid, in front of the pipe
add("tray", box(240, 110, 6, -190, -125, LID + 4))
for x in np.arange(-290, -80, 35):
    for y in (-150, -125, -100):
        add("tray", box(25, 18, 24, x, y, LID + 10))
add("store", box(240, 110, 12, 190, -125, LID + 4))
for k in range(5):
    add("store", box(230, 14, 36, 190, -125 - 40 + k * 20, LID + 16))
# ---- the cart (OpenPocket #312 motors-inward cart + #330 water sampler), simplified, at the dock on the BOTTOM run, hanging under the track on the lid side.
# Numbers are the cart's own (cart_assembly.py, cart_dims.py, water_sampler.py: cart frame x across the pipes, y out of the track plane, z along the track). cart() moves a cart-frame point into the unit:
# unit x = dock + z_c, unit y = y_c - 60 (track plane), unit z = track height - 60 - x_c (cart +x is DOWN, towards the lid). With the layout's 45 mm of air the lowest cart part (parking block) is 45 mm over the lid.
DOCK = 100.0
def cp(x, y, z):
    return np.array([DOCK + z, y + LOOP_Y, ZB - 60.0 - x])
def cbox(x0, x1, y0, y1, z0, z1):
    a, b = cp(x0, y0, z0), cp(x1, y1, z1)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    return box(*(hi - lo), *((lo + hi)[:2] / 2), lo[2])
def crod(p, q, r, sections=14):
    return rod(cp(*p), cp(*q), r, sections)
# plate (168 x 146 x 6 in the real cart is 160 x 146 x 6 on pads), battery under the arm, folded arm
add("cart_plate", cbox(-80, 80, -56, -50, -73, 73))
add("cart", cbox(-35, 35, -106, -56, -35, 35))                                   # battery 70 x 50 x 70
add("cart_arm", cbox(-35, 35, -131, -106, -35, 35))                              # arm base
add("cart_arm", crod((0, -118, -35), (0, -125, 200), 20))                        # upper arm, folded up along the track (simplified)
add("cart_arm", crod((0, -145, 200), (0, -145, 20), 17))                         # forearm folded back on it
# the top hand (sleeve) closed on the track pipe, two drive and two roll motors INSIDE the sleeves, pointing inward (#312), hall sensor omitted
add("cart", crod((-60, 0, -62), (-60, 0, 62), 40))                               # sleeve round the 32 mm track pipe (the real sleeve is a three-lobe frame, 61 mm to its furthest lobe)
add("cart_motors", crod((-95, -40.5, -33), (-95, -40.5, 22), 14))                # drive motor 28 x 55 (cart_assembly.py: x -109..-81, y -54.5..-26.5, z -33..22)
add("cart_motors", crod((-95, -16, -77), (-95, -71, -77), 14))                   # roll motor, axis out of the plane (y -71..-16, z -91..-63)
add("cart", cbox(-121, -26, -50, -30, -62, 62))                                  # sleeve frame and pads on the plate side
# water sampler (water_sampler.py): pump on the plate, silicone link, the blue PU recoil coil, tail and nozzle, parking block on the plate's top edge
add("sampler_pump", crod((-62, -96, -28), (-62, -56, -28), 17))
add("sampler_pump", cbox(-79, -45, -96, -56, -53, -17))
CX_, CY_, CZ0 = 67.0, -87.0, -58.0
add("sampler_tubing", crod((-62, CY_, -53), (-62, CY_, -66), 4)); add("sampler_tubing", crod((-62, CY_, -66), (93, CY_, -66), 4)); add("sampler_tubing", crod((93, CY_, -66), (93, CY_, CZ0), 4))
for k in range(14 * 24):                                                         # the coil: 14 turns, 8 mm pitch, 26 mm mean radius, 8 mm OD tube
    a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
    p0 = (CX_ + 26 * math.cos(a0), CY_ + 26 * math.sin(a0), CZ0 + 8.0 * k / 24)
    p1 = (CX_ + 26 * math.cos(a1), CY_ + 26 * math.sin(a1), CZ0 + 8.0 * (k + 1) / 24)
    add("sampler_tubing", crod(p0, p1, 4, 8))
add("sampler_tubing", crod((93, CY_, CZ0 + 112), (93, CY_, 62), 4))
add("sampler_nozzle", crod((93, CY_, 62), (93, CY_, 74), 6))
add("sampler_nozzle", cbox(81, 105, -92, -56, 73, 89))                           # parking block, flat bottom face carries the flush socket

# ---- the water testing station of #330 (simplified), on legs on the lid, 64 mm higher than before because the track rose; flush nozzle socket in the roof above the cup
RISE = LAY.TRACK_RISE
SY0, SY1 = 14.0, 108.0
add("station", box(200, SY1 - SY0, 113 - 3, 160, (SY0 + SY1) / 2, 330 + RISE))
add("station_roof", box(216, SY1 - SY0 + 8, 3, 160, (SY0 + SY1) / 2 + 4, 440 + RISE))
for lx in (70.0, 250.0):
    for ly in (22.0, 80.0):
        add("station", box(20, 20, 330 + RISE - LID, lx, ly, LID))
add("station_cup", trimesh.creation.annulus(r_min=28, r_max=30, height=80, sections=40).apply_translation((100, 50, 339 + RISE + 40)))
add("station_drain", rod((100, 50, 336 + RISE), (100, 50, 324), 3))
add("station_drain", rod((100, 50, 324), (100, 215, 324), 3))
add("station_drain", rod((100, 215, 324), (100, 215, 5), 3))
add("lid_socket", trimesh.creation.cylinder(radius=13, height=8, sections=24).apply_translation((20, -105, LID - 4)))       # the unit's own flush sample socket (dip tube below)
add("lid_socket", rod((20, -105, 8), (20, -105, LID - 8), 3))

scene = trimesh.Scene()
for name, ms in parts.items():
    m = trimesh.util.concatenate(ms)
    m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]]))   # Z up -> glTF Y up
    col = list(COLORS[name]) + ([255] if len(COLORS[name]) == 3 else [])
    m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        baseColorFactor=col, metallicFactor=0.0, roughnessFactor=0.8, alphaMode="BLEND" if col[3] < 255 else "OPAQUE", doubleSided=True))
    scene.add_geometry(m, node_name=name, geom_name=name)
scene.export(OUT)
print("wrote", os.path.relpath(OUT), n_holes, "pods,", sum(len(v) for v in parts.values()), "shapes")
