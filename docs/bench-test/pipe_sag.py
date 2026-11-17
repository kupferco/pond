"""Pipe sag for the cart roll redesign (Pond #275, owner answer Q1/Q6).
Standard PVC-U round pipe, cart load as a point load at the worst place on a run.
Run: python3 docs/bench-test/pipe_sag.py
Assumptions are in the constants: change them if the real pipe or supports differ."""
import math

CART_KG = 3.0                    # plan section 3: cart about 3 kg
LOAD_N = CART_KG * 9.81 * 1.5    # x1.5 for the cart being carried by one pipe at a time + shock
E_SHORT = 3000.0                 # MPa, PVC-U short term
E_CREEP = 1000.0                 # MPa, PVC-U after years under load (about 1/3 of short term)
LIMIT_MM = 1.0                   # target: sag under the cart no more than 1 mm (wheels keep contact)

# (OD, wall) mm: wall is for the common thin pressure/waste grades; check the real pipe
PIPES = {"32 mm x 1.8 (waste)": (32, 1.8), "32 mm x 3.0 (pressure)": (32, 3.0),
         "25 mm x 1.5 (waste)": (25, 1.5), "25 mm x 2.3 (pressure)": (25, 2.3)}
# Spans: run segment between the centre bracket (x=0) and the corner / leg joint is 140..290 mm.
# Brackets hold the centre, so the middle is stiff and the sag is at the ends: model each end
# segment as a beam fixed at the bracket, pinned at the corner (stiff) and, worst case, a
# cantilever with the cart at the free end (nothing supporting the corner).
SPANS = (140, 290)

def inertia(od, wall):
    return math.pi / 64 * (od**4 - (od - 2 * wall)**4)

print(f"point load {LOAD_N:.0f} N, limit {LIMIT_MM} mm")
for name, (od, t) in PIPES.items():
    I = inertia(od, t)
    for L in SPANS:
        # fixed-pinned, load at midspan: d = 7 F L^3 / (768 E I)
        # cantilever, load at the tip:  d = F L^3 / (3 E I)
        for label, k in (("fixed-pinned", 7 / 768), ("cantilever", 1 / 3)):
            d_short = k * LOAD_N * L**3 / (E_SHORT * I)
            d_creep = k * LOAD_N * L**3 / (E_CREEP * I)
            flag = "ok" if d_creep <= LIMIT_MM else "TOO SOFT"
            print(f"{name:24s} L={L:3d} {label:13s} short {d_short:5.2f} mm  creep {d_creep:5.2f} mm  {flag}")
