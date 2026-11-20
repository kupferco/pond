# Arm sample run: simulated first, then on the real arm (OpenPocket #357, part of plan 307)

The sampling job from [README.md](README.md) as commands: the cart stops at a unit, the arm takes the nozzle from the cart's parking socket and plugs it into the unit's lid socket, the cart's peristaltic pump draws the sample (counted in pump turns) into the coiled tube, the arm unplugs and parks the nozzle. At the shared test station the arm plugs the nozzle into the roof socket above the test cup and the pump runs in reverse: the old sample is flushed out over the standpipe, the new one stays in the cup for the reading. **Daily by default, adjustable.**

## See it (simulator)

Open the control UI (the `/sim` page) and pick scene **10. Water sample**. "Run the sample cycle" plays the whole job (5x speed by default; 1x, 20x and Max exist). The panel shows the cart stop, where the nozzle is, the pump turns, the ml in the tube, and the cup. "Every ... days" is the interval (1 by default). "One command" runs a single line of the language below. "The cycle, as commands" lists the full script.

Code: `control-ui/src/sample/` (`layout.ts` numbers and poses, `language.ts` commands and the plan, `world.ts` the simulator), `control-ui/src/scenes/water-sample.ts` (the scene), `control-ui/test/sample.test.ts` (the test, part of `npm test`).

## Commands added to the language

Same lines for the Sim and the Real driver. One command per line; `#` starts a comment.

