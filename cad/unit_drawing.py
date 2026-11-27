# cad/unit_drawing.py: the unit as the DRAWINGS show it from OpenPocket #570 on: the unit's own parts (cad/parts/unit.py, unchanged, the sim still reads those)
# with ONE change: the track shows the spine-to-track connector (cad/spine_connector.py) on both runs at x = 0: nut plate, M8 rod, lock nut, the two spine
# nuts (PROPOSAL), and the rod holes in the track, growing pipe and spine. It replaces the old bracket stubs (spine_brackets), which stood where the rod goes.
# The two 50 mm clamp collars (they hold the A-frame legs / leg sleeves) are NOT pipe collars and stay exactly as in unit_parts(). No drawing listed in #570
# shows a pod pipe collar (the pods are the simplified ones of cad/parts/pods.py), so the three-seat collar of cad/pipe_collar_3seat.py is not placed anywhere.
# Used by complete_unit.py, unit_v3_dimensioned.py and unit_structure_drawing.py (unit_v3_aframe.py and the track-supports drawing keep the plain unit).
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spine_connector as sc
from parts.common import inter
from parts.unit import unit_parts


def drawing_parts(water=True):
    """unit_parts() with the connector on the track. Same (name, shape, colour) list shape."""
    cut = {}
    for zc in sc.ZONES.values():
        for n, c in sc.unit_cutters(zc).items():
            cut[n] = c if n not in cut else cut[n].union(c)
    out = []
    for n, s, c in unit_parts(water=water):
        if n == "spine_brackets":
            continue
        if n in cut:
            s = s.cut(cut[n])
        out.append((n, s, c))
        if n == "track_loop":
            for k, zc in sc.ZONES.items():
                out += [("%s_connector_%s" % (nm, k), w, col + (1,)) for nm, w, col in sc.unit_hardware(zc)]
    return out


def check():
    """Overlaps (mm3) of the connector hardware with the unit parts it passes (after the holes are cut), plus its clash with the legs and leg sleeves
    (clamp collars). All must be 0."""
    out = {}
    pr = {n: s for n, s, c in drawing_parts()}
    legs = [pr[n] for n in pr if "legs" in n or n.startswith("clamp_collars")]
    for k in sc.ZONES:
        for n in ("nut_plate", "m8_rod", "lock_nut", "PROPOSAL_spine_nut_outside", "PROPOSAL_spine_nut_inside"):
            hw = pr["%s_connector_%s" % (n, k)]
            others = ["track_loop", "growing_pipe", "spine_tube", "internal_spacers", "tank", "lid"]
            for other in others:
                v = inter(hw, pr[other])
                if v > 1e-3:
                    out["connector %s %s vs %s" % (k, n, other)] = round(v, 2)
            for i, l in enumerate(legs):
                v = inter(hw, l)
                if v > 1e-3:
                    out["connector %s %s vs legs/sleeves %d" % (k, n, i)] = round(v, 2)
    return out


if __name__ == "__main__":
    r = check()
    for k, v in r.items():
        print("%-60s %s mm3" % (k, v))
    print("overlaps:", len(r), "(0 = clear of legs, leg sleeves, pipe, spine, tank)")
