"""Pipe sag WITH the new track supports (OpenPocket #315, part 1 of plan #295; owner answers Q1 to Q5).
Run: python3 docs/bench-test/track_support_sag.py
Beam model (Euler-Bernoulli finite elements, 2 mm elements), 32 x 1.8 mm PVC-U, one 44 N point load swept along the run
(the worst place is found by sweeping, not assumed). x = 0 is the centre bracket / collar, clamped (no sag, no rotation).

Owner spans (Q1): bottom run L = 300 mm, top run L = 400 mm, "the bend acting as a pinned end" (the far end of the span is
held down, free to turn). Limits (Q2): 1 mm bottom, 3 mm top. Wall 1.8 (Q3, weaker case, re-run when measured).

Supports (Q4), each is a spring, not a rigid point (the rod and its post flex a little, that is counted):
- bottom: one support each side, just before the curve starts: post on the tank lid + 34 mm free M8 rod (a cantilever in
  bending) into the pipe wall (nut plate inside, like the track joint rod).
- top: a short vertical hanger from the crossbar (top_bar) to a small block, and the same 34 mm M8 stub from the block into
  the pipe. No diagonal rods. The hanger is a spring in series with the stub: the steel bar (20 x 15, held at its two ends by the
  top triangle legs) bent by the load, the hanger itself is short and counted rigid.
Top run end (the bend): the bend sits on the vertical leg, so the end is not rigid, it is the leg's axial spring (E A / leg
length) standing on a locked bottom run ("bottom locked", Q4). Bottom run end: pinned (Q1).
Run: python3 docs/bench-test/track_support_sag.py  (needs numpy)"""
import math
import numpy as np

CART_KG = 3.0
LOAD_N = CART_KG * 9.81 * 1.5            # 44 N, same as plan section 1
E_CASES = (("new", 3000.0), ("creep", 1000.0), ("hot+creep", 600.0))   # MPa
OD, WALL = 32.0, 1.8
I_PIPE = math.pi / 64 * (OD**4 - (OD - 2 * WALL)**4)        # mm4, 19 500
A_PIPE = math.pi / 4 * (OD**2 - (OD - 2 * WALL)**2)         # mm2
LIMIT_BOTTOM, LIMIT_TOP = 1.0, 3.0

# steel M8 rod (E 200 GPa), thread minor diameter 6.5 mm
E_ROD = 200000.0
D_ROD = 6.5
I_ROD = math.pi / 64 * D_ROD**4
A_ROD = math.pi / 4 * D_ROD**2
STUB_FREE = 34.0                          # mm of M8 rod between the pipe surface and the post / block face (CAD)
K_STUB = 3 * E_ROD * I_ROD / STUB_FREE**3  # N/mm, the rod as a cantilever bent by the vertical reaction

# CAD geometry (cad/track_supports.py): leg 1466 mm between the loop bends (ZT - R) - (ZB + R).
# The support sits at x = 125 mm in the CAD (the straight part ends at 140, the bend starts there).
LEG_MM = 1466.0
CAD_SUPPORT_X = 125.0


BAR_HALF = 200.0
BAR_L, BAR_I = 400.0, 20.0 * 15.0**3 / 12      # crossbar between the leg ends, mm, mm4 (steel 20 x 15)


def bar_k(a):
    """Stiffness (N/mm) of the crossbar at a hanger a mm from one end (pinned-pinned beam, point load)."""
    b = BAR_L - a
    return 3 * E_ROD * BAR_I * BAR_L / (a * a * b * b)


def series(*ks):
    return 1.0 / sum(1.0 / k for k in ks)


