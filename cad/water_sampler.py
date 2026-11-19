# cad/water_sampler.py: the cart's water sampler (OpenPocket #330, owner redesign of 19 Nov 2026; plan 307 part 2). docs/water-station/README.md has the story.
# ONE peristaltic pump on the cart (not one per unit), a food-safe polyurethane (PU) recoil tube from the pump to a nozzle, a short silicone section through the pump head.
# The tube itself holds the sample (about 50 to 100 ml, metered by counting pump turns, no bottle). The nozzle parks in a socket on the plate; the coil retracts by itself.
# Frame: the cart frame of cart_assembly.py / cart_dims.py (pipes along Z at x = +-60, plate on the -Y side, front face y = PLATE_Y0 = -56, out from the plate = -Y).
# ASSUMED (nothing bought): mini peristaltic pump, rotor 34 mm round x 40 deep, with a pump head that takes 6 mm ID silicone; PU recoil tube 8 mm OD x 6 mm ID
# (28 mm2 bore, so 2.5 m holds about 70 ml); recoil coil about 52 mm mean diameter, 14 turns, 8 mm pitch (about 112 mm long retracted, stretches to about 2 m).
# The sampler sits in the free strips of the plate either side of the battery/arm column (x +-35): pump on the pipe B side, coil and parking socket on the pipe C side.
# It was NOT there in the #312 cart, so check() below also tests it against everything on the cart. The arm poses (take the nozzle, plug it in, park it) are a LATER part of the plan.
import math
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cart_dims import PLATE_Y0, PLATE_X0, PLATE_X1, PLATE_ZH, BATT, BATT_X, ARM_BASE_W, ARM_Y0  # noqa: E402
from cart_geom import box, cyl  # noqa: E402

TUBE_OD, TUBE_ID = 8.0, 6.0            # PU recoil tube
SIL_OD = 9.0                           # silicone section through the pump head (6 ID)
NOZZLE_R = 5.5                         # 11 mm OD brass-free printed nozzle, plugs 24 mm into a socket (bore radius 7 in water_station.py / 6+1 on the unit)
COIL_R = 26.0                          # mean coil radius
COIL_PITCH = 8.0
COIL_TURNS = 14
COIL_X = 67.0                          # coil axis (x): 13 mm beyond the plate edge on pipe C side; inner edge 2 mm from the battery column (x +-35)
COIL_Y = PLATE_Y0 - (COIL_R + TUBE_OD / 2 + 1.0)    # axis out from the plate so the coil clears the plate face by 1 mm
COIL_Z0 = -58.0                         # starts above the pipe C roll motor (z -91..-63 at x 81..109) so the coil, which overhangs the plate edge, clears it
PUMP_X, PUMP_Z = -62.0, -28.0          # pump axis along Y, on the pipe B side strip of the plate
PUMP_R, PUMP_L = 17.0, 40.0
PARK_Z0, PARK_Z1 = 62.0, 88.0          # parking socket sleeve (axis Z, open to +Z), z range
SAMPLE_TUBE_M = COIL_TURNS * 2 * math.pi * COIL_R / 1000.0 + 0.3     # coil plus tails, metres
COL = dict(pump=(0.92, 0.5, 0.15, 1), sil=(0.85, 0.85, 0.9, 0.9), pu=(0.2, 0.75, 0.85, 1), nozzle=(0.95, 0.95, 0.4, 1), park=(0.95, 0.95, 0.95, 1))


def hose(r, pts):
    out = None
    for a, b in zip(pts, pts[1:]):
        v = cq.Vector(*b) - cq.Vector(*a)
        s = cq.Workplane("XY").add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*a), v.normalized()))
        out = s if out is None else out.union(s)
    for p in pts[1:-1]:
        out = out.union(cq.Workplane("XY").add(cq.Solid.makeSphere(r, cq.Vector(*p), cq.Vector(0, 0, 1), -90, 90, 360)))
    return out


