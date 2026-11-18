# cad/complete_unit.py: SIMPLIFIED "complete unit" model (OpenPocket #311). Not detailed: boxes, cylinders and tubes only, to show
# everything together in one picture: frame and braces, solar panel, growing pipe with a pod/cup in every hole (4 per level), water tank,
# seedling tray, seedling storage and the cart on the track. Numbers come from unit_v3_aframe.py (mm, Z up); holes 100 mm apart (assumed).
# Needs numpy + trimesh only (not CadQuery). Writes docs/drawings/renders/complete-unit-v1.glb (Y up, as the other GLBs).
#   python cad/complete_unit.py
import math
import os

import numpy as np
import trimesh

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "drawings", "renders", "complete-unit-v1.glb")
TW, TD, TH = 700.0, 400.0, 300.0
GP, SP, TR, R = 75.0, 33.7, 16.0, 150.0
TX, LOOP_Y = 290.0, -60.0
LID = TH + 4
ZB, ZT = TH + 150.0, 1900.0 - TR
ZC1, ZC2, FOOT_X, ZBAR, BAR_X = 1215.0, 1547.5, 340.0, 1900.0, 200.0
HOLE_PITCH, POD_D = 100.0, 25.0
COLORS = {"tank": (190, 195, 205), "frame": (140, 145, 150), "legs": (240, 150, 50), "pipe": (235, 235, 235), "track": (180, 180, 185),
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
add("tank", box(TW, TD, TH, 0, 0, 0))
add("tank", box(TW, TD, 4, 0, 0, TH))
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
# cart on the right track: plate across both rails, battery, arm base and a short arm
cz = 1000.0
add("cart", box(170, 12, 120, TX, LOOP_Y - 30, cz - 60))
add("cart", box(80, 40, 60, TX, LOOP_Y - 56, cz - 50))
add("cart", rod((TX, LOOP_Y - 40, cz + 20), (TX - 50, LOOP_Y - 130, cz + 60), 10))
add("cart", rod((TX - 50, LOOP_Y - 130, cz + 60), (TX - 110, LOOP_Y - 120, cz + 20), 8))

scene = trimesh.Scene()
for name, ms in parts.items():
    m = trimesh.util.concatenate(ms)
    m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]]))   # Z up -> glTF Y up
    m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        baseColorFactor=list(COLORS[name]) + [255], metallicFactor=0.0, roughnessFactor=0.8))
    scene.add_geometry(m, node_name=name, geom_name=name)
scene.export(OUT)
print("wrote", os.path.relpath(OUT), n_holes, "pods,", sum(len(v) for v in parts.values()), "shapes")