def solve(L, E, supports, end_k=None, load_step=5.0, h=2.0):
    """Max deflection under the load (mm) over load positions 0..L, and where. supports = [(x, k_N_per_mm)].
    end_k = None: far end pinned (rigid); else the far end stands on a spring of that stiffness."""
    n = int(round(L / h))
    EI = E * I_PIPE
    N = n + 1
    K = np.zeros((2 * N, 2 * N))
    ke = EI / h**3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                               [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
    for e in range(n):
        K[2 * e:2 * e + 4, 2 * e:2 * e + 4] += ke
    free = list(range(2, 2 * N))              # node 0 clamped (w = 0, theta = 0)
    if end_k is None:
        free.remove(2 * n)                    # far end: w = 0, free to turn
    else:
        K[2 * n, 2 * n] += end_k
    for x, k in supports:
        K[2 * int(round(x / h)), 2 * int(round(x / h))] += k
    Kf = K[np.ix_(free, free)]
    inv = np.linalg.inv(Kf)
    idx = {d: i for i, d in enumerate(free)}
    best = (0.0, 0.0)
    for i in range(1, n):
        d = 2 * i
        if d not in idx:
            continue
        w = inv[idx[d], idx[d]] * LOAD_N       # deflection at the load point
        x = i * h
        if w > best[0]:
            best = (w, x)
    return best


def fmt(w):
    return f"{w:5.2f}"


def main():
    print(f"32 x {WALL} mm PVC-U, I = {I_PIPE:.0f} mm4, load {LOAD_N:.0f} N (3 kg x 9.81 x 1.5), worst load place found by sweeping")
    print(f"M8 rod stub {STUB_FREE:.0f} mm free: {K_STUB/1000:.2f} kN/mm\n")

    # --- check against the plan's table (no supports, fixed-pinned): L 300 creep 0.56 mm, L 400 creep 1.32 mm (load at midspan);
    print("Check, no supports, centre clamped / far end pinned (worst place, plan table used midspan so is up to 3 % lower):")
    for L in (300, 400):
        print("  L", L, "  ".join(f"{name} {fmt(solve(L, E, [])[0])}" for name, E in E_CASES))
    print()

    # --- bottom run
    print("BOTTOM run, L = 300 mm (owner), limit 1 mm. Support just before the curve starts.")
    print("  support at x      new / creep / hot+creep (mm), worst load place (creep)")
    rows_bottom = []
    for xs in (120, CAD_SUPPORT_X, 130, 200, 260, None):
        sup = [] if xs is None else [(xs, K_STUB)]
        res = [solve(300, E, sup) for _, E in E_CASES]
        rows_bottom.append((xs, res))
        label = "none (before)" if xs is None else f"{xs} mm"
        ok = "ok" if res[1][0] <= LIMIT_BOTTOM else "OVER"
        print(f"  {label:14s} {fmt(res[0][0])} / {fmt(res[1][0])} / {fmt(res[2][0])}   at x = {res[1][1]:.0f}  {ok} (creep)")
    print("  CAD: the straight part is 140 mm and the support is at x = 125 mm (15 mm before the curve); with the span between"
          "\n  support and bend taken as a straight pinned-pinned beam, which is pessimistic for a bend.")
    # the loaded side beyond the support, cart on the bend, is the span support -> 300
    print()

    # --- top run
    print("TOP run, L = 400 mm (owner), limit 3 mm. Vertical hanger from the crossbar at the middle of the span (x = 200).")
    k_sup = series(bar_k(200.0), K_STUB)
    print(f"  crossbar {bar_k(200.0)/1000:.1f} kN/mm at x = 200 from the end; with the stub {k_sup/1000:.2f} kN/mm")
    print("  columns: new / creep / hot+creep (mm); end = bend on the leg's axial spring, bottom locked")
    rows_top = []
    for label, sup_x, end in (("no hanger, pinned end (before)", None, False),
                              ("no hanger, leg spring end", None, True),
                              ("hanger at 200, pinned end", 200.0, False),
                              ("hanger at 200, leg spring end", 200.0, True)):
        res = []
        for _, E in E_CASES:
            ek = E * A_PIPE / LEG_MM if end else None
            res.append(solve(400, E, [] if sup_x is None else [(sup_x, k_sup)], end_k=ek))
        rows_top.append((label, res))
        ok = "ok" if res[1][0] <= LIMIT_TOP else "OVER"
        print(f"  {label:31s} {fmt(res[0][0])} / {fmt(res[1][0])} / {fmt(res[2][0])}   at x = {res[1][1]:.0f} {ok} (creep)")
    print("  Leg spring (creep): %.0f N/mm, the leg shortens by %.2f mm under 44 N if the cart's whole weight reached it" % (
        E_CASES[1][1] * A_PIPE / LEG_MM, LOAD_N / (E_CASES[1][1] * A_PIPE / LEG_MM)))
    print()

    # --- CAD span, for the drawing: top half span in the CAD is 290 mm; hanger at 125, the bar's leg end is at 200 from the centre
    print("Same, CAD span (centre to leg 290 mm top, hanger at 125, the CAD), creep:")
    k2 = series(bar_k(BAR_HALF - CAD_SUPPORT_X), K_STUB)   # the bar is held at x = -200 and +200
    a = solve(290, E_CASES[1][1], [], end_k=E_CASES[1][1] * A_PIPE / LEG_MM)
    res_cad = [solve(290, E, [(CAD_SUPPORT_X, k2)], end_k=E * A_PIPE / LEG_MM) for _, E in E_CASES]
    print(f"  no hanger {fmt(a[0])} mm, hanger new / creep / hot+creep {fmt(res_cad[0][0])} / {fmt(res_cad[1][0])} / {fmt(res_cad[2][0])} mm")
    print()

    # --- loads in the supports (to size them): reaction at the worst load place, creep
    print("Support strength check (creep case, worst place):")
    # reaction = k * w_at_support; read from a quick solve at the worst place
    bw = solve(300, 1000.0, [(CAD_SUPPORT_X, K_STUB)])
    print(f"  bottom: sag {bw[0]:.2f} mm under 44 N")
    print(f"  top hanger: vertical load at most {LOAD_N:.0f} N if the support took the whole 44 N, in tension / compression in a short block")
    m = LOAD_N * STUB_FREE
    sig = m / (math.pi * D_ROD**3 / 32)
    print(f"  M8 stub bending stress at 44 N: {sig:.0f} MPa (steel 4.6 yields at 240)")
    print()

    top_ok = rows_top[3][1][2][0] <= LIMIT_TOP
    print("RESULT bottom run under 1 mm (new, creep and hot) with the supports:",
          all(r[2][0] <= LIMIT_BOTTOM for xs, r in rows_bottom if xs in (120, CAD_SUPPORT_X, 130)))
    print("RESULT top run under 3 mm (new, creep and hot) with the hangers:", top_ok and all(r[0] <= LIMIT_TOP for r in res_cad))
    return rows_bottom, rows_top


if __name__ == "__main__":
    main()
