# Printable 38 mm omni wheel (OpenPocket #291)

Our own double-row omni wheel for the cart, instead of the bought ones (about £14 to £19 each, 4 per cart: the drive wheel and the roll wheel on each of the two sleeves). Built in `cad/omni_wheel.py`, rendered by `cad/render_omni_wheel.py`. Pictures: `cad/renders/omni-wheel-*.png`, 3D model: `cad/renders/assembly.glb`, print files: `cad/stl/`.

Nothing here is tested on a real pipe yet. Every size is a parameter at the top of `omni_wheel.py`.

## What it is

- 38 mm across, 18.8 mm wide, about 25 g printed plus the pins.
- Two hub halves (A and B), printed in PETG or ASA, held together by four M3 x 14 screws (nuts in hex traps in half A, heads sunk in half B).
- 14 rollers (two rows of 7, the second row turned half a pitch), each on a 2 mm steel pin 14 mm long. The pins lie in half-grooves in the hub; the split between the halves steps up and down to follow each pin, so tightening the screws clamps all 14 pins and nothing else holds them.
- Rows do not overlap in height, so there is always a roller under the pipe and no roller goes over a gap.
- Bore 6 mm with a D flat (0.5 mm), for the motor shaft. Change `BORE_D` and `FLAT` to match the motor. No set screw: the D flat drives it. If the real shaft is round, glue it or add a grub screw by making a boss on the hub (not drawn).
- Outdoors: no closed pockets. The roller pockets are open at the rim and at both faces, the screw heads sit in open recesses, so water and dirt fall out.

## Grip: two variants, I would pick the O-ring

| | O-ring | Silicone tube |
|---|---|---|
| Buy | O-ring 5 x 1.5 mm (5 mm inside diameter, 1.5 mm cross-section), silicone (VMQ) or EPDM, 60 to 70 Shore A. 56 for 4 wheels, buy 100. | Silicone tube 6 mm inside x 9 mm outside (1.5 mm wall), 1 m, cut into 56 pieces 7 mm long. |
| Roller | Barrel with one groove 6.0 mm across, 1.8 wide. Ring stands 0.3 mm above the barrel. | Straight core 6.4 mm with a 1 mm flange at each end. |
| Fit | Stretch it into the groove. No glue. | Stretch it over the core; a drop of cyanoacrylate at each end if it creeps. |
| Dirt | Nothing trapped, open groove. | Water can get between tube and core. |
| Grip | A narrow 1.5 mm line of rubber. | A wider 7 mm band of rubber. |
| Wheel shape | Rounder (barrel). | Bulges about 0.4 mm over 38 mm at the roller ends. |

Pick: **O-ring**. It is cheaper and easier to find, nothing needs gluing, a worn ring is replaced in seconds, and nothing traps dirt. The risk is grip: a thin line of rubber on a wet pipe may slip earlier than the tube. That is what the bench test (task 290) should settle, so print a few rollers of both and test both. The tube is the fallback.

## Print settings

- Material: PETG or ASA (ASA best in the sun). No PLA outdoors.
- Layer height 0.16 mm for the hubs, 0.12 mm for the rollers. 0.4 mm nozzle.
- Hub half A: print as it is (flat face down). Hub half B: the STL is already turned upside down so its flat top face is on the bed. No supports: the pockets are cut straight through.
- Rollers: stand them on one end, with a 3 mm brim (the STLs are already upright). 100% infill. Ream the 2.3 mm hole with a 2.3 mm drill if the pin does not spin freely: it must turn by hand with no wobble.
- Hubs: 4 walls, 40% gyroid or 6 walls and 100% for a first set. Slow down on the first layers, no ironing.
- Ear walls are only 3 mm: do not scale the model, and print 3 spare hubs in case a pin pushes an ear out.
- Quantity for the cart (4 wheels): 4 of half A, 4 of half B, 56 rollers (print 70).

## Assembly

1. Fit the rings or tubes on the rollers.
2. Lay half A face up (nut traps down). Drop 7 rollers on their pins into the lower row's grooves and 7 into the upper row's (the upper row is only held once B is on).
3. Lay half B on top, rotating it until the 4 screw holes line up. All 14 pins should lie in the grooves with no gap.
4. Push the 4 M3 x 14 screws in from the B side into the nuts in A. Tighten. Spin every roller by hand: it should turn freely and the wheel should be round.

## Bench test (task 290)

One pair of bought 38 mm double aluminium omni wheels (about £18.89 each on Amazon UK) can be used as a reference in the bench test: run the same protocol with the bought pair and the printed pair, and compare grip, wobble and noise.
