# Command language for the control UI (draft, 10 Nov 2026)

The control UI (sim spike: Viber task 47, page at /sim) talks to one command layer. Behind it sit two drivers: **Sim** (MuJoCo in the browser) and **Real** (Web Serial to the Waveshare board). The same commands go to either, chosen by the Sim/Real toggle. Commands grow in four levels; each level is built only from the one below.

## Level 1: motors

- `motor <A–F> <degrees>` — move one arm joint to an angle, then Go.
- `motors <a> <b> <c> <d> <e> <f>` — set all six at once.
- `home` — all joints to the home pose.
- `stop` — hold where you are.
- Readout: current angle of every joint.

Arm joints (SO-101 follower): A shoulder pan, B shoulder lift, C elbow flex, D wrist flex, E wrist roll, F gripper.

## Level 2: poses

- `save pose <name>` — store the current joint angles under a name.
- `pose <name>` — move to a stored pose.
- `sequence <name>` — play stored poses in order (e.g. `above_tray`, `down`, `grip`, `up`).
- `gripper open` / `gripper close`.

## Level 3: cart

- `cart up <mm>` / `cart down <mm>` — move along the track.
- `cart to <level>` — go to a named stop on the track.
- `cart dock` — go to the charging dock on the bottom run.
- Later: drive motors on/off, hand clamp status, battery readout.

## Level 4: tasks

- `pick <dry row>` — take one pod from the front pick hole of a dry store row.
- `place <tray cell>` — put the held pod in a seedling tray cell.
- `pick D3, place B5` — the full move, cart included.
- Later: `plant <tray cell> to <pipe slot>`, `clear <pipe slot>` (remove a failed plant), `inspect <pipe slot>`.

## Naming

- **Dry store rows:** `D1` … `Dn`, one per sloped row, numbered left to right. Each row has a single pick hole at its front, so a row number is enough. (Pod store v3 draws 14 rows.)
- **Seedling tray cells:** a letter for the row and a number for the column, `A1` top-left. A 4 × 4 tray runs `A1` to `D4`; a 3 × 5 tray runs `A1` to `C5`.
- **Growing pipe slots:** `P1` … `Pn` around and up the central pipe (about 24 assumed). Exact order to decide once the rotation is designed.

## Configurable, not hard-coded

These numbers live in one settings file, not in code, because they are not decided yet:

- number of dry store rows (14 in v3)
- seedling tray rows and columns (4 × 4 = 16 or 3 × 5 = 15 under discussion)
- number of growing pipe slots (about 24)
- the positions of each pick hole, tray cell and pipe slot, in unit coordinates
- named track stops and the dock position

## Open

- Seedling tray grid: 4 × 4 or 3 × 5.
- Number and order of pipe slots, and how the pipe rotates.
- Cart commands wait for the cart model to join the sim.
