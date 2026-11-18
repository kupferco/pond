# OpenPocket #316: close-ups of ONE ball cup (back hole, four 2 mm side holes) with its sleeve lobe (drain slots), plus cup GLB.
# Usage: python cad/render_cup_drain.py        writes cad/renders/cup-drain-{iso,front,top,side,back}.png and cup-drain.glb
# Cup frame: x = radially outward (back hole axis), y = round the pipe (two side holes), z = along the pipe (two side holes).
# The sleeve is cut to a 40 mm block round the cup so the holes and slots can be seen; the ball is left out so the seat is visible.
import os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl
import cart_omni as co
import hand_sleeve as hs
import cart_wheel_pairs as cw

R = os.path.join(HERE, "renders")
A = hs.INNER_ANGS[0]
Z = hs.ROW_Z
XC = co.CUP["centre_r"] if hasattr(co, "CUP") else hs.CUP["centre_r"]


def scene(cut=None, sleeve=True):
    """cut = 'z' keeps z <= cup centre (section through the back hole and the two +/-y side holes); 'y' keeps y >= 0 (section through the two +/-z side holes)."""
    a = cq.Assembly()
    keep = None
    if cut == "z":
        keep = cq.Workplane("XY").box(60, 60, 30, centered=(True, True, False)).translate((XC, 0, Z - 30))
    elif cut == "y":
        keep = cq.Workplane("XY").box(60, 30, 60, centered=(True, False, True)).translate((XC, 0, Z))
    blk = cq.Workplane("XY").box(44, 44, 44).translate((XC, 0, Z))
    cup = hs.CUP["cup"].translate((XC, 0, Z))
    if keep is not None:
        cup = cup.intersect(keep, clean=False)
    if sleeve:
        lobe = hs.result.rotate((0, 0, 0), (0, 0, 1), -A).intersect(blk)
        if keep is not None:
            lobe = lobe.intersect(keep, clean=False)
        a.add(lobe, name="sleeve_lobe", color=cq.Color(0.6, 0.6, 0.65, 1))
    a.add(cup, name="ball_cup", color=cq.Color(*cw.CUP_COL))
    return a


if __name__ == "__main__":
    a = scene()
    a.export(os.path.join(R, "cup-drain.glb"), tolerance=0.1, angularTolerance=0.2)
    jobs = (("iso", scene("z"), 40, 35), ("front", scene("y"), 0, -90), ("top", scene("z"), 90, -90),
            ("side", scene(sleeve=False), 25, 25))     # iso/top: section through the cup axis seen from +z; front: section seen from -y; side: cup alone seen from outside
    for view, sc, el, az in jobs:
        rl.draw(rl.collect(sc), el, az, os.path.join(R, "cup-drain-%s.png" % view),
                "Ball cup: back hole, four 2 mm side holes, sleeve slots (%s)" % view)
        print("wrote", view, flush=True)
