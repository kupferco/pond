# Spine to track connector (OpenPocket #561)

The bracket that joins the central spine to the track. Script: `cad/spine_connector.py` (pictures: `cad/render_spine_connector.py`), drawings "Spine to track connector" on the Drawings page.

**What it is.** A split clamp ring on the 33.7 mm spine, a 16 x 30 mm arm through a window in the 75 mm growing pipe, and the same M8 rod system as the track joint and the track supports (nut plate inside the 32 mm track pipe, rod out of the spine-side hole, lock nut, then the arm).

**Where along the spine.** One connector on each run of the track at x = 0: bottom run at 514 mm over the tank floor (shared layout), top run at 1884 mm. These are the places of the two stand-in blocks (`spine_brackets`) the unit drew before.

**Rule: no pod place may occupy a connector position.** `python cad/spine_connector.py` lists every pod place that touches a connector. Today: one, the front pod of the level at 500 mm (it also runs into the track pipe). The top connector has none. The pods are NOT changed in this task; leave that pod out in task 537 together with putting the connectors in the complete unit.

**Numbers used (none invented).** Spine, growing pipe and track pipe sizes, track height and `track_rod_out_mm` (50, from `track_joint.py`; the brief said the key existed in `layout.json`, it did not, so it was added with that value): the rod needs 14.5 mm out of the track pipe, the check fails above 50. Arm size 16 x 30 = the stand-in blocks. Nut plate, lock nut, rod and hole sizes come from `track_supports.py`.

**ASSUMED, open questions for the owner**
1. Ring wall 6 mm and ring height 30 mm on the spine.
2. How the ring is tightened: a split ring with a 2 mm gap, the clamp screw is not drawn (which screw, which side?).
3. The window in the growing pipe (arm + 2 mm each side) is a new cut in the pipe; the pipe is not changed in this task.
4. The top connector sits on the very end of the spine and the growing pipe (both end at 1884, the track axis is 1884): half the ring hangs past the spine end. Lower the top run, lengthen the spine by 15 mm, or move the connector down?
5. One M8 rod per connector holds the track; is that enough against the cart's weight at the middle of each run (the supports already use one rod each)?
6. Is a connector at x = 0 on both runs what you want, or only one?
