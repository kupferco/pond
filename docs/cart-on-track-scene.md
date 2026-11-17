# Cart on track scene (OpenPocket #282, plan task 265 part 8)

What the scene (`control-ui/src/scenes/cart.ts`) now does, and what it found. Code: `src/cart/omni-track.ts` (placement, bend trim, contacts),
`src/cart/roll.ts` (roll rules and interlocks), `src/cart/homing.ts` (sensing and the home station), `src/cart/track-sag.ts` (pipe sag),
`scripts/search-roll.ts` (the contact searches below). Tests: the "Cart on track" block at the end of `test/sim.test.ts`.

## Findings

1. **The rigid 124 mm sleeve does not follow the R150 bend.** With the best sideways shift and yaw (1 cm steps through the bend) the riding sleeve still
   penetrates the pipe by up to **3.99 mm** in the middle of the bend (the ring, the lobes, the wheels and the ball cups all touch). Cause: the pipe's
   sag from the straight line over 124 mm on R150 is 12.8 mm, the bore only leaves 4 mm all round. It needs about 4 mm more radial room in the
   sleeve, or a shorter sleeve, or a larger bend radius, before the transfer (part 9) can work. The scene shows the contact in red text; it does not
   block driving, so the bend can be watched. The test pins the 4 mm figure so a CAD change makes it fail and the rows get searched again.
2. **Roll clearance of the free hand and the base against the track is not the problem**: with hand B riding and hand C released on the inside, a roll
   of 0 to 180 degrees in either direction touches nothing on the leg, and held through the bend (every 30 degrees, every 2 cm) the free hand and
   the base clear the curved pipe too. Both directions clear, so by Q3 the controller uses + (the plate side), and stops and asks if neither ever clears.
   Not yet tested: the other pipe, the spine, the joint rods, the tank (they are in the transfer and reach scenes, parts 9 and 11).
3. **Roll speed**: from `rollBudget()` the sleeve rolls at about 71 rpm (427 deg/s), not the plan's 33 rpm (the carried-motor kinematics in `omni.ts`).
   180 degrees takes about 0.4 s in the scene; the real limit is the motor and the grip (plan risk 1), not the kinematics.

## Rules in the controller (`roll.ts`)

- Roll only on the vertical legs, up to 180 degrees (Q8). On the top and bottom runs the cart stays flat (roll 0). On the bend the roll is held, not
  changed (Q7).
- No driving unless the roll is within 3 degrees of home, except a declared transfer roll ("carry"): it may go up the leg and round the bend, never onto
  a run.
- Direction: the one that clears (+ when both do); if neither does, stop and come back to the owner (Q3).

## Sensing and the home station (`homing.ts`)

The controller counts the drive wheel and roll wheel encoder turns (position along the pipe, roll angle) and corrects the drift at a home station
near the base of the track (positions are placeholders until the track is built):

- a **ring** of magnet tape all the way round the pipe at 10 cm (cannot be missed: "you are at home"),
- a single **point magnet** at 16 cm, 6 cm further up: zero for roll and the reference for position,
- a hall sensor on the cart reads both. Lost cart: drive down until the ring is hit (turn round at the base end), middle of the two edges is the ring's
  position; drive on to the point; roll until the point is seen (a full turn at most); the middle of its window is roll zero.
- Optional: point magnets at corners and legs as position checkpoints (`CHECKPOINTS_CM`, empty); an IMU (e.g. BNO055) for absolute roll on the
  horizontal sections. Not built.

With 3 % position slip and 5 % roll slip, homing from 36 start positions and rolls ends within 0.5 cm and 2 degrees (test).

## Pipe sag (Q1, Q6): `track-sag.ts`

Model: from the spine bracket at the middle of a run the pipe is a cantilever to where the cart stands; the cart's 3 kg weight with a 1.5 dynamic
factor (44 N) acts on the pipe it rides; PVC-U modulus 3 GPa short term and 1 GPa after creep; limit 2 mm of sag at the cart. Wall thicknesses are
assumed standard sizes: **check them against the datasheet of the pipe that is bought**.

| Pipe | Cart at the end of the straight run (140 mm from the bracket) short / creep | Cart at the corner, whole run as a cantilever (290 mm) short / creep |
|---|---|---|
| 32 x 1.8 | 0.7 / 2.1 mm | 6.1 / 18.4 mm |
| 32 x 3.0 (pressure) | 0.5 / 1.4 mm | 4.1 / 12.4 mm |
| 25 x 1.5 | 1.8 / 5.3 mm | 15.6 / 46.8 mm |
| 25 x 2.5 (pressure) | 1.2 / 3.6 mm | 10.6 / 31.7 mm |

- **A standard 25 mm pipe is not stiff enough**, even with the thick wall (3.6 mm of creep sag at the end of the straight run). Keep 32 mm.
- 32 mm with the thin 1.8 mm wall is marginal (2.1 mm after creep at the straight's end); the 3 mm wall pressure pipe passes there.
- The corner row is the pessimistic case (it ignores the bend's own stiffness and whatever holds the leg end); it still says: add supports near the run
  ends. The longest unsupported cantilever from a support at the cart load, after creep, is about 138 mm for 32 x 1.8 (101 mm for 25 x 1.5) (`maxCantileverMm`).
- Per Q6 the cart is allowed to work along the whole bottom run; the sag is at the ends, not the middle, so the supports go near the ends.
