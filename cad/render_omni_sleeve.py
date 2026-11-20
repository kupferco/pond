# Renders the v5 omni-wheel hand (OpenPocket #278): PNG views (iso, front, top, side) of every changed part IN ITS ASSEMBLY CONTEXT and a GLB.
# Usage: python cad/render_omni_sleeve.py [name ...]     (writes cad/renders/; no names = everything)
#   cart-omni            drive + roll omni wheels, ball cups, motors of one hand on the pipe (cart_omni.py in context, no sleeve)
#   hand-sleeve          the v5 three-lobe sleeve with its wheels, cups and motors on the pipe (hand_sleeve.py in context)
#   cart-sleeves         both hands clamped, rigid plate (cart_sleeves.py)
#   cart-sleeves-transfer  hand C static, hand B released, whole cart rolled 36 deg about pipe C
#   cart-wheel-pairs     both hands' wheel pairs on the two pipes (cart_wheel_pairs.py context)
#   cart-wheel-pairs-corner  the hand on the 150 mm loop corner
#   cart-assembly        (OpenPocket #280) the whole cart: plate, battery, arm folded, both omni hands on two pipes
#   cart-arm-stowed      whole cart, arm folded for travel (cart_arm.py)
#   cart-arm-working     whole cart, arm reaching a pick hole and a seedling cell (cart_arm.py)
#   cart-base            the rigid base plate with battery stops, cables and the hands in context (cart_base.py)
#   cart-pod-holder      the pod holder cup with a pod on the plate, hands and arm base around it (cart_pod_holder.py)
#   home-station-ring    (OpenPocket #286) hand on the pipe with its hall sensor over the ring of magnet tape
#   home-station-point   hand rolled to zero with its hall sensor over the point magnet
#   home-station-rolled  hand rolled 90 deg: the sensor still sees the ring, the point magnet is out of reach
#   assembly.glb         the whole cart (cart_assembly.py) for the 3D viewer. NOTE (#330): the committed assembly.glb is the cart + water sampler + station, from cad/render_water_station.py; run that after this script
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
    import cart_assembly as ca
    import cart_arm as arm
    import cart_base as cb
    import cart_pod_holder as ph
    import home_station as hst
    hand = cq.Assembly()
    hand.add(cs.cyl(hs.R_PIPE, 250.0, "z", (0, 0, 0)), name="track_pipe", color=cq.Color(0.75, 0.78, 0.8, 1))
    for n, (s, col) in cs.hand_parts().items():
        hand.add(s, name=n, color=cq.Color(*col))
    return {
        "cart-omni": (cw.result, "Omni wheels, ball cups and motors of one hand on the 32 mm pipe"),
        "hand-sleeve": (hand, "Hand sleeve v5 (three lobes) with wheels, cups and motors, on the pipe"),
        "cart-assembly": (ca.result, "Whole cart: rigid plate, battery, folded arm, two omni hands on two pipes"),
        "cart-arm-stowed": (arm.result_stowed, "Arm folded for travel on the cart"),
        "cart-arm-working": (arm.result, "Arm working on the cart"),
        "cart-base": (cb.result, "Rigid base plate on the sleeve pads, battery, cables"),
        "cart-pod-holder": (ph.scene(True, show=("plate", "battery", "arm_base")), "Pod holder with a pod, below the plate"),
        "home-station-ring": (hst.scene("ring"), "Home station: hall sensor over the ring of magnet tape"),
        "home-station-point": (hst.scene("point"), "Home station: hall sensor over the point magnet, roll 0"),
        "home-station-rolled": (hst.scene("ring", 90.0), "Home station: hand rolled 90 deg, sensor still over the ring"),
        "cart-sleeves": (cs.clamped, "Cart: both hands clamped, rigid plate"),
        "cart-sleeves-transfer": (cs.transfer, "Cart rolled 36 deg about the static pipe, other hand released"),
        "cart-wheel-pairs": (cw.context, "Wheel pairs of both hands on pipes 120 mm apart"),
        "cart-wheel-pairs-corner": (cw.corner, "Hand on the 150 mm loop corner"),
    }


if __name__ == "__main__":
    want = sys.argv[1:]
    sc = scenes()
    if not want or "assembly.glb" in want:
        import cart_assembly as ca
        ca.result.export(os.path.join(R, "assembly.glb"), tolerance=0.5, angularTolerance=0.3)   # coarser mesh: 11 MB instead of 50 MB (#316)
        print("GLB done", flush=True)
    for name, (assy, title) in sc.items():
        if not want or name in want:
            views(assy, name, title)
