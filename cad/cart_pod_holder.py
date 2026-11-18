# cad/cart_pod_holder.py: seedling-pod holder on the cart plate (DRAFT v3, 17 Nov 2026, OpenPocket #229, #230).
# v4 (Pond #280, plan task 265 part 6): fitted to the v5 omni sleeves. The plate is now 146 mm high (z -73..73, was about 112) and the sleeves, wheels and
#   motors end at z = -88 (were -45), but they are BEHIND the plate (y > -50) and the cup is in FRONT of it (y < -56), so they cannot touch. The cup stays
#   at z = -88; the old "motors on the plate" are gone (the four motors are in the sleeves); the hands in context() are the real sleeves, not boxes.
#   check() now also prints the closest distance from the pod and the holder to the hands, arm base and battery.
# v3: the cup is STRAIGHT again, axis square to the plate (90 degrees, no tilt): CUP_TILT = 0. WHY: the cart goes up pipe A and comes down
#   pipe B, so it is upside down for part of the trip. The pod sits in the cup on the 24 x 2 O-ring (it squeezes the pod body, a friction fit)
#   and must stay put upside down, which a straight cup does better than a tilted one; it also takes the cup out of the arm's way (the 45 degree
#   cup swung up towards the arm base and made the pod hard to reach). The pod axis is now horizontal (out of the plate) when the cart stands
#   upright; the arm turns the pod to the collar's 45 degree seat itself (one wrist move). Friction fit: see check() 'oring_squeeze_mm'.
# v2 (superseded): the cup was ANGLED 45 degrees (axis out of the plate AND up the pipe, +Z), to match the collar's 45 degree pod seat.
# v2: the cup is ANGLED 45 degrees (axis out of the plate AND up the pipe, +Z), to match the collar's 45 degree pod seat.
#   WHY: the robot then carries the pod at the same attitude it goes into the seat, so pick (from the cup) and insert (into
#   the collar) are one straight pull-and-push with the same gripper angle; no wrist re-orientation in between. The cost is
#   that the cup swings up toward the arm base, so it was moved 8 mm lower (cup root z = -88) and 18 mm out from the plate;
#   the pod (cap included) stays 14 mm from the arm base, 8 mm from the battery (distances computed in CadQuery).
#   ASSUMES +Z on the cart points up the pipe, the same way as the collar's +Z; flip CUP_TILT if the cart rides the other way.
# The robot puts a seedling pod in this cup so it can carry it up the pipe in one trip. Same seat as the collar's
# (bore 26, 24 x 2 O-ring, 2 mm cap recess), so the gripper does the same grip on the 6 mm of pod cap that stands proud.
# Frame: cart frame (cart_dims.py): pipes along Z, plate on the -Y side. The cup axis points out of the plate (-Y), like the arm's base axis.
# WHERE: hung from the BOTTOM edge of the base plate, centred on the arm (x = -12), cup root z = -88. Checked clear of:
#   battery (z >= -35), battery corner stops, arm base footprint (z >= -35), both drive motors and saddles (x outside
#   -33..9 and z >= -47.5), the 12 V tie slots in the plate's bottom band (pads and web sit between them), both hands
#   (sleeves end at z = -45, x outside -26..26), both hinges and worm drives (at the plate ends / above the top edge).
#   The folded arm lies towards +Z, the other side. See check() below (numerical overlap tests).
# Fixing: two printed pads on the plate's front face, 2 x M4 (4.3 mm holes at x = -34 and 10, z = -46) into the plate band
#   (plate holes to be drilled: none exist there yet), a bar under the plate edge, a web up to the cup.
# NOT IK-CHECKED: the pod cap sits well forward of the arm base and the distance to the arm's pan axis was not measured; reach with the real SO-101 and gripper angle still has to be tried (cart_arm.py poses).
# PRINT: ASA or PETG (outdoors), cup axis tilted: print with the plate pads flat on the bed and the web as support (or split the cup off and print it mouth up), 4 perimeters, 40 % infill.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_dims as cd
import pipe_collar as pc

