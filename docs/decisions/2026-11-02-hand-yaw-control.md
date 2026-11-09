# Decision — Hand yaw control and bracket clearance (2 Nov 2026)

Status: proposed, pending a printed test hand.

## Problem

In the unit-change video the riding hand's wheels clash with the top-bar brackets on unit 2 (previously 4–8 mm too close). If the wheel assembly never rotates about the pipe, the bracket always passes through the hand's open gap. The question is how to guarantee it doesn't rotate (yaw) while riding.

## Findings (MuJoCo, sim/guide_test.py and sim/bend_test.py)

All runs: 1 kg cart, centre of mass 10 mm off-centre sideways, dry, up 6 s then down 6 s.

| Case | Worst twist |
|---|---|
| One pipe, 3 wheels (single ring), no guide | 107° |
| One pipe, 3 wheels, funnel guide | 61° (drifted past the funnel mouth before reaching it) |
| One pipe, 6 wheels (pairs 60 mm apart), no guide | 11° |
| One pipe, 6 wheels, pairs 24 mm apart (hand v6), funnel | 15° |
| One pipe, 6 wheels, pairs 40 mm apart, funnel | 8° |
| One pipe, 6 wheels, pairs 60 mm apart, funnel, full pass up and down | 4°, exits ~2° off square |
| Two pipes (B + C), both hands gripping, no guide | under 4° |

- Gripping two parallel pipes locks rotation on its own (Dani's hypothesis confirmed).
- On single-pipe stretches, wheel-pair spacing is the main lever; a funnel alone cannot catch large drift.

## Corner check (150 mm loop corners)

One hand, 6 wheels, driven round a 150 mm centreline-radius 90° bend, gravity off. 24, 40 and 60 mm pair spacing all passed without jamming; idler springs moved at most ~2 mm of the 2.5 mm travel. 60 mm showed a brief slip spike mid-bend, not a jam.

## Decision

1. Hands keep 6 wheels (3 pairs), with pairs spread to ~60 mm (up from 24 mm in hand v6). Rigid pairs, not free rockers (free rockers fell off in the earlier test).
2. Guide: funnel on the CART, built into the hand's bracket gap, flared top and bottom so it works in both directions.
3. Track: short screws/pins on the pipes pointing the same way as the brackets, spaced along each pipe, so every pin and bracket nudges the hand back to square. (Dani's idea; cheaper and easier than rails on the track.)

## Open items

- Print a test hand at 60 mm to confirm real tyres (not point-contact spheres) get round the corners under gravity.
- Model the screw-pin + cart-funnel version in the sim and decide pin spacing.
- Downhill: the cart slid fast after reversing in every run; drive grip and braking need their own look.
- Twin-pipe case only has drive on one hand and barely climbed; check drive on both hands.
