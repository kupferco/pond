# cad/cart_pod_holder.py: seedling-pod holder on the cart plate (DRAFT v1, 16 Nov 2026, OpenPocket #229).
# The robot puts a seedling pod in this cup so it can carry it up the pipe in one trip. Same seat as the collar's
# (bore 26, 24 x 2 O-ring, 2 mm cap recess), so the gripper does the same grip on the 6 mm of pod cap that stands proud.
# Frame: cart frame (cart_dims.py): pipes along Z, plate on the -Y side. The cup axis points out of the plate (-Y), like the arm's base axis.
# WHERE: hung from the BOTTOM edge of the base plate, centred on the arm (x = -12), cup axis z = -80. Checked clear of:
#   battery (z >= -35), battery corner stops, arm base footprint (z >= -35), both drive motors and saddles (x outside
#   -33..9 and z >= -47.5), the 12 V tie slots in the plate's bottom band (pads and web sit between them), both hands
#   (sleeves end at z = -45, x outside -26..26), both hinges and worm drives (at the plate ends / above the top edge).
#   The folded arm lies towards +Z, the other side. See check() below (numerical overlap tests).
# Fixing: two printed pads on the plate's front face, 2 x M4 (4.3 mm holes at x = -34 and 10, z = -46) into the plate band
#   (plate holes to be drilled: none exist there yet), a bar under the plate edge, a web up to the cup.
# NOT IK-CHECKED: the cup mouth is 96 mm out from the plate (pod cap ends 102 out, level with the arm base plate) and 80 mm
#   from the arm's pan axis; reach with the real SO-101 and gripper angle still has to be tried (cart_arm.py poses).
# PRINT: ASA or PETG (outdoors), cup axis vertical (mouth up), 4 perimeters, 40 % infill.
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_dims as cd
import pipe_collar as pc

PLATE_Y0 = cd.PLATE_Y0                  # plate front face, -52
CUP_X, CUP_Z = cd.ARM_X, -80.0
CUP_D = 42.0
CUP_L = 40.0                            # cup body length, from the pads' outer face to the mouth
Y_FACE = PLATE_Y0                       # pads start on the plate face
Y_MOUTH = Y_FACE - 4.0 - CUP_L          # mouth face, 44 mm out from the plate face (cup body starts 4 mm out, on the pads)
POD_CAP_Y_OUT = Y_MOUTH - (pc.CAP_T - pc.RECESS_T)

def ycyl(r, y0, y1, x, z):
    """Cylinder along Y from y0 to y1 (y1 < y0 goes out from the plate)."""
    lo, hi = min(y0, y1), max(y0, y1)
    return cq.Workplane("XZ").workplane(offset=-hi).center(x, z).circle(r).extrude(hi - lo)
def ytube(ro, ri, y0, y1, x, z):
    return ycyl(ro, y0, y1, x, z).cut(ycyl(ri, y0 + 1, y1 - 1, x, z))
