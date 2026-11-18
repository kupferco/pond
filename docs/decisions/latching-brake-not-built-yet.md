# Latching solenoid brake: not built yet (OpenPocket #285, plan task 13)

Decision, 18 Nov 2026: no brake CAD and no parts-list entry for now.

Why: the owner's answer to Q5 sets an order. First rubber-roller omni wheels (common 48 or 58 mm size, buyable in the UK
and Brazil), then the cheap fixes (rubber on the pipe, a rubber-tyred roll wheel), and only then the brake.
The bench test (`docs/bench-test/README.md`, test 3, worm hold on a tilt) has not been run, so nothing yet shows
the cheap options fail. The sim (`sim/README.md`, `wet_test()`) says the drive wheel alone at 20 to 40 N cannot hold
3 kg on a wet vertical pipe, but that is the reason to try the cheap options first, not to build the brake.

Build the brake (plan task 13) only if bench test 3 fails with rubber-roller omni wheels, rubber on the pipe and a
rubber-tyred roll wheel. Then: one latching solenoid per sleeve, a driver channel each, pad on the pipe.
