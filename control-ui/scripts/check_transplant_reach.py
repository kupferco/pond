# Reach check for the Transplant scene, with the REAL parts in their REAL places (no invented geometry). Prints the result and draws the plan (top) and front views.
# Real numbers: tank 700 x 400 x 300 + 4 lid, growing pipe 75 mm at x = y = 0 (cad/unit_v3_aframe.py); track pipes 16 mm radius at x = -/+290, y = -60 (LOOP_Y); the cart hangs on
# TWO neighbouring pipes 120 mm apart (cad/cart_dims.py), so on this unit's side it straddles x = 290 and 410 (or -290 and -410); plate 6 mm, battery 50 mm, SO-101 base underside 102 mm
# out from the pipe plane, shoulder 95 mm up its base axis, links 115 + 135 mm, hand 110 mm to the cap top (control-ui/src/arm/kinematics.ts); collar with the pod seat 45 degrees up
# (cad/pipe_collar.py), its azimuth round the pipe left FREE here. Usage: python3 control-ui/scripts/check_transplant_reach.py OUT_DIR
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

S = math.sqrt(0.5)
TX, LOOP_Y, SPACING = 0.29, -0.06, 0.12
ARM_Y0 = 0.102                 # base underside, out of the plate (cart_dims.py ARM_Y0 = -102)
SH, L1, L2, HAND = 0.095, 0.115, 0.135, 0.1085
ZH, RP = 0.80, 0.0375          # hole height is ASSUMED in the scene (collar height on the pipe is not fixed in the CAD)
U_CAP, CAP_T = 0.0217, 0.008


def search():
    best = (1e9, None)
    for side in (-1, 1):
        for flip in (-1, 1):                       # flip +1: plate on the pipe's side of the track plane, arm pointing at the pipe; -1: plate on the front side
            xb = side * (TX + SPACING / 2)
            yb = LOOP_Y + flip * ARM_Y0
            for th in range(360):
                h = (math.cos(math.radians(th)), math.sin(math.radians(th)))
                ax = (S * h[0], S * h[1], S)
                p0 = ((RP - 0.0015) * h[0], (RP - 0.0015) * h[1], ZH)
                t = [p0[i] + ax[i] * (U_CAP + CAP_T) for i in range(3)]
                w = [t[i] + ax[i] * HAND for i in range(3)]
                for k in range(0, 101):
                    zb = 0.4 + 0.01 * k
                    d = math.dist(w, (xb, yb + flip * SH, zb))
                    if d > L1 + L2 - 0.002 or d < 0.03:
                        continue
                    rho = (t[0] - xb, t[2] - zb)    # the arm plane holds the base axis (along y) and this radial vector
                    n = (rho[1], -rho[0]); nl = math.hypot(*n) or 1
                    err = math.degrees(math.asin(abs(ax[0] * n[0] + ax[2] * n[1]) / nl))
                    if err < best[0]:
                        best = (err, (side, flip, th, zb, d))
    return best


