# cad/pod_layout.py: the ONE definition of the pod-grab layout (OpenPocket #531, owner decision 26 Nov 2026). Pure Python (no CadQuery), so the CAD
# (cad/pond_full_unit.py, cad/parts/shelf_items.py, cad/parts/tank.py) and the sim (sim/pod_grab.py) both read the same numbers. mm, CAD frame:
# X along the bottom track run, Y front(-) / back(+), Z up, tank floor z = 0, growing pipe at x = y = 0.
#
# THE DECISION
#   * Both carts stay UPRIGHT on the track (no 45 deg roll), track height unchanged (cad/layout.json).
#   * Real SO-101 arm, base straight on the cart plate (cad/cart_dims.py v4), pods stay vertical.
#   * Seedling tray: 6 x 3 cells, every cell picked upright (the claw tilts sideways on the outer columns).
#   * Dry pod store: a gravity-feed tray, 7 lanes sloping SLOPE_DEG towards the front, each ending in a short flat landing with a stop lip, so the
#     front pod stands upright under its pick slot. 4 pods per lane (28). SLOPE_DEG is ONE parameter: a guess pending a real-pot ramp test.
#   * The lid has a pick slot (SLOT_X x SLOT_Y) over every tray cell and every store landing.
# Anything marked ASSUMED is not given by the owner.
import json
import math
import os

_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout.json")))
TANK_H, LID_T = float(_D["tank_h_mm"]), float(_D["lid_t_mm"])
LID_TOP = TANK_H + LID_T                                              # 304
WATER_LEVEL = float(_D["water_level_mm"])
SHELF_T = 4.0
SHELF_TOP = WATER_LEVEL + 5.0 + SHELF_T                               # 159: the shelf the tray and the store stand on (cad/parts/unit_dims.py)
TRACK_Z = LID_TOP + float(_D["cart_below_track_mm"]) + float(_D["cart_clearance_mm"])   # 514: bottom run axis (cad/layout.py TRACK_BOTTOM_Z)
TRACK_Y, TRACK_R = -60.0, 16.0                                        # track loop plane and pipe radius (cad/parts/unit_dims.py LOOP_Y, TR)
STRAIGHT_X = 140.0                                                    # the bottom run is straight for |x| <= 140 (TX 290 - corner radius 150)

# ---------------- the cart (cad/cart_dims.py v4; cad/check_pod_layout.py asserts these equal it) ----------------
PARK_TRAY, PARK_STORE = -130.0, 135.0   # cart centre when parked over the tray and at the store. The cart's jaw motors stick out 104 mm past its centre on the +Z side (cart frame), which
                                     # is towards the growing pipe at the store: at +130 they clip the pipe (R 37.5), at +135 they clear it
PLATE_Y0 = -56.0                     # plate front face, out of the pipe axis
PLATE_T, PLATE_ALONG, PLATE_DOWN = 6.0, 146.0, 160.0
PLATE_CZ_REL = -60.0                 # plate centre height relative to the pipe axis (pipe C hand on the track, plate hangs below)
ARM_X = -9.0                         # arm base centre, cart frame x (up/down across the plate), cad/cart_dims.ARM_X (v4)
ARM_Z = 0.0                          # arm base centre along the track
BATT = (50.0, 70.0, 70.0)            # cart_dims.BATT: X (across the plate), Y (out of the plate), Z (along the track); stood on its edge beside the arm
BATT_X = 55.0

# ---------------- the pod ----------------
POD_D, POD_H = 25.0, 40.0
CELL_X, CELL_Y = 35.0, 34.0         # tray cell footprint (one block per cell, a round pocket for the pod)
TRAY_BASE_T, CELL_H = 6.0, 24.0

# ---------------- seedling tray: 6 columns x 3 rows (the drafts-branch full unit the owner approved), 18 cells ----------------
# Columns 1..6 run from the parked cart (x -130) outwards: x -115, -150, ..., -290 (35 mm pitch); rows A..C at y -138, -100, -62 (38 mm pitch, A nearest the front edge).
# The drafts had the rows 25 mm apart (pods touching): the sim shows the claw's jaws (24 mm wide at the tip) then hit the neighbouring pod by about 6 mm in rows B and C, so the rows are 38 mm apart.
TRAY_COLS = 6
TRAY_COL_X0, TRAY_PITCH = -115.0, 35.0
TRAY_SHIFT = 12.0                    # rows moved back (+y) so the wrist stays off the tank's front wall (the sim has the wall: sim/pod_grab_check.py)
TRAY_ROWS_Y = tuple(y + TRAY_SHIFT for y in (-150.0, -112.0, -74.0))
ROW_NAMES = "ABC"
POD_BOTTOM_TRAY = SHELF_TOP + TRAY_BASE_T                             # 165: pods stand on the tray base inside their cell
POD_TOP_TRAY = POD_BOTTOM_TRAY + POD_H                                # 205: the grip height of a tray pod