| Command | Does |
|---|---|
| `pose <name>` | arm joints A to E to a named pose (below), by joint-space move |
| `gripper open` / `gripper close` | open; close on the nozzle collar (13 deg) |
| `cart to unit` / `cart to station` | drive to a track stop |
| `pump in <turns>` | pump forward: draws from the nozzle into the tube |
| `pump out <turns>` | pump in reverse: pushes from the tube out of the nozzle |
| `wait <s>` | wait (the station's 60 s pH reading) |

In code: `RobotDriver.pump(turns)` and `pumpTurns()` (signed, positive = draw), `CommandLayer.pose(name)`, `CommandLayer.pump(turns)`. The Real driver still says "not connected" (Web Serial is not written); the sim counts the turns.

ml and turns: `turns = ml / ml_per_turn`. ASSUMED 1 ml per turn (a 70 ml sample is 70 turns, 35 s at 2 turns/s); the bench test measures it, then it is one number (`ML_PER_TURN` in `layout.ts`, `mlPerTurn` in the config).

### Named poses

Each is the nozzle tip over a socket, nozzle pointing straight down, found by inverse kinematics (`POSES` in `layout.ts`):

| Pose | Nozzle tip |
|---|---|
| `rest` | arm folded over the cart deck, nothing near |
| `park_above` / `park_in` | 20 mm above / 14 mm into the cart's parking socket |
| `unit_above` / `unit_in` | same, unit's lid socket |
| `station_above` / `station_in` | same, station roof socket |

### The cycle (`samplePlan()`)

```
cart to unit
gripper open / pose park_above / pose park_in / gripper close / pose park_above      # take the nozzle
pose unit_above / pose unit_in
pump in 70                                                                           # draw the sample
pose unit_above
pose park_above / pose park_in / gripper open / pose park_above / pose rest / gripper close   # park it
cart to station
(take the nozzle as above)
pose station_above / pose station_in
pump out 70                                                                          # reverse: flush the old sample, the new one stays
pose station_above
(park the nozzle as above)
wait 60                                                                              # the station reads pH, EC, temperature
```

### Interval

`DEFAULT_CONFIG.intervalDays = 1`. `runDue(lastRunMs, nowMs, days)` says if a run is due, `nextRunMs` when the next is. Something has to call it (the scheduler is not built; the scene shows "Next run" after a successful cycle).

## What the simulator checks (the test fails if any of these does not hold)

- Every pose is reachable and puts the nozzle tip within 1 mm of its socket, pointing straight down.
- The nozzle counts as plugged in only with the spigot within 2.5 mm of the socket axis, 10 to 16 mm deep, within 4 degrees of straight.
- The pump refuses to run with the nozzle parked, unplugged, or in the wrong socket (draws only at the unit, pushes only at the station), draws no more than the tube holds (73 ml), and cannot push more than the tube holds (no air into the cup).
- The hand lets go of the nozzle only in the parking socket; the cart drives only with the nozzle parked and the arm at `rest`.
- The arm touches nothing of the cart, unit or station on any tick (MuJoCo contact check).
- Water ledger: 70 ml drawn, 70 ml pushed in, everything not in the cup went over the standpipe. With a perfectly mixed 91 ml heel about **46 percent** of the old sample stays (the README's carry-over number).

## What the simulator does NOT show (be honest about it)

- **Layout is the sim's own, not the CAD frame.** The arm stands upright on the cart deck, 40 mm higher over the lid than the CAD cart, so that the SO-101 stand-in reaches the station roof with the nozzle pointing straight down. In the CAD (#359) the station socket was 88 percent of the arm's reach and only solvable with the gripper tilted; here it is 204 mm from the shoulder, but the arm is raised. **Open decision**: raise the arm on the real cart, lower the station roof, or accept a tilted nozzle entry (the Omron-style spigot pushes straight in, so tilt is the risk).
- Kinematic, no physics: no tube pull, drips, friction of the plug, or arm sag. The tube is drawn as a sagging line.
- Pump speed (2 turns/s), ml per turn, tube volume (73 ml), cup (190 ml, heel 91 ml) are ASSUMED.

## Real-hardware run sheet (do these in order; stop at any step that fails)

Needs: the cart on the track at a unit with the arm (SO-101) fitted, the printed nozzle and parking socket, the pump and the coiled tube from `cad/water_sampler.py`, a unit with its lid socket, the station (or the bench rig, see README). The Real driver (Web Serial) is not written yet: until it is, do the arm steps with the Arm scene's motor sliders or the servo tool, using the pose angles printed by `POSES` in `control-ui/src/sample/layout.ts` (print them with `node --experimental-strip-types -e "import('./src/sample/layout.ts').then(m=>console.log(m.POSES))"` in `control-ui`). Treat the sim's poses as a first guess: re-teach each one on the real arm and save its angles.

0. **Pump on its own (no arm, no unit).** 2.6 m tube in a jug of water: `pump in 10`, measure the ml, repeat 3 times, then `pump out 10`. Write down ml per turn (both ways) and set `ML_PER_TURN`. Check the coil does not drip by itself when the nozzle is lifted (a little is fine).
1. **Park and take, no water.** Cart at the unit stop, power on, arm at `rest`. Move to `park_above` (nozzle in the parking socket, gripper open, 20 mm clear). Then `park_in`: the gripper must sit on the collar without pushing the nozzle. `gripper close`: the nozzle must not slip. `park_above`: the nozzle comes straight out. Fix the pose angles until it does, with the nozzle held straight (4 degrees).
2. **Unit socket, dry.** With the nozzle in the hand: `unit_above`, `unit_in` (the spigot goes in 14 mm; the collar sits flush on the lid), `unit_above`. Do it 5 times in a row; every time it must go in without force.
3. **Draw.** `unit_in`, then `pump in 10` (10 turns). Water must move into the tube. Check no air bubble at the start of the tube. Then the full `pump in 70`. `unit_above`: the tube holds the sample; check for dripping.
4. **Park it.** `park_above`, `park_in`, `gripper open`, `park_above`, `rest`, `gripper close`. The nozzle must stay in its socket while the arm leaves.
5. **Drive.** `cart to station` (nozzle parked, arm at rest). The coil must not catch on the track pipe or the supports.
6. **Station socket, dry.** Take the nozzle again, `station_above`, `station_in`, `station_above`: 5 times, same checks. This is the tight one (the CAD put it at 88 percent of reach). If the arm cannot reach it straight down, do not tilt it in: tell the owner, and decide between raising the arm, lowering the station roof, or re-aiming the socket.
7. **Reverse.** `station_in`, `pump out 70`. Old sample runs out of the drain, the new stays in the cup at the standpipe level. `station_above`, park the nozzle as in step 4. `wait 60`, read pH, EC, temperature.
8. **Carry-over** (bench test in the README): after pH 7 buffer, a tap-water sample must read within 0.1 pH of tap water on the second run.
9. **Daily.** Set the interval (1 day) and let it run once a day. Log each reading and the ml drawn.

Stop and do not run again if: the nozzle falls out when the gripper opens away from the parking socket, the pump runs with the nozzle not plugged in, or the tube is drawn tight when the cart drives.

## Left open

- Real driver (Web Serial) and a place that calls `runDue` once a day.
- Station socket reach and the arm height (above).
- Pump ml per turn, speed, drips, carry-over: bench tests.
- Hand and gripper geometry in the sim is the stand-in arm's; the nozzle collar is held by the gripper's pads only for the look (the jaws do not collide in the sim).