def main(out):
    os.makedirs(out, exist_ok=True)
    err, cfg = search()
    side, flip, th, zb, d = cfg
    print(f"Best case with the wrist in reach: the pod axis is {err:.1f} degrees out of the arm's plane "
          f"(pair at x {side*TX*1000:+.0f}/{side*(TX+SPACING)*1000:+.0f} mm, plate {'towards' if flip > 0 else 'away from'} the pipe, collar azimuth {th} deg, cart z {zb:.2f} m, wrist {d*1000:.0f} mm from the shoulder of {1000*(L1+L2):.0f} max).")
    print("A 26 mm bore round a 25 mm pod tolerates about 1 degree over the 24 mm it goes in: this does not work.")
    xb = side * (TX + SPACING / 2)
    for view in ("top", "front"):
        fig, ax = plt.subplots(figsize=(10, 6.2), dpi=110)
        ax.set_aspect("equal")
        if view == "top":
            ax.add_patch(Rectangle((-0.35, -0.2), 0.7, 0.4, fc="#cfd5de", ec="#667", label="tank 700 x 400"))
            ax.add_patch(Circle((0, 0), RP, fc="#fff", ec="#222", lw=2)); ax.text(0, 0, "growing\npipe 75", ha="center", va="center", fontsize=8)
            for px in (-TX - SPACING, -TX, TX, TX + SPACING):
                ax.add_patch(Circle((px, LOOP_Y), 0.016, fc="#888", ec="#222"))
            ax.text(-TX - SPACING / 2, LOOP_Y - 0.045, "track pipes\n(16 mm, y = -60)", ha="center", fontsize=8)
            # the cart: plate, battery, arm base, shoulder; plate side towards the pipe (flip +1) or away (flip -1), as found best
            y_plate = LOOP_Y + flip * 0.049
            ax.add_patch(Rectangle((xb - 0.083, y_plate - 0.003), 0.166, 0.006, fc="#555"))
            ax.add_patch(Rectangle((xb - 0.035, min(y_plate, LOOP_Y + flip * ARM_Y0) if flip < 0 else y_plate), 0.07, 0.05, fc="#3b73d9"))
            ax.add_patch(Rectangle((xb - 0.035, LOOP_Y + flip * ARM_Y0 - (0.008 if flip < 0 else 0)), 0.07, 0.008, fc="#ddd", ec="#333"))
            ys = LOOP_Y + flip * (ARM_Y0 + SH)
            ax.plot([xb], [ys], "o", color="#d33"); ax.text(xb, ys + flip * 0.015, "arm shoulder", ha="center", fontsize=8, color="#d33")
            ax.annotate("", xy=(xb, ys + flip * 0.12), xytext=(xb, ys), arrowprops=dict(arrowstyle="->", color="#d33"))
            ax.text(xb + 0.02, ys + flip * 0.09, "arm base axis\n(pan axis)", fontsize=8, color="#d33")
            ax.add_patch(Circle((xb, ys), L1 + L2 + HAND, fill=False, ls="--", ec="#d33"))
            ax.text(xb + 0.2, ys - 0.28, "furthest the hand tip can be\nfrom the shoulder: 360 mm", fontsize=8, color="#d33", ha="center")
            h = (math.cos(math.radians(th)), math.sin(math.radians(th)))
            ax.annotate("", xy=(RP * h[0] + 0.07 * h[0], RP * h[1] + 0.07 * h[1]), xytext=(RP * h[0], RP * h[1]), arrowprops=dict(arrowstyle="->", color="#080", lw=2))
            ax.text(0.08 * h[0], 0.08 * h[1] + 0.02, "hole (best azimuth)", fontsize=8, color="#080")
            ax.set_xlim(-0.55, 0.45); ax.set_ylim(-0.32, 0.28)
            ax.set_title(f"TOP VIEW, real parts in their real places: shoulder to hole is {1000*math.hypot(xb, ys):.0f} mm in plan, and the pod axis is {err:.0f} deg out of the arm's plane at best")
        else:
            ax.add_patch(Rectangle((-0.35, 0), 0.7, 0.304, fc="#cfd5de", ec="#667"))
            ax.add_patch(Rectangle((-RP, 0.304), 2 * RP, 1.25, fc="#e9eef2", ec="#222"))
            for px in (-TX - SPACING, -TX, TX, TX + SPACING):
                ax.add_patch(Rectangle((px - 0.016, 0.6), 0.032, 1.15, fc="#888", ec="#222"))
            ax.add_patch(Rectangle((-0.345, 0.23), 0.2, 0.035, fc="#4caf70", ec="#264"))
            ax.text(-0.245, 0.17, "seedling tray\n190 x 360 x 35,\nin the tank under\nthe lid (z 230..265)", ha="center", fontsize=7)
            ax.plot([0.0], [ZH], "o", color="#080"); ax.text(0.03, ZH, "hole (height assumed)", fontsize=8, color="#080")
            ax.add_patch(Rectangle((xb - 0.083, zb - 0.056), 0.166, 0.112, fc="#555", alpha=0.8))
            ax.text(xb, zb + 0.08, "cart plate\n166 x 112", ha="center", fontsize=8)
            ax.plot([xb], [zb], "o", color="#d33")
            ax.add_patch(Circle((xb, zb), L1 + L2 + HAND, fill=False, ls="--", ec="#d33"))
            ax.set_xlim(-0.8, 0.8); ax.set_ylim(0, 1.8)
            ax.set_title("FRONT VIEW: tank, growing pipe, track pipes and cart; dashed = furthest the hand can be from the shoulder (360 mm, shown flat)")
        ax.grid(alpha=0.25)
        fig.savefig(os.path.join(out, f"transplant-real-layout-v3-{view}.png"), bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/drawings/renders")
