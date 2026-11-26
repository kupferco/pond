# cad/track_supports.py — pipe supports on the track (OpenPocket #315, part 1 of plan #295), 18 Nov 2026
# The unit of unit_v3_aframe.py (tank, spine, collars, top triangle, track loop) plus the supports, on the SAME M8 rod
# system as the track joint (track_joint.py): an M8 rod screws into a captive nut on a curved plate INSIDE the pipe, goes out
# through an 8.5 mm hole on the +Y side (the sleeve's C-gap side, towards the spine) and ends in a post or block. The cart
# rolls to home (roll 0) so that its C-gap faces the rod, the same software interlock as for the joint rods.
#  - BOTTOM run: one support each side, left and right, just before the curve starts (x = +-125, the straight part ends at 140).
#    A post on a small base plate on top of the tank lid. With the centre bracket the bottom run is held at three points.
#  - TOP run: no diagonal rods (removed after owner review). A short vertical hanger from the grey crossbar (top_bar, under the
#    solar panel) straight down to a block on the same rod stub, at x = +-125. The orange top triangle legs stay as they were.
# Numbers: docs/bench-test/track_support_sag.py (output in track_support_sag.txt). The unit's track loop is a solid
# cylinder in the unit scripts; here each support gets a local bore for its nut plate (the loop is a 32 x 1.8 pipe in reality).
import math, os, runpy, sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
unit = runpy.run_path(os.path.join(HERE, "unit_v3_aframe.py"))
TH, TX, TR, R, LOOP_Y, ZB, ZT = (unit[k] for k in ("TH", "TX", "TR", "R", "LOOP_Y", "ZB", "ZT"))
ZC2, LID = unit["ZC2"], unit["LID"]
box, cyl, tdir = unit["box"], unit["cyl"], unit["tdir"]

SUP_X = 125.0                       # support position along the run, from the centre bracket (the bend starts at 140)
WALL = 1.8; RI = TR - WALL          # 32 x 1.8 pipe
ROD_D = 8.0; HOLE_D = 8.5
PLATE_T = 3.0; PLATE_ANG = 50.0; PLATE_L = 30.0
NUT_BOSS_D = 14.0; NUT_BOSS_H = 6.5
LOCKNUT_AF = 13.0; LOCKNUT_H = 6.5
import layout as LAY                 # OpenPocket #537: the ONE layout (cad/layout.json)
STUB = LAY.TRACK_STUB               # 50 mm of free rod from the pipe surface: track_joint.py ROD_OUT (it was a 34 mm stub here, which disagreed with the joint)
FACE_Y = LOOP_Y + TR + STUB         # face of the post / block (towards the spine side): on the central pipe's axis (y = 0)
TRACK_OFFSET = LAY.TRACK_OFFSET     # 66: track axis to central pipe axis, stated on the two close-up drawings
POST_W, POST_D = 20.0, 16.0
BASE_X, BASE_Y, BASE_T = 44.0, 36.0, 4.0

def arc_seg(r_out, r_in, ang, length, z0):
    a = math.radians(ang / 2)
    return (cq.Workplane("XY").moveTo(r_in * math.cos(a), -r_in * math.sin(a))
            .lineTo(r_out * math.cos(a), -r_out * math.sin(a)).threePointArc((r_out, 0), (r_out * math.cos(a), r_out * math.sin(a)))
            .lineTo(r_in * math.cos(a), r_in * math.sin(a)).threePointArc((r_in, 0), (r_in * math.cos(a), -r_in * math.sin(a)))
            .close().extrude(length).translate((0, 0, z0)))

def to_run(shape, x, z):
    """Pipe-local frame (pipe along Z, jaw / C-gap side +X) -> a run along world X, jaw side towards +Y (the spine)."""
    return shape.rotate((0, 0, 0), (1, 1, 1), 120).translate((x, LOOP_Y, z))

plate_in = RI - 0.1 - PLATE_T
def nut_plate():
    p = arc_seg(RI - 0.1, plate_in, PLATE_ANG, PLATE_L, -PLATE_L / 2)
    boss = cq.Workplane("YZ").polygon(6, NUT_BOSS_D).extrude(NUT_BOSS_H).translate((plate_in - NUT_BOSS_H + 0.5, 0, 0))
    return p.union(boss).cut(cq.Workplane("YZ").circle(ROD_D / 2).extrude(30).translate((-5, 0, 0)))
