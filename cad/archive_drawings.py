# cad/archive_drawings.py: retires duplicate and outdated drawings to docs/drawings/archive/ (OpenPocket #459). Nothing is deleted.
#   python cad/archive_drawings.py
# A card is retired when its status is "superseded", or when a newer version of the same drawing (same id apart from the "-vN" at the end) exists.
# Its GLB and picture files move to docs/drawings/archive/renders/ and its entry moves from docs/drawings/renders.json to
# docs/drawings/archive/renders.json (paths rewritten, status "archived"). The Drawings page shows the archive under its own "Archive" button.
# The complete unit and anything the 3D Models page or the home page still opens (docs/models/models.json, docs/home.json) are never moved.
import glob
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "docs", "drawings")
RJ = os.path.join(D, "renders.json")
AJ = os.path.join(D, "archive", "renders.json")


# Drawings that show the same thing as a kept one (owner review, OpenPocket #459).
RETIRE = {"unit-water-v1", "transplant-real-layout-v3"}


def stem_version(rid):
    m = re.match(r"^(.*)-v(\d+)$", rid)
    return (m.group(1), int(m.group(2))) if m else (rid, None)


def main():
    data = json.load(open(RJ))
    arch = json.load(open(AJ)) if os.path.exists(AJ) else {"updated": "", "renders": []}
    models = open(os.path.join(D, "..", "models", "models.json")).read() + open(os.path.join(D, "..", "home.json")).read()
    newest = {}
    for r in data["renders"]:
        s, v = stem_version(r["id"])
        if v is not None and r.get("status") != "superseded":
            newest[s] = max(newest.get(s, 0), v)
    keep, move = [], []
    for r in data["renders"]:
        s, v = stem_version(r["id"])
        old = r["id"] in RETIRE or r.get("status") == "superseded" or (v is not None and v < newest.get(s, 0))
        if old and ("renders/%s.glb" % r["id"]) not in models:
            move.append(r)
        else:
            keep.append(r)
    os.makedirs(os.path.join(D, "archive", "renders"), exist_ok=True)
    for r in move:
        for f in glob.glob(os.path.join(D, "renders", r["id"] + "[.-]*")):
            shutil.move(f, os.path.join(D, "archive", "renders", os.path.basename(f)))
        r["status"] = "archived"
        r["viewer"] = r["viewer"].replace("src=renders/", "src=archive/renders/")
        r["thumb"] = "archive/" + r["thumb"]
    have = {r["id"] for r in arch["renders"]}
    arch["renders"] += [r for r in move if r["id"] not in have]
    arch["updated"] = data["updated"]
    data["renders"] = keep
    for path, obj in ((RJ, data), (AJ, arch)):
        with open(path, "w") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print("kept %d, archived %d" % (len(keep), len(move)))


if __name__ == "__main__":
    main()
