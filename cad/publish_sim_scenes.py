# cad/publish_sim_scenes.py: puts the sim scene pictures (made from the MuJoCo scenes with the CAD cart, OpenPocket #447) on the Drawings page.
#   python cad/publish_sim_scenes.py
# Reads cad/renders/<prefix>-iso.png (all four colour views stay in cad/renders) and the scene GLB written by control-ui/scripts/export-*.ts + render_*.py, copies them to docs/drawings/renders/<id>-*,
# and adds or updates one card per scene in docs/drawings/renders.json. The sim now draws the CAD cart (control-ui/src/generated, cad/export_sim_model.py).
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "renders")
D = os.path.join(HERE, "..", "docs", "drawings")
GROUP = "Sim scenes (CAD cart)"
NOTE = (" DRAFT, OpenPocket #447: the MuJoCo sim draws the cart from the CAD parts (cad/export_sim_model.py), not its own hand-built shapes, and the scene audit "
        "(control-ui/test/sim.test.ts) checks the cart sits on the track leg, upright, at the right roll. Drawn from the MuJoCo model by a software renderer. Views: -iso, -front, -top, -side.")
# id, picture prefix in cad/renders, glb, title, comment
SCENES = [
    ("sim-cart-on-track-v1", "cart-on-track-1-leg", "cart-on-track-assembly.glb", "Sim: cart on the track",
     "The Cart scene: the cart rides the track leg on hand C with hand B hanging on the OUTER side, as in the Complete unit (before, hand B rode with hand C hanging over the unit)."),
    ("sim-transfer-v1", "transfer-wide-1-start", "transfer-assembly.glb", "Sim: transfer, start at the roll station",
     "The Transfer scene: the CAD cart on pipes B and C of two neighbouring units, both hands clamped."),
    ("sim-pod-grab-v1", "podgrab-omni-1-start", "podgrab-assembly.glb", "Sim: pod grab, start",
     "The Pod grab scene (OpenPocket #537, one layout): the central pipe on the centre of the tank, the track 66 mm from it, the CAD cart riding the bottom run on its TOP sleeve (hand B) with the body and the free hand hanging below the pipe, plate on the side away from the central pipe. Known clash: from there the arm cannot reach the store and the tray (see docs/pod-grab-and-transplant-scenes.md)."),
    ("sim-transplant-v1", "transplant-omni-2-drive", "transplant-assembly.glb", "Sim: transplant seedling, at the hole",
     "The Transplant scene: the CAD cart rolled 180 degrees on the -y leg, plate towards the growing pipe."),
]


def main():
    path = os.path.join(D, "renders.json")
    data = json.load(open(path))
    cards = {c["id"]: c for c in data["renders"]}
    for sid, prefix, glb, title, comment in SCENES:
        if sys.argv[1:] and sid not in sys.argv[1:]:
            continue   # python cad/publish_sim_scenes.py sim-pod-grab-v1: only these cards (the transfer pictures are not in cad/renders)
        for v in ("iso",):     # the colour iso; -line, -front, -top, -side are the black-and-white line views of render_line_thumbs.py (run: python cad/render_line_thumbs.py views <ids>)
            shutil.copy(os.path.join(R, "%s-%s.png" % (prefix, v)), os.path.join(D, "renders", "%s-%s.png" % (sid, v)))
        # the sim works in metres; every other GLB on the site is in millimetres (Y up), so scale it (the viewer and the line drawings expect mm)
        import trimesh
        sc = trimesh.load(os.path.join(R, glb))
        sc.apply_scale(1000.0)
        sc.export(os.path.join(D, "renders", sid + ".glb"))
        cards[sid] = {"id": sid, "date": "2026-11-22", "part": "Sim scene", "category": "Sim", "status": "draft", "version": 1, "group": GROUP, "title": title,
                      "comment": comment + NOTE, "thumb": "renders/%s-line.png" % sid, "viewer": "viewer.html?src=renders/%s.glb&title=%s" % (sid, title.replace(" ", "%20"))}
    order = [c["id"] for c in data["renders"] if c["id"] not in cards or c["id"] not in {s[0] for s in SCENES}]
    data["renders"] = [cards[i] for i in order] + [cards[s[0]] for s in SCENES]
    data["updated"] = "2026-11-22"
    json.dump(data, open(path, "w"), indent=2, ensure_ascii=False)
    open(path, "a").write("\n")
    print("published", len(SCENES), "sim scenes")


if __name__ == "__main__":
    main()
