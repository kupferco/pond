# Pond – Water sensing for the prototype (19 Nov 2026)

Part 1 of the shared water sensing plan (task #307). Working note, not a decision. Docs only: no CAD, so no renders.
Prices are rough guesses from memory, **not quotes**. Part numbers are the models to search for; check stock and price on Mercado Livre before ordering.

## What the owner decided (answers to the plan)

- Water level: float switch on every unit, always on, wired so a low level cuts the pump by itself.
- pH and EC: **not** in each tank. One shared water testing station on the first unit, next to the dock, powered from the base battery. One good pH probe (about GBP 40) and one cheap EC probe, bought once for all units. No weekly hand pH checks.
- Sample path: a small peristaltic pump draws water from the tank up a thin tube to a sample point on top. The arm collects it there and carries it to the station. No hatch in the lid; the arm never reaches into the water.
- Drain: sample and rinse water go to the soil.
- Frequency: pH and EC once a day by default, adjustable (for example every two days). Level is always on.
- Calibration: by hand every month or two. Robot self-calibration is a later idea.
- Sourcing: Mercado Livre first, AliExpress for bulk later.
- Wait for the cart roll redesign (#265) to settle before adding any sensing part to the cart. This note adds nothing to the cart.

## Parts (first prototype)

| Job | Where | Part to search for | Rough price (R$) | Notes |
|---|---|---|---|---|
| Water level, always on | each unit | Vertical mini float switch, polypropylene, 10 W, 2 wires ("chave boia vertical mini", e.g. the common ZP4510 / PP float) | 10 to 25 | Wired in series with the pump supply (normally-closed when the water is high enough), so it works with the controller off. The controller also reads it, only to raise an alarm. |
| pH | station only | DFRobot Gravity Analog pH Meter Pro, SEN0169-V2 | 250 to 400 (about GBP 40, imported by resellers, check stock) | The one good probe. Keep it in storage solution between tests. |
| EC / TDS | station only | DFRobot Gravity Analog TDS Sensor, SEN0244, or the generic "sensor TDS" board of the same kind | 40 to 90 | Cheap on purpose. Rough but fine for "strength is about right". |
| Water temperature | station only | DS18B20 waterproof probe | 12 to 25 | Needed to correct EC and pH readings. |
| ADC for the analog boards | station only | ADS1115 16-bit I2C module | 20 to 40 | The boards output 0 to 3 V. |
| Sample pump | each unit | 12 V peristaltic pump, small DIY type (for example "bomba peristáltica 12V" with a 3 x 5 mm silicone tube) | 40 to 80 | Draws water from the tank to the sample point on top. |
| Tube and fittings | each unit | Silicone tube 3 x 5 mm, 1 to 2 m | 10 to 20 | |
| Rinse pump | station only | Same 12 V peristaltic pump | 40 to 80 | Rinse the probe cup, then it drains to the soil. |
| Calibration | station | pH 4.01 and 6.86 buffer sachets, EC 1413 µS/cm solution | 50 to 120 a year | By hand every month or two. |

Per unit (float, sample pump, tube): about R$ 60 to 125. The station (pH, EC, temperature, ADC, rinse pump, calibration) is bought once: about R$ 360 to 640 plus calibration.

## Energy budget, updated

The old line "Sensors + controller (always on) ~20 Wh" is split. Estimates, to check against real parts.

| Load | Assumption | Per day |
|---|---|---|
| Float switch, per unit | A reed switch in the pump supply. Draws nothing. | ~0 Wh |
| Unit controller (reads the float, alarms, runs the pump timer) | A small board, about 0.3 W on average | ~7 Wh |
| Sample pumps | About 3 W for 1 minute per unit per test, 10 units | ~0.5 Wh |
| Station, daily test | pH, EC, temperature and ADC powered only for the test, about 0.5 W for 5 minutes per unit, 10 units, plus the rinse pump | ~0.5 Wh |
| **Sensing total** | | **~8 Wh, down from ~20 Wh** |

Effect on the total in the [7 Nov budget](2026-11-07-energy-budget.md): about 60 Wh becomes about 48 Wh, and about 70 Wh with losses becomes about 58 Wh. The 30 W panel and the 20 Ah battery stay as they are, with more margin.

The probes are switched on only for the daily test. Powering the pH probe board off between tests does not dry the probe: the probe sits in its storage solution.

## How to check

- Read the table against the shops: confirm each part exists on Mercado Livre and replace the guessed price with the real one.
- Check that the float switch is wired in series with the pump supply, not only read by the controller.

## Left open

- The sample point on top of the tank, and the arm poses for collecting and carrying: later tasks of the plan, after the cart redesign settles.
- Where exactly the station sits next to the dock, and its drain to the soil.
- Real power numbers once the controller board is chosen.
