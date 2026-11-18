# cad/track_supports.py — pipe supports on the track (OpenPocket #315, part 1 of plan #295), 18 Nov 2026
# The unit of unit_v3_aframe.py (tank, spine, collars, top triangle, track loop) plus the supports, on the SAME M8 rod
# system as the track joint (track_joint.py): an M8 rod screws into a captive nut on a curved plate INSIDE the pipe, goes out
# through an 8.5 mm hole on the +Y side (the sleeve's C-gap side, towards the spine) and ends in a post or block. The cart
# rolls to home (roll 0) so that its C-gap faces the rod, the same software interlock as for the joint rods.
#  - BOTTOM run: one support each side, left and right, just before the curve starts (x = +-125, the straight part ends at 140).
#    A post on a small base plate on top of the tank lid. With the centre bracket the bottom run is held at three points.
#  - TOP run: a diagonal M8 brace from the centre collar (where the top triangle legs meet, z 1547.5) to a block at the middle
#    of each half span (x = +-125), the block hangs on the same rod stub.
# Numbers: docs/bench-test/track_support_sag.py (output in track_support_sag.txt). The unit's track loop is a solid
# cylinder in the unit scripts; here each support gets a local bore for its nut plate (the loop is a 32 x 1.8 pipe in reality).
import math, os, runpy
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
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
FACE_Y = -10.0                      # face of the post / block (towards the spine side), 34 mm of free rod from the pipe surface
STUB = FACE_Y - (LOOP_Y + TR)       # 34 mm
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

# top: block on the rod stub, brace to the centre collar
RC = unit["RC"]
blocks = []; braces = []; lugs = []
for sx in SX:
    blocks.append(box(POST_W, POST_D, 20, sx * SUP_X, yc, ZT - 10))
    ax = 10.0
    p0 = cq.Vector(sx * ax, -math.sqrt(RC**2 - ax**2), ZC2 + 10)         # lug on the collar, front side (clear of the legs at y = 0)
    p1 = cq.Vector(sx * SUP_X, yc, ZT - 10)
    d = p1 - p0
    braces.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(4.0, d.Length, p0, d.normalized())))
    lugs.append(box(18, 12, 16, p0.x, p0.y + 3, p0.z - 8))
add(many(blocks), "top_brace_blocks", (0.95, 0.6, 0.2, 1))
add(many(braces), "top_braces_m8", (0.3, 0.3, 0.3, 1))
add(many(lugs), "top_brace_lugs_on_collar", (0.55, 0.57, 0.6, 1))
result = assy
