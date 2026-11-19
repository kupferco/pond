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

## Water top-up: two options per unit

Evaporation and plant use lower the water. The float switch always stops the main pump before it runs dry. What happens next is the owner's choice per unit.

### Option 1 (default): notify only, a person tops up

- The float switch cuts the main pump by itself (wired in series with the pump supply, see Parts). The controller reads the same switch and raises an alarm: "unit N low on water".
- A person pours water in. Nothing extra to buy, no power, nothing that can flood.

### Option 2 (optional): automatic top-up from a tap

For people who can connect a garden hose from a tap to the unit. Two ways, pick one:

**2a. Mechanical float valve (toilet-style), no electronics.** A small float (fill) valve sits in the tank, fed by the hose. It opens when the water drops and closes when it is back at the set level. Cheapest and most robust; uses no power. Its level is fixed by the float arm, so set it a little above the pump-safe float switch level. Drawback: if the valve seat fails (dirt in the tap water), it keeps filling, so add the overflow guard below.

**2b. Electric (solenoid) valve, opened by the unit controller.** The controller opens a normally-closed 12 V solenoid valve when the float switch says low, and closes it when full. This needs a second float switch (the "full" level) or a two-level float, so the valve closes without waiting for a timer. Lets the controller log every top-up, which is useful for spotting leaks.

**Safety against a stuck valve or a stuck float (both options):**

- Max fill time (2b): the controller closes the valve after a fixed time per event (for example 3 minutes, set from the tank volume and the flow of the tap), raises an alarm and does not reopen until a person resets it. Also a daily cap on total fill time.
- The valve is normally closed: if power or the controller fails, it shuts.
- Overflow guard (both): an overflow pipe (stand pipe) in the tank, sized larger than the fill hose flow, leading to the soil. If the valve sticks open, the extra water leaves through the overflow, not over the lid or the electronics.
- A hand shut-off tap (hose ball valve) on the hose, closed when away for long.
- Electronics and valve outlet above the overflow level and kept dry (not under the lid mesh).

**Top-up water dilutes the nutrients.** Fresh tap water lowers EC, and may shift pH. The daily EC check at the station matters more with auto top-up on: if EC falls below the target, the dosing pumps (or a person) add nutrient. Keep top-up small and frequent rather than large.

### Parts and rough prices for option 2 (R$, not quotes)

| Part | For | Part to search for | Rough price (R$) | Notes |
|---|---|---|---|---|
| Float valve, toilet-style | 2a | "torneira de boia" / "válvula de boia 1/2 pol" (plastic, hose thread) | 15 to 40 | No power. Needs a hose fitting. |
| Solenoid valve, 12 V DC, normally closed | 2b | "válvula solenoide 12V 1/2 pol NF" (plastic, the common 1/2 inch water type) | 40 to 90 | Needs a minimum water pressure (typically 0.02 to 0.8 MPa); check the label against the tap. |
| Second float switch ("full" level) | 2b | Same vertical mini float switch as the low level | 10 to 25 | |
| MOSFET or relay module, 12 V | 2b | "módulo relé 5V 1 canal" or logic-level MOSFET board | 10 to 25 | Switches the valve from the controller. Add a flyback diode on the coil if the module has none. |
| Garden hose, 1/2 inch, 3 to 5 m, tap connector and hose clamps | both | "mangueira 1/2 jardim", "conector torneira", "abraçadeira" | 40 to 90 | Length depends on the tap. |
| Hand shut-off (hose ball valve) | both | "registro esfera 1/2" with hose fitting | 15 to 30 | |
| Overflow pipe + fitting | both | Small PVC pipe and bulkhead ("adaptador soldável com flange") | 15 to 40 | Drains to soil. |
| Strainer / mesh filter at the valve inlet | 2b | "filtro de tela para registro" | 10 to 20 | Stops grit sticking the valve open. |

Rough total per unit: option 2a about R$ 85 to 200, option 2b about R$ 140 to 340 (the hose, shut-off and overflow are shared by both). Option 1 costs nothing extra.

### Energy for the solenoid

- A small 12 V solenoid valve draws about 4 to 6 W while open, and nothing when closed (normally closed, so it needs power to open, not to stay shut).
- Example: 5 L of top-up a day at a tap flow of about 3 L/min means about 2 minutes open, 5 W x 2 min = **~0.2 Wh a day per unit** (about 2 Wh for 10 units). Even with the 3 minute cap on every event, a few events a day stay under about 1 Wh per unit.
- Mechanical float valve (2a): 0 Wh.
- The controller and the float switches stay on the always-on line (the second float switch also draws nothing).

Effect on the budget: option 2b adds about 2 Wh a day for 10 units on top of the ~48 Wh in the [energy budget](2026-11-07-energy-budget.md), inside the 20% losses margin. Panel and battery stay as they are. The valve runs from the tap's pressure, not from a pump, so no extra pump power.

## Water supply, refill and drain (owner decisions, follow-up)

These add to the two top-up options above and, where they differ, win.

**Every unit has both:** a mechanical toilet-style float valve (does the refill) and a digital float switch (alert, and pump safety). The solenoid in option 2b is therefore optional on top of that.

**Low-water notification is on by default.** It can be switched off for units with a hose connected, since the float valve refills them.

**With a hose:**
- Units are daisy-chained on one supply line with a T fitting and one float valve per unit, plus a manual shut-off tap on each branch.
- Top-up goes straight into the nutrient tank, with the outlet above the water line so water cannot flow back into the supply (air gap against backflow).
- Then the daily EC check doses concentrate to correct the dilution.
- Optional carbon filter on the line for chlorine. Reverse osmosis is not needed for São Paulo water.

**Without a hose:**
- A big clean-water tank, filled by bucket and kept low (less weight, less algae), with one small pump with a pressure switch feeding the supply line to the float valves.
- Rough parts (Mercado Livre first, R$, not quotes): pressure-switch water pump 12 V, "bomba diafragma 12V pressostato" 80 to 200; water tank 100 to 200 L, "caixa d'água" or drum 100 to 300; T fittings, branch taps and hose 40 to 90.

**Seedlings:** a small separate clean-water tank.

**Drain:** a drain tap on every unit, for a full water change every 2 to 4 weeks (for example at harvest). Rough part: "registro esfera 1/2" with bulkhead fitting, R$ 15 to 35.

**Rough parts for the carbon filter:** "filtro de carvão ativado para água 10 pol" with housing, R$ 40 to 120.

## Left open for the owner

- Is the clean-water storage tank needed at all when a hose is connected? The float valves can feed straight from the tap, but the tank would give water when the tap is off.
- Nutrient dosing method: peristaltic pumps or gravity (drip from a bottle through a valve). Not decided.

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

- Top-up: if option 2 is used, hold the valve open and check the overflow pipe carries the flow to the soil, and that the max fill time stops the valve.

- Read the table against the shops: confirm each part exists on Mercado Livre and replace the guessed price with the real one.
- Check that the float switch is wired in series with the pump supply, not only read by the controller.

## Left open

- The sample point on top of the tank, and the arm poses for collecting and carrying: later tasks of the plan, after the cart redesign settles.
- Where exactly the station sits next to the dock, and its drain to the soil.
- Real power numbers once the controller board is chosen.
