# Plan: Shared water sensing plan

- Task: #307
- Title: Shared water sensing plan
- Date: 2026-11-18
- Link: https://viber-f7sxvx63aq-nw.a.run.app/?task=307

Status: PLAN ONLY. No app code, CAD or hardware changes. All prices are rough guesses from memory, not quotes: check them on the real shops before ordering.

Other plans read: `docs/plans/cart-roll-redesign-plan.md` (#265, on `main`) and `docs/plans/295-pipe-sag-and-cup-drain/plan.md` (#295, on `origin/feat/pipe-sag-and-cup-drain`). No other plan files exist on `main` or any remote branch.
Overlaps: (1) #265 puts roughly 3 kg on the cart and a ~20 Wh battery on it ([energy note](../../notes/2026-11-07-energy-budget.md) says the cart uses ~4 Wh a day), and its sleeves/plate are already crowded. Option B and C add mass and parts to that, so they must wait for the roll redesign to settle (Q2). (2) #295's sag numbers assume a 44 N design load; extra probe weight is small but not free (see section 5). (3) The energy note counts "sensors always on" at ~20 Wh a day for per-unit sensing; sharing would change that (section 6). Nothing contradicts them.

## 1. What we need to measure, and how often

| Reading | Why | Must be continuous per unit? | How often is enough |
|---|---|---|---|
| Water level | Stops the pump running dry, which kills it and the plants | **Yes.** Safety, must work with the robot away | Always on, cheap, a fault must turn the pump off by itself |
| pH | Lettuce wants about 5.5 to 6.5; drifts slowly | No | Once or twice a day is plenty; a daily trend is what matters |
| EC / TDS (nutrient strength) | Plants use nutrients, water evaporates, strength moves | No | Once a day |
| Water temperature | Hot water holds less oxygen and grows algae; São Paulo summers are hot | Nice to have, slow-moving | Same visit as pH/EC, or a 2 GBP probe left in the tank |

Only water level is a safety item. The rest drift over hours and days, so a visit once a day (or per patrol, 6 a day in the energy note) is a good fit for a shared sensor. This is the main argument for sharing.

## 2. The problem with per-unit probes

- pH probes are the weak point: glass bulb must **never dry out**, drift, and need a two-point calibration (pH 4 and 7 buffer) every 1 to 3 months. Cheap probes last about 6 to 12 months in constant immersion.
- Leaving a probe in a nutrient tank all the time speeds up fouling (algae, salt crust) and drift. Constant immersion is also what shortens life for cheap probes.
- EC probes drift less but still foul; they need a calibration solution (1413 µS/cm) every few months.
- A fault shows up as a wrong number, not a failure, so a bad probe can quietly make the system dose wrongly. A shared set has one thing to check; 10 sets have 10.

## 3. The four options

Assumed context: unit has a 30 cm deep tank (15 cm water), the track loop runs 10 to 15 cm above the tank, the cart carries ~3 kg and a ~20 Wh battery, one robot serves up to ~10 units, and the arm is the SO-101 style (5 joints + gripper). Sensor boards run at 3.3 or 5 V and need an ADC; the cart computer and the unit controller can read them.

### Rough prices (guesses, one set = pH + EC + temperature + level)

| Part | UK (GBP) | São Paulo (R$, Mercado Livre / AliExpress) |
|---|---|---|
| pH probe + board, cheap generic | 12 to 25 | R$ 60 to 130 (AliExpress ~R$ 40 to 80 before import tax) |
| pH probe + board, better quality (e.g. Atlas, DFRobot industrial) | 40 to 130 | R$ 250 to 700 (mostly imported, slower) |
| EC / TDS probe + board, cheap | 8 to 20 | R$ 30 to 80 |
| Water temperature (DS18B20 waterproof) | 2 to 4 | R$ 12 to 25 |
| Level: float switch | 2 to 5 | R$ 8 to 25 |
| Level: ultrasonic or capacitive | 4 to 10 | R$ 25 to 60 |
| Calibration kit (pH 4 + 7 sachets, EC 1413) | 10 to 20 per year | R$ 50 to 120 per year |
| Small peristaltic pump (rinse) / tiny 12 V pump | 4 to 10 | R$ 25 to 60 |
| Silicone tube, cups, glue, printing | 3 to 8 | R$ 15 to 40 |

AliExpress import tax into Brazil is large (about 60 percent or more on small parcels), so the AliExpress price is lower but not by half. Mercado Livre is faster and easier to return. Both prices are to confirm.
A cheap full set costs about **GBP 25 to 55 (R$ 130 to 300)**; a good set about **GBP 80 to 200 (R$ 500 to 1,200)**.

### A) Sensors on every unit (baseline)

- Cost: cheap set per unit, GBP 25 to 55 (R$ 130 to 300), times 10 units = GBP 250 to 550 (R$ 1,300 to 3,000). With good probes, ten times as much as that again is not needed, but several hundred pounds per ten units is easy to reach. Plus calibration solutions for each unit, and probe replacement about once a year.
- Reliability: constant immersion shortens pH probe life; ten probes means ten chances of a silent drift. The most likely failure is a drifted pH reading nobody notices.
- Calibration and maintenance: highest. A person must visit each unit every 1 to 3 months; the robot cannot do it.
- Cart fit: none. No weight, power or design change to the cart. Power cost is on the unit (energy note, ~20 Wh a day for sensors and controller; could be cut by switching the pH/EC boards on only to take a reading).
- Verdict: simplest and most obviously works, but the dearest and the most upkeep. This is the baseline to beat.

### B) Robot carries the probes and dips them into each tank

- Cost: one set (GBP 25 to 55 / R$ 130 to 300) on the cart, plus a storage cup, rinse bottle and pump or squeeze bottle, a bracket, and perhaps an extra servo. About GBP 40 to 90 (R$ 220 to 500) for the whole robot, and nothing per unit apart from the water-level switch. For 10 units that is about one tenth of baseline.
- Reliability: the pH probe sits in a storage cup (storage solution, e.g. 3 M KCl) between dips, so it stays wet, which is better than constant immersion in nutrients. The risks: the arm must place the probe in a tank every time (alignment, lid, the tank is 10 to 15 cm below the track); cross-contamination (rinse needed between tanks, and rinse water has to go somewhere); pH probes need 30 to 60 seconds to settle, so the arm holds still for that long per tank. A probe in a moving arm can be knocked or dry out if a trip is interrupted (needs a "back to the cup" safe state).
- Calibration and maintenance: one set only. Calibration could even be done by the robot dipping into a buffer cup kept at the home station (later idea). Rinse bottle and storage solution need topping up.
- Cart fit: the probes weigh about 50 to 100 g with cables (small against 3 kg, matching #295's load margin), power is tiny (a few mW to read, a few Wh a day at most). The hard part is room: the plate, battery, arm base and pod cup (#265, section 8 of that plan) are already tight, and the cart is on a pipe at 1.9 m, so the arm must reach down into a tank and also carry the probe out of the tank without dripping onto the track. Needs a reach test (like #262) with the probe held in the gripper or on a fixed arm bracket.
- Verdict: cheapest shared option. Mechanically fiddly, and the number of things the arm must do grows (pick up the probe, dip, hold, return, rinse).

### C) Robot fetches a sample to a fixed sensor station

- Cost: one good sensor set at the home station, where mains/solar power and water already are (GBP 40 to 130 / R$ 250 to 700), plus a sample cup or tube on the cart, a pour funnel and a small rinse pump, a drain. A good set is affordable here because it is bought once. About GBP 60 to 160 (R$ 350 to 900) for the whole station plus cups. Nothing per unit but the level switch.
- Reliability: best sensor quality and the best environment (probe sits in a clean, dry-protected, controlled cup; rinsing and draining are done in one known place; storage solution kept at the station). Risks: the sample has to survive the trip without spilling (cart tilts on bends and rolls; a cup with a lid or a narrow tube helps) and temperature changes over the trip (pH is a bit temperature-dependent, so also take the temperature). Dirty-rinse water needs a drain; clean water or a tube to refill is needed. Station takes sample time per unit.
- Calibration and maintenance: lowest per unit. One set, at a fixed spot, in easy reach of a person. A calibration buffer cup can sit next to it, so the robot can run an automatic check.
- Cart fit: the cart carries only a light empty cup (about 20 to 100 g with 50 to 100 ml of water), no probe, no cable. Power: a few extra seconds of arm motion per unit. The cart needs the arm to dip a cup into the tank, lift without spilling, and drive on. This is the same kind of motion as the planned pod pick-and-place, but it is wet and has to be level on the roll.
- Verdict: best long-term shape: one good sensor set, little weight on the cart. Costs the most arm work to build and the most careful tilt control.

### D) Minimal: level float per unit, maybe a cheap EC probe, pH by hand weekly

- Cost: float switch per unit, GBP 2 to 5 (R$ 8 to 25); a cheap EC probe, GBP 8 to 20 (R$ 30 to 80); pH test kit (drops or strips) or one handheld pH pen, GBP 10 to 25 (R$ 50 to 150) shared by hand. About GBP 5 to 25 (R$ 20 to 110) per unit.
- Reliability: the float switch is almost fool-proof. A cheap EC probe is rough but fine for "strength is about right". With a stable nutrient mix and good tap or rain water, pH usually drifts slowly; weekly checks catch it. Risk: a weekly gap hides fast problems (e.g. hot week, water change).
- Calibration and maintenance: a person does a weekly check. Fine for the first prototype (1 to 2 units, a person is there anyway), a poor fit for 10 units, where weekly rounds is what we are trying to avoid.
- Cart fit: none. No weight, no power.
- Verdict: the right place to start. It adds almost no cost and it teaches us how fast pH and EC drift in real tanks, which decides how often the shared approach has to visit.

### Comparison

| | A) Per unit | B) Robot dips | C) Robot fetches sample | D) Minimal |
|---|---|---|---|---|
| Cost per 10 units (cheap parts) | GBP 250 to 550 (R$ 1.3k to 3k) | GBP 40 to 140 (R$ 220 to 800) | GBP 60 to 210 (R$ 350 to 1.1k) | GBP 50 to 250 (R$ 200 to 1.1k) |
| Quality of readings | Fair, drifts | Good if rinsed | Best | Rough, EC only |
| Calibration effort | High, ten sets | Low, one set | Lowest, one set, fixed spot | None for pH (by hand), EC rough |
| Cart weight added | none | ~50 to 100 g | ~20 to 100 g cup | none |
| Arm work added | none | probe dip, hold, return, rinse | cup dip, carry, pour (section 7) | none |
| Build risk | low | medium | medium to high | lowest |
| Fit with cart design now | no change | needs room and a reach test | needs a cup holder, tilt care | no change |

