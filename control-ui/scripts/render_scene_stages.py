# Software renderer for scene pictures made of stage poses (OpenPocket #284; no GPU here): draws the triangle lists of a scripts/export-*.ts run in four views (iso, front, top, side)
# with the Transplant renderer's painter's algorithm (render_tris.py).
# Usage: python3 scripts/render_scene_stages.py TRI_DIR OUT_DIR PREFIX
# TRI_DIR/stages.json: [{id, label, centre: [x, y, z], half}]; writes OUT_DIR/PREFIX-<id>-<view>.png
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_tris import draw  # noqa: E402


def main():
    src, out, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    for st in json.load(open(os.path.join(src, "stages.json"))):
        tris = json.load(open(os.path.join(src, st["id"] + ".json")))
        cx, cy, cz = st["centre"]
        hw = st["half"]
        for view in ("iso", "front", "top", "side"):
            k = 1.25 if view == "iso" else 1.0
            draw(tris, view, (cx, cy, cz, hw * k, hw * k), os.path.join(out, f"{prefix}-{st['id']}-{view}.png"), px=900)
        print(st["id"], st["label"])


if __name__ == "__main__":
    main()