PLATE_Y0 = cd.PLATE_Y0                  # plate front face, -56 (plate back face on the pads)
CUP_X, CUP_Z = cd.ARM_X, -88.0
CUP_D = 42.0
CUP_L = 40.0                            # cup body length, from the pads' outer face to the mouth
Y_FACE = PLATE_Y0                       # pads start on the plate face

def ycyl(r, y0, y1, x, z):
    """Cylinder along Y from y0 to y1 (y1 < y0 goes out from the plate)."""
    lo, hi = min(y0, y1), max(y0, y1)
    return cq.Workplane("XZ").workplane(offset=-hi).center(x, z).circle(r).extrude(hi - lo)
def ytube(ro, ri, y0, y1, x, z):
    return ycyl(ro, y0, y1, x, z).cut(ycyl(ri, y0 + 1, y1 - 1, x, z))
def bx(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

CUP_TILT = 0.0                          # 90 degrees to the plate: no tilt (v2 had 45 degrees UP the pipe, +Z, like the collar's pod seat)
ROOT_Y = Y_FACE - 18.0                  # where the angled cup starts (18 mm out from the plate face; web joins it to the pads)

def _rot(wp):
    """Tilt a cup part built straight (axis -Y) about the X axis through the cup root so it points out AND up (+Z)."""
    return wp.rotate((0, ROOT_Y, CUP_Z), (1, ROOT_Y, CUP_Z), -CUP_TILT)

def _straight_cup():
    """Straight frame: cup root plane at y = ROOT_Y, mouth CUP_L further out (-Y). Returns (solid, seat cut tools)."""
    mouth = ROOT_Y - CUP_L
    body = ycyl(CUP_D / 2, ROOT_Y + 2.0, mouth, CUP_X, CUP_Z)
    y_floor = mouth + pc.RECESS_T + pc.POD_BODY_L + 0.5
    g0 = mouth + 12.0
    tools = [ycyl(pc.BORE_D / 2, y_floor, mouth - 1, CUP_X, CUP_Z),
             ycyl(pc.RECESS_D / 2, mouth + pc.RECESS_T, mouth - 1, CUP_X, CUP_Z),
             ycyl(pc.OR_GROOVE_D / 2, g0, g0 - pc.OR_GROOVE_W, CUP_X, CUP_Z),
             ycyl(1.5, y_floor + 1, y_floor - 6.0, CUP_X, CUP_Z)]       # last: vent / drain
    return body, tools

def holder():
    cup, tools = _straight_cup()
    body = _rot(cup)
    # pads on the plate face (clear of the tie slots x -26..-18 and -6..2), bar under the plate edge, web up to the cup root
    pads = None
    for x0, x1 in ((-40.0, -28.0), (4.0, 16.0)):
        p = bx(x0, x1, Y_FACE - 4.0, Y_FACE, -62.0, -37.0)
        pads = p if pads is None else pads.union(p)
    bar = bx(-40.0, 16.0, Y_FACE - 8.0, Y_FACE, -66.0, -56.5)
    web = bx(-17.0, -7.0, ROOT_Y - 2.0, Y_FACE - 4.0, CUP_Z - 6.0, -56.5)     # web: plate bar down to the cup root
    body = body.union(pads).union(bar).union(web)
    for t in tools:                                                          # seat cuts last, so the web does not fill the bore
        body = body.cut(_rot(t))
    for x in (-34.0, 10.0):                                                 # M4 holes through the pads
        body = body.cut(ycyl(2.15, Y_FACE + 1, Y_FACE - 5, x, -46.0))
    return body

def oring():
    mouth = ROOT_Y - CUP_L
    g0 = mouth + 12.0
    r = ycyl(pc.OR_GROOVE_D / 2 - 0.05, g0 - 0.3, g0 - 2.3, CUP_X, CUP_Z).cut(ycyl(12.0, g0 + 1, g0 - 3, CUP_X, CUP_Z))
    return _rot(r)

def pod_in_holder():
    mouth = ROOT_Y - CUP_L
    cap_in = mouth + pc.RECESS_T                        # cap underside rests in the recess
    body = ycyl(pc.POD_BODY_D / 2, cap_in, cap_in + pc.POD_BODY_L, CUP_X, CUP_Z)
    cap = ycyl(pc.CAP_D / 2, cap_in, cap_in - pc.CAP_T, CUP_X, CUP_Z)
    return _rot(body.union(cap))

_CTX = {}
def context():
    if not _CTX:
        _CTX.update(_build_context())
    return _CTX

def _build_context():
    """Plate and the things next to the holder, as boxes, for the render and for the clearance test."""
    items = {}
    items["plate"] = bx(cd.PLATE_X0, cd.PLATE_X1, cd.PLATE_Y0, cd.PLATE_Y1, -cd.PLATE_ZH, cd.PLATE_ZH)
    items["battery"] = bx(cd.BATT_X - cd.BATT[0] / 2, cd.BATT_X + cd.BATT[0] / 2, cd.PLATE_Y0 - cd.BATT[1], cd.PLATE_Y0,
                          cd.BATT_Z - cd.BATT[2] / 2, cd.BATT_Z + cd.BATT[2] / 2)
    items["arm_base"] = bx(cd.ARM_X - 35, cd.ARM_X + 35, cd.ARM_Y0 - 8, cd.ARM_Y0, -35, 35)
    # the real v5 hands (sleeve, jaw, omni wheels, ball cups, motors), clamped, as placed on the cart (Pond #280; was boxes of the v4 sleeve)
    import cart_sleeves as csl
    for sgn, nm in ((-1, "hand_B"), (1, "hand_C")):
        h = None
        for _n, (shp, _c) in csl.hand_parts().items():
            s = csl.place_hand(shp, sgn)
            h = s if h is None else h.union(s)
        items[nm] = h
    return items

def check():
    h = holder()
    pod = pod_in_holder()
    res = {}
    for k, v in context().items():
        i = h.intersect(v)
        res[k] = i.val().Volume() if i.vals() else 0.0
    for k, v in context().items():
        i = pod.intersect(v)
        res["pod_vs_" + k] = i.val().Volume() if i.vals() else 0.0
    for k in ("plate", "battery", "arm_base", "hand_B", "hand_C"):          # closest approach in mm (0 = touching)
        res["pod_gap_" + k] = round(pod.val().distance(context()[k].val()), 1) if k not in ("plate",) else None
        res["holder_gap_" + k] = None if k == "plate" else round(h.val().distance(context()[k].val()), 1)
    pb = pod.val().BoundingBox()
    res["pod_bbox"] = (pb.xmin, pb.xmax, pb.ymin, pb.ymax, pb.zmin, pb.zmax)
    res["oring_squeeze_mm"] = pc.POD_BODY_D / 2 - 12.0   # pod body radius minus the O-ring bore radius (12.0, as cut in oring()): >0 means the ring squeezes the pod
    res["pod_vs_holder"] = (lambda i: i.val().Volume() if i.vals() else 0.0)(pod.intersect(h))
    bb = h.val().BoundingBox()
    res["bbox"] = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    return res

def scene(with_pod=False, show=("plate", "battery", "arm_base")):
    a = cq.Assembly()
    a.add(holder(), name="cart_pod_holder", color=cq.Color(0.25, 0.28, 0.3, 1))
    a.add(oring(), name="oring_24x2", color=cq.Color(0.1, 0.5, 0.2, 1))
    if with_pod:
        a.add(pod_in_holder(), name="seedling_pod", color=cq.Color(*pc.C_POD))
    cols = {"plate": (0.35, 0.35, 0.38, 0.6), "battery": (0.2, 0.45, 0.85, 0.6), "arm_base": (0.88, 0.88, 0.9, 0.6),
            "hand_B": (0.3, 0.55, 0.85, 0.35), "hand_C": (0.3, 0.55, 0.85, 0.35)}
    for k, v in context().items():
        if k in show:                     # the hands are checked in check() but left out of the picture (they hide the plate)
            a.add(v, name=k, color=cq.Color(*cols[k]))
    return a

result = scene(True)

if __name__ == "__main__":
    for k, v in check().items():
        print(k, v)