def pump():
    y0 = PLATE_Y0 - PUMP_L
    body = cyl(PUMP_R, PUMP_L, "y", (PUMP_X, y0 + PUMP_L / 2, PUMP_Z))
    base = box(2 * PUMP_R, PUMP_L, PUMP_R + 8, (PUMP_X, y0 + PUMP_L / 2, PUMP_Z - PUMP_R / 2 - 4))        # motor/foot block under the rotor
    return body.union(base)


def link_hose():
    """Silicone: out of the pump head, along the bottom of the plate (under the battery column) to the coil start on pipe C's side."""
    sx = COIL_X + COIL_R
    return hose(SIL_OD / 2 - 0.5, [(PUMP_X, COIL_Y, PUMP_Z - 25), (PUMP_X, COIL_Y, COIL_Z0 - 8), (sx, COIL_Y, COIL_Z0 - 8), (sx, COIL_Y, COIL_Z0)])


def coil():
    """PU recoil coil, retracted: a helix of the tube radius along +Z, starting at (COIL_X + COIL_R, COIL_Y, COIL_Z0)."""
    h = cq.Wire.makeHelix(COIL_PITCH, COIL_PITCH * COIL_TURNS, COIL_R)
    path = cq.Workplane("XY").add(h).translate((COIL_X, COIL_Y, COIL_Z0))
    start = cq.Vector(COIL_X + COIL_R, COIL_Y, COIL_Z0)
    prof = cq.Workplane(cq.Plane(origin=(start.x, start.y, start.z), xDir=(1, 0, 0), normal=(0, 1, 0))).circle(TUBE_OD / 2)
    return prof.sweep(path, isFrenet=True)


def nozzle_and_tail():
    ex = COIL_X + COIL_R
    z_end = COIL_Z0 + COIL_PITCH * COIL_TURNS
    tail = hose(TUBE_OD / 2, [(ex, COIL_Y, z_end), (ex, COIL_Y, PARK_Z0 + 4)])
    nozzle = cyl(NOZZLE_R, PARK_Z1 - PARK_Z0 - 2, "z", (ex, COIL_Y, (PARK_Z0 + 4 + PARK_Z1) / 2 + 5))
    return tail, nozzle


def parking_socket():
    """Sleeve on a bracket on the plate's top edge (bracket 24 x 36 x 16, bolts to the plate), open upwards; the nozzle rests in it, the arm lifts it out."""
    ex = COIL_X + COIL_R
    sleeve = cyl(13.0, PARK_Z1 - PARK_Z0, "z", (ex, COIL_Y, (PARK_Z0 + PARK_Z1) / 2)).cut(cyl(NOZZLE_R + 1.0, PARK_Z1 - PARK_Z0 + 2, "z", (ex, COIL_Y, (PARK_Z0 + PARK_Z1) / 2)))
    bracket = box(24.0, 36.0, 16.0, (ex, PLATE_Y0 - 16.0, PARK_Z0 + 8.0))     # x ex +-12, y -56..-92, z 62..78 (plate top is 73)
    return sleeve.union(bracket.cut(cyl(NOZZLE_R + 1.0, 40, "z", (ex, COIL_Y, PARK_Z0 + 8))))


def parts():
    tail, nozzle = nozzle_and_tail()
    return {"sampler_pump": (pump(), COL["pump"]), "sampler_silicone_link": (link_hose(), COL["sil"]), "sampler_pu_coil": (coil(), COL["pu"]),
            "sampler_pu_tail": (tail, COL["pu"]), "sampler_nozzle": (nozzle, COL["nozzle"]), "sampler_parking_socket": (parking_socket(), COL["park"])}


def vol(w):
    return sum(s.Volume() for s in w.solids().vals()) if w.solids().vals() else 0.0


