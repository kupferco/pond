# cad/check_sim_matches_cad.py: fails if the MuJoCo sim (control-ui) has drifted from the CAD (OpenPocket #447).   python cad/check_sim_matches_cad.py
# The sim does not keep its own copy of the cart: cad/export_sim_model.py writes control-ui/src/generated/cad-sim.ts (every cart / sleeve / wheel / track / unit number, the part
# list with the CAD bounding boxes) and cad-sim-cart.ts (the cart meshes), and the sim imports them. This check
#   1. rebuilds the numbers and the part list from the CAD sources and fails if they differ from the committed file (the CAD changed, the sim was not regenerated);
#   2. fails if the sim's cart or track code stops importing the generated numbers (control-ui/src/cart/omni.ts, cart/track.ts, transplant/layout.ts, cart/cad-cart.ts).
# The sim test (control-ui/test/sim.test.ts) then checks the scenes against the Complete unit: pipe axis on the leg, upright, roll, side of the free hand.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "..", "control-ui", "src")
MUST_IMPORT = {"cart/omni.ts": "generated/cad-sim", "cart/track.ts": "generated/cad-sim", "transplant/layout.ts": "generated/cad-sim", "cart/cad-cart.ts": "generated/cad-sim-cart"}


def main():
    problems = []
    r = subprocess.run([sys.executable, os.path.join(HERE, "export_sim_model.py"), "--check"], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode:
        problems.append("the generated sim files differ from the CAD: run python cad/export_sim_model.py and commit control-ui/src/generated/")
    for f, need in MUST_IMPORT.items():
        if need not in open(os.path.join(UI, f)).read():
            problems.append("control-ui/src/%s no longer imports %s: the sim must take its cart and unit numbers from the CAD export" % (f, need))
    if problems:
        print("\nSIM-MATCHES-CAD CHECK FAILED:")
        for p in problems:
            print(" -", p)
        return 1
    print("sim matches the CAD: generated files current, sim code imports them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
