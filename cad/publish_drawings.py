# cad/publish_drawings.py: puts the regenerated models on the Drawings page and the 3D Models page (OpenPocket #365).
#   python cad/publish_drawings.py [id ...]
# For every row of PUBLISH: copies cad/renders/<glb> to docs/drawings/renders/<id>.glb and the colour iso render to <id>-iso.png, draws the black-and-white
# line views (render_line_thumbs.py: -line, -front, -top, -side), adds or updates the card in docs/drawings/renders.json (older versions in the same group
# stay under the card, marked "superseded"), and adds the model to docs/models/models.json (the data-driven viewer list of #355).
# Everything shown comes from the GLBs the build just made from cad/parts/, so a card can never show an old copy of a part.
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
R = os.path.join(HERE, "renders")
DATE = "2026-11-20"
COMMON = " Views: -iso, -front, -top, -side. Water volume is a separate named part (water_volume) that the 3D viewer can hide."

# id, cad glb, cad png prefix, part, category, group, title, comment, supersedes (ids), models page section (None = drawings only), caption
PUBLISH = [
    ("complete-unit-v2", "complete-unit.glb", "complete-unit", "Complete unit", "Complete unit", "Complete unit",
     "Complete unit v2 (single-source: tank with water, real cart, sample coil)",
     "DRAFT, OpenPocket #365. Rebuilt from the single-source parts (cad/parts/): tank with the water volume at the normal 15 cm level (translucent blue), frame, solar panel, growing pipe with a pod in each of its 48 holes (simplified), seedling tray and storage, and the REAL cart (motors inward, #312) with its sample tubing coil (#330) clamped on the right track run, instead of the old red box stand-in. 3D model: cad/renders/complete-unit.glb." + COMMON,
     ("complete-unit-v1",), ("home", "Complete unit"), "Tank with water, frame, panel, pods, trays and the cart with its sample coil on the track."),
    ("cart-assembly-v5", "cart-assembly.glb", "cart-assembly", "Whole cart assembly", "Cart", "Cart assembly",
     "Whole cart assembly v5 (motors inward)",
     "DRAFT, OpenPocket #365 (regenerated from cart_assembly.py after #312). The cart with the drive and roll motors INWARD in the sleeves, clear of the lettuce; rigid plate, battery under the arm, folded SO-101 envelope. Pipes 120 mm apart. 3D model: cad/renders/cart-assembly.glb." + COMMON,
     ("cart-assembly-v4",), ("models", "Cart"), "The climbing cart with its motors inward, plate, battery and arm mount."),
    ("cart-base-v3", "cart-base.glb", "cart-base", "Cart base plate", "Cart", "Cart base",
     "Cart base plate v3 (regenerated, motors inward)",
     "DRAFT, OpenPocket #365. Same rigid plate as v2, redrawn with the current hands (motors inward, #312).", ("cart-base-v2",), ("models", "Cart"), "The base plate the wheels and motors attach to."),
    ("cart-arm-v4", "cart-arm-working.glb", "cart-arm-working", "Cart arm", "Arm", "Cart arm",
     "Cart arm v4 (working pose, regenerated, motors inward)",
     "DRAFT, OpenPocket #365. Arm reaching a pick hole and a seedling cell, on the current cart (motors inward, #312).", ("cart-arm-v3",), ("models", "Cart"), "The small arm that picks and plants pods."),
    ("cart-arm-stowed-v4", "cart-arm-stowed.glb", "cart-arm-stowed", "Cart arm, stowed", "Arm", "Cart arm, stowed",
     "Cart arm v4 (folded for travel, regenerated, motors inward)", "DRAFT, OpenPocket #365. Arm folded for travel on the current cart.", ("cart-arm-stowed-v3",), None, None),
    ("cart-pod-holder-v3", "cart-pod-holder.glb", "cart-pod-holder", "Pod holder", "Pod handling", "Pod holder",
     "Pod holder v3 (regenerated, motors inward)", "DRAFT, OpenPocket #365. Pod holder cup below the plate with the current hands.", ("cart-pod-holder-v2",), None, None),
    ("track-supports-assembly-v2", "track-supports-assembly.glb", "track-supports-assembly", "Track supports: whole unit", "Track", "Track supports",
     "Whole unit with the track supports (with water)",
     "DRAFT, OpenPocket #315 supports, regenerated in #365 from the single-source unit: the tank now holds its water volume (15 cm, separate part). Supports unchanged: a post on the lid at each end of the bottom run and a hanger from the crossbar on the top run, on the M8 rod entering from the spine side." + COMMON,
     ("track-supports-assembly-v1",), ("models", "Track"), "The unit with the track supports and the water in the tank."),
    ("track-supports-bottom-v2", "track-supports-bottom.glb", "track-supports-bottom", "Track supports: bottom run", "Track", "Track supports, bottom run",
     "Bottom-run support (regenerated)", "DRAFT, regenerated in #365: close-up of the post on the tank lid.", ("track-supports-bottom-v1",), None, None),
    ("track-supports-top-v2", "track-supports-top.glb", "track-supports-top", "Track supports: top run", "Track", "Track supports, top run",
     "Top-run support (regenerated)", "DRAFT, regenerated in #365: close-up of the hanger from the crossbar.", ("track-supports-top-v1",), None, None),
    ("unit-dimensioned-v4", "unit-dimensioned.glb", "unit-dimensioned", "Unit v3 dimensioned", "Unit structure", "Unit v3 dimensioned",
     "Unit v3 dimensioned 3D model (current design, with water)",
     "DRAFT, OpenPocket #365. The dimensioned unit rebuilt from the single-source parts: the old 155 mm shelf and its seedling tray and the red cart stand-in are gone (not in the current design); the water volume is drawn at the normal 15 cm level with a '150 water' dimension. Other dimensions unchanged (1900 total, 300 tank, 150 to the bottom run, 612 and 1466 loop, 700 tank width)." + COMMON,
     ("20261107-134132-a2c1", "20261107-133943-631f"), None, None),
    ("unit-water-v1", "unit-water.glb", "unit-water", "Unit structure with water", "Unit structure", "Unit structure with water",
     "Unit structure with the water in the tank", "DRAFT, OpenPocket #365. The unit's frame, track, spine and growing pipe (cad/unit_v3_aframe.py, assembled from cad/parts/) with the water volume at the normal 15 cm level." + COMMON,
     (), ("models", "Unit"), "The unit structure with its water."),
    ("tank-water-v1", "tank-water.glb", "tank-water", "Tank with water", "Unit structure", "Tank with water",
     "Tank (lid off) with the water volume at 15 cm", "DRAFT, OpenPocket #365. 700 x 400 x 300 mm tank, 4 mm walls, water 696 x 392 x 146 mm inside (about 40 litres), 15 cm from the floor, translucent blue, a separate named part you can hide." + COMMON,
     (), ("models", "Unit"), "The tank with its water volume."),
    ("sample-coil-v1", "sample-coil.glb", "sample-coil", "Sample tubing coil", "Water", "Sample tubing coil",
     "Cart with the water-test sample tubing coil", "DRAFT, OpenPocket #330 coil, drawn on its own in #365 (cad/parts/sample_coil.py). Thin tube from the peristaltic pump: silicone link, PU recoil coil (8 mm OD, 6 mm ID, 14 turns, about 70 ml held), tail up to the male nozzle parked in its socket." + COMMON,
     (), ("models", "Water"), "The cart's peristaltic pump and the thin sample tubing coil to the sample nozzle."),
    ("water-assembly-v1", "assembly.glb", "water-assembly", "Cart at the water testing station", "Water", "Water testing station",
     "Cart with sampler beside the shared water testing station",
     "DRAFT, OpenPocket #330, regenerated in #365 from the single-source parts: the cart (motors inward) with its sample coil at the dock beside the water testing station on the unit's lid (door off, cup cut open; tank not drawn in the pictures, the 3D model has it, with its water). 3D model: cad/renders/assembly.glb." + COMMON,
     (), ("models", "Water"), "The cart at the shared water testing station."),
    ("water-station-v1", "water-station.glb", "water-station", "Water testing station", "Water", "Water testing station, unit",
     "Shared water testing station on the unit", "DRAFT, OpenPocket #330, regenerated in #365: the station (cup, three probes, standpipe, flush socket, drain) on the unit lid corner, with the tank's water volume." + COMMON,
     (), ("models", "Water"), "The water testing station on the lid."),
]


