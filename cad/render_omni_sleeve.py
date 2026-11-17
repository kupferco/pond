# Renders the v5 omni-wheel hand (OpenPocket #278): PNG views (iso, front, top, side) of every changed part IN ITS ASSEMBLY CONTEXT and a GLB.
# Usage: python cad/render_omni_sleeve.py [name ...]     (writes cad/renders/; no names = everything)
#   cart-omni            drive + roll omni wheels, ball cups, motors of one hand on the pipe (cart_omni.py in context, no sleeve)
#   hand-sleeve          the v5 three-lobe sleeve with its wheels, cups and motors on the pipe (hand_sleeve.py in context)
#   cart-sleeves         both hands clamped, rigid plate (cart_sleeves.py)
#   cart-sleeves-transfer  hand C static, hand B released, whole cart rolled 36 deg about pipe C
#   cart-wheel-pairs     both hands' wheel pairs on the two pipes (cart_wheel_pairs.py context)
#   cart-wheel-pairs-corner  the hand on the 150 mm loop corner
#   assembly.glb         cart_sleeves.clamped for the 3D viewer
import os
import sys
import time
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_local as rl

R = os.path.join(HERE, "renders")
os.makedirs(R, exist_ok=True)
VIEWS = (("iso", 28, -55), ("front", 0, -90), ("top", 90, -90), ("side", 0, 0))


def views(assy, name, title):
    parts = rl.collect(assy)
    for view, el, az in VIEWS:
        t = time.time()
        rl.draw(parts, el, az, os.path.join(R, "%s-%s.png" % (name, view)), "%s (%s)" % (title, view))
        print("wrote", name, view, "%.0fs" % (time.time() - t), flush=True)


def scenes():
    import cart_sleeves as cs
    import cart_wheel_pairs as cw
    import hand_sleeve as hs
    hand = cq.Assembly()
    hand.add(cs.cyl(hs.R_PIPE, 250.0, "z", (0, 0, 0)), name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    for n, (s, col) in cs.hand_parts().items():
        hand.add(s, name=n, color=cq.Color(*col))
    return {
        "cart-omni": (cw.result, "Omni wheels, ball cups and motors of one hand on the 32 mm pipe"),
        "hand-sleeve": (hand, "Hand sleeve v5 (three lobes) with wheels, cups and motors, on the pipe"),
        "cart-sleeves": (cs.clamped, "Cart: both hands clamped, rigid plate"),
        "cart-sleeves-transfer": (cs.transfer, "Cart rolled 36 deg about the static pipe, other hand released"),
        "cart-wheel-pairs": (cw.context, "Wheel pairs of both hands on pipes 120 mm apart"),
        "cart-wheel-pairs-corner": (cw.corner, "Hand on the 150 mm loop corner"),
    }


if __name__ == "__main__":
    want = sys.argv[1:]
    sc = scenes()
    if not want or "assembly.glb" in want:
        import cart_sleeves as cs
        cs.clamped.export(os.path.join(R, "assembly.glb"))
        print("GLB done", flush=True)
    for name, (assy, title) in sc.items():
        if not want or name in want:
            views(assy, name, title)
