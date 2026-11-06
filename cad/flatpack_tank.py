import cadquery as cq

TW, TD = 700.0, 400.0
FLOOR = 4.0; SHELF_Z = 200.0
GP = 75.0; SP = 33.7; TR = 16.0; R = 150.0

def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))

def xtube(od, idd, L, x0, y, zc):
    w = cq.Workplane("YZ").circle(od/2)
    if idd: w = w.circle(idd/2)
    return w.extrude(L).translate((x0, y, zc))

assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))

# tank shell (lower part, under the shelf) and shelf
shell = box(TW, TD, 260, 0, 0, 0).cut(box(TW - 8, TD - 8, 260, 0, 0, FLOOR))
add(shell, "tank_lower", (0.75, 0.75, 0.8, 0.25))
add(box(TW - 8, TD - 8, 4, 0, 0, SHELF_Z), "shelf_ceiling", (0.5, 0.5, 0.55, 0.3))

# layer 1: growing pipe sections (3 x 382), cleanout + sleeve, spine nested inside
zc1 = FLOOR + GP/2 + 0.5
for i, y in enumerate([-155, -78, -1]):
    add(xtube(GP, GP - 6, 382, -191, y, zc1), f"grow_pipe_{i+1}", (0.95, 0.95, 0.95, 1))
    add(xtube(SP, SP - 4, 450, -225, y, zc1), f"spine_{i+1}", (0.35, 0.35, 0.35, 1))
add(xtube(GP, GP - 6, 250, -330, 76, zc1), "cleanout_section", (0.8, 0.8, 0.85, 1))
add(xtube(GP + 8, GP + 1, 100, -60, 76, zc1), "sleeve", (0.3, 0.55, 0.85, 1))
add(xtube(GP + 20, GP + 2, 25, 60, 76, zc1), "socket_ring", (0.95, 0.6, 0.2, 1))
add(xtube(SP, SP - 4, 450, -225, 150, FLOOR + SP/2 + 0.5), "spine_4", (0.35, 0.35, 0.35, 1))

# layer 2: track straights (4 x 455 vertical runs split, 2 x 200 top/bottom)
zc2 = FLOOR + GP + 1 + TR + 0.5
ys = [-175, -140, -105, -70, -35, 0]
for i, y in enumerate(ys[:4]):
    add(xtube(2*TR, 0, 455, -227, y, zc2), f"track_straight_{i+1}", (0.7, 0.7, 0.72, 1))
for i, y in enumerate(ys[4:]):
    add(xtube(2*TR, 0, 200, -100, y, zc2), f"track_short_{i+1}", (0.6, 0.6, 0.65, 1))

# layers 3-4: four corner pieces lying flat, two per layer
def corner(cx, cy, zc):
    t = cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, cy, zc), dir=cq.Vector(0, 0, 1))
    clip = box(R + TR + 1, R + TR + 1, 2*TR + 2, cx + (R + TR + 1)/2, cy + (R + TR + 1)/2, zc - TR - 1)
    return cq.Workplane("XY").add(t).intersect(clip)
zc3 = zc2 + 2*TR + 1
zc4 = zc3 + 2*TR + 1
k = 0
for zc in (zc3, zc4):
    for cx in (-340, -160):
        k += 1
        add(corner(cx, -192, zc), f"track_corner_{k}", (0.75, 0.75, 0.78, 1))

# cart and folded arm (sizes ASSUMED) in the free bay
z_bay = FLOOR + GP + 2
add(box(110, 90, 70, 200, 120, z_bay), "cart_body", (0.9, 0.2, 0.2, 1))
add(box(280, 100, 100, -150, 130, z_bay), "arm_folded_ASSUMED", (0.95, 0.75, 0.3, 1))

result = assy