def main():
    want = sys.argv[1:]
    rj = os.path.join(DOCS, "drawings", "renders.json")
    mj = os.path.join(DOCS, "models", "models.json")
    data = json.load(open(rj))
    models = json.load(open(mj))
    out_dir = os.path.join(DOCS, "drawings", "renders")
    done = []
    for (rid, glb, png, part, cat, group, title, comment, supersedes, model, caption) in reversed(PUBLISH):   # reversed: the first row ends up first on the page (the complete unit must be the first card)
        if want and rid not in want:
            continue
        src = os.path.join(R, glb)
        if not os.path.exists(src):
            print("MISSING", src, "(run cad/build_all.py first)")
            continue
        shutil.copyfile(src, os.path.join(out_dir, rid + ".glb"))
        iso = os.path.join(R, png + "-iso.png")
        if os.path.exists(iso):
            shutil.copyfile(iso, os.path.join(out_dir, rid + "-iso.png"))
        version = int(rid.rsplit("-v", 1)[1])
        entry = {"id": rid, "date": DATE, "part": part, "category": cat, "status": "draft", "version": version, "group": group, "title": title,
                 "comment": comment, "thumb": "renders/%s-line.png" % rid,
                 "viewer": "viewer.html?src=renders/%s.glb&title=%s" % (rid, title.replace(" ", "%20"))}
        rows = [r for r in data["renders"] if r["id"] != rid]
        for r in rows:
            if r["id"] in supersedes:
                r["status"] = "superseded"
        data["renders"] = [entry] + rows
        if model:
            page, section = model
            m = {"id": rid, "title": title, "glb": "drawings/renders/%s.glb" % rid, "caption": caption, "page": page, "section": section,
                 "poster": "drawings/renders/%s-line.png" % rid}
            if page == "home":
                m["camera"] = {"orbit": "35deg 70deg auto"}
            ms = [x for x in models["models"] if x["id"] != rid and x["id"] not in supersedes]
            idx = next((i for i, x in enumerate(models["models"]) if x["id"] in supersedes), None)
            at = idx if idx is not None else len(ms)
            ms.insert(min(at, len(ms)), m)
            models["models"] = ms
        done.append(rid)
    data["updated"] = DATE
    json.dump(data, open(rj, "w"), indent=2, ensure_ascii=False)
    open(rj, "a").write("\n")
    json.dump(models, open(mj, "w"), indent=1, ensure_ascii=False)
    open(mj, "a").write("\n")
    if done:
        subprocess.check_call([sys.executable, os.path.join(HERE, "render_line_thumbs.py"), "views"] + done)
    print("published:", ", ".join(done))


if __name__ == "__main__":
    main()
