# cad/roll_swing_estimate.py: 2D estimate of the roll angle the cart needs to get its free hand off its pipe, in BOTH roll
# directions, and what the roll sweeps into on the way (Pond #277, plan task 265 part 3, section 8). Numbers only: no part is drawn.
# View: a cross-section looking along the STATIC hand's pipe. The static pipe axis is the origin; x runs across the track plane
# towards the free hand's pipe, y out of the track plane (negative y = plate side, in front; positive y = spine side, behind).
# The cart (plate, battery, arm, motors, free sleeve) is rigid and rolls about the origin. The free pipe, growing pipe stay put.
# Directions: "plate" = the free hand moves towards -y (the way the plate faces), "spine" = towards +y (growing pipe side).
# Run: python3 roll_swing_estimate.py [out.png]      (needs cadquery only because cart_dims imports hand_sleeve)
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_dims as cd

SLEEVE_REACH = 54.0      # ASSUMED (plan section 4): furthest wheel point from the sleeve axis, 38 mm omni on a 32 mm pipe
CLEAR = 3.0              # ASSUMED clearance added to every obstacle
ENVELOPE_R = SLEEVE_REACH + CLEAR          # the free sleeve's swept radius about its own axis
PIPE_R = cd.PIPE_R
SPINE_R, SPINE_Y = 37.5, 60.0              # growing pipe R37.5, 60 mm behind the track plane (plan section 2)
SPINE_X_LEG, SPINE_X_BEND_END = 290.0, 140.0   # static pipe to the spine axis: legs are 580 apart; end of the 150 mm bend is 150 closer
ARM_TOP = cd.PLATE_Y0 - cd.BATT[1] - 110.0     # folded arm reaches about 110 mm above the battery (ASSUMED envelope)
SLEEVE_HALF_L = 62.5                       # sleeve about 125 long (plan section 4)
STEP = 0.25


def boxes(static_sgn):
    """Cart boxes (x0, x1, y0, y1) in the static pipe frame. static_sgn = +1: static hand on pipe C (x=+60), free hand B on -x."""
    cx = -static_sgn * cd.HX                  # cart centre line, relative to the static pipe
    def b(x0, x1, y0, y1):
        xs = sorted((cx + x0, cx + x1))
        return (xs[0], xs[1], min(y0, y1), max(y0, y1))
    return {"plate": b(cd.PLATE_X0, cd.PLATE_X1, cd.PLATE_Y0, cd.PLATE_Y0 + cd.PLATE_T),
            "battery": b(cd.BATT_X - cd.BATT[0] / 2, cd.BATT_X + cd.BATT[0] / 2, cd.PLATE_Y0, cd.PLATE_Y0 - cd.BATT[1]),
            "motors": b(cd.MOTOR_XS[-1] - cd.MOTOR_R, cd.MOTOR_XS[1] + cd.MOTOR_R, cd.PLATE_Y0, cd.PLATE_Y0 - 2 * cd.MOTOR_R),
            "arm": b(-cd.ARM_BASE_W / 2, cd.ARM_BASE_W / 2, cd.PLATE_Y0 - cd.BATT[1], ARM_TOP)}


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def disc_box(cx, cy, r, bx):
    """Distance from a disc centre to a box edge minus r (negative = overlap)."""
    x0, x1, y0, y1 = bx
    dx, dy = max(x0 - cx, 0, cx - x1), max(y0 - cy, 0, cy - y1)
    return math.hypot(dx, dy) - r


def free_pipe_x(static_sgn, z, diverge):
    """Free pipe's x (static frame) at height z along the pipe. Straight leg: 120 away. On the bend the two pipes curve away from each
    other (B bends left, C right, 150 mm radius), so at z from the cart's mid point the gap is wider by about z^2 / 150 (ASSUMED)."""
    return -static_sgn * (cd.PIPE_SPACING + (z * z / 150.0 if diverge else 0.0))


def phi_of(static_sgn, direction, theta):
    """Counter-clockwise turn (deg) of the cart in the (x, y) section for a roll of `theta` towards `direction`.
    The free hand sits at angle 180 deg (static on C) or 0 deg (static on B); "plate" moves it to -y."""
    return static_sgn * theta if direction == "plate" else -static_sgn * theta


