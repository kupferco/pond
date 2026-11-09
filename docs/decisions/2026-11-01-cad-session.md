# Pond – CAD session decisions (1 Nov 2026)

First real session using the render server (CadQuery → PNG/STEP/STL/GLB).

## Render server

- Works end to end. Claude writes CadQuery, the server renders, and Claude can see the views.
- PNG views are single-colour; the GLB keeps the colours. View the GLB at gltf-viewer.donmccurdy.com (phone or desktop).
- Links expire after 7 days. Idea: the server could host its own viewer page.

## Unit frame (decided)

- Loop narrowed to **70 cm wide** × 2 m tall (was 1 m), so the arm can reach the pods. Corner radius 150 mm.
- Loop is **10 cm in front of the spine**. That's the minimum, because the plant pipe is 11 cm across.
- Spine sits in a deep socket. The plant pipe rests on a support ring with drain holes.
- **Pods face sideways** (left/right), every 20 cm. Plants grow in the gap between the plant pipe and the loop sides (~25–30 cm).
- Crops: lettuce, rocket, herbs. Tomatoes only as dwarf varieties (e.g. Micro Tom), maybe in the top pods.
- Tanks shrunk to **70 × 46 cm** so units fit side by side and at corners. ⚠️ Stability concern: 46 cm deep for 2.4 m tall. Needs top ties between units or a different corner tank.

## Cart hand (current: v6)

- Short (40 mm) so it can go round curves. Three wheel pairs that rock on pivots; 2 wheels per pair are needed to stop tipping.
- Hinged jaw, driven by a servo + **worm gear** (self-locking, so it stays shut if the power fails).
- Drive: an N20 gearmotor on the outside wheel pair, with a belt to its second wheel. Only the riding hand drives.

## Cart (current)

- Two hands, 14 cm apart centre to centre, so **neighbouring pipes (B/C) are 14 cm apart**.
- **Ride on the outer hand**: the free hand always hangs outside the loop, so it always faces the neighbouring unit. The hands swap roles at each crossover.
- Motors: 4 for straight rows (drive + jaw per hand). Corners need a swivel on each hand (+2). The arm has its own servos.
- **Arm: stretched SO-101, ~40 cm** (custom printed longer links). The pod at a handover is 37.6 cm away, so it just reaches. Alternative: reBot B601 (~$1200, 650 mm reach).

## Corners (decided approach)

- Unit 3 is **swung clockwise about pipe E** (its left pipe), so it runs forwards from the end of the row.
- The cart grabs E without swivelling, rides up E sideways (the vertical pipes have no brackets), then **swivels round the top bar** back into unit 3's plane, before reaching the centre bracket.
- Rejected: swivelling on the vertical pipe. It either hits the spine-side brackets or leaves the free hand inside the loop.

## Open questions

- Real SO-101 reach, and whether stretched links are stiff enough.
- Whether the wheel pairs cope with the top curve while the cart is sideways (test in MuJoCo).
- Tank stability at 46 cm depth.
- Arm reach through fully grown foliage.
- Exact position of the cart on unit 3's top bar (not checked closely).

## Key renders

- Frame v2: 20261101-091750-ffbd
- Hand v6 (drive): 20261101-102944-4237
- Unit v3 (70 cm loop, arm reach): 20261101-102342-6b38
- 3-unit layout v2 (corner at E): 20261101-104909-328f
