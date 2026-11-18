# Plan: Pipe sag and cup drain

- Task: #295
- Title: Pipe sag and cup drain
- Date: 2026-11-17
- Link: https://viber-f7sxvx63aq-nw.a.run.app/?task=295

Status: PLAN ONLY. Numbers and a decision list; no CAD or app change.
Other plans read: `docs/plans/cart-roll-redesign-plan.md` (task 265, on `main`) is the only plan on `main` or on any remote branch. This plan
answers its Q1 and Q6 (pipe sag) and Q10 (drain hole). It **withdraws the "stay within 500 mm of the legs" rule** that plan's Q6 had
assumed (owner already said no), and it **overlaps with `docs/bench-test/pipe_sag.py`** (Pond #275), which has only two end spans (140 and 290 mm).
The table below uses the same load and moduli and adds more spans and the other support cases; where they overlap the numbers agree.
The task 277 roll budget (`9edde94`) does not touch pipe stiffness or the cups.

## 1. Pipe sag

### Inputs
- Cart weight: `cad/cart_dims.py` has no mass; the plan (section 3) says about 3 kg (29 N). Design load **44 N** = 3 kg x 9.81 x 1.5
  (one pipe taking all the weight while the other hand lets go in a transfer, plus shock). It is one point load, at the worst place.
- PVC-U modulus: 3000 MPa new, **1000 MPa after years under load** (creep), **600 MPa** as a hot-day check (pipe in sun at 40 to 50 C, plus creep).
- Pipe (OD x wall, I = second moment of area): 32 x 1.8 (waste grade, I = 19 500 mm4), 32 x 3.0 (pressure grade, 29 000), 25 x 1.5 (7 700), 25 x 2.3 (10 700).
  The real wall is not in the repo (Q3).
- Sag limits ASSUMED (Q2): bottom run (cart carries seedlings, wheels need constant contact on 20 to 40 N spring preload) **1 mm**;
  top run (travel only) **3 mm**.
- Only the pipe end region sags. The run is secured at its centre, so the middle is stiff. L below is the free length of pipe between the
  centre bracket and the next support (or the bend, if nothing is nearer), and the cart is at the worst place, the middle of L.
  The bend is stiffer than a free end but is not a fixed wall: reality sits between "fixed-pinned" and "pinned-pinned".
  Self weight of the pipe is negligible (0.2 kg per 500 mm).

### Sag in mm, 32 x 1.8 mm pipe (the thinnest 32 mm; 32 x 3.0 is about 1/1.5 of these)
Case A: held at both ends (fixed-fixed). Case B: held at the centre bracket, pinned at the other end (fixed-pinned, used by the existing script).
Case C: simple ends (pinned-pinned, pessimistic). Columns: new / after creep / hot and crept.

| L (mm) | A new / creep / hot | B new / creep / hot | C new / creep / hot |
|---|---|---|---|
| 150 | 0.01 / 0.04 / 0.07 | 0.02 / 0.07 / 0.12 | 0.05 / 0.16 / 0.26 |
| 200 | 0.03 / 0.09 / 0.16 | 0.05 / 0.16 / 0.27 | 0.13 / 0.38 / 0.63 |
| 300 | 0.11 / 0.32 / 0.53 | 0.19 / **0.56** / 0.93 | 0.42 / 1.27 / 2.12 |
| 400 | 0.25 / 0.75 / 1.26 | 0.44 / 1.32 / 2.20 | 1.00 / 3.01 / 5.02 |
| 500 | 0.49 / 1.47 / 2.45 | 0.86 / 2.57 / 4.29 | 1.96 / 5.88 / 9.81 |

32 x 3.0 after creep, case B: L 300 = 0.37, 400 = 0.89, 500 = 1.73 mm; case C: 300 = 0.86, 400 = 2.03, 500 = 3.96 mm.

The free end (cantilever, nothing at the bend; cart at the tip), 32 x 1.8 after creep: 100 mm = 0.75, 150 = 2.5, 200 = 6.0, 300 = 20 mm.
So a loose end is the real danger: **the last 150 mm before an unsupported end sags 2.5 mm or more**, and a free end of 300 mm is useless.
(The same table for all four pipes, with all three load cases, is printed by `sag_table.py` in this folder.)

### Answers
- **Bottom run (carries seedlings, limit 1 mm):** 32 x 1.8 is fine after creep while L is **300 mm or less** in case B (0.56 mm, 0.93 mm hot).
  At 400 mm it is 1.3 mm and over the limit. 32 x 3.0 stretches this to about 400 mm after creep (0.89 mm) or about 350 mm on a hot day (1.5 mm at 400 mm).
  Pinned-pinned (case C) allows only about 250 mm for 32 x 1.8.
- **Top run (travel only, limit 3 mm):** 32 x 1.8 passes up to L = 400 mm in case B (1.3 mm crept, 2.2 hot) and is borderline in case C (3.0 mm crept at 400 mm).
  Over 400 mm it needs a support. The top run does not need to be rigid for work, only for the wheels not to lose the pipe.
- **Does a standard 25 mm pipe do?** Not with margin. 25 x 1.5 after creep, case B: L 200 = 0.42, 300 = 1.42 mm, so it needs a support every
  200 to 250 mm. 25 x 2.3: 300 = 1.0 mm, 400 = 2.4 mm. It would work only for L of 250 mm or less on the bottom run and 400 mm or less
  on the top run, and then only if the wall is the 2.3 mm grade. A 25 x 2.3 pipe has about 0.55 of the stiffness of 32 x 1.8 (I 10 700 against 19 500), and 25 x 1.5 about 0.39. It also needs smaller sleeves and wheels (the cart is designed round 32 mm, and the track joints and rod are for 32 mm), so a switch is
  not worth it for sag alone. **Recommendation: stay at 32 mm** (already the answer to the earlier Q1).
- **Where to add supports:** if the owner's span L is more than 300 mm on the bottom run, add one support per end region about **250 to 300 mm
  from the centre bracket and no closer than 100 mm to the start of the bend** (the stiff bend itself acts as a support, so the last span is from
  the extra support to the bend). Keeping a support 100 to 150 mm before the bend also removes the cantilever case. The cart is 125 mm long, so leave at least 150 mm
  of straight pipe free on each side of a support. The track-joint rings (R17.5) must stay clear of the supports.
- **Can the cart pass a support?** A sleeve wraps the pipe (C-gap on the +X side only), so a clamp that goes round the pipe blocks the cart.
  A support that works must grip the pipe through the C-gap side only (a post or a side bracket at the pipe's +X or top, with the cart at roll 0 and a software
  interlock like the joint rod), or hold the pipe from behind the tank wall, or the cart must stop at it. See Q4. The same problem applies to the centre bracket
  and the spine brackets, which the cart plan already mentions.

## 2. Ball cup drain hole

### What decides it
- Each cup holds a 10 to 12 mm ball in a blind pocket. The pocket opens towards the pipe (the ball touches the pipe), the back of the cup is away from the pipe.
  A cup's "down" depends on both its place on the sleeve (three positions 120 degrees apart) and the roll angle.
- **On the vertical legs** the pipe is along gravity, so every cup axis is horizontal at every roll angle, and a cup's "down" in its own frame never changes: it is always
  the same side along the pipe. The hole through the back of the cup (the plan's assumed hole) does **not drain at all there**: it sits level with the middle of the pocket,
  and water stays up to the lowest edge of the opening.
- **On the horizontal runs** the cup turns with the roll: back hole drains only for cups below the pipe (roughly a 120 degree window), and a back hole on top lets rain in.
  Cups at the side have the same problem as on the legs.
- So one back hole is not enough. Leftover water in a pocket: a pocket of 6.5 mm radius holds a crescent of depth R(1 - cos a), where a is the angle between the
  lowest point and the nearest hole.

### Options
| | Option | Water left at the worst angle | Dirt in | Print | Notes |
|---|---|---|---|---|---|
| 1 | One back hole only (the 265 plan) | Pocket full to the rim on the legs and for side cups | low | easy | Fails the brief |
| 2 | Back hole + **4 side holes** (2 mm, 90 degrees apart, round the pocket floor at the level of the lowest part of the seat, going out through the cup wall) | worst hole 45 degrees from down: crescent about 1.9 mm deep | medium: needs a hood from the sleeve | easy (2 mm holes need 0.4 mm nozzle, print them in the wall plane) | Drains at every angle on the legs and the runs |
| 3 | Back hole + **6 side holes** (60 degrees apart) | worst 30 degrees: about 0.9 mm | medium to high | easy | Best drainage, more holes for dirt |
| 4 | **Open-frame cup**: ball held by 3 or 4 prongs and a ring, no floor (the ball can be pushed out only from the pipe side) | none: cannot hold water | highest (no pocket for the lip) | harder (overhangs) | Never holds water, but the dirt lip is weak |
| 5 | Sealed cup (wiper lip on the ball, no hole) | keeps water out, not in | n/a | hard | A wiper drags on the ball and a seal fails when the ball wears: not recommended |

**Recommendation: option 2.** Back hole (2 mm, as already assumed) for the below-the-pipe case and four 2 mm side holes at 90 degrees through the pocket floor wall.
The sleeve must leave all four outlets uncovered (no wall within 3 mm of an outlet) at every roll angle and at the 180 degree roll for the reach test.
Check in CAD by turning the cup in 15 degree steps about both a vertical and a horizontal pipe axis and testing that the lowest point of the pocket is within 45 degrees of a hole.
On the bench use the existing test 5 (`docs/bench-test/README.md`: roll angles 0, 45, 90, 135, 180, water after 30 s), with the cup at 0 degrees on a vertical pipe too.
Pass: less than about 0.5 ml left after 30 s at every angle. If the crescent is too much, go to option 3; if dirt gets in, go to a hooded sleeve outlet before going to option 4.

## 3. What is not covered
- Real span and real pipe wall (Q1, Q3).
- No CAD change was made (as requested). Supports and the cup hole are changes to `cad/hand_sleeve.py`, `cad/cart_wheel_pairs.py` (cup) and the tank or spine brackets.
- Cart weight is the plan's 3 kg, not a measurement. The load is 44 N including 1.5 for shock; if the cart really weighs 4 kg, scale every sag by 1.33.

## Suggested tasks
1. Measure the real spans and pipe: measure span L between centre bracket and bend, the pipe wall thickness, and the cart weight; re-run `sag_table.py` with them.
2. Pipe supports: design and add the end supports (and the cart-pass method of Q4) to the track CAD, once the span is known (after 1).
3. Cup drain holes in the cup CAD: back hole + 4 side holes, check at every roll angle, update the sleeve so the outlets stay open (part of the cup task in the roll plan).
4. Drain bench test: print the cup with the holes and run test 5 of the bench test (after 3).

## Open questions
### Q1. What is the real span L between the centre bracket and the corner (or nearest support) on the bottom run, and on the top run?
Context: it is not in the repo, and sag grows with L cubed (300 mm is 0.56 mm after creep for 32 x 1.8, 500 mm is 2.6 mm).
Assumed: 300 mm on the bottom run, 400 mm on the top run, with the bend acting as a pinned end.
Answer: _open_

### Q2. Are 1 mm of sag on the bottom run and 3 mm on the top run the right limits?
Context: these set which L is fine (Q1); the limit is how far the wheels' spring carriers can follow the pipe.
Assumed: 1 mm bottom run, 3 mm top run.
Answer: 1 mm bottom run, 3 mm top run.

### Q3. What is the wall thickness of the 32 mm pipe you will use (1.8 waste grade, 3.0 pressure grade, other)?
Context: the 3.0 mm wall is about 1.5 times stiffer, and the UK and Brazil pipes differ. It decides whether 300 or about 400 mm is the longest bottom-run span.
Assumed: 1.8 mm (the weaker case), re-run when measured.
Answer: _open_

### Q4. May a support only touch the pipe through the sleeve's C-gap side (or hold it from behind), so the cart can pass it, or may the cart stop at a support?
Context: the sleeve wraps the pipe, so a clamp round the pipe blocks the cart; the cart must work the whole bottom run.
Assumed: supports pass through the C-gap side only, and the cart rolls to home (roll 0) to pass them, with a software interlock like the track-joint rod.
Answer: Add supports using the same rod system as the existing track-joint rod (supports come in through the sleeve's C-gap side; the cart rolls to home to pass them, with the same software interlock). Bottom run: one support on each side, left and right, just before the curve starts (not on the bend), fixed via small brackets on top of the tank, so the bottom run is held at three points (these plus the centre bracket). Top run: also add support, a brace from the centre collar (where the braces meet) to the middle of each top span. Calculate the remaining sag on the top with the bottom locked, and size the supports so both runs stay under the limits.

### Q5. Stay at 32 mm, not move to a standard 25 mm pipe?
Context: 25 x 2.3 only just passes with supports every 250 mm (bottom) and needs smaller sleeves, wheels and joints.
Assumed: yes, stay at 32 mm.
Answer: _open_

### Q6. Which drain option: 2 (back hole + 4 side holes), 3 (6 side holes), or 4 (open-frame cup)?
Context: the back hole alone does not drain on the vertical legs at any roll angle, so side holes (or no pocket) are needed.
Assumed: option 2, back hole + four 2 mm side holes at 90 degrees, outlets kept open by the sleeve at every roll angle.
Answer: _open_

### Q7. Is a small leftover crescent of water (about 2 mm deep, under 0.5 ml) acceptable in a cup, or must a cup empty fully?
Context: full emptying needs more holes (option 3) or no pocket (option 4), which let more dirt in.
Assumed: a small crescent is fine, it dries out.
Answer: _open_
