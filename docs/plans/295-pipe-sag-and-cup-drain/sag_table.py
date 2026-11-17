"""Sag table for plan 295. Run: python3 docs/plans/295-pipe-sag-and-cup-drain/sag_table.py
Cart 3 kg -> 29.4 N, x1.5 for shock/one pipe taking it = 44 N, point load at the worst place (midspan of the unsupported length L)."""
import math
F = 3.0 * 9.81 * 1.5
E = {"new 3000": 3000.0, "creep 1000": 1000.0, "hot+creep 600": 600.0}
PIPES = {"32x1.8": (32, 1.8), "32x3.0": (32, 3.0), "25x1.5": (25, 1.5), "25x2.3": (25, 2.3)}
I = lambda od, t: math.pi / 64 * (od**4 - (od - 2 * t)**4)
CASES = {"both ends held (fixed-fixed, F/192)": 1/192, "one end pinned (fixed-pinned, 7/768)": 7/768,
         "simple ends (pinned-pinned, 1/48)": 1/48}
for name, (od, t) in PIPES.items():
    print(f"\n{name}  I = {I(od,t):.0f} mm4")
    for cname, k in CASES.items():
        print(" ", cname)
        for L in (150, 200, 300, 400, 500):
            print(f"    L={L}: " + "  ".join(f"{en} {k*F*L**3/(e*I(od,t)):5.2f}" for en, e in E.items()))
    for L in (100, 150, 200, 300):
        print(f"  cantilever tip L={L}: " + "  ".join(f"{en} {F*L**3/(3*e*I(od,t)):6.2f}" for en, e in E.items()))
