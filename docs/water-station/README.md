# Shared water testing station (OpenPocket #330, part 2 of 4 of plan 307)

One station on the first unit, on the tank lid next to the dock. The arm brings a water sample and pours it into a funnel on the station's roof. One good pH probe and one cheap EC probe (plus a small temperature probe) are bought once and serve every unit. Used sample and rinse water drain to the ground. Powered from the base battery. The water level float switch stays on every unit, always on, and is not part of this station.

Drawn in `cad/water_station.py` (numbers, parts and the check), pictures by `cad/render_water_station.py`. Pictures: `cad/renders/water-station-*.png` (on the unit), `water-station-closeup-*.png` (station alone), `water-station-closed-iso.png` (door on), `water-station-bench-*.png` (bench rig). 3D model: `cad/renders/water-station.glb` (also `assembly.glb`, which the viewer opens). In the pictures the front door is off and the front of the sample cup is cut away, so you can see inside.

## What is in it

- **Box on the tank lid**, 200 x 94 x 113 mm, standing on the lid bar, shaded by a roof plate. A removable front door (printed, or cut from sheet).
- **Funnel** through the roof, right under the dock position (x = 100 on the track, the same as the dock centre, assumed). Its rim is 18 mm over the track axis and 60 mm inboard of the track line, so the arm only tips the cup over it from where it already parks.
- **Sample cup**, round, about 190 ml, with three grommets on a flat boss for the probes (all three lie flat, tips under the water).
- **pH probe** (the one good probe, about GBP 40), **EC probe** (cheap), **DS18B20 temperature probe** (EC and pH both need the temperature).
- **Standpipe** in the cup floor: the cup drains down to it and no further, so a "heel" of about 37 mm (about 90 ml) of water always stays round the probe tips. The pH glass never dries out. Pull the standpipe out by hand to empty the cup (calibration, cleaning).
- **Rinse**: a 2 L bottle on the lid behind the box, a small peristaltic pump in the box, a nozzle tube over the cup rim. Two flushes of about 50 ml a day, so 2 L lasts about 16 days. Use clean water (rain or distilled is best; tap water is acceptable at first, ASSUMED).
- **Drain**: 6 mm silicone tube out of the cup floor, over the back edge of the lid and down to the soil (about 550 mm, over the lid bar with 2 mm to spare). Nothing drains into the tank.
- **Electronics** (ASSUMED parts, nothing is bought): an ESP32 board, a pH amplifier board, an EC board, a 12 V to 5 V converter, standing on the back wall. 12 V comes from the base battery.

## The daily test (default, adjustable)

Default is once a day; the interval is one number (1 day, or 2 days and so on). Water level is always on and not part of this.

1. Arm fetches a sample from the tank sample point (a later part of the plan) and pours it into the funnel.
2. Wait 60 s for the pH reading to settle. Read pH, EC and temperature. Send the numbers up.
3. Rinse twice (pump about 50 ml each, then let it drain down to the heel).
4. Leave the probes sitting in the heel. Nothing else to do.

The first pour after a rinse is the one that counts: pour 100 ml, let it overflow the standpipe, then read from the second 100 ml.

## Bench rig (build this first, no robot, no unit)

The same cup, standpipe, probes, boards, pump and bottle on a 450 x 300 mm plywood board, no box. A person pours 100 ml of water from a jug into the funnel each day instead of the arm; the drain tube runs into a bucket. See `water-station-bench-*.png`. What to check on it:

- the pH reading settles in under 60 s and repeats within 0.05 pH when the same sample is poured twice;
- the probe tips stay under the heel after a drain and after a week of daily rinses;
- the rinse leaves no carry-over: pour pH 7 buffer, read, rinse, pour tap water, read; the second reading must not drift towards 7;
- the drain does not siphon the heel away or overflow the cup at the pour rate (100 ml in 5 s);
- the pump moves about 50 ml in 10 s (change the run time to suit).

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
| Mini peristaltic pump | 4 to 10 | 25 to 60 |
| ESP32, 12 V to 5 V converter | 6 to 12 | 40 to 70 |
| Bottle, silicone tube, grommets, printing | 5 to 10 | 25 to 50 |
| pH 4 + 7 sachets, EC 1413 (a year) | 10 to 20 | 50 to 120 |
| **Whole station** | **about 75 to 155** | **about 430 to 650** |

## Checks (python cad/water_station.py)

Nothing in the station touches the unit or itself (apart from the intended joins); funnel and box stay clear of the track; the standpipe leaves 37 mm of heel; every probe sits 15 mm or more under the heel surface and 10 mm or more over the cup floor; probes are 3 mm or more apart; the drain tube clears the lid bar and leaves the tank 15 mm to the side. The reach of the arm to the funnel is NOT checked here: that is the arm poses part of the plan.

## Left open

- The sample point on the tank (small peristaltic pump and thin tube, no hatch) and the cup the arm carries are other parts of the plan; they wait for the cart redesign (#265) to settle before anything is added to the cart.
- Dock position (x = 100) and arm reach to the funnel; both need the real track.
- Real boards and probes: dimensions here are generic.