(The D figure includes the per-unit float and EC probe times ten and one shared pH pen.)

## 4. Recommendation

**Start with D for the prototype (1 to 2 units).** Float switch (continuous, per unit, wired to pump safety) plus a cheap EC/TDS and temperature probe, and pH by hand with a handheld pen or test kit once a week. It costs almost nothing, adds nothing to the cart, and gives us a log of how fast pH really drifts.

**Then move to C, not B, as the shared approach**, on this path:
1. **Now:** D on the prototype. Keep a hand log of pH, EC and temperature.
2. **Home-station bench rig:** put one good pH + EC + temperature set into a cup at the home station, a person pours a sample by hand each day. This tests the sensor, rinse and drain, and calibration, with no robot work.
3. **Robot fetch, simple:** once the cart and the arm are working on the track, teach the arm to dip a cup and pour it into the station (section 7), in the simulator first.
4. **Keep the float switch on every unit for good.** Sharing never replaces it.
5. **B only as a fallback** if the tank is too far from the track for a cup (Q3), or if the station is too far from the unit (Q4).

Why C over B: the probe stays in one clean, easy-to-calibrate place, and the cart stays light, which matches the weight and the crowded plate in #265. B is cheaper, but it needs a wet probe in the arm and a safe state for every interrupted trip.

