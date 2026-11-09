# Pond – Energy budget and battery plan, first estimate (7 Nov 2026)

Working note, not a decision. Rough numbers with stated assumptions; to be checked against real parts.

## Assumptions

- Water pump: small 12 V DC pump, about 5 W, runs 15 min every hour (6 h/day), lifts water about 1.6 m.
- Cart patrols 6 times a day; one loop is about 4 m at about 5 cm/s, so about 80 s per loop.
- Camera and compute wake only for patrols (duty-cycled), not on all day.
- Sensors (pH, EC, temperature, level) and the controller stay on all the time.

## Daily budget

| Load | Estimate per day |
|---|---|
| Water pump | ~30 Wh |
| Sensors + controller (always on) | ~20 Wh |
| Camera + compute (patrols only) | ~3 Wh |
| Cart drive + arm | ~4 Wh (climbing 1.4 m costs almost nothing; motor losses dominate) |
| Dosing pumps (2 peristaltic) | <1 Wh |
| **Total** | **~60 Wh, ~70 Wh with ~20% losses** |

Biggest levers: pump duty cycle, and never running a computer like a Pi 4 all day (that alone would add ~85 Wh/day).

## Storage

- Base battery: 12 V 20 Ah LiFePO4 (256 Wh, ~200 Wh usable). About 3 days through cloudy weather.
- Cart battery: small pack, about 20 Wh, topped up at the dock.

## Solar

- São Paulo: roughly 3.5 to 4.5 peak sun hours a day (lower in winter).
- 70 Wh/day ÷ (3.5 h × ~0.75 system efficiency) ≈ 27 W, so ~40 W with margin.
- Later decision (7 Nov bracing doc): one ~30 W panel, relying on running the pump about 10 minutes an hour.

## Battery layout (recommendation)

- One battery in the base, one on the cart. The dock is just a charger fed from the base battery, not a battery of its own.
- A second base battery or a spare isn't needed: the cart uses about 4 Wh a day and recharges at the dock in well under an hour.
- Cycle: cart leaves the dock, patrols or does a job, returns, charges from the base battery; the solar panel tops up the base battery.

## Open

- Pick real parts (pump, controller, camera board) and replace the estimates.
- ~~Draw the charging dock on the unit.~~ Done: charging dock v1 (7 Nov).
- ~~Resize the roof to a single panel.~~ Done: one 30 W panel (7 Nov).
