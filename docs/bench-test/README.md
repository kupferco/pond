# Bench test: omni wheels and ball cups (Pond #275, part 1 of 12 of the cart roll redesign)

Status: protocol and data sheets ready. **No measurement has been taken**: this needs real parts on a real
pipe, and nothing was bought or run. Fill in `results.csv` while testing.

## What to buy (UK now; must also be easy in Brazil, Q9)
- 2 rubber-roller omni wheels, a common size (48 or 58 mm; the plan's 38 mm is also fine to start). Any
  seller on Mercado Livre / AliExpress carries these sizes. Order a few extra if cheap.
- 1 worm-gear motor (the same family as today's drive/hinge worm drives) for the tilt-hold test.
- A 32 mm PVC pipe, about 1 m (the same pipe as the track), plus an optional offcut of rubber sheet.
- 10 to 12 mm balls: stainless steel (304/316, not chrome steel) and Delrin (acetal), 4 of each.
- Printed ball cups, PETG or nylon, drain hole 2 mm: ask for a CadQuery model in the CAD task if wanted; for the
  bench test a simple cup (concave face R16, ball 1 to 1.5 mm proud, lip not touching the ball) is enough.
- Tools: spring (luggage) scale to 100 N or kitchen scale, a 3 kg weight, a 150 mm lever arm, a tilt jig, a jug of water,
  fine grit/soil for the "dirt" runs.

## Tests (each: dry, wet, 20 / 40 N preload; 60 N only to see where it fails, it is above the wheel rating)
1. **Hold along the pipe** (cart on a vertical pipe, power off): hang weights until it slides. Target: 3 kg.
2. **Hold round the pipe**: 150 mm lever with weight until the roll wheel slips. Target: 2 kg (about 3 N m).
3. **Worm hold on a tilt** (Q5): worm motor off, pipe tilted 0, 30, 60, 90 degrees from vertical, load 2 kg on the 150 mm
   lever. Record the angle where it creeps. If it fails: try rubber on the pipe, then a rubber-tyred roll wheel; only
   then the latching brake (task 13).
4. **Ball cups, stainless vs Delrin**: pull force to roll the cup along and round the pipe, at 20 N preload, dry, wet,
   dirty. Note sticking after 24 h wet (stainless/Delrin on the printed seat), any rust after 1 week outdoors, and
   whether the ball stands free of the lip.
5. **Water in the cup (drain hole)**: fill the cup, turn it to roll angles 0, 45, 90, 135, 180 degrees, note the
   water left after 30 s. Q10 (where the hole goes) is still open; this test gives the data for it.
6. **Preload check**: with the scale, record the real force per contact (omni rollers have gaps).

Decisions the data feeds: Q4 (preload: design 20 N, test to 40 N), Q5 (hold, rubber rollers), ball material.

## Pipe stiffness (Q1, Q6): `python3 docs/bench-test/pipe_sag.py`
Point load 44 N (3 kg x 1.5), PVC E = 3000 MPa short term, 1000 MPa after creep, sag limit 1 mm.
The runs are secured in the centre, so sag is at the ends. Two cases are shown for the 140 and 290 mm end spans
between the centre bracket and the corner.
- 32 mm pipe: fine if the end span is held at the corner (0.06 to 0.5 mm after creep). If the corner end is free
  (cantilever) it sags 2 to 18 mm: so **supports near the ends are needed whatever the diameter**.
- **Flag: a standard 25 mm pipe** is stiff enough only if the span is short or pressure-grade: 25 x 2.3 passes the 1 mm limit
  for the 290 mm end span with the corner held (0.92 mm), 25 x 1.5 does not (1.28 mm). It has no margin; 32 mm stays the choice unless the
  wall thickness of the real pipe is confirmed. Measure the real wall thickness and re-run the script.
