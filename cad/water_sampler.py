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
from parts import water_connector as wc  # noqa: E402
from parts.common import hose, vol, inter  # noqa: E402,F401
from parts.sample_coil import *  # noqa: E402,F401,F403  (the tubing: coil, link, tail, nozzle and their numbers)
from parts import sample_coil as sc  # noqa: E402

PUMP_R, PUMP_L = 17.0, 40.0
PARK_Z1 = 89.0                        # parking block z 73..89 (PARK_Z0 in parts/sample_coil.py): its flat BOTTOM face carries the flush female socket, looking down (-Z)
COL = dict(pump=(0.92, 0.5, 0.15, 1), sil=sc.COL['sil'], pu=sc.COL['pu'], nozzle=(0.95, 0.95, 0.4, 1), park=(0.95, 0.95, 0.95, 1))


def pump():
    y0 = PLATE_Y0 - PUMP_L
    body = cyl(PUMP_R, PUMP_L, "y", (PUMP_X, y0 + PUMP_L / 2, PUMP_Z))
    base = box(2 * PUMP_R, PUMP_L, PUMP_R + 8, (PUMP_X, y0 + PUMP_L / 2, PUMP_Z - PUMP_R / 2 - 4))        # motor/foot block under the rotor
    return body.union(base)


def parking_socket():
    """Block 24 x 36 x 16 on the plate's top edge (bolts to the plate, z 73..89, x ex +-12, y -56..-92) with a plain round hole with a slight recess FLUSH with its bottom face.
    Nothing sticks out of the face. The nozzle is pushed straight up into it and pulled straight down out of it by the arm; friction holds it."""
    ex = COIL_X + COIL_R
    bracket = box(24.0, 36.0, PARK_Z1 - PARK_Z0, (ex, PLATE_Y0 - 16.0, (PARK_Z0 + PARK_Z1) / 2))
    return bracket.cut(wc.female_cut(ex, COIL_Y, PARK_Z0, -1))


def parts():
    _, nozzle = tail_and_nozzle()
    out = {"sampler_pump": (pump(), COL["pump"])}
    out.update(sample_tubing())                      # silicone link, PU coil and tail: cad/parts/sample_coil.py
    out["sampler_nozzle"] = (nozzle, COL["nozzle"])
    out["sampler_parking_socket"] = (parking_socket(), COL["park"])
    return out


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
    pk = pp["sampler_parking_socket"][0].val().BoundingBox()
    nb_ = pp["sampler_nozzle"][0].val().BoundingBox()
    out["parking_socket_face_z_mm (flush: the block bottom face)"] = pk.zmin
    out["parking_socket_sticks_out_below_face_mm (0 = flush)"] = round(PARK_Z0 - pk.zmin, 6)
    out["parked_spigot_depth_in_hole_mm"] = round(nb_.zmax - PARK_Z0, 3)
    out["parked_nozzle_vs_block_clash_mm3 (0 = fits)"] = round(inter(pp["sampler_nozzle"][0], pp["sampler_parking_socket"][0]), 4)
    out["nozzle_collar_bottom_over_coil_top_mm"] = round((PARK_Z0 - wc.COLLAR_L) - (COIL_Z0 + COIL_PITCH * COIL_TURNS + TUBE_OD / 2), 3)
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
    ok = {("sampler_silicone_link", "sampler_pump"), ("sampler_silicone_link", "sampler_pu_coil"), ("sampler_pu_tail", "sampler_pu_coil"), ("sampler_pu_tail", "sampler_nozzle")}   # nozzle vs parking block is NOT allowed: the spigot fits the flush hole with clearance
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
