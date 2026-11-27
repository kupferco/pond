# cad/publish_transplant_scene.py: puts the regenerated Transplant seedling drawings on the Drawings page (OpenPocket #537, v12).
#   cd control-ui && node --experimental-strip-types scripts/export-transplant.ts /tmp/tpout
#   python control-ui/scripts/render_tris.py /tmp/tpout /tmp/tprender          (writes ...-v11-*.png: renamed to v12 here)
#   python cad/publish_transplant_scene.py /tmp/tpout /tmp/tprender
#   python cad/render_line_thumbs.py views <the v12 ids>                       (line views)
# v12: the scene is drawn from the ONE layout (cad/layout.json via control-ui/src/generated/cad-sim.ts): central pipe on the tank centre, track plane 66 mm in front of it (tube radius 16 + the
# 50 mm rod of the track joint; v11 had 60). Copies the four views (iso, front, side, top) + the closeups, the clip and the GLB of every step to docs/drawings/renders and cad/renders.
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs", "drawings")
STEPS = {"step0": "start", "step1": "step1-pick", "step2": "step2-drive", "step3": "step3-plug", "step4": "step4-seat"}
NOTE = (" v12 (OpenPocket #537, owner review: one fixed layout): redrawn from cad/layout.json. The central pipe stays on the centre of the tank and the track loop is 66 mm in front of it "
        "(16 mm tube radius + the 50 mm M8 rod of the flush track joint, cad/track_joint.py ROD_OUT; v11 had 60 mm). The arm poses are solved again with the sim's own inverse kinematics.")


def main():
    src, rend = sys.argv[1], sys.argv[2]
    path = os.path.join(DOCS, "renders.json")
    data = json.load(open(path))
    cards = {c["id"]: c for c in data["renders"]}
    out = os.path.join(DOCS, "renders")
    new_ids = []
    for sid, name in STEPS.items():
        old, new = "transplant-seedling-%s-v11" % name, "transplant-seedling-%s-v12" % name
        for suffix in ("iso", "front", "side", "top", "closeup", "collar"):
            f = os.path.join(rend, "%s-%s.png" % (old, suffix))
            if os.path.exists(f):
                shutil.copy(f, os.path.join(out, "%s-%s.png" % (new, suffix)))
                if suffix in ("iso", "front", "side", "top"):
                    shutil.copy(f, os.path.join(HERE, "renders", "%s-%s.png" % (new, suffix)))
        clip = os.path.join(rend, old + "-clip.gif")
        if os.path.exists(clip):
            shutil.copy(clip, os.path.join(out, new + "-clip.gif"))
        shutil.copy(os.path.join(src, sid + ".glb"), os.path.join(out, new + ".glb"))
        shutil.copy(os.path.join(src, sid + ".glb"), os.path.join(HERE, "renders", new + ".glb"))
        c = dict(cards[old])
        c.update(id=new, version=12, date="2026-11-26", comment=c["comment"].replace(old + "-clip", new + "-clip") + NOTE,
                 thumb="renders/%s-line.png" % new, viewer=c["viewer"].replace(old, new))
        old_card = cards[old]
        old_card["status"] = "superseded"
        data["renders"] = [c] + [r for r in data["renders"] if r["id"] != new]
        new_ids.append(new)
    data["updated"] = "2026-11-26"
    json.dump(data, open(path, "w"), indent=2, ensure_ascii=False)
    open(path, "a").write("\n")
    print(" ".join(new_ids))


if __name__ == "__main__":
    main()
