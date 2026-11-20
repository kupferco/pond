# cad/parts/sample_coil.py: the SAMPLE TUBING COIL of the water test (OpenPocket #330, plan 307 part 2; single-sourced in #365).
# Thin tube from the cart's peristaltic pump to the sample point: a short silicone section through the pump head (link), a food-safe PU recoil coil
# that holds the sample (about 50 to 100 ml, metered by counting pump turns) and a straight tail up to the male nozzle (parts/water_connector.py).
# Frame: the cart frame of cart_dims.py / cart_assembly.py. ASSUMED (nothing bought): PU recoil tube 8 mm OD x 6 mm ID, coil 52 mm mean diameter,
# 14 turns, 8 mm pitch (about 112 mm long retracted, stretches to about 2 m).
import math
import cadquery as cq
from cart_dims import PLATE_Y0
from .common import hose
from . import water_connector as wc

TUBE_OD, TUBE_ID = 8.0, 6.0            # PU recoil tube
SIL_OD = 9.0                           # silicone section through the pump head (6 ID)
COIL_R = 26.0                          # mean coil radius
COIL_PITCH = 8.0
COIL_TURNS = 14
COIL_X = 67.0                          # coil axis (x): 13 mm beyond the plate edge on pipe C side; inner edge 2 mm from the battery column (x +-35)
COIL_Y = PLATE_Y0 - (COIL_R + TUBE_OD / 2 + 1.0)    # axis out from the plate so the coil clears the plate face by 1 mm
COIL_Z0 = -58.0                        # starts above the pipe C roll motor so the coil, which overhangs the plate edge, clears it
PUMP_X, PUMP_Z = -62.0, -28.0          # pump axis along Y (pump itself: water_sampler.py)
PARK_Z0 = 73.0                         # bottom face of the parking block, where the nozzle is parked
SAMPLE_TUBE_M = COIL_TURNS * 2 * math.pi * COIL_R / 1000.0 + 0.3     # coil plus tails, metres
COL = dict(sil=(0.85, 0.85, 0.9, 0.9), pu=(0.2, 0.75, 0.85, 1))


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


def tail_and_nozzle():
    """Tube tail straight up from the coil end to the male nozzle, shown PARKED (spigot pushed up into the flush hole in the parking block)."""
    ex = COIL_X + COIL_R
    z_end = COIL_Z0 + COIL_PITCH * COIL_TURNS
    nozzle = wc.male(ex, COIL_Y, PARK_Z0, +1)
    tail = hose(TUBE_OD / 2, [(ex, COIL_Y, z_end), (ex, COIL_Y, PARK_Z0 - wc.COLLAR_L + 2.0)])
    return tail, nozzle


def sample_tubing():
    """name -> (shape, colour) of the whole tubing run: silicone link, PU coil, PU tail (the nozzle is a connector part, see tail_and_nozzle)."""
    tail, _ = tail_and_nozzle()
    return {"sampler_silicone_link": (link_hose(), COL["sil"]), "sampler_pu_coil": (coil(), COL["pu"]), "sampler_pu_tail": (tail, COL["pu"])}
