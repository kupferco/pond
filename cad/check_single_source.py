# cad/check_single_source.py: fails if two scripts define the same part (OpenPocket #365).   python cad/check_single_source.py
# Rules (see docs/cad-structure.md):
#  1. A function defined in cad/parts/ (a part, or a part helper) must not be defined again in any other cad/*.py. (box, cyl, tube, tdir are the
#     generic one-line helpers every script has with its own signature; they are the only exception.)
#  2. The names of the unit's parts (tank, water_volume, track_loop, growing_pipe, ...) may be given to an assembly child only in cad/parts/unit.py,
#     or in a script that imports them from `parts` (it takes the shape from there). A script that builds its own "tank" or "track_loop" fails.
#  3. Two scripts must not define the same top-level function name, except the generic orchestration names below, the frozen KNOWN_DUPLICATES (older
#     design studies, listed so they stay visible: shrink the list, never grow it), and the STUDIES files, which are superseded design history that the
#     build does not run (cad/build_all.py).
#  4. (#447) The cart's part names (base_plate, battery, so101_arm_envelope, track_pipe_*, hand_on_pipe_*) may be given to an assembly child only in the cart's own
#     files (cart_*.py, cad/parts/cart.py); every other assembly adds the cart with add_cart(). And add_cart(..., drop_hand=True), which leaves a sleeve out, is allowed
#     only in the listed scripts (CART_HAND_DROPPED): everywhere else the cart has BOTH sleeves (a dropped sleeve made "Complete unit v2" show one).
#  6. (#447) The cart source carries no track pipe, and no assembly adds a child called track_pipe*; the seedling tray and storage stand on the shelf (cad/parts/shelf.py), under the lid.
#  5. (#447) The cart source itself still has both sleeves (hand_on_pipe_B_sleeve and hand_on_pipe_C_sleeve), when cadquery is available.
import ast
import collections
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GENERIC_HELPERS = {"box", "cyl", "tube", "tdir", "_box", "_cyl"}
ORCHESTRATION = {"add", "scene", "check", "checks", "main", "draw", "views", "build", "compound", "rot", "parts", "basis", "overlay", "parts_of",
                 "to_cart", "xshift", "reach", "station", "rail", "pin", "oring", "rod", "bore", "many"}
# superseded design studies: kept for the drawings they made, not built by build_all.py, not checked as sources (their copies are the reason this list exists)
STUDIES = {"unit_v1_assembly.py", "pod_store_reach.py", "pod_store.py", "flatpack_tank.py", "flatpack_check.py", "charging_dock.py", "bottom_bracket.py",
           "base_module.py", "cart_wheel_pairs_v4.py", "hand_sleeve_v4.py", "so101_servo_layout.py", "aframe_pipe_joint.py", "spine_joint.py", "track_joint.py",
           "cleanout_section.py", "cleanout_section_door.py", "pick_hole_cap.py", "pick_hole_membrane.py", "home_station.py",
           "spine_connector_v3.py"}   # (#588) draft V3 copied exactly from claude/drafts (#581): not run by build_all, builds its own pipes, left unedited by the owner's request
CART_NAMES = {"base_plate", "battery", "so101_arm_envelope"}
TRACK_NAMES = {"track_pipe_B", "track_pipe_C", "track_pipe"}   # (#447) the cart carries no track pipe: nothing may add a child with these names to the cart
CART_PREFIXES = ("hand_on_pipe_",)
CART_FILES = {"cart_assembly.py", "cart_arm.py", "cart_base.py", "cart_sleeves.py", "cart_omni.py", "cart_geom.py", "cart_dims.py", "cart_pod_holder.py",
              "cart_wheel_pairs.py", "export_cart_v2_views.py", "render_omni_sleeve.py", "render_cart_wheel_pairs.py", "render_base_gallery.py", "render_motor_layouts.py",
              "export_drawing_models.py", "check_transfer_hands.py", "render_transfer_hands.py", "water_sampler.py", "export_sim_model.py"}
HAND_GAUGE_FILES = {"render_omni_sleeve.py", "render_motor_layouts.py", "export_drawing_models.py", "cart_sleeves.py", "cart_wheel_pairs.py"}   # single-hand pictures: a pipe gauge round one hand, not the cart
CART_HAND_DROPPED = {"water_assembly.py"}     # pictures and the #364 tank-clearance check of the cart at the station: top sleeve only (see water_assembly.py)
KNOWN_DUPLICATES = {"build_plate": {"cart_geom.py", "cart_base.py"},        # cart_base.py adds the battery/arm cut-outs to cart_geom's plate (same name, extended)
                    "bent_pipe": {"cart_wheel_pairs.py"}, "corner_model": {"cart_wheel_pairs.py"}, "two_hand_model": {"cart_wheel_pairs.py"}, "idler_travel": {"cart_wheel_pairs.py"},
                    "arc_seg": {"track_supports.py", "track_joint.py"}, "inter": set(), "latest": set()}


def top_defs(path):
    tree = ast.parse(open(path).read())
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}, tree