def inter(a, b):
    bb, cc = a.val().BoundingBox(), b.val().BoundingBox()
    if bb.xmax < cc.xmin or cc.xmax < bb.xmin or bb.ymax < cc.ymin or cc.ymax < bb.ymin or bb.zmax < cc.zmin or cc.zmax < bb.zmin:
        return 0.0
    return vol(a.intersect(b))


def check():
    import cart_assembly as ca
    out = {}
    pp = parts()
    out["sample_tube_length_m"] = SAMPLE_TUBE_M
    out["sample_volume_ml"] = math.pi * (TUBE_ID / 2) ** 2 * SAMPLE_TUBE_M * 1000.0 / 1000.0
    out["coil_length_retracted_mm"] = COIL_PITCH * COIL_TURNS + TUBE_OD
    bb = {n: s.val().BoundingBox() for n, (s, c) in pp.items()}
    out["coil_x_range_mm"] = (bb["sampler_pu_coil"].xmin, bb["sampler_pu_coil"].xmax)
    out["coil_inner_gap_to_battery_mm"] = bb["sampler_pu_coil"].xmin - (BATT_X + BATT[0] / 2)
    out["coil_overhang_past_plate_edge_mm"] = bb["sampler_pu_coil"].xmax - PLATE_X1
    out["coil_y_range_mm"] = (bb["sampler_pu_coil"].ymin, bb["sampler_pu_coil"].ymax)
    out["coil_gap_to_plate_face_mm"] = PLATE_Y0 - bb["sampler_pu_coil"].ymax
    out["pump_x_range_mm"] = (bb["sampler_pump"].xmin, bb["sampler_pump"].xmax)
    out["pump_inside_plate_x"] = bb["sampler_pump"].xmin >= PLATE_X0 and bb["sampler_pump"].xmax <= PLATE_X1
    out["parking_socket_top_over_plate_top_mm"] = PARK_Z1 - PLATE_ZH
    # against everything else on the cart (the arm included)
    clash = {}
    for n, (s, c) in pp.items():
        for m in ("base_plate", "battery", "so101_arm_envelope", "track_pipe_B", "track_pipe_C"):
            v = inter(s, ca.plate if m == "base_plate" else {"battery": ca.battery, "so101_arm_envelope": ca.arm}.get(m) or cq.Workplane("XY").add(cq.Solid.makeCylinder(16, 330, cq.Vector(-60 if m.endswith("B") else 60, 0, 0), cq.Vector(0, 0, 1))))
            if v > 1e-3:
                clash["%s vs %s" % (n, m)] = round(v, 2)
    # sleeves/hands: use the assembly's own parts
    hand_hits = {}
    for nm, shp, col in ca.clamp_hand_parts():
        for side, sgn in (("C", 1), ("B", -1)):
            h = ca.csl.place_hand(shp, sgn)
            for n, (s, c) in pp.items():
                v = inter(s, h)
                if v > 1e-3:
                    hand_hits["%s vs hand_%s_%s" % (n, side, nm)] = round(v, 2)
    out["sampler_vs_cart_clashes_mm3"] = clash
    out["sampler_vs_hands_clashes_mm3"] = hand_hits
    ok = {("sampler_silicone_link", "sampler_pump"), ("sampler_silicone_link", "sampler_pu_coil"), ("sampler_pu_tail", "sampler_pu_coil"), ("sampler_pu_tail", "sampler_nozzle"),
          ("sampler_nozzle", "sampler_parking_socket"), ("sampler_pu_tail", "sampler_parking_socket")}
    names = list(pp)
    internal = {}
    for i, n in enumerate(names):
        for m in names[i + 1:]:
            if (n, m) in ok or (m, n) in ok:
                continue
            v = inter(pp[n][0], pp[m][0])
            if v > 1e-3:
                internal["%s vs %s" % (n, m)] = round(v, 2)
    out["sampler_internal_clashes_mm3"] = internal
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(check(), indent=1, default=str))
