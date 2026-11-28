# cad/complete_unit_v3.py: COMPLETE UNIT V3 (OpenPocket #574). Builds docs/drawings/renders/complete-unit-v3.glb. Nothing is drawn here: every part is imported.
#   = complete unit V2 (cad/complete_unit.py scene), fully ASSEMBLED (nothing exploded), with these changes:
#   1. the pod-shaped stand-in blocks ("spine_brackets") and the old simplified pods (round cylinders with black caps, cad/parts/pods.py) are removed;
#   2. pods WITH THEIR COLLAR: the three-seat pipe collar, draft V2 (#563), is placed on the growing pipe exactly as cad/pipe_collar_3seat.scene("pods") builds
#      it (same parts, same colours, same pods: pipe_collar.pod(), colour pipe_collar.C_POD), one collar per level, three pods per collar (seats 0/120/240);
#   3. the real spine-to-track connector (cad/spine_connector.py: joint tube, plugs, nut plate, M8 rod, lock nut, the two spine nuts) at both track runs;
#      the connector SETS THE TRACK DISTANCE: track axis to spine axis = spine_connector.AXIS = 66 mm (the unit's own 60 mm is replaced), so the track
#      (and the cart on it) sits at y = -66 and the rod ends exactly in the spine.
#   The growing pipe is drilled where the three seats and the connector rods go through it (same 45 mm holes as the collar drawing's pipe).
#   Open (docs/pipe-collar-3seat.md): how many collars per unit and at what pitch is not in the repo. Here: one collar at every second hole level of the
#   old pod layout (the collar is 108 mm high, the old pitch 100 mm), none within reach of the two clamp collars or the connector heights. ASSUMED.
#   python cad/complete_unit_v3.py            -> docs/drawings/renders/complete-unit-v3.glb
#   python cad/complete_unit_v3.py --compare  -> also the PNG comparison sheets in cad/renders/complete-unit-v3-*.png (unit | pipe-collar-3seat-assembled-v2 / pods-v2)
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import complete_unit as cu
import pipe_collar as pc
import pipe_collar_3seat as p3
import spine_connector as sc
from parts.pods import hole_levels
from parts.unit_dims import LOOP_Y, ZC1, ZC2, RP

OUT = os.path.join(HERE, "..", "docs", "drawings", "renders", "complete-unit-v3.glb")
CONNECTOR_PARTS = ("joint_tube", "plug_a", "plug_b", "nut_plate", "m8_rod", "lock_nut")   # the unit's own track_loop and spine_tube replace pipe_a/pipe_b/spine_tube
REPLACED = ("spine_brackets", "pods", "pod_caps", "growing_pipe", "spine_tube", "track_loop")
TRACK_Y = -sc.AXIS                       # the connector puts the track 66 mm from the spine axis (spine at y = 0); the unit's LOOP_Y was -60
DY = TRACK_Y - LOOP_Y                    # -6: how far the track and everything clamped on it move
COLLAR_LO, COLLAR_HI = -pc.ZH, pc.H - pc.ZH     # collar extent relative to its seat height z
CLEAR = 2.0


def collar_levels():
    """Seat heights: every hole level of the old layout that keeps a whole collar clear of the previous collar, the two clamp collars (50 mm) and both connectors."""
    blocked = [(zc - 25, zc + 25) for zc in (ZC1, ZC2)] + [(z - 20, z + 20) for z in sc.ZONES.values()]
    out = []
    for z in hole_levels():
        lo, hi = z + COLLAR_LO - CLEAR, z + COLLAR_HI + CLEAR
        if any(lo < b1 and hi > b0 for b0, b1 in blocked):
            continue
        blocked.append((lo, hi))
        out.append(z)
    return out


def collars():
    """The collar drawing's own scene (three pieces, magnets, gaskets, O-rings, three pods; no pipe, no spine, no parked plug), one copy per level, turned 60 degrees on alternate levels."""
    src = [c for c in p3.scene(content="pods", with_pipe=False, with_spine=False).children if c.name != "plug_parked_seat_1"]
    return src


