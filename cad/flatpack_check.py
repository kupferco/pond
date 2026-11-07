import cadquery as cq

# Flat-pack check v3 (7 Nov 2026): v2 contents + bracing v5 parts.
# New: 30 W panel flat above the shelf; lower side legs (948) and back strut (910) split in two halves
# (push-fit spigot joints, like the spine); top legs 389; base bar halves, top bar, panel rails;
# 4 fold-out feet; clamp collars shipped as halves (ENVELOPE boxes); 2 internal spacers; sandbags folded flat.
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
fz = BUCKET_Z0 + BW
xc = 101.0
zc1 = fz + GP/2 + 0.3
rows = [-152.5, -76.0, 0.0, 76.0, 152.5]
for i, y in enumerate(rows):
    L = PIPE_L if i < 4 else CLEAN_L
    add(xtube(GP, GP - 6, L, xc - L/2, y, zc1), f"grow_pipe_{i+1}" if i < 4 else "cleanout_section", (0.95, 0.95, 0.95, 1))
    add(xtube(SP, SP - 4, SPINE_L, xc - SPINE_L/2, y, zc1), f"spine_{i+1}", (0.35, 0.35, 0.35, 1))
zc2 = fz + GP + 1 + TR
ys = [-175, -141, -107, -73, -39, -5, 29, 63]
for i, y in enumerate(ys):
    L = LONG if i < 6 else SHORT
    add(xtube(2*TR, 0, L, xc - L/2, y, zc2), f"track_long_{i+1}" if i < 6 else f"track_short_{i-5}", (0.7, 0.7, 0.72, 1))
zc3 = fz + TR + 0.3
zc4 = zc3 + 2*TR + 1
k = 0
for zc in (zc3, zc4):
    for cy in (-188, 8):
        k += 1
        add(corner(-337, cy, zc), f"track_corner_{k}", (0.75, 0.75, 0.78, 1))
add(box(110, 90, 70, -245, 0, zc4 + TR + 2), "cart_body", (0.9, 0.2, 0.2, 1))
z_top = SHELF_Z + 4
add(box(100, 280, 100, -290, 0, z_top), "arm_folded_ASSUMED", (0.95, 0.75, 0.3, 1))
add(ytube(GP + 8, GP + 1, 100, -195, -50, z_top + (GP + 8)/2), "sleeve", (0.3, 0.55, 0.85, 1))

# ---- new in v3, above the shelf, x from -145 to 340 ----
add(box(450, 350, 25, 95, 0, z_top), "solar_panel_30W", (0.08, 0.12, 0.35, 1))
z1 = z_top + 26
LR = 16.0
legs = [(480.0, "lower_leg_half")] * 4 + [(470.0, "back_strut_half")] * 2 + [(389.0, "top_leg")] * 2
for i, (L, n) in enumerate(legs):
    y = -185 + i * 19
    add(xtube(LR, LR - 3, L, 95 - L/2, y, z1 + LR/2), f"{n}_{i+1}", (0.95, 0.6, 0.2, 1))
bars = [(290.0, 20.0, 15.0, "base_bar_half_1"), (290.0, 20.0, 15.0, "base_bar_half_2"), (420.0, 20.0, 15.0, "top_bar"), (260.0, 20.0, 15.0, "panel_rail_1"), (260.0, 20.0, 15.0, "panel_rail_2")]
for i, (L, w, h, n) in enumerate(bars):
    add(box(L, w, h, 95, -25 + i * 22, z1), n, (0.55, 0.57, 0.6, 1))
for i, (fx, dz) in enumerate([(-25, 0), (215, 0), (-25, 7), (215, 7)]):
    f = box(220, 50, 6, fx, 145, z1 + dz).union(box(6, 50, 80, fx + 107, 145, z1 + dz))
    add(f, f"fold_out_foot_{i+1}", (0.2, 0.2, 0.2, 1))
z2 = z1 + LR + 1
for i, (cx, cy) in enumerate([(-75, -140), (65, -140), (205, -140), (-75, -45)]):
    add(box(130, 90, 60, cx, cy, z2), f"collar_half_{i+1}_ENVELOPE", (0.55, 0.57, 0.6, 0.6))
for i, cx in enumerate((90, 175)):
    add(cq.Workplane("XY").circle(34.5).circle(16.85).extrude(50).translate((cx, -45, z2)), f"internal_spacer_{i+1}", (0.1, 0.1, 0.1, 1))
for i in range(4):
    add(box(200, 150, 5, 140, -110, z2 + 61 + i * 5), f"sandbag_folded_{i+1}", (0.8, 0.7, 0.45, 1))
print("highest new part top z:", z2 + 61 + 4 * 5, "inner lid limit: 296")
result = assy
