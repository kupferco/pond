# cad/parts/cart.py: the cart as other assemblies use it. The cart itself (plate, two clamp/jaw hands with the motors INWARD, battery, SO-101 arm envelope) is
# defined ONCE in cart_assembly.py (+ cart_sleeves.py, cart_omni.py, cart_base.py, cart_arm.py); this is the single entry point for reuse, so no assembly
# copies or filters the cart's geometry on its own. Frame: the cart frame (pipes along Z at x = +-60, plate on the -Y side).
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cart_assembly as ca   # noqa: E402


def cart_children(drop_pipe=None, skip=(), drop_hand=False):
    """(name, shape-with-location, colour, loc) of every cart part, flat. drop_pipe 'B' or 'C' leaves out that track pipe stub (used when the unit's own
    track pipe stands in for it, so there is ONE track pipe in the picture). The hand (sleeve, wheels, motors) clamped on it STAYS: the cart always has
    both sleeves (#447; leaving one out is what made "Complete unit v2" show one sleeve). Only drop_hand=True removes it too."""
    out = []
    for ch in ca.result.children:
        if drop_pipe and (ch.name == "track_pipe_%s" % drop_pipe or (drop_hand and ch.name.startswith("hand_on_pipe_%s_" % drop_pipe))):
            continue
        if ch.name in skip:
            continue
        out.append(ch)
    return out


def add_cart(assy, prefix="cart_", drop_pipe=None, shift=(0, 0, 0), skip=(), drop_hand=False):
    """Add the cart to a cq.Assembly as flat parts named prefix + original name, moved by the plain translation `shift` (no rotation, no mirroring)."""
    import cadquery as cq
    mv = cq.Location(cq.Vector(*shift))
    for ch in cart_children(drop_pipe, skip, drop_hand):
        assy.add(ch.obj, name=prefix + ch.name, loc=mv * ch.loc if ch.loc else mv, color=ch.color)
    return assy
