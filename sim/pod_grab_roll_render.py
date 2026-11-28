"""Four-view PNGs (iso, front, top, side) and GLBs of the 26 Nov pod grab layout with the arm at a pick pose (OpenPocket #522 follow-up).

    MUJOCO_GL=glfw xvfb-run -a python3 sim/pod_grab_roll_render.py      # or MUJOCO_GL=egl without xvfb
Writes cad/renders/pod-grab-roll-{rolled,upright}-{iso,front,top,side}.png and cad/renders/pod-grab-roll-{rolled,upright}.glb.
Rolled: cart rolled 45 degrees over tray cell D1. Upright: cart upright over the far-left tray corner D4. Needs mujoco, numpy, imageio, trimesh.
"""
import importlib.util
import math
import os

import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G, R = load("pod_grab"), load("pod_grab_render")
C = load("pod_grab_roll_check")
OUT = os.path.join(HERE, "..", "cad", "renders")


def posed(cell, roll):
    p = C.params()
    m = mujoco.MjModel.from_xml_string(G.build(**p))
    d = mujoco.MjData(m)
    x, y, z, park = G.cell_target(p, cell)
    C.set_pose(m, d, park, roll, G.solve(park, roll, (x, y, z))["pose"])
    return m, d


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for tag, cell, roll in (("rolled", "D1", 45.0), ("upright", "D4", 0.0)):
        m, d = posed(cell, roll)
        R.pngs(m, d, f"pod-grab-roll-{tag}")
        R.glb(m, d, os.path.join(OUT, f"pod-grab-roll-{tag}.glb"))
    print("written to", OUT)
