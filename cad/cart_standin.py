# cad/cart_standin.py: a SIMPLIFIED cart for the unit drawings (OpenPocket #364). unit_v3_aframe.py, unit_v3_dimensioned.py and unit_v1_assembly.py drew the cart as one red box standing at a corner of
# the track. This is the cart as it is now designed, hanging under the BOTTOM track run at the dock (unit x = 100) with the top sleeve closed on the track: the motors-inward hand of #312 (sleeve, drive and roll
# motors inside it), rigid plate, battery, folded arm, and the water sampler of #330 (pump, the blue sample tubing coil, nozzle parked in its block). Boxes, cylinders and rings only (no CadQuery booleans, fast).
# Numbers are the cart's own (cart_assembly.py bounding boxes, cart_dims.py, water_sampler.py; cart frame: x across the pipes, y out of the track plane, z along the track). cp() moves a cart-frame point into the unit frame:
#   unit x = dock + z_c, unit y = y_c + loop_y, unit z = track_z - 60 - x_c      (cart +x is DOWN, towards the lid)
# The detailed cart is in cart_assembly.py / water_assembly.py; this is only so the unit pictures show the real cart's size, place and depth under the track (165 mm, cad/layout.json).
import math
import cadquery as cq

COL = dict(cart=(0.85, 0.2, 0.2, 1), plate=(0.88, 0.88, 0.9, 1), motors=(0.95, 0.75, 0.15, 1), arm=(0.25, 0.25, 0.3, 1), pump=(0.92, 0.5, 0.15, 1), tubing=(0.15, 0.45, 1.0, 1), nozzle=(0.95, 0.95, 0.4, 1))


def parts(track_z, dock=100.0, loop_y=-60.0):
    def cp(x, y, z):
        return cq.Vector(dock + z, y + loop_y, track_z - 60.0 - x)

    def cbox(x0, x1, y0, y1, z0, z1):
        a, b = cp(x0, y0, z0), cp(x1, y1, z1)
        lo = cq.Vector(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))
        sz = cq.Vector(abs(a.x - b.x), abs(a.y - b.y), abs(a.z - b.z))
        return cq.Workplane("XY").box(sz.x, sz.y, sz.z, centered=False).translate((lo.x, lo.y, lo.z))

    def crod(p, q, r):
        a, b = cp(*p), cp(*q)
        v = b - a
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, a, v.normalized()))

    def U(items):
        out = items[0]
        for i in items[1:]:
            out = out.union(i)
        return out

    out = {}
    out["cart_plate_battery"] = (U([cbox(-80, 80, -56, -50, -73, 73), cbox(-35, 35, -106, -56, -35, 35)]), COL["plate"])
    out["cart_sleeve_top_hand"] = (U([crod((-60, 0, -62), (-60, 0, 62), 40), cbox(-121, -26, -50, -30, -62, 62)]), COL["cart"])
    out["cart_motors_inward"] = (U([crod((-95, -40.5, -33), (-95, -40.5, 22), 14), crod((-95, -16, -77), (-95, -71, -77), 14)]), COL["motors"])
    out["cart_arm_folded"] = (U([cbox(-35, 35, -131, -106, -35, 35), crod((0, -118, -35), (0, -125, 200), 20), crod((0, -145, 200), (0, -145, 20), 17)]), COL["arm"])
    out["cart_sampler_pump"] = (U([crod((-62, -96, -28), (-62, -56, -28), 17), cbox(-79, -45, -96, -56, -53, -17)]), COL["pump"])
    cx, cy, cz0 = 67.0, -87.0, -58.0
    rings = [cq.Workplane("XY").add(cq.Solid.makeTorus(26.0, 4.0, pnt=cp(cx, cy, cz0 + 8.0 * k), dir=cq.Vector(1, 0, 0))) for k in range(14)]   # the 14-turn, 8 mm pitch recoil coil as stacked rings
    link = [crod((-62, cy, -53), (-62, cy, -66), 4), crod((-62, cy, -66), (93, cy, -66), 4), crod((93, cy, -66), (93, cy, cz0), 4), crod((93, cy, cz0 + 112), (93, cy, 62), 4)]
    out["cart_sample_tubing_coil"] = (U(rings + link), COL["tubing"])
    out["cart_nozzle_and_parking_block"] = (U([crod((93, cy, 62), (93, cy, 74), 6), cbox(81, 105, -92, -56, 73, 89)]), COL["nozzle"])
    import layout as LAY
    low = min(s.val().BoundingBox().zmin for s, c in out.values())
    assert low > LAY.LID_TOP, "the cart stand-in reaches the tank lid (lowest point %.1f, lid top %.1f): raise the bottom track in cad/layout.json" % (low, LAY.LID_TOP)    # same rule as water_assembly.cart_tank_check(), for the unit drawings
    return out


def lowest_z(track_z):
    """Lowest point of the stand-in (unit z): the parking block, 165 mm under the track axis."""
    return min(s.val().BoundingBox().zmin for s, c in parts(track_z).values())
