# Decision — Spine bracing, feet, solar and flat-pack (7 Nov 2026)

## Problem

The track loop is fixed to the spine only at the top and bottom. With the cart 250 mm out on one side, the loop and spine could twist and wobble. A solar panel up top adds wind load, and the base is only 400 mm deep.

## Decided

**Bracing**

- Lower A-frame in the spine plane, behind the track: a bar across the lid, two legs in angled lid sleeves, meeting at a collar about 1.2 m up. Stiffens the spine side to side.
- Back strut from the back edge of the lid up to the same collar. Stops front-to-back sway (the A-frame does nothing in that direction).
- Small top triangle: a 400 mm bar on top of the spine, two legs down to a second collar about 1.55 m up. The panel sits on that bar. No third leg needed: the panel is small and the spine plus back strut carry it front to back. The top bar must be clamped to the spine, not held by a single bolt.
- Legs: 16 mm steel tube. The lower legs and back strut split in two with push-fit joints so they flat-pack.

**Clamp collars**

- Hinged clamp collars on the OUTSIDE of the 75 mm growing pipe. No holes in the PVC.
- 50 mm tall, so they take as little growing space as possible. Long angled sleeves take the legs.
- Hinge on one side, a single M6 wing nut on the other: no tools needed. The big half carries all the sleeves; a small front gate closes it. 2 mm rubber liner so it grips without crushing the pipe.
- Spacer ring inside the pipe at each collar height carries the load to the spine.
- Model: cad/clamp_collar.py (v1).

**Feet**

- Four fold-out L feet bring the base to about 840 mm deep. Each has a hole for a bolt (slabs) or a peg (grass); otherwise a sandbag on each foot (about 13 kg total).
- Rough check: with a 400 mm base and a full tank, a solar roof could tip the unit in gusts of about 45 km/h. With the feet and about 13 kg of ballast it reaches about 70 km/h.

**Solar and power**

- One panel, about 30 W (450 × 350 mm), facing north and tilted 23° for São Paulo. One panel rather than a V roof: a V roof needs about 1.5× the wattage, because one side always faces away from the sun.
- Load estimate about 60–70 Wh a day. See the working note "Energy budget and battery plan (7 Nov 2026)". The 30 W panel relies on running the pump about 10 minutes an hour.
- One 12 V LiFePO4 battery in the base (about 20 Ah) and a small pack (about 20 Wh) on the cart. The dock is just a charger fed from the base battery. No spare battery.
- Shade from the small panel is not a problem for lettuce and helps with midday heat.
- With solar the unit is power self-sufficient: the only connection is the water inlet.

**Flat-pack**

- Everything still fits in the 30 cm tank: the panel lies flat on the shelf, with the legs, bars, feet, collars and folded sandbags on top. The tallest part is 283 mm, leaving 13 mm under the lid. Model: cad/flatpack_check.py (v3). The collars are still placeholder envelopes in that check.

## Models

- Unit with bracing: cad/unit_v3_aframe.py (v5). [Viewer](https://pond-render-500653746288.us-east1.run.app/v/1fpkwDxHGDRla9)
- [Clamp collar v1](https://pond-render-500653746288.us-east1.run.app/v/1fqT4PaR8eND2b)
- [Flat-pack check v3](https://pond-render-500653746288.us-east1.run.app/v/1fqRfmXSF3w1uZ)

## Open

- Sizing of the collar and leg joint (real loads, steel gauge).
- Simulate the wobble with the cart moving on one side.
- Charging dock position. (Since done: charging dock v1, 7 Nov.)
