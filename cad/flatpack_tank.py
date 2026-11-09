import cadquery as cq

# Flat-pack check v2 (6 Nov 2026): 30 cm tank, track top at 1.90 m, buckets in place.
TW, TD, TH = 700.0, 400.0, 300.0
GP = 75.0; SP = 33.7; TR = 16.0; R = 150.0
BUCKET_Z0, BUCKET_H = 4.0, 150.0; BW = 3.0
SHELF_Z = 155.0
LONG = 378.0; SHORT = 200.0; SPINE_L = 377.0; PIPE_L = 333.0; CLEAN_L = 250.0

def box(sx, sy, sz, cx, cy, z0):
    return cq.Workplane("XY").box(sx, sy, sz, centered=(True, True, False)).translate((cx, cy, z0))

def open_box(x0, x1, y0, y1, z0, h, w):
    o = box(x1 - x0, y1 - y0, h, (x0 + x1)/2, (y0 + y1)/2, z0)
    i = box(x1 - x0 - 2*w, y1 - y0 - 2*w, h, (x0 + x1)/2, (y0 + y1)/2, z0 + w)
    return o.cut(i)

def xtube(od, idd, L, x0, y, zc):
    w = cq.Workplane("YZ").circle(od/2)
    if idd: w = w.circle(idd/2)
    return w.extrude(L).translate((x0, y, zc))

def ytube(od, idd, L, x, y0, zc):
    w = cq.Workplane("XZ").circle(od/2)
    if idd: w = w.circle(idd/2)
    return w.extrude(-L).translate((x, y0, zc))

def corner(cx, cy, zc):
    t = cq.Solid.makeTorus(R, TR, pnt=cq.Vector(cx, cy, zc), dir=cq.Vector(0, 0, 1))
    clip = box(R + TR + 1, R + TR + 1, 2*TR + 2, cx + (R + TR + 1)/2, cy + (R + TR + 1)/2, zc - TR - 1)
    return cq.Workplane("XY").add(t).intersect(clip)

assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))

add(open_box(-350, 350, -200, 200, 0, TH, 4), "tank_30cm", (0.75, 0.75, 0.8, 0.2))
add(open_box(-344, -146, -194, 194, BUCKET_Z0, BUCKET_H, BW), "clean_bucket", (0.5, 0.75, 1.0, 0.35))
add(open_box(-142, 344, -194, 194, BUCKET_Z0, BUCKET_H, BW), "nutrient_bucket", (0.4, 0.75, 0.5, 0.35))
add(box(692, 392, 4, 0, 0, SHELF_Z), "shelf", (0.5, 0.5, 0.55, 0.3))

# nutrient bucket, layer 1: 4 growing pipe sections + cleanout, spine sections nested inside
fz = BUCKET_Z0 + BW
xc = 101.0
zc1 = fz + GP/2 + 0.3
rows = [-152.5, -76.0, 0.0, 76.0, 152.5]
for i, y in enumerate(rows):
    L = PIPE_L if i < 4 else CLEAN_L
    name = f"grow_pipe_{i+1}" if i < 4 else "cleanout_section"
    add(xtube(GP, GP - 6, L, xc - L/2, y, zc1), name, (0.95, 0.95, 0.95, 1))
    add(xtube(SP, SP - 4, SPINE_L, xc - SPINE_L/2, y, zc1), f"spine_{i+1}", (0.35, 0.35, 0.35, 1))

# nutrient bucket, layer 2: 6 long track pieces + 2 short
zc2 = fz + GP + 1 + TR
ys = [-175, -141, -107, -73, -39, -5, 29, 63]
for i, y in enumerate(ys):
    L = LONG if i < 6 else SHORT
    name = f"track_long_{i+1}" if i < 6 else f"track_short_{i-5}"
    add(xtube(2*TR, 0, L, xc - L/2, y, zc2), name, (0.7, 0.7, 0.72, 1))

# clean bucket: 4 corners (2 layers of 2) and the cart on top
zc3 = fz + TR + 0.3
zc4 = zc3 + 2*TR + 1
k = 0
for zc in (zc3, zc4):
    for cy in (-188, 8):
        k += 1
        add(corner(-337, cy, zc), f"track_corner_{k}", (0.75, 0.75, 0.78, 1))
add(box(110, 90, 70, -245, 0, zc4 + TR + 2), "cart_body", (0.9, 0.2, 0.2, 1))

# seedling corner above the shelf: folded arm (ASSUMED size) + sleeve
z_top = SHELF_Z + 4
add(box(100, 280, 100, -290, 0, z_top), "arm_folded_ASSUMED", (0.95, 0.75, 0.3, 1))
add(ytube(GP + 8, GP + 1, 100, -195, -50, z_top + (GP + 8)/2), "sleeve", (0.3, 0.55, 0.85, 1))

result = assy