ROD_X0 = plate_in - NUT_BOSS_H + 1
def rod():       # ends 8 mm inside the post / block
    return cq.Workplane("YZ").circle(ROD_D / 2).extrude(TR + STUB + 8 - ROD_X0).translate((ROD_X0, 0, 0))
def locknut():
    return (cq.Workplane("YZ").polygon(6, LOCKNUT_AF / math.cos(math.pi / 6)).extrude(LOCKNUT_H).translate((TR, 0, 0))
            .cut(cq.Workplane("YZ").circle(ROD_D / 2).extrude(20).translate((TR - 1, 0, 0))))
def bore():      # nut plate pocket and the rod hole, cut out of the solid loop cylinder of the unit scripts
    return (cq.Workplane("XY").circle(RI).extrude(40).translate((0, 0, -20))
            .union(cq.Workplane("YZ").circle(HOLE_D / 2).extrude(TR + 2)))

SX = (-1, 1)
RUN_Z = {"bottom": ZB, "top": ZT}
def many(parts):
    out = None
    for p in parts:
        out = p if out is None else out.union(p)
    return out

# --- the unit, with the loop cut for the supports
assy = cq.Assembly()
for ch in unit["result"].children:
    obj = ch.obj
    if ch.name == "track_loop":
        for sx in SX:
            for z in RUN_Z.values():
                obj = obj.cut(to_run(bore(), sx * SUP_X, z))
    assy.add(obj, name=ch.name, color=ch.color, loc=ch.loc)
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))

pl = [(sx, z) for sx in SX for z in RUN_Z.values()]
add(many([to_run(nut_plate(), sx * SUP_X, z) for sx, z in pl]), "support_nut_plates", (0.9, 0.2, 0.2, 1))
add(many([to_run(rod(), sx * SUP_X, z) for sx, z in pl]), "support_m8_rods", (0.3, 0.3, 0.3, 1))
add(many([to_run(locknut(), sx * SUP_X, z) for sx, z in pl]), "support_lock_nuts", (0.2, 0.7, 0.3, 1))

# bottom: post on a small base plate on top of the lid
yc = FACE_Y + POST_D / 2
posts = []; bases = []
for sx in SX:
    top = ZB + 10
    posts.append(box(POST_W, POST_D, top - (LID + BASE_T), sx * SUP_X, yc, LID + BASE_T))
    bases.append(box(BASE_X, BASE_Y, BASE_T, sx * SUP_X, yc, LID))
add(many(posts), "bottom_support_posts", (0.95, 0.6, 0.2, 1))
add(many(bases), "bottom_support_base_plates", (0.55, 0.57, 0.6, 1))

# top: a short vertical hanger from the grey crossbar (top_bar, under the solar panel) straight down to the rod stub into the pipe.
# No diagonals: the orange legs of the top triangle (collar to the crossbar ends) are the only braces.
hangers = []
for sx in SX:
    hangers.append(box(POST_W, POST_D, unit["ZBAR"] - (ZT - 10), sx * SUP_X, yc, ZT - 10))
add(many(hangers), "top_hangers_from_crossbar", (0.95, 0.6, 0.2, 1))

# the track offset, stated on the drawings (#537): blue dimension from the track pipe axis to the central pipe axis, at each support, with the label
def hdim_y(x, z, label):
    g = box(4, -LOOP_Y, 4, x, LOOP_Y / 2, z).union(box(40, 4, 4, x, LOOP_Y, z)).union(box(40, 4, 4, x, 0, z))
    t = cq.Workplane("XY").text(label, 14, 2).translate((x - 70, LOOP_Y / 2 + 4, z + 4))
    return g.union(t)
DIMS = ("track %d mm from the central pipe" % round(TRACK_OFFSET))
dims = many([hdim_y(sx * SUP_X, z + dz, DIMS) for sx in SX for z, dz in ((ZB, -34.0), (ZT, 34.0))])
add(dims, "track_offset_dimension", (0.1, 0.35, 0.85, 1))
result = assy
