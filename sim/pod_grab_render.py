"""Four-view PNGs (iso, front, top, side) and a GLB of the pod grab scene with the arm at a pick pose (OpenPocket #522).

    MUJOCO_GL=egl python3 sim/pod_grab_render.py [tray_shift_mm] [tilt_deg] [target]    # writes cad/renders/pod-grab-reach-*
Needs mujoco, numpy, imageio, trimesh.
"""
import importlib.util
import os
import sys

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pod_grab", os.path.join(HERE, "pod_grab.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
OUT = os.path.join(HERE, "..", "cad", "renders")


def posed(shift, tilt, target):
    p = {k: v[0] for k, v in G.PARAMS.items()}
    p.update(tray_shift_mm=shift, tilt_deg=tilt)
    m = mujoco.MjModel.from_xml_string(G.build(**p))
    d = mujoco.MjData(m)
    x, y, z = G.targets(p)[target]
    q, ok = G.pose_for(p, y, z)
    for n, v in zip(("shoulder_lift", "elbow_flex", "wrist_flex"), q):
        d.qpos[m.joint(n).qposadr[0]] = v
    d.qpos[m.joint("cart_x").qposadr[0]] = (x - G.TRAY_X) / 1000.0
    mujoco.mj_forward(m, d)
    return m, d


def pngs(m, d, prefix):
    import imageio
    r = mujoco.Renderer(m, 720, 1280)
    for cam, name in (("iso", "iso"), ("front", "front"), ("top", "top"), ("side", "side")):
        r.update_scene(d, camera=cam)
        imageio.imwrite(os.path.join(OUT, f"{prefix}-{name}.png"), r.render())


def glb(m, d, path):
    import trimesh
    sc = trimesh.Scene()
    T = mujoco.mjtGeom
    for g in range(m.ngeom):
        t, s = int(m.geom_type[g]), m.geom_size[g]
        name = m.geom(g).name
        if t == T.mjGEOM_PLANE or name in ("lid",):
            continue
        if t == T.mjGEOM_BOX:
            mesh = trimesh.creation.box(extents=2 * s)
        elif t == T.mjGEOM_CYLINDER:
            mesh = trimesh.creation.cylinder(radius=s[0], height=2 * s[1])
        elif t == T.mjGEOM_CAPSULE:
            mesh = trimesh.creation.capsule(radius=s[0], height=2 * s[1])
        elif t == T.mjGEOM_SPHERE:
            mesh = trimesh.creation.icosphere(radius=s[0])
        else:
            continue
        T4 = np.eye(4)
        T4[:3, :3] = d.geom_xmat[g].reshape(3, 3)
        T4[:3, 3] = d.geom_xpos[g]
        mesh.visual.face_colors = (np.array(m.geom_rgba[g]) * 255).astype(np.uint8)
        sc.add_geometry(mesh, node_name=name or f"geom{g}", transform=T4)
    # glTF is Y up: rotate the sim's Z up into it
    rot = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    sc.apply_transform(rot)
    sc.export(path)


if __name__ == "__main__":
    shift = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    tilt = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    target = sys.argv[3] if len(sys.argv) > 3 else "D"
    os.makedirs(OUT, exist_ok=True)
    m, d = posed(shift, tilt, target)
    pngs(m, d, "pod-grab-reach")
    glb(m, d, os.path.join(OUT, "pod-grab-reach.glb"))
    print("written to", OUT)