If the weekly hand log shows pH hardly moves, we may never need C. That is a good outcome and costs us nothing.

## 5. Weight and power, plainly

- Weight: B adds about 50 to 100 g, C about 20 to 100 g (an empty cup, plus up to 100 ml of water on the trip). The cart is about 3 kg and the pipe-sag plan #295 uses 44 N (3 kg x 9.81 x 1.5) as design load, so 100 g is about 3 percent and fits that margin. The 2 kg arm and battery are already the biggest items.
- Power: reading a probe takes milliwatts for seconds. Extra arm moves cost a few joules each. Against ~4 Wh a day for the cart drive and arm, a dozen sample trips a day is well under 0.5 Wh. Sharing also removes per-unit always-on boards: the energy note's ~20 Wh a day is for sensors and controller together, so a good part of it could go if pH and EC boards are only powered for a reading.
- Water on a tilting cart: C carries water. The cart rolls the plate round the pipe during transfers (#265). A sample must not be carried during a roll or a bend, or must be in a lidded cup. This is a design rule to check, not a number.

## 6. Where each reading lives

- Per unit, always on: water level float (wired to the unit controller, cuts the pump itself). Optional per-unit temperature probe for sun and heat alarms.
- Shared, on demand: pH, EC, and temperature at the same visit (temperature matters for reading EC and pH).
- Energy note effect: the "sensors always on ~20 Wh" line should split in two once this is decided: always-on level switch (almost nothing) and switched-on pH/EC at the station.

## 7. What the arm and gripper need for option C

The arm is a small SO-101 style arm with a gripper, today designed for pods. Needs, in order:
1. **Tube or cup holder:** a cup with a handle or a ring the gripper can grab, or a cup that sits in a fixed clip on the plate that the arm only tips. A lidded 50 to 100 ml cup, with a handle shaped to the gripper jaws. Print in PETG. A second cup (or the same cup with a clean cycle) to avoid carrying old sample.
2. **Dip:** the arm reaches over the tank opening, lowers the cup under the surface by about 2 to 4 cm, waits to fill, and lifts. Needs the tank to be reachable: lid or hatch above the track (the tank is below the loop, which is 10 to 15 cm above it, and the lid has to open). A sensor-access hatch, about 6 to 8 cm across, in the lid.
3. **Hold level:** keep the cup upright while the cart moves; a lid or a narrow neck so a few sloshes don't spill. No roll with water on board.
4. **Pour:** at the station, a funnel into the sensor cup, and the arm tips the cup by about 90 to 120 degrees. The station is at the home position where the arm can already reach (the dock), so the arm only needs one more fixed pose.
5. **Rinse:** the same cup dips into a rinse bucket (or is sprayed by a small pump) after pouring, and the station sensor cup rinses itself with a small pump, then drains. Drain goes to a bucket or the base tank, to decide (Q5).
6. **Calibration visits (later):** the arm can also carry the cup to a buffer cup (pH 7, EC 1413) once a week to check drift.
7. **Software:** new named arm poses (dip, lift, pour, rinse) in the command language and the simulator, plus a "sample" job per unit. The simulator can show spills as a cup-tilt limit.

## 8. Risks and what we will check

- Does the arm reach into the tank from the track? (reach test, like #262, plus the access hatch)
- Spill during a bend or roll with a cup on board.
- Cross-contamination when a rinse is skipped, or a probe is stuck dry after a power loss.
- pH meter settle time (30 to 60 s) times 10 units, about 10 minutes of arm time, which is acceptable once a day.
- Station weather: rain and sun on a pH probe. Needs a shaded, covered box.
- Prices and Brazil availability (probes, buffers, storage solution) are assumed, not checked.

## Open questions

### Q1. Do we start the first prototype with the minimal option (float switch, cheap EC probe, pH checked by hand weekly)?
Context: It costs almost nothing and tells us how fast pH really drifts, which decides how often the robot has to visit later.
Assumed: Yes, start with D on the prototype units.
Answer: Start minimal but with no hand checks: float switch for water level, a cheap EC probe, and pH measured automatically with one good probe at the home station (no weekly hand pH checks).

### Q2. Should sensing wait until the cart roll redesign (#265) has settled, so we don't add parts to a plate that is still changing?
Context: The plate, battery, arm and pod cup are already tight, and option B or C would add a holder and a few extra arm moves.
Assumed: Yes, wait; plan the cup holder only after the new sleeves are drawn.
Answer: Yes, wait for the cart redesign to settle before adding sensing parts to the cart.

### Q3. Can the tank have a small access hatch in the lid that the arm can reach, 6 to 8 cm across?
Context: Option B and C both need the arm to get into the water from the track. The lid also has to keep out mosquitoes and light (the unit design says sealed, opaque, with mesh).
Assumed: Yes, a small hatch with a flap or mesh-covered slot.
Answer: No hatch into the tank. A small peristaltic pump draws water up from the tank through a thin tube to a sample point on top; the arm collects it from the top and brings it to the shared testing station, so the arm never has to reach into the water.

### Q4. Where should the home sensor station sit, and may it be a second small box with its own power?
Context: It needs shade, clean water for rinsing, and a drain. A spot near the dock is easiest because the arm already goes there.
Assumed: Next to the dock on the first unit, in a shaded box, powered from the base battery.
Answer: One shared water testing station on the first unit, next to the dock; the arm brings a water sample to it, so only one set of probes (pH, EC) is bought for all units. Keep cost minimal. Powered from the base battery.

### Q5. Where may the rinse and sample drain go: back into the base tank, or into a bucket or the ground?
Context: Pouring used sample back into a tank is easy but could carry a little rinse water into it; a bucket needs emptying by a person.
Assumed: A small bucket, emptied by hand at first.
Answer: Into the ground (small amounts of sample and rinse water drained to the soil).

### Q6. Is a good pH probe worth the money for the shared station (about GBP 40 to 130), instead of the cheap one?
Context: One shared set makes the better probe affordable, and pH is the reading that goes wrong most quietly.
Assumed: Yes, buy one good probe for the station, cheap ones for the prototype hand checks.
Answer: _open_

### Q7. Is it acceptable that pH and EC are only checked once or twice a day, not all the time?
Context: This is what makes sharing possible. Water level stays always-on per unit. A sudden pH swing between visits would not be seen until the next one.
Assumed: Yes, one or two checks a day is enough, with water level always on.
Answer: _open_

### Q8. Do we want the robot to also do pH and EC calibration checks itself, or is a person doing it every month or two fine?
Context: Robot checks need a buffer cup at the station and more arm poses; hand calibration costs a visit but is simple.
Assumed: By hand at first, robot checks as a later idea.
Answer: _open_

### Q9. For sourcing, do we buy sensors on Mercado Livre first (faster, easier returns) rather than AliExpress (cheaper but slower and taxed)?
Context: Import tax makes the AliExpress saving smaller than it looks, and bad probes need quick swaps.
Assumed: Mercado Livre first, AliExpress for bulk later.
Answer: _open_

## Suggested tasks

1. Prototype sensing (option D): add a float switch for pump-safe water level, a cheap EC/temperature probe, and a weekly hand pH log sheet to the prototype.
2. Update the energy budget: split the always-on sensor line into level (always) and pH/EC (switched on), with real part numbers.
3. Home sensor station bench rig: one good pH/EC/temperature set in a cup, a manual daily pour, a rinse and drain, calibration notes. (after 1)
4. Tank access hatch and reach test: draw a hatch in the lid and test the arm reaching a cup into the water from the track. (after 2 of the cart roll plan #265 is settled)
5. Sample cup and gripper holder: design the cup, lid and gripper handle, and the plate clip. (after 4)
6. Arm sampling poses in the simulator: dip, lift, level carry, pour, rinse. (after 5)
7. Robot fetch job on the real cart: one sample trip per unit to the station, with the log in the control UI. (after 3 and 6)
