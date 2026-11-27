# Spine to track connector (OpenPocket #561)

Script: `cad/spine_connector.py` (pictures: `cad/render_spine_connector.py`), drawings "Spine to track connector" on the Drawings page. Redrawn on 27 Nov 2026 to match the approved sketch; the first version (clamp ring, arm, pods, red part) was rejected and is gone.

**What the main drawing shows, and nothing else**
1. The real flush track joint of `cad/track_joint.py`, coloured as that script colours it: an M8 rod through the 32 mm track pipe to the central pipe axis (`ROD_OUT` 50 mm = `track_rod_out_mm`); a captive nut on a curved plate INSIDE the track pipe, a lock nut OUTSIDE, so nothing stands proud and the cart sleeve passes.
2. The track pipe lies horizontal; the rod is horizontal too; the spine is the vertical tube the rod ends in (33.7 mm OD, 2 mm wall).
3. **PROPOSAL (the owner's idea, not from existing drawings):** one M8 nut on each side of the spine tube wall (outside and inside), so the rod cannot spin. The inside nut sits 1.6 mm off the wall so its corners clear the curve of the tube.

No collars, no pods, no clamp ring, no arm, no growing pipe.

**Where along the spine.** One joint on each run of the track at x = 0: bottom run 514 mm over the tank floor, top run 1884 mm (shown as plain ring markers in "where on the spine"; no pods drawn).

**Open questions for the owner (not drawn)**
1. Does the joint need anything between the rod and the spine other than the two nuts (a washer, a sleeve through the wall)? Not drawn.
2. The rod passes through the growing pipe (75 mm) between the track and the spine; how does it get through (a hole in its wall)? Not drawn; the complete unit is not changed here (task 537).
3. The top run is at the very end of the spine (both end at 1884): a nut inside the spine there is at the tube end. Lower the top run or lengthen the spine?
4. Is a connector at x = 0 on both runs what you want, or only one?
5. One M8 rod per connector holds the track; is that enough against the cart's weight in the middle of each run?
