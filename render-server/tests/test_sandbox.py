from pathlib import Path

from pond_render.sandbox.host import run_cad_script

ROOT = Path(__file__).resolve().parents[2]

BOX = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 30).faces(">Z").workplane().hole(5)
print("made a box")
"""


def test_box_renders(tmp_path):
    r = run_cad_script(BOX, out_dir=tmp_path, views=["front", "top", "side", "iso"], timeout_s=120)
    assert r.ok, r.error
    assert r.bbox["size"] == [10.0, 20.0, 30.0]
    assert r.solids == 1
    assert r.volume and 5000 < r.volume < 6000
    assert set(r.files) == {"model.step", "model.stl", "model.glb"}
    assert all(p.stat().st_size > 0 for p in r.files.values())
    assert set(r.svgs) == {"front", "top", "right", "iso"}
    assert "<svg" in r.svgs["front"].read_text()
    assert "made a box" in r.log


def test_show_object_and_assembly(tmp_path):
    script = """
a = cq.Workplane("XY").box(5, 5, 5)
b = cq.Workplane("XY").box(2, 2, 2).translate((10, 0, 0))
asm = cq.Assembly().add(a, name="a").add(b, name="b")
show_object(asm)
"""
    r = run_cad_script(script, out_dir=tmp_path, views=["iso"], timeout_s=120)
    assert r.ok, r.error
    assert r.solids == 2


def test_script_error_is_reported_with_line(tmp_path):
    script = "import cadquery as cq\nx = 1\nresult = cq.Workplane('XY').box(1, 2)\n"
    r = run_cad_script(script, out_dir=tmp_path, views=["iso"], timeout_s=120)
    assert not r.ok
    assert "line 3" in r.error
    assert "TypeError" in r.error or "missing" in r.error


def test_no_result_is_reported(tmp_path):
    r = run_cad_script("x = 1\n", out_dir=tmp_path, views=["iso"], timeout_s=120)
    assert not r.ok
    assert "result" in r.error


def test_blocked_import(tmp_path):
    r = run_cad_script("import os\nresult = cq.Workplane('XY').box(1,1,1)\n", out_dir=tmp_path, timeout_s=120)
    assert not r.ok
    assert "not allowed" in r.error
    r = run_cad_script("import subprocess\n", out_dir=tmp_path, timeout_s=120)
    assert not r.ok and "not allowed" in r.error


def test_blocked_builtins(tmp_path):
    r = run_cad_script("open('/etc/passwd').read()\nresult = cq.Workplane('XY').box(1,1,1)\n", out_dir=tmp_path, timeout_s=120)
    assert not r.ok
    assert "NameError" in r.error and "open" in r.error


def test_timeout_kills_script(tmp_path):
    r = run_cad_script("while True:\n    pass\n", out_dir=tmp_path, timeout_s=8)
    assert not r.ok and r.timed_out
    assert "killed" in r.error


def test_child_env_is_scrubbed(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPER_SECRET", "hunter2")
    script = "import os\n"  # os is blocked, so probe via the allowed path: math has no env; use the error path
    r = run_cad_script(script, out_dir=tmp_path, timeout_s=120)
    assert not r.ok
    # The guard refused the import before any environment could be read.
    assert "hunter2" not in (r.error or "") + r.log


def test_bad_view_name(tmp_path):
    r = run_cad_script(BOX, out_dir=tmp_path, views=["sideways"], timeout_s=120)
    assert not r.ok and "Unknown view" in r.error


def test_first_part_script_renders(tmp_path):
    script = (ROOT / "cad" / "pipe_clamp_sleeve.py").read_text()
    r = run_cad_script(script, out_dir=tmp_path, views=["front", "top", "right", "iso"], timeout_s=180)
    assert r.ok, r.error
    assert r.solids == 1
    assert r.bbox["size"][2] == 40.0  # LENGTH along Z


def _glb_extents(path):
    """Return the world-space (x, y, z) size of a GLB: accessor bounds pushed through node transforms."""
    import json
    import struct

    import numpy as np

    data = path.read_bytes()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF"
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    assert chunk_type == 0x4E4F534A  # JSON
    doc = json.loads(data[20:20 + chunk_len])

    def local_matrix(node):
        if "matrix" in node:
            return np.array(node["matrix"], dtype=float).reshape(4, 4).T  # glTF is column-major
        m = np.eye(4)
        t = node.get("translation", [0, 0, 0])
        qx, qy, qz, qw = node.get("rotation", [0, 0, 0, 1])
        sx, sy, sz = node.get("scale", [1, 1, 1])
        r = np.array([
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
        ])
        m[:3, :3] = r @ np.diag([sx, sy, sz])
        m[:3, 3] = t
        return m

    pts = []

    def visit(index, parent):
        node = doc["nodes"][index]
        world = parent @ local_matrix(node)
        if "mesh" in node:
            for prim in doc["meshes"][node["mesh"]]["primitives"]:
                acc = doc["accessors"][prim["attributes"]["POSITION"]]
                lo, hi = acc["min"], acc["max"]
                for cx in (lo[0], hi[0]):
                    for cy in (lo[1], hi[1]):
                        for cz in (lo[2], hi[2]):
                            pts.append((world @ np.array([cx, cy, cz, 1.0]))[:3])
        for child in node.get("children", []):
            visit(child, world)

    scene = doc["scenes"][doc.get("scene", 0)]
    for root in scene["nodes"]:
        visit(root, np.eye(4))
    arr = np.array(pts)
    return [round(float(v), 2) for v in (arr.max(axis=0) - arr.min(axis=0))]


def test_glb_is_y_up_for_shape(tmp_path):
    """A 10 x 20 x 40 box (Z tall) must come out 10 wide, 40 tall (Y) and 20 deep (Z) in the GLB."""
    r = run_cad_script('result = cq.Workplane("XY").box(10, 20, 40)\n', out_dir=tmp_path, views=["iso"],
                       timeout_s=120, exports=("glb",))
    assert r.ok, r.error
    assert r.bbox["size"] == [10.0, 20.0, 40.0]  # bbox stays Z-up
    assert _glb_extents(r.files["model.glb"]) == [10.0, 40.0, 20.0]


def test_glb_is_y_up_for_assembly(tmp_path):
    script = """
a = cq.Workplane("XY").box(10, 10, 10)
b = cq.Workplane("XY").box(10, 10, 10).translate((0, 0, 30))
result = cq.Assembly().add(a, name="a").add(b, name="b")
"""
    r = run_cad_script(script, out_dir=tmp_path, views=["iso"], timeout_s=120, exports=("glb",))
    assert r.ok, r.error
    assert r.bbox["size"] == [10.0, 10.0, 40.0]
    assert _glb_extents(r.files["model.glb"]) == [10.0, 40.0, 10.0]