def sweep(static_sgn, direction, spine_x, diverge):
    """Roll from 0 in `direction` until the free hand is off its pipe, stopping at the first contact.
    Returns (roll deg needed to be off the pipe, first contact text or None, roll deg of the contact)."""
    bx = boxes(static_sgn)
    hit = hit_deg = off = None
    for k in range(int(180 / STEP) + 1):
        th = k * STEP
        phi = phi_of(static_sgn, direction, th)
        hx, hy = rot(-static_sgn * cd.PIPE_SPACING, 0.0, phi)          # free hand's axis after the roll
        # off the pipe: the swept envelope (R57) must clear the free pipe (R16) at the middle and at both sleeve ends
        sep = min(math.hypot(hx - free_pipe_x(static_sgn, z, diverge), hy) for z in (-SLEEVE_HALF_L, 0.0, SLEEVE_HALF_L))
        if off is None and sep >= ENVELOPE_R + PIPE_R:
            off = th
        # contacts: rotate the fixed obstacles by -phi into the cart frame, test against the cart's boxes
        obstacles = [("free pipe", free_pipe_x(static_sgn, z, diverge), 0.0, PIPE_R) for z in (-cd.PLATE_ZH, 0.0, cd.PLATE_ZH)]
        obstacles.append(("growing pipe", -static_sgn * spine_x, SPINE_Y, SPINE_R))
        for name, ox, oy, orad in obstacles:
            px, py = rot(ox, oy, -phi)
            for n, b in bx.items():
                if hit is None and disc_box(px, py, orad + CLEAR, b) < 0:
                    hit, hit_deg = "%s vs %s" % (name, n), th
        if off is not None and (hit is not None or th >= off + 1.0):
            break
    return off, hit, hit_deg


def report():
    """Table of both trips, both directions, at the three places that matter. Returns the rows."""
    rows = []
    cases = (("straight leg", True, False), ("bend start (pipes diverge)", True, True),
             ("end of the bend, near the spine", False, True))
    for trip, s in (("up pipe C, hand B released", +1), ("up pipe B, hand C released", -1)):
        for label, on_leg, diverge in cases:
            spine_x = SPINE_X_LEG if on_leg else SPINE_X_BEND_END
            for direction in ("plate", "spine"):
                off, hit, hd = sweep(s, direction, spine_x, diverge)
                rows.append((trip, label, direction, off, hit, hd))
    return rows


def draw(path, static_sgn=+1):
    """PNG of the cross-section: left = rolled to the plate side to the angle where the free hand is off, right = spine side at the first contact."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon
    fig, axs = plt.subplots(1, 3, figsize=(15, 6))
    bx = boxes(static_sgn)
    col = {"plate": "#8aa", "battery": "#c96", "motors": "#6a6", "arm": "#a8c"}
    off, _, _ = sweep(static_sgn, "plate", SPINE_X_LEG, False)
    _, hit, hd = sweep(static_sgn, "spine", SPINE_X_LEG, False)
    for ax, (title, direction, th) in zip(axs, (("start (roll 0)", "plate", 0.0),
                                                ("PLATE side, %.0f deg: free hand off its pipe, no contact" % off, "plate", off),
                                                ("SPINE side, %.0f deg: %s" % (hd, hit), "spine", hd))):
        phi = phi_of(static_sgn, direction, th)
        for n, (x0, x1, y0, y1) in bx.items():
            ax.add_patch(Polygon([rot(x, y, phi) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))], closed=True, fc=col[n], ec="k", alpha=0.7, label=n))
        hx, hy = rot(-static_sgn * cd.PIPE_SPACING, 0.0, phi)
        ax.add_patch(Circle((hx, hy), ENVELOPE_R, fc="none", ec="b", ls="--", label="free sleeve (R%.0f)" % ENVELOPE_R))
        ax.add_patch(Circle((0, 0), PIPE_R, fc="#444", label="static pipe"))
        ax.add_patch(Circle((-static_sgn * cd.PIPE_SPACING, 0), PIPE_R, fc="#d33", label="free pipe (stays)"))
        ax.add_patch(Circle((-static_sgn * SPINE_X_LEG, SPINE_Y), SPINE_R, fc="#9c9", ec="k", label="growing pipe (290 mm away)"))
        ax.set_xlim(-330, 330); ax.set_ylim(-260, 130); ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_title(title, fontsize=9)
        ax.set_xlabel("across the track plane, mm   (static pipe at 0)"); ax.set_ylabel("out of the track plane, mm (+ spine side, - plate side)")
    axs[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Pond #277: roll about the static pipe, cross-section, hand B released (up pipe C). Estimate, ASSUMED sizes.")
    fig.tight_layout(); fig.savefig(path, dpi=110)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        draw(sys.argv[1])
    print("Roll about the static pipe's centre, free hand off its pipe needs a centre separation of %.0f mm (R%.0f envelope + R%.0f pipe)."
          % (ENVELOPE_R + PIPE_R, ENVELOPE_R, PIPE_R))
    for trip, label, d, off, hit, hd in report():
        ok = off is not None and (hit is None or hd > off)
        print("%-28s %-34s %-5s needs %s deg, first contact %s -> %s" % (
            trip, label, d, "%.1f" % off if off is not None else "never", "none" if hit is None else "%s at %.1f deg" % (hit, hd),
            "CLEARS" if ok else "BLOCKED"))
