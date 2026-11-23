# Transfer scene on the omni cart (OpenPocket #283, plan task 265 part 9)

The go or no-go of the roll redesign: can the free hand leave its pipe by rolling the whole cart about the other pipe's centre line, and can the cart then
drive round the bend with the roll held? Code: `control-ui/src/cart/omni-transfer.ts` (model, placement, contacts), `omni-transfer-run.ts` (controller),
`src/scenes/transfer.ts` (scene), `scripts/search-swing.ts` (the search). Tests: the "Transfer on the omni cart" block of `control-ui/test/sim.test.ts`.
Pictures: `cad/renders/transfer-*.png` (four views of nine poses) and `cad/renders/transfer-assembly.glb`.

## The answer (updated, OpenPocket #460): the sim uses the CAD wedge only

The sim always draws the jaw wedge as the CAD does (0 to 110 degrees). The widened 150 degree what-if, its button and the `jaw=wide` URL are gone: the owner
tried the widened wedge and the transfer got stuck, while the CAD wedge works.

1. What the contact check finds at 110 degrees (both trips, same for B and C as the hands are mirrors): the free hand's jaw sector (25 to 95 degrees of its
   ring) and its +60 degree lobe pass through its own pipe for a roll of about 3 to 40 degrees to the plate side (up to about 1 cm deep, `free:pipe`). From 45 to 180
   degrees the plate side is clear at the roll station and held at every 0.25 cm through the whole bend; rolling back flat at the start of the top run is clear.
   The roll used is **90 degrees**. The 3 to 45 degree stretch is the transit (`TRANSIT_ROLL_DEG`): the controller rolls through it and the checks leave it out. It
   is a known open point of the CAD, not hidden: a rigid roll about the other pipe cannot avoid it for any jaw opening (searched in 0.1 steps of the opening).
2. The old 150 degree result (clear in the contact check) could not be reproduced as "stuck" by the contact check, which looks at the free hand, the base and
   the riding sleeve against the track only. The likely cause is outside that check: moving the hinge pin to 150 degrees puts it 30 degrees from the 180 degree
   wheel lobe, so the jaw would swing against its own hand. Unverified.
3. Both trips give the same corridor (test).

## How the roll is done and limited (controller)

- The cart drives to the **roll station** on the leg (47 to 50 cm), releases the free hand's jaw (92 degrees), rolls 90 degrees to the plate side on the roll
  wheel, drives on the static pipe round the bend **with the roll held** (Q7), rolls back flat at the start of the top run (just after the bend, 83.6 cm), and drives
  on to the top of the bar (117.6 cm). The way back is the same in reverse and ends with the free hand clamped again.
- Interlocks: the roll turns only with the static hand clamped and the free jaw fully open, at the roll station or at the roll-back point; a rolled cart drives
  only inside the declared transfer roll, never onto the run; a jaw opens only on the leg with the cart flat; the roll goes the way that clears (plate side first)
  and never beyond 180 degrees (Q8: legs only; the run keeps roll 0 apart from this one declared roll-back).
- **Open point (Q7 against Q8):** held through the bend means the roll must change somewhere else, and the runs must stay flat to pass the track brackets. The
  roll back is at the start of the top run, 5 cm of straight track after the bend where there is no bracket. The owner may prefer another place.
- The roll station is where the rolled sleeve (124 mm long, R61 at the wheel lobe) is clear of the M8 track-joint rods. The rods and rings are in the model
  at four heights of each leg (6, 16, 26 and 36 cm, **ASSUMED**: the real heights are not in the repo); the rolled cart then passes no rod on its way to the bend.
- Roll speed: the scene runs at 60 deg/s so it can be followed; `rollBudget()` gives about 430 deg/s (motor limited), 90 degrees in 0.2 s.

## What is and is not counted as a collision

Counted: the free hand (sleeve, lobes, jaw, wheels, balls), the base (plate, battery, arm base) and the riding sleeve against the track-joint rods, and the free hand
and base against the track pipes. Not counted: the riding sleeve against its own pipe (the known bend finding below) and the sleeves against the 1.5 mm joint rings
(the wheels ride over them; bore R20 against the ring's R17.5).

**Known finding, unchanged by this task:** the rigid 124 mm sleeve does not follow the R150 bend. With the best trim (searched again here for the riding hand C on pipe C's
bend, away from the other hand) it still penetrates its own pipe by **4.01 mm** in the middle of the bend (3.99 mm for hand B in the Cart on track scene). It needs about 4 mm
more bore, a shorter sleeve or a bigger bend radius. The trim rows are `TRIM_ROWS` in `omni-transfer.ts`.

## Other findings of the checks

- Hand and jaw: the jaw joint is a hinge about an axis along the pipe on the tube surface at the wedge's far edge; the jaw carries the ring sector 20 to the far edge, the
  +60 degree lobe and its two ball cups (`omni.ts`). Closed it is identical to the cart on track scene (no contact at roll 0, tests unchanged).
- Wet pipe grip (`sim/pipe_climb.py` `wet_test()`, the new omni contact model): with the drive locked by the worm a 3 kg cart on a wet vertical pipe slides at 20, 40, 60, 80
  and 100 N preload and only just holds at 140 N; dry it holds from 50 N. This confirms plan risk 1 (the wheel rating of about 20 N is far below what the grip needs).
  See `sim/README.md`.

## Re-running

```
cd control-ui
node --experimental-strip-types scripts/search-swing.ts            # the corridors, CAD wedge (about 1.5 min)
JAW_A1=150 node --experimental-strip-types scripts/search-swing.ts # what-if only (not in the scene)
node --experimental-strip-types scripts/search-swing.ts bend       # the best trim through the bend
node --experimental-strip-types scripts/export-transfer.ts /tmp/tr && python3 scripts/render_transfer.py /tmp/tr ../cad/renders   # the pictures
npm test
```
The scene: open `?scene=transfer`.
