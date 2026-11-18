# Software renderer for the Transfer scene pictures (OpenPocket #283; no GPU here): draws the triangle lists written by export-transfer.ts in four views (iso, front, top, side),
# using the Transplant renderer's painter's algorithm (render_tris.py).
# Usage: python3 scripts/render_transfer.py TRI_DIR OUT_DIR
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_tris import draw  # noqa: E402


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for st in json.load(open(os.path.join(src, "stages.json"))):
        tris = json.load(open(os.path.join(src, st["id"] + ".json")))
        cx, cy, cz = st["centre"]
        wide = "top" in st["id"] or "rollback" in st["id"] or "bend" in st["id"]
        hw = 0.5 if wide else 0.3
        # the camera looks at the cart (rider pipe at path position s); the cart is about 0.15 m in front of the pipe plane (-y)
        for view in ("iso", "front", "top", "side"):
            box = (cx, -0.05, cz, hw * (1.3 if view == "iso" else 1.0), hw * (1.3 if view == "iso" else 1.0))
            draw(tris, view, box, os.path.join(out, f"transfer-{st['id']}-{view}.png"), px=900)
        print(st["id"], "contact:" if st["hit"] else "clear", st["hit"])


if __name__ == "__main__":
    main()
