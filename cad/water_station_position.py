# cad/water_station_position.py: where does the shared water testing station go, at the BACK of the unit lid (+y, inboard of the track) or at the FRONT (-y, the cart's side)?
# OpenPocket #330 follow-up (19 Nov 2026). Prints, for both positions: (1) the smallest gap (mm) from the station to the unit's braces, #315 track supports, lid bar, seedling tray,
# growing pipe and tank; (2) overlaps with the cart, sampler, hands, plate, battery and arm (water_assembly.check); (3) the arm reach from the shoulder to the station socket mouth
# and to the unit's sample socket, using cart_arm.py (REACH 350). Run: python cad/water_station_position.py
import math
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import water_station as ws       # noqa: E402
import water_assembly as wa      # noqa: E402
import cart_arm as carm          # noqa: E402

BACK_DY = ws.OFF_Y               # back: as drawn, front of the box 64 mm from the track axis
FRONT_DY = -179.0                # front: the box back face (y1 = 58) lands at y -121, just outside the cart sleeve radius 61 round the track (y -60)
COMFORT = 0.80                   # "comfortable": the socket mouth is within 80 percent of the 350 mm reach from the shoulder, and the gripper can be at 90 deg or less
SCAN = range(0, 181, 5)


def to_cart_pt(p):
    b = wa.to_cart(cq.Workplane("XY").box(0.01, 0.01, 0.01).translate(p)).val().BoundingBox()
    return ((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2, (b.zmin + b.zmax) / 2)


def reach(p_unit):
    c = to_cart_pt(p_unit)
    d = math.dist(c, carm.S_CART)
    ok = []
    for a3 in SCAN:
        try:
            carm.solve_pose(c, a3_deg=a3)
            ok.append(a3)
        except ValueError:
            pass
    return {"cart_xyz_mm": tuple(round(v, 1) for v in c), "shoulder_to_mouth_mm": round(d, 1), "percent_of_reach": round(100 * d / carm.REACH),
            "gripper_angles_that_work_deg": (min(ok), max(ok)) if ok else None, "works_with_gripper_90_deg_or_less": bool(ok) and min(ok) <= 90,
            "comfortable": d <= COMFORT * carm.REACH and bool(ok) and min(ok) <= 90}


def gaps(dy):
    st = {n: s for n, (s, c) in ws.station_parts(True, False, dy=dy).items()}
    ctx = {n: s for n, (s, c) in ws.context_parts().items() if n not in ("track_bottom_run", "track_corner", "dock_plate_minus", "dock_plate_plus", "ground")}
    for n, (s, c) in wa.track_support_parts().items():
        ctx[n] = s
    out, clashes = {}, []
    for m, o in ctx.items():
        best = None
        for n, s in st.items():
            ov = ws.inter(s, o)
            if ov > 1e-3 and not (n == "ws_legs" and m == "tank"):       # the legs stand on the lid on purpose
                clashes.append("%s vs %s %.0f mm3" % (n, m, ov))
            d = s.val().distance(o.val())
            best = d if best is None else min(best, d)
        out[m] = round(best, 1)
    out["clashes"] = clashes
    return out


def overhang(dy):
    b = ws.BOX
    return {"box_y_range_mm": (b["y0"] + dy, b["y1"] + dy + 8), "lid_y_range_mm": (-ws.TD / 2, ws.TD / 2),
            "overhang_past_lid_edge_mm": round(max(0.0, -ws.TD / 2 - (b["y0"] + dy), (b["y1"] + dy + 8) - ws.TD / 2), 1)}


def run(name, dy):
    print("=== station at the %s (dy = %.0f) ===" % (name, dy))
    print("gaps to the unit (smallest distance, mm):", gaps(dy))
    print("lid:", overhang(dy))
    print("cart clashes (assembly check):")
    a = wa.check(dy=dy)
    for k in ("station_vs_sampler_clashes_mm3", "station_vs_cart_hands_clashes_mm3", "station_vs_plate_battery_arm_clashes_mm3"):
        print("  ", k, a[k])
    print("reach to the station socket mouth:", reach((ws.CX, ws.CY + dy, ws.SOCKET_Z_TOP)))


if __name__ == "__main__":
    run("back", BACK_DY)
    run("front", FRONT_DY)
    print("=== unit sample socket (mouth) at (%.0f, %.0f) ===" % ws.UNIT_SOCKET)
    print("reach:", reach((ws.UNIT_SOCKET[0], ws.UNIT_SOCKET[1], ws.LID + 40.0)))
    tp = ws.TRACK_Y
    print("gap from the socket mouth edge to the track pipe footprint (y):", abs(ws.UNIT_SOCKET[1] - tp) - ws.TRACK_R - 20.0)