def tray_cell_x(c):
    """x of tray column c (0-based, 0 = nearest the parked cart): -115, -150, ..., -290."""
    return TRAY_COL_X0 - c * TRAY_PITCH


def tray_cells():
    """{'A1': (x, y, grip_z, park_x)} for the 18 cells."""
    return {f"{ROW_NAMES[r]}{c + 1}": (tray_cell_x(c), TRAY_ROWS_Y[r], POD_TOP_TRAY, PARK_TRAY) for r in range(len(TRAY_ROWS_Y)) for c in range(TRAY_COLS)}


# ---------------- dry pod store: gravity feed, 7 lanes ----------------
SLOPE_DEG = 15.0                     # ASSUMED (the owner's guess): enough for a dry plastic net pot to slide; test with the real pots, change it HERE only
LANES = 7
LANE_PITCH = 30.0
STORE_CX = 190.0                     # store centre x: lanes at x 100 ... 280 (the drafts-branch full unit)
LANE_PODS = 4                        # pods per lane, 28 in all
STORE_BASE_T = 12.0
ZL = SHELF_TOP + STORE_BASE_T                                         # 171: landing floor
STORE_SHIFT = 28.0                   # store moved back (+y) for the same reason
LAND_Y = (-180.0 + STORE_SHIFT, -152.0 + STORE_SHIFT)   # the flat landing; the front pod is centred on it
LAND_CY = -165.0 + STORE_SHIFT
LIP_T, LIP_H = 6.0, 14.0             # stop lip in front of the landing
RAMP_Y1 = -62.0 + STORE_SHIFT                      # back end of the ramp
RAIL_H, RAIL_T = 22.0, 3.0
STORE_Y_BACK = RAMP_Y1
POD_TOP_STORE = ZL + POD_H                                            # 211: grip height of the front pod on a landing
POD_PITCH_ON_RAMP = 26.0             # queued pods behind the front one, along the ramp


def lane_x(i):
    return STORE_CX + (i - (LANES - 1) / 2) * LANE_PITCH


def ramp_rise():
    return (RAMP_Y1 - LAND_Y[1]) * math.tan(math.radians(SLOPE_DEG))


def queue_ok():
    """The 3 queued pods fit on the ramp: their run along the slope must be shorter than the ramp."""
    return (LANE_PODS - 1) * POD_PITCH_ON_RAMP <= (RAMP_Y1 - LAND_Y[1]) / math.cos(math.radians(SLOPE_DEG))


def store_cells():
    """{'S1': (x, y, grip_z, park_x)} for the 7 landings (S1 at x 100 ... S7 at x 280)."""
    return {f"S{i + 1}": (lane_x(i), LAND_CY, POD_TOP_STORE, PARK_STORE) for i in range(LANES)}


# ---------------- lid pick slots ----------------
# The claw and the wrist go below the lid top. Owner: slots of about 70 x 50 over every target. The sim (sim/pod_grab_check.py --write-slots) measures the claw and wrist
# footprint at the lid for the pose of every cell and writes cad/pod_slots.json: each slot is that footprint plus SLOT_MARGIN, never smaller than SLOT_X x SLOT_Y. On the 38 mm cell
# pitch the tray slots overlap into one window (and the store slots into another). The claw leans towards the arm on the outer columns, so the slots are NOT centred on the pods.
SLOT_X, SLOT_Y = 70.0, 50.0          # the minimum slot, along the track and front-to-back
SLOT_MARGIN = 4.0
SLOT_R = 6.0                         # corner radius of a slot in the CAD
SLOTS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pod_slots.json")


def slot_rects():
    """{target name: (x0, x1, y0, y1)} of the lid slots: from pod_slots.json (written by the sim), else the minimum slot centred on the target."""
    if os.path.exists(SLOTS_JSON):
        return {k: tuple(v) for k, v in json.load(open(SLOTS_JSON))["slots"].items()}
    return {k: (x - SLOT_X / 2, x + SLOT_X / 2, y - SLOT_Y / 2, y + SLOT_Y / 2) for k, (x, y, _, _) in list(tray_cells().items()) + list(store_cells().items())}


# ---------------- other things the arm must not hit ----------------
PILLAR_R = 37.5                      # growing pipe, 75 mm OD
STATION = dict(x0=60.0, x1=260.0, y0=14.0, y1=108.0, z0=394.0, z1=507.0)   # water station box (cad/water_station.py BOX + OFF_Y 50 + the 64 mm track rise), behind the track, on four legs to the lid
