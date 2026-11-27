# Track supports (OpenPocket #315, part 1 of plan #295)

CAD: `cad/track_supports.py` (the unit of `unit_v3_aframe.py` plus the supports). Pictures and 3D model: `cad/renders/track-supports-*.png`
(whole unit, bottom close-up, top close-up; iso, front, top, side) and `cad/renders/track-supports-assembly.glb`.
Render with `python cad/render_track_supports.py`. Sag: `python docs/bench-test/track_support_sag.py` (output kept in `track_support_sag.txt`).

## What was added
- **Same rod system as the track joint** (`track_joint.py`): M8 rod, nut plate inside the pipe, hole on the +Y side (the sleeve's C-gap side, towards the spine),
  lock nut outside. The cart rolls to home (roll 0) to pass a support, same interlock as the joint rods (`control-ui/src/cart/roll.ts`: the runs are held at roll 0 already).
- **Bottom run**: one support each side at x = +-125 mm, 15 mm before the bend starts (the straight part ends at 140). A 20 x 16 post on a 44 x 36 x 4 base plate on the tank lid, **50 mm of free rod** from the pipe surface (the rod of the flush track joint, `ROD_OUT` in `cad/track_joint.py`; it was a 34 mm stub here, which disagreed with the joint, OpenPocket #537). The track pipe axis is therefore **66 mm** from the central pipe axis (16 tube radius + 50 rod), stated on the two close-up drawings.
  With the centre bracket the run is held at three points.
- **Top run**: an M8 diagonal brace from a lug on the centre collar (where the top triangle legs meet) to a block under the top pipe at x = +-125 (middle of the CAD half span), on the same rod stub.

## Sag, 32 x 1.8 mm, 44 N, worst load place (mm: new / after creep / hot and crept)
| Run | Before | With the supports | Limit |
|---|---|---|---|
| Bottom, L 300, bend pinned | 0.20 / 0.60 / 1.00 | 0.08 / 0.19 / 0.30 | 1 mm |
| Top, L 400, bend on the leg's spring, bottom locked | 0.50 / 1.49 / 2.48 | 0.13 / 0.36 / 0.60 | 3 mm |

Both runs stay under their limits, also on a hot day. The supports are springs in the model (M8 stub bending, brace stretch), not rigid points.
"Bottom locked": the top bend stands on the leg, which shortens under load (0.38 mm at 44 N if the whole load went down the leg), so the end is a spring, not rigid; it is counted.

## Not settled
- The owner's spans (300 and 400 mm) are longer than the CAD loop (140 mm straight, 290 mm centre to leg). The sag uses the owner's spans (the harder case); the CAD
  half span gives 0.34 mm on top with the brace. The supports are put at the CAD positions. If the real loop is longer, move them with `SUP_X`.
- The bend between the bottom support and the leg is treated as a straight beam (pessimistic).
- The cart's own clearance to the posts, the post on the lid and the brace is not simulated: check with the cart on the model.
- Wall measured later (Q3): re-run the sag script with the real wall.