def imports_parts(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "parts":
            return True
        if isinstance(n, ast.Import) and any(a.name.split(".")[0] == "parts" for a in n.names):
            return True
    return False


def child_names(tree):
    """String names given to assembly children: add(x, "name", ...), assy.add(x, name="name"), p["name"] = (shape, colour)."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            fn = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if fn == "add":
                for k in n.keywords:
                    if k.arg == "name" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
                        out.add(k.value.value)
                if len(n.args) >= 2 and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str):
                    out.add(n.args[1].value)
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript):
            s = n.targets[0].slice
            if isinstance(s, ast.Constant) and isinstance(s.value, str):
                out.add(s.value)
    return out


def main():
    problems, notes = [], []
    part_files = sorted(glob.glob(os.path.join(HERE, "parts", "*.py")))
    part_defs = {}
    for f in part_files:
        defs, tree = top_defs(f)
        for d in defs:
            if not d.startswith("_") and os.path.basename(f) != "common.py" or d in ("hose", "vol", "inter"):
                part_defs.setdefault(d, []).append(os.path.basename(f))
    for d, fs in part_defs.items():
        if len(fs) > 1 and d not in GENERIC_HELPERS and d not in ORCHESTRATION:
            problems.append("part function %s defined in two files of cad/parts/: %s" % (d, ", ".join(fs)))
    # the unit's part names, from cad/parts/unit.py itself
    unit_names = child_names(ast.parse(open(os.path.join(HERE, "parts", "unit.py")).read())) | {"tank", "lid", "water_volume", "track_loop", "growing_pipe", "sampler_pu_coil", "sampler_pu_tail", "sampler_silicone_link"}
    scripts = [f for f in sorted(glob.glob(os.path.join(HERE, "*.py"))) if os.path.basename(f) not in STUDIES and os.path.basename(f) != os.path.basename(__file__)]
    defs_by_name = collections.defaultdict(set)
    for f in scripts:
        b = os.path.basename(f)
        defs, tree = top_defs(f)
        for d in defs:
            defs_by_name[d].add(b)
            if d in part_defs and d not in GENERIC_HELPERS:
                problems.append("%s defines %s again; it belongs to cad/parts/%s" % (b, d, part_defs[d][0]))
        if not imports_parts(tree):
            for nm in sorted(child_names(tree) & unit_names):
                problems.append("%s builds a part named %r itself; take it from cad/parts/ (import it) instead" % (b, nm))
    for f in scripts:
        b = os.path.basename(f)
        tree = ast.parse(open(f).read())
        if b not in CART_FILES:
            for nm in sorted(child_names(tree)):
                if nm in CART_NAMES or nm.startswith(CART_PREFIXES):
                    problems.append("%s gives a child the cart part name %r; add the cart with parts.cart.add_cart() instead" % (b, nm))
        if b not in HAND_GAUGE_FILES:
            for nm in sorted(child_names(tree) & TRACK_NAMES):
                problems.append("%s adds a child named %r: the cart carries no track pipe (#447), the track comes only from cad/parts/track.py" % (b, nm))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) in ("add_cart", "cart_children"):
                for k in n.keywords:
                    if k.arg == "drop_hand" and not (isinstance(k.value, ast.Constant) and k.value.value is False) and b not in CART_HAND_DROPPED:
                        problems.append("%s leaves a cart sleeve out (drop_hand); the cart has both sleeves" % b)
    try:
        sys.path.insert(0, HERE)
        import cart_assembly as ca
        have = {c.name for c in ca.result.children}
        for need in ("hand_on_pipe_B_sleeve", "hand_on_pipe_C_sleeve"):
            if need not in have:
                problems.append("the cart source is missing %s" % need)
        for c in sorted(have):
            if c.startswith("track_pipe"):
                problems.append("the cart source carries its own track pipe %r; remove it (#447): the track comes only from cad/parts/track.py" % c)
        # (#447) the seedling tray and the storage stand ON the shelf and under the lid; the shelf is above the water and under the lid
        from parts import unit_dims as ud
        from parts.shelf import shelf
        from parts.shelf_items import seedling_tray, seedling_storage
        sb = shelf().val().BoundingBox()
        if abs(sb.zmin - ud.SHELF_Z) > 1e-6 or sb.zmin < ud.WATER_LEVEL or sb.zmax > ud.TH:
            problems.append("the shelf (z %.1f..%.1f) must be above the water (%.1f) and under the lid (%.1f)" % (sb.zmin, sb.zmax, ud.WATER_LEVEL, ud.TH))
        for nm, fn in (("seedling_tray", seedling_tray), ("seedling_storage", seedling_storage)):
            b = fn().val().BoundingBox()
            if abs(b.zmin - sb.zmax) > 1e-6 or b.zmax > ud.TH:
                problems.append("%s (z %.1f..%.1f) must stand on the shelf top (%.1f) and stay under the lid (%.1f)" % (nm, b.zmin, b.zmax, sb.zmax, ud.TH))
    except ImportError as e:
        notes.append("cart sleeve check skipped (%s)" % e)
    for d, fs in sorted(defs_by_name.items()):
        if len(fs) > 1 and d not in GENERIC_HELPERS and d not in ORCHESTRATION and not d.startswith("render") and d != "vol":
            if fs - KNOWN_DUPLICATES.get(d, set()):
                problems.append("%s is defined in more than one script: %s" % (d, ", ".join(sorted(fs))))
            else:
                notes.append("known: %s in %s" % (d, ", ".join(sorted(fs))))
    for n in notes:
        print(n)
    if problems:
        print("\nSINGLE-SOURCE CHECK FAILED:")
        for p in problems:
            print(" -", p)
        return 1
    print("single-source check OK: %d part files in cad/parts/, %d scripts checked, %d study scripts skipped" % (len(part_files), len(scripts), len(STUDIES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