def bx(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def holder():
    body = ycyl(CUP_D / 2, Y_FACE - 4.0, Y_MOUTH, CUP_X, CUP_Z)
    # pads on the plate face (clear of the tie slots x -26..-18 and -6..2), bar under the plate edge, web to the cup
    pads = None
    for x0, x1 in ((-40.0, -28.0), (4.0, 16.0)):
        p = bx(x0, x1, Y_FACE - 4.0, Y_FACE, -62.0, -37.0)
        pads = p if pads is None else pads.union(p)
    bar = bx(-40.0, 16.0, Y_FACE - 8.0, Y_FACE, -66.0, -56.5)
    web = bx(-17.0, -7.0, Y_FACE - 30.0, Y_FACE - 4.0, -70.0, -56.5)
    body = body.union(pads).union(bar).union(web)
    # seat: bore, cap recess, O-ring groove, vent hole
    y_floor = Y_MOUTH + pc.RECESS_T + pc.POD_BODY_L + 0.5          # bore floor (toward the plate)
    body = body.cut(ycyl(pc.BORE_D / 2, y_floor, Y_MOUTH - 1, CUP_X, CUP_Z))
    body = body.cut(ycyl(pc.RECESS_D / 2, Y_MOUTH + pc.RECESS_T, Y_MOUTH - 1, CUP_X, CUP_Z))
    g0 = Y_MOUTH + 12.0
    body = body.cut(ycyl(pc.OR_GROOVE_D / 2, g0, g0 - pc.OR_GROOVE_W, CUP_X, CUP_Z))
    body = body.cut(ycyl(1.5, y_floor + 1, y_floor - 6.0, CUP_X, CUP_Z))   # vent / drain
    for x in (-34.0, 10.0):                                                 # M4 holes through the pads
        body = body.cut(ycyl(2.15, Y_FACE + 1, Y_FACE - 5, x, -46.0))
    return body

def oring():
    g0 = Y_MOUTH + 12.0
    return ycyl(pc.OR_GROOVE_D / 2 - 0.05, g0 - 0.3, g0 - 2.3, CUP_X, CUP_Z).cut(ycyl(12.0, g0 + 1, g0 - 3, CUP_X, CUP_Z))

def pod_in_holder():
    cap_in = Y_MOUTH + pc.RECESS_T                      # cap underside rests in the recess
    body = ycyl(pc.POD_BODY_D / 2, cap_in, cap_in + pc.POD_BODY_L, CUP_X, CUP_Z)
    cap = ycyl(pc.CAP_D / 2, cap_in, cap_in - pc.CAP_T, CUP_X, CUP_Z)
    return body.union(cap)

def context():
    """Plate and the things next to the holder, as boxes, for the render and for the clearance test."""
    items = {}
    items["plate"] = bx(cd.PLATE_X0, cd.PLATE_X1, cd.PLATE_Y0, cd.PLATE_Y1, -cd.PLATE_ZH, cd.PLATE_ZH)
    items["battery"] = bx(cd.BATT_X - cd.BATT[0] / 2, cd.BATT_X + cd.BATT[0] / 2, cd.PLATE_Y0 - cd.BATT[1], cd.PLATE_Y0,
                          cd.BATT_Z - cd.BATT[2] / 2, cd.BATT_Z + cd.BATT[2] / 2)
    items["arm_base"] = bx(cd.ARM_X - 35, cd.ARM_X + 35, cd.ARM_Y0 - 8, cd.ARM_Y0, -35, 35)
    m = None
    for sgn in (-1, 1):
        mx = cd.MOTOR_XS[sgn]
        c = bx(mx - cd.MOTOR_R, mx + cd.MOTOR_R, cd.PLATE_Y0 - 2 * cd.MOTOR_R, cd.PLATE_Y0, -cd.MOTOR_L / 2, cd.MOTOR_L / 2 + 20)
        m = c if m is None else m.union(c)
    items["motors"] = m
    for sgn, nm in ((-1, "hand_B"), (1, "hand_C")):
        items[nm] = bx(sgn * cd.HX - cd.SLEEVE_R, sgn * cd.HX + cd.SLEEVE_R, -43, 43, -45, 45)
    return items

def check():
    h = holder()
    pod = pod_in_holder()
    res = {}
    for k, v in context().items():
        i = h.intersect(v)
        res[k] = i.val().Volume() if i.vals() else 0.0
    res["pod_vs_holder"] = (lambda i: i.val().Volume() if i.vals() else 0.0)(pod.intersect(h))
    bb = h.val().BoundingBox()
    res["bbox"] = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    return res

def scene(with_pod=False, show=("plate", "battery", "arm_base", "motors")):
    a = cq.Assembly()
    a.add(holder(), name="cart_pod_holder", color=cq.Color(0.25, 0.28, 0.3, 1))
    a.add(oring(), name="oring_24x2", color=cq.Color(0.1, 0.5, 0.2, 1))
    if with_pod:
        a.add(pod_in_holder(), name="seedling_pod", color=cq.Color(*pc.C_POD))
    cols = {"plate": (0.35, 0.35, 0.38, 0.6), "battery": (0.2, 0.45, 0.85, 0.6), "arm_base": (0.88, 0.88, 0.9, 0.6),
            "motors": (0.85, 0.25, 0.25, 0.6), "hand_B": (0.3, 0.55, 0.85, 0.35), "hand_C": (0.3, 0.55, 0.85, 0.35)}
    for k, v in context().items():
        if k in show:                     # the hands are checked in check() but left out of the picture (they hide the plate)
            a.add(v, name=k, color=cq.Color(*cols[k]))
    return a

result = scene(True)

if __name__ == "__main__":
    for k, v in check().items():
        print(k, v)