def scene():
    old = cu.scene()
    a = cq.Assembly()
    levels = collar_levels()
    parts = {c.name: c for c in old.children}
    for ch in old.children:
        if ch.name in REPLACED:
            continue
        if ch.name.startswith("cart_") or ch.name.startswith("sampler_"):
            a.add(ch.obj.translate((0, DY, 0)), name=ch.name, loc=ch.loc, color=ch.color)       # the cart rides on the track: it moves with it
        else:
            a.add(ch.obj, name=ch.name, loc=ch.loc, color=ch.color)
    # growing pipe: holes for the seats and the connector rods; spine: rod holes
    pipe = parts["growing_pipe"].obj
    spine = parts["spine_tube"].obj
    for i, z in enumerate(levels):
        for k in range(3):
            pipe = pipe.cut(p3.rotz(pc.cylx(pc.DRILL_D / 2, 0, RP + 5, 0, z), p3.SEATS[k] + 60.0 * (i % 2)))
    for zc in sc.ZONES.values():
        rod = cq.Workplane("XZ").circle(sc.HOLE_D / 2).extrude(-(RP + 5)).translate((0, 0, zc))     # XZ normal is -Y: negative extrude reaches to -Y
        pipe = pipe.cut(rod)
        spine = spine.cut(rod)
    a.add(pipe, name="growing_pipe", loc=parts["growing_pipe"].loc, color=parts["growing_pipe"].color)
    a.add(spine, name="spine_tube", loc=parts["spine_tube"].loc, color=parts["spine_tube"].color)
    a.add(parts["track_loop"].obj.translate((0, DY, 0)), name="track_loop", loc=parts["track_loop"].loc, color=parts["track_loop"].color)
    # collars with pods, from the collar drawing
    src = collars()
    for i, z in enumerate(levels):
        for ch in src:
            o = p3.rotz(ch.obj, 60.0 * (i % 2)).translate((0, 0, z - pc.ZH))
            a.add(o, name="collar_%d_%s" % (i + 1, ch.name), color=ch.color)
    # the connector, at the track
    src = {c.name: c for c in sc.joint_assembly().children}
    cols = dict(sc.JOINT_PARTS)
    cols["PROPOSAL_spine_nut_outside"] = cols["PROPOSAL_spine_nut_inside"] = (0.2, 0.7, 0.3)
    _, outside, inside, _ = sc.spine_parts()
    for zone, zc in sc.ZONES.items():
        move = lambda s: s.translate((0, TRACK_Y, zc))
        for n in CONNECTOR_PARTS:
            a.add(move(src[n].obj), name="spine_connector_%s_%s" % (zone, n), color=cq.Color(*cols[n], 1))
        for n, s in (("PROPOSAL_spine_nut_outside", outside), ("PROPOSAL_spine_nut_inside", inside)):
            a.add(move(sc.to_horizontal(s)), name="spine_connector_%s_%s" % (zone, n), color=cq.Color(*cols[n], 1))
    return a


REF = os.path.join(HERE, "..", "docs", "drawings", "renders")
PNG = os.path.join(HERE, "renders")


def _crop(glb, box, el, az, path, title):
    """Draw only the triangles whose centre lies in box = (x0, x1, y0, y1, z0, z1), Z up (the GLB is Y up: see render_glb_views)."""
    import render_glb_views as g
    import render_local as rl
    parts = []
    for t, c in g.collect_glb(glb):
        lo, hi = t.min(axis=1), t.max(axis=1)      # keep a triangle only if it lies wholly inside the box (long pipe triangles would else stretch the view)
        k = (lo[:, 0] > box[0]) & (hi[:, 0] < box[1]) & (lo[:, 1] > box[2]) & (hi[:, 1] < box[3]) & (lo[:, 2] > box[4]) & (hi[:, 2] < box[5])
        if k.any():
            parts.append((t[k], c))
    rl.draw(parts, el, az, path, title)


def compare():
    """Side-by-side sheets: this unit | the pipe collar draft V2 (assembled / with pods) and the connector part. Written to cad/renders/complete-unit-v3-*.png."""
    from PIL import Image, ImageDraw
    import render_glb_views as g
    import tempfile
    os.makedirs(PNG, exist_ok=True)
    tmp = tempfile.mkdtemp()
    unit = OUT
    asm = os.path.join(REF, "pipe-collar-3seat-assembled-v2.glb")
    pods = os.path.join(REF, "pipe-collar-3seat-pods-v2.glb")
    conn = os.path.join(REF, "spine-connector-positions-v2.glb")
    z1 = collar_levels()[1]
    zb = sc.ZONES["bottom"]
    big = (-1e5, 1e5, -1e5, 1e5, -1e5, 1e5)
    jobs = {   # sheet: [(glb, crop box, elevation, azimuth, label)]
        "iso": [(unit, big, 28, -50, "complete-unit-v3 (full unit)"), (asm, big, 25, -50, "pipe-collar-3seat-assembled-v2")],
        "pod-closeup": [(unit, (-90, 90, -90, 90, z1 - 75, z1 + 50), 25, -50, "complete-unit-v3: pods in their collar"),
                        (pods, (-120, 120, -120, 120, -20, 130), 25, -50, "pipe-collar-3seat-pods-v2 (pods)"),
                        (asm, (-120, 120, -120, 120, -20, 130), 25, -50, "pipe-collar-3seat-assembled-v2 (empty)")],
        "connector-closeup": [(unit, (-300, 300, TRACK_Y - 30, 45, zb - 70, zb + 70), 28, -50, "complete-unit-v3: spine-to-track connector"),
                              (conn, big, 28, -50, "spine-connector-positions-v2")],
        "front": [(unit, big, 0, -90, "complete-unit-v3 (front)"), (asm, big, 0, -90, "pipe-collar-3seat-assembled-v2 (front)")],
        "top": [(unit, (-400, 400, -400, 100, 330, 470), 90, -90, "complete-unit-v3 (top, one collar level)"), (asm, big, 90, -90, "pipe-collar-3seat-assembled-v2 (top)")],
    }
    for sheet, items in jobs.items():
        ims = []
        for n, (glb, box, el, az, label) in enumerate(items):
            f = os.path.join(tmp, "%s%d.png" % (sheet, n))
            _crop(glb, box, el, az, f, label)
            ims.append(Image.open(f).convert("RGB"))
        h = max(i.height for i in ims)
        out = Image.new("RGB", (sum(i.width for i in ims), h), "white")
        x = 0
        for i in ims:
            out.paste(i, (x, 0)); x += i.width
        out.save(os.path.join(PNG, "complete-unit-v3-compare-%s.png" % sheet))
        print("wrote complete-unit-v3-compare-%s.png" % sheet)


if __name__ == "__main__":
    if "--compare" in sys.argv:
        compare()
    else:
        scene().export(OUT, tolerance=0.5, angularTolerance=0.3)
        print("wrote", os.path.relpath(OUT))
