# Shared water testing station (OpenPocket #330, part 2 of 4 of plan 307)

One station on the first unit, on the tank lid next to the dock. The cart brings a water sample in a tube and the arm plugs the tube's nozzle into a socket on the station roof. One good pH probe and one cheap EC probe (plus a small temperature probe) are bought once and serve every unit. Used sample drains to the ground. Powered from the base battery. The water level float switch stays on every unit, always on, and is not part of this station.

**Redesign of 19 Nov 2026 (owner):** no rinse bottle, no rinse pump, no funnel, and no per-unit pump. ONE peristaltic pump on the cart, a coiled recoil tube with a nozzle, a passive socket on every unit.

Drawn in `cad/water_station.py` (station and unit socket, numbers and check), `cad/water_sampler.py` (the cart's pump, tube, nozzle, parking socket, and check) and `cad/water_assembly.py` (both in one drawing with the whole cart, and check). Pictures by `cad/render_water_station.py`:
- `cad/renders/water-assembly-*.png`: the whole cart (layout B from #312) with the sampler, at the dock beside the station;
- `cad/renders/cart-water-sampler-*.png`: the cart with the pump, coil, nozzle and parking socket;
- `cad/renders/water-station-*.png` (on the unit), `water-station-closeup-*.png` (station alone), `water-station-closed-iso.png` (door on), `water-station-bench-*.png` (bench rig).

3D models: `cad/renders/assembly.glb` is the FULL assembly (cart + sampler + the unit's lid corner + station; the viewer opens it) and `cad/renders/water-station.glb` is the station on the unit only. In the pictures the front door is off and the front of the sample cup is cut away, so you can see inside.

## How the sampling works

1. **Collect.** The arm takes the nozzle out of its parking socket on the cart, plugs it into the unit's socket on the tank lid (a short dip tube runs to 8 mm over the tank floor; no pump, no power on the unit; a little dripping is accepted). The cart pump draws the sample up into the tube. The tube itself holds it: about 70 ml (a 6 mm bore tube about 2.6 m long, ASSUMED; owner asked for 50 to 100 ml), metered by counting pump turns (ml per turn to be measured on the bench). The arm parks the nozzle on the cart for the trip; the coil pulls itself back in.
2. **Test (at the station).** The arm plugs the nozzle into the socket above the test cup. The pump runs in reverse: the first part of the sample flushes the previous sample out of the cup over the standpipe, the rest stays in the cup (the pH glass stays wet) until the next test.
3. **Read** pH, EC and temperature after 60 s and send the numbers up. Nothing else to do: no rinse, the leftover in the cup is the storage.

## What is in it

- **Cart sampler** (`cad/water_sampler.py`): a mini peristaltic pump (ASSUMED, rotor 34 x 40 mm, takes 6 mm ID silicone) on the pipe B side of the plate, a short silicone link under the battery column, a PU recoil tube (8 mm OD, 6 mm ID, food-safe) coiled about 52 mm mean diameter, 14 turns, 8 mm pitch, 120 mm long retracted, and a male nozzle that parks in a flush hole in the bottom face of a block on the plate's top edge. The coil hangs 17 mm past the plate edge on pipe C's side (the roll motor is below it and clears); it is 2 mm from the battery. Checked: nothing clashes with the plate, battery, arm, pipes or either hand.
- **Unit socket** (on every unit): a round insert let 8 mm into the lid, its plain round hole FLUSH with the lid top (follow-up 3: it used to be a raised cup with a flared mouth), and a 6 mm dip tube. It sits 80 mm from the dock centre and 45 mm OUTBOARD of the track axis (moved in the 19 Nov follow-up: it used to sit at y -48, right under the track), so the arm reaches it from the cart's side with the mouth 9 mm clear of the track's footprint. Clear of the pipe, lid bar and seedling storage. Cost: a few GBP of printing and tube.
- **Station box on the tank lid**, 200 x 94 x 113 mm, standing on the lid bar, shaded by a roof plate. A removable front door (printed, or cut from sheet). **Moved 40 mm inboard in this round**: the cart's omni sleeve is 61 mm in radius round the track pipe, and the old box front was only 24 mm from the pipe axis, so the cart could not have parked or passed beside it. Now the front is 64 mm from the track axis (3 mm clear of the sleeve radius).
- **Nozzle socket** in the roof, right above the cup (unit x = 100, the dock centre, assumed): a plain round hole with a slight recess, FLUSH with the roof top (no funnel, nothing sticks up). It is 100 mm from the track axis.
- **Sample cup**, round, about 190 ml, with three grommets on a flat boss for the probes (all three lie flat, tips under the water).
- **pH probe** (the one good probe, about GBP 40), **EC probe** (cheap), **DS18B20 temperature probe** (EC and pH both need the temperature).
- **Standpipe** in the cup floor: the cup drains down to it and no further, so a "heel" of about 37 mm (about 91 ml) of water always stays round the probe tips. The pH glass never dries out. Pull the standpipe out by hand to empty the cup (calibration, cleaning).
- **Drain**: 6 mm silicone tube out of the cup floor, over the back edge of the lid and down to the soil (about 550 mm, over the lid bar with 2 mm to spare). Nothing drains into the tank.
- **Electronics** (ASSUMED parts, nothing is bought): an ESP32 board, a pH amplifier board, an EC board, a 12 V to 5 V converter, standing on the back wall. 12 V comes from the base battery. The cart pump is driven from the cart's own battery and board (not designed here).

## The daily test (default, adjustable)

Default is once a day; the interval is one number (1 day, or 2 days and so on). Water level is always on and not part of this.

1. Arm collects a sample from the unit's socket (the pump draws about 70 ml into the tube) and parks the nozzle for the drive to the station.
2. Arm plugs the nozzle into the station socket. Pump in reverse: the sample flows into the cup, the first part pushes the old heel out over the standpipe, the rest stays.
3. Wait 60 s for the pH reading to settle. Read pH, EC and temperature. Send the numbers up.
4. Arm parks the nozzle on the cart. The probes stay in the cup's water until the next test.

**Open point, carry-over.** With a 70 ml sample and a 91 ml heel, a perfectly mixed cup would still hold about 46 percent old sample (check() prints it). Real mixing is better or worse; the bench test below measures it. If it is too much, shrink the heel (a lower standpipe is limited by the probe depth: the probes need 15 mm of water over them) or take 100 ml (about 33 percent), or run the first 30 ml in and out once (a second flush).

## Bench rig (build this first, no robot, no unit, no cart)

The same cup, standpipe, probes, boards and socket on a 450 x 300 mm plywood board, no box. A person plugs a 100 ml syringe (nozzle tip) into the socket and pushes the sample in by hand each day instead of the pump; the drain tube runs into a bucket. See `water-station-bench-*.png`. The cart pump and recoil tube are tested on their own bench: pump, 2.6 m of tube, a measuring jug (turns per 10 ml, stretched and retracted, how much the coil drips). What to check:

- the pH reading settles in under 60 s and repeats within 0.05 pH when the same sample is pushed in twice;
- the probe tips stay under the heel after a drain and after a week of daily tests;
- carry-over: push in pH 7 buffer, read, then push in tap water, read; the second reading must not stay near 7 (it should be within 0.1 pH of the tap water on a second push);
- the drain does not siphon the heel away or overflow the cup at the pump rate;
- the pump moves the right ml per turn both ways, and the coil does not drain by itself when the nozzle is lifted (a little dripping is accepted).

## Calibration by hand (every month or two, robot self-calibration is a later idea)

You need: pH 4 and pH 7 buffer sachets, EC 1413 uS/cm standard, three small clean cups, clean water, paper towel.

1. Pull the standpipe out and let the cup drain. Pull the three probes back out of the grommets (pH last, never let the glass dry for more than a minute).
2. Rinse all three in clean water, dab (do not rub) dry.
3. pH: put the probe in pH 7 buffer, wait 60 s, set the 7 point. Rinse. Put it in pH 4 buffer, wait 60 s, set the 4 point. Write the two raw readings and the slope in the log. A slope under about 85 percent, or readings that take over 90 s, means the probe is worn.
4. EC: rinse, put the probe in the 1413 standard, wait 30 s, set the point.
5. Rinse all three, push them back through the grommets to the marked depth (tip about 112 mm from the cup axis), push the standpipe back in, fill the heel with clean water (or storage solution, ASSUMED) up to the standpipe top.
6. Log the date. Change the pH probe about once a year.

## Rough cost (guesses, check the shops; Mercado Livre first, AliExpress for bulk later)

| Part | GBP | R$ |
|---|---|---|
| Good pH probe + amp board, cheaper end | about 40 | about 250 |
| Cheap EC probe + board | 8 to 20 | 30 to 80 |
| DS18B20 waterproof | 2 to 4 | 12 to 25 |
| ESP32, 12 V to 5 V converter | 6 to 12 | 40 to 70 |
| Silicone drain tube, grommets, printing (box, cup, socket) | 4 to 8 | 20 to 40 |
| pH 4 + 7 sachets, EC 1413 (a year) | 10 to 20 | 50 to 120 |
| **Station** (was 75 to 155 with bottle and pump) | **about 70 to 105** | **about 400 to 585** |
| Cart: ONE mini peristaltic pump (once, on the cart) | 4 to 10 | 25 to 60 |
| Cart: 2.6 m PU recoil tube 8 x 6 mm, food-safe, plus 0.3 m silicone for the pump head | 5 to 12 | 30 to 70 |
| Cart: printed nozzle and parking socket | 1 to 2 | 5 to 10 |
| Each further unit: printed lid socket, 6 mm dip tube | 1 to 3 | 5 to 15 |
| **Whole system for 1 unit** | **about 80 to 130** | **about 465 to 730** |
| **Each extra unit** | **about 1 to 3** | **about 5 to 15** |

The rinse bottle (2 L) and rinse pump (GBP 4 to 10) are gone; the one pump on the cart serves all units and does the flush.

## Checks

`python cad/water_station.py`, `python cad/water_sampler.py` and `python cad/water_assembly.py` (CadQuery needed).
- Station: nothing in it touches the unit or itself (apart from the intended joins); the box front is 3 mm clear of the cart sleeve radius (61) round the track; the standpipe leaves 37 mm of heel; every probe sits 15 mm or more under the heel surface and 10 mm or more over the cup floor; probes are 3 mm or more apart; the drain tube clears the lid bar and leaves the tank 55 mm to the back; the unit socket touches nothing; check() also prints the sample volume against the heel and the old-sample percentage.
- Sampler: tube length and volume (about 73 ml), coil clear of the battery (2 mm), arm, plate, pipes and both hands, nothing overlaps inside it.
- Assembly: the station and unit socket clash with none of the cart, sampler, hands, plate, battery or arm when the cart is at the dock.
The reach of the arm (lift the nozzle from its parking socket, to the unit socket, to the station socket) is NOT checked: that is the arm poses part of the plan. The cart-to-unit frame move in `water_assembly.py` is a drawing aid.

## Left open

- Arm poses: take the nozzle, plug it into a unit socket and the station socket, park it. The station socket mouth is 100 mm from the track axis and 12 mm above it; the parked nozzle is on the cart plate's top edge, about 87 mm out from the pipe plane. Both need the real arm and track.
- Carry-over of the old sample (see above), pump ml per turn, and how much the tube drips: bench tests.
- Cart sampler parts (pump head size, 6 mm bore tube, the coil overhanging the plate by 17 mm) are ASSUMED; this adds parts to the cart plate that #265 had said should wait to settle, but the owner asked for it explicitly. Check that against the final plate.
- Dock position (x = 100) and the real boards and probes: dimensions here are generic.
- The sample point on the tank is now just the socket and dip tube; the 8 mm dip tube end clearance and the lid sealing (mosquitoes) around the socket are not designed.

## Follow-up: box on legs, and the blue rectangle

- The station box used to hover 26 mm over the lid. It now stands on four printed 20 x 20 mm legs (`legs()` in `cad/water_station.py`) from the lid (z 304) to the box floor (z 330). `check()` reports `box_floor_gap_to_support_mm` = 0 (and asserts it), the legs clear the lid bar and the drain tube.
- The big blue rectangle in front of the station is the unit's **seedling storage tray** (`seedling_storage` in `context_parts()`, 240 x 110 x 16 mm on the lid). It belongs to the unit, is not a leftover, and is now labelled in the station and assembly renders.

## Follow-up 2: sample socket off the track, and station back or front (19 Nov 2026)

Run `python cad/water_station_position.py`.

- **Unit sample socket** moved from y -48 to y -105 (45 mm outboard of the track axis, mouth edge 9 mm clear of the track pipe's footprint). Distance from the arm shoulder to its mouth: 276 mm (79 percent of the 350 mm reach) before, 237 mm (68 percent) now, and the gripper can be at 45 to 180 degrees. Nothing clashes.
- **Station at the BACK clashed with main's #315 track supports** (post x 115..135, y -10..6, base plate y -20..16): the box overlapped the post by 160 mm3 and the front legs the base plate. Moved 10 mm further back (`OFF_Y` 40 to 50). Now: box front 8 mm from the post, front legs 22 mm from the base plate, 16 mm from the M8 rods, 18 mm from the back brace, 12 mm over the lid bar, 13 mm clear of the cart sleeve (R 61), no overlaps with the cart, sampler, hands, plate, battery or arm.
- **Arm reach, station socket mouth** (cart at the dock, shoulder to mouth): back 308 mm (88 percent of 350), only solvable with the gripper at 125 degrees or more (tilted away); front 89 mm (25 percent), any gripper angle.
- **Station at the FRONT** (box back face just outside the sleeve radius, y -113 to -215): clashes with the sampler coil (392 mm3) and parking socket (1152 mm3), the cart plate (1045 mm3), the unit's seedling tray (legs 9600 mm3) and the tank (drain tube), and overhangs the lid edge by 15 mm. The cart's roll sleeve, plate and sampler sit in the same strip, so it cannot go there without redrawing the sampler, the tray and the box height.
- **Chosen: back.** The rule was back if the arm reaches comfortably and nothing clashes, else front. Back fails "comfortable" (88 percent of reach, gripper tilted), front fails on nine clashes and the overhang. Back is the one that builds; the reach is the open problem: arm poses are a later part of the plan, and the nozzle is on a recoil tube.
- Not caused by the station, still open from #315: with the cart at the dock the M8 rod and lock nuts of the support at x = 125 overlap the cart's right-hand jaw (731 + 273 mm3). The cart rolls to home to pass a support, as the track-supports note says.

## Assembly: the one track pipe (follow-up 19 Nov 2026, evening)

- The assembly (`cad/water_assembly.py`) draws ONE track pipe: pipe C of main's `cart_assembly.py`, at the unit's track position and height (axis check in `check()`: offset 0.0 mm). The #315 supports are placed on it and the cart is main's cart, not redrawn.
- Pipe B and the clamp that grips it are left out (pipe B is the neighbouring unit's track), so no clamp hangs in the air.
- `check()` now prints: clamp C to pipe (no overlap; the sleeve body keeps main's 4 mm clearance, wheels run 0.3 to 0.95 mm off the pipe, ball cups touch), rods and lock nuts touching the pipe, and that only one pipe and no pipe-B clamp parts are in the scene.
- OPEN: main's clamp C-gap faces the plate, the #315 rods leave the track on the spine side. At the dock (cart z = 0) the closed jaw overlaps the rod (about 730 mm3) and the lock nut. Turning the unit 90 deg about the track clears all of it, but puts the unit on the other side of the cart, so it is not applied. Owner to decide.

## Follow-up 3: connector like the Omron cuff, top sleeve on the track (19 Nov 2026)

- **Connector** (`cad/water_connector.py`), after the owner's photo of the Omron blood pressure monitor. MALE on the end of the soft tube: a thin rigid straight spigot (4.4 mm across, 1.5 mm bore, 14 mm long) on a 13 mm collar with three ring grooves that you grip. FEMALE: a plain round hole (4.6 mm) with a 1 mm deep recess, FLUSH with the surface. Pushes straight in, holds by friction (ASSUMED: a soft liner or O-ring in the hole gives the grip; the CAD hole is 0.1 mm bigger so parts do not overlap), pulled straight out. No twist, no clip.
- **Female sockets, all flush:** top of each unit's tank lid (insert let into the lid, dip tube under it), top of the station box (roof top, z 443; the raised funnel to z 462 is gone), and the cart's parking socket (hole in the bottom face of the block on the plate edge, nozzle plugs in straight up). `check()` prints "0 = flush" for each, and that the nozzle fits each hole with no overlap (14 mm in).
- **Cart clamp: top sleeve on the track.** The track is now the TOP pipe (pipe B of `cart_assembly.py`) and the top sleeve (hand B) is closed on it: gap to the pipe is the same 4 mm bore clearance as for every sleeve, no clash with the pipe. The #315 supports sit on it as before. Same rod-versus-jaw overlap as the earlier round (730 mm3, rod through the closed jaw; unchanged finding, see above).
- **Bottom sleeve not drawn:** pipe C is 120 mm from the track, level with the lid, the #315 posts and the station box. A bottom sleeve there would sit inside them (posts 6376 mm3, box and door about 1900 mm3, unit socket 3792 mm3; `check()` lists it). Its pipe would be the neighbour unit's track, not drawn either.
- **Reading used:** "top sleeve" = the upper one when the unit stands upright with its lid below. If the owner meant two sleeves on the SAME pipe, this is not that: say so.

## Follow-up 4 (OpenPocket #364): one shared layout, cart clear of the tank, water in the tank

- **The collision.** In `assembly.glb` the cart's lowest parts (the blue sample tubing coil, the silicone link and the parking block under the cart) were 19 mm *below* the top of the tank lid. Cause: the bottom track height (450), the tank and the cart depth were guessed separately in each drawing. Now `cad/layout.json` is the only place (see `docs/layout.md`): the cart hangs 165 mm under the track (measured), there is 45 mm of air (**ASSUMED**), so the bottom run is 210 mm over the lid, axis at z = 514.
- **The station moved up 64 mm with the track** (on longer legs), so the socket is still 7 mm under the track axis and the arm's reach to it is the same as before. The unit's lid socket is unchanged (it is on the lid). The #315 posts are 64 mm taller.
- **New check** `water_assembly.cart_tank_check()` (printed by `python cad/water_assembly.py` as "CART VS TANK"): fails if the cart or anything on it touches the tank shell, lid or water anywhere along the straight run, or if the cart is deeper than the layout says. Result now: lowest part (the parking block) 45 mm over the lid; no intersections at x = -140, -70, 0, 100, 140.
- **Water in the tank**: a translucent blue part named `tank_water` (150 mm over the floor, the dip tube and spine cut out of it) in every model that draws the tank, so a viewer can hide it. The tank is now hollow and see-through there.
- Still open from before and unchanged: with the cart at the dock the #315 M8 rod and lock nut of the support at x = 125 overlap the closed top sleeve's jaw (731 + 273 mm3), see above.

## Arm reach check (OpenPocket #359, 20 Nov 2026)

`python cad/water_assembly.py` now prints `arm_reach_to_sampler_points`: the distance from the arm shoulder to the three places the gripper has to go, with the cart at the dock, and which gripper angles (0 to 180 deg) the arm can solve (`cart_arm.py`, 350 mm reach).

| Point | Shoulder to point | Of reach | Gripper angles that work |
|---|---|---|---|
| Parked nozzle (parking socket on the plate edge) | 157 mm | 45 % | any (0 to 180) |
| Unit lid socket | 175 mm | 50 % | 20 to 180 |
| Station socket (box at the back) | 309 mm | 88 % | 125 to 180 (tilted away) |

The parking socket and the unit socket are comfortable. The station socket is the tight one (known from the earlier station-position round). Only the end points are tested, not the path or the pull of the recoil tube.

Parts list with rough prices (Mercado Livre first): see "Rough cost" above (cart pump, PU recoil tube, printed nozzle and parking socket, and the per-unit printed lid socket with dip tube).
