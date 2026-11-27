# cad/build_all.py: ONE command that regenerates every check, render, GLB and drawing from the single-source parts (OpenPocket #365).
#   python cad/build_all.py            everything (about 20 minutes: the renderer is software)
#   python cad/build_all.py quick      only the single-source check and the clash checks (about 3 minutes)
# Order matters in one place: render_water_station.py writes assembly.glb (the full cart + sampler + station + unit); nothing else writes it.
# Needs: cadquery, numpy, matplotlib, pillow, scipy, trimesh.   See docs/cad-structure.md.
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS_CHECK = [
    ("single-source check (fails if two scripts define the same part)", ["check_single_source.py"]),
    ("sim matches the CAD (control-ui/src/generated vs the cart, track and unit sources; fails on drift)", ["check_sim_matches_cad.py"]),
    ("water assembly clash check (cart, sampler, station, unit supports)", ["water_assembly.py"]),
    ("spine-to-track connector: fit checks and the pod places in its way (#561)", ["spine_connector.py"]),
    ("complete unit: cart and sample coil vs every unit part (writes complete-unit.glb)", ["complete_unit.py"]),
]
STEPS_BUILD = [
    ("regenerate the MuJoCo sim's cart meshes and numbers from the CAD (control-ui/src/generated)", ["export_sim_model.py"]),
    ("cart family renders + GLBs (cart assembly, arm, base, pod holder, sleeves, wheel pairs, home station)", ["render_omni_sleeve.py"]),
    ("track supports renders + GLBs", ["render_track_supports.py"]),
    ("spine-to-track connector renders + GLBs (#561)", ["render_spine_connector.py"]),
    ("unit renders + GLBs (complete unit, unit with water, tank with water, sample coil)", ["render_unit.py"]),
    ("water station + water assembly renders + assembly.glb", ["render_water_station.py"]),
    ("publish to the Drawings page and the 3D Models page", ["publish_drawings.py"]),
]


def run_step(label, args):
    t = time.time()
    print("== %s" % label, flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:], cwd=os.path.join(HERE, ".."))
    if r.returncode:
        print("FAILED: %s (exit %d)" % (label, r.returncode))
        sys.exit(r.returncode)
    print("   done in %.0fs" % (time.time() - t), flush=True)


if __name__ == "__main__":
    for step in STEPS_CHECK + ([] if "quick" in sys.argv[1:] else STEPS_BUILD):
        run_step(*step)
    print("build_all OK")
