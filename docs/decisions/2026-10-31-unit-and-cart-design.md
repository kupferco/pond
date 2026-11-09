# Pond – Unit & cart design decisions (31 Oct 2026)

Walk notes.

## Assembly

- Humans assemble the frame (flat-pack style). Self-assembly is parked as a long-term moonshot.
- Keep joints robot-friendly (twist-lock) so self-assembly stays possible later.
- Frame is plain pipe, not truss. Bracing only where the cart never goes.

## Standalone unit

- Portrait module, about 1 m wide × 2 m tall. Customers buy as many as they want and stand them side by side.
- Loop track: a rounded rectangle (elbows only), so the cart circles with no junctions on the loop itself.
- Centre plant pipe holds the pods, and the cart reaches it from every side of the loop.
- Hidden structural spine: a stainless steel (grade 316) pipe inside the plant pipe, which acts as a sleeve.
- Spine stands in a deep socket (pipe-in-pipe, parasol-stand style), welded inside the base tank. Triangular bracing also sits inside the tank, so nothing sticks out.
- Water in the tank is the ballast. Tank is deeper front to back than the frame, for a wide footprint.
- Loop raised 10–15 cm above the tank, so the cart passes underneath and the lid can open.
- Spine ties to the loop at the top and bottom with ~10 cm brackets, each with two bolt points (T-plate) so the track can't spin. A flat or square section on the spine stops brackets twisting.
- All attachments on the inner face of the loop = the no-wheels zone. Internal couplers keep the outside of the track smooth.

## Water

- Flexible tube carries water up. It trickles down inside the plant pipe past the pods and drains into the tank.
- Keep water off and out of the track (grip, algae, standing water / dengue). Add drain holes at the bottom of the track as a backup, and rubber grommets where brackets pass through the plant pipe.
- Sealed, opaque tank with mesh over any openings, plus circulation (pump cycle, optionally an air stone). This prevents mosquitoes and algae.
- Empty pod holes: spring-loaded self-closing flaps (preferred), or blank pods the robot inserts.

## Cart

- Base stays parallel to the units' plane, so the arm always faces the plants (rejected: the upside-down travel option).
- Two clamping "hands" (C-shaped wheel sleeves that open on the inner side), with the wheels spread along the pipe to resist twisting.
- Unit-to-unit transfer: stop on a vertical side, Hand B clamps the neighbour's pipe, Hand A releases. Units are spaced a few cm apart with a spacer clip.
- The SO-101 is too weak to lift the cart (the monkey move is rejected), so the hands do the transfer.
- Balance: units close together, the arm folds over the clamped side as a counterweight, long hands.
- A 90° swivel between Hand B and the base allows corners: the base pivots round the held pipe like a door on a hinge.
- Layout: two rows of five plus a corner unit turned 90° = a U shape, with one robot serving 11 units.

## Junction concepts (kept for reference)

- Passive turntable collar turned by the cart's own gear (spring detent / magnet + hall sensor). Superseded by the loop + hand-transfer approach.

## Sketches

- Hand-drawn SVG sketches (in /Sketches on Drive) are unreliable, because Claude draws them blind.
- Early Phase 1 task: add a render tool to the MCP server (SVG / CadQuery / OpenSCAD → PNG), so Claude can check its drawings before sharing them. CadQuery models can later feed MuJoCo and the printer.

## Open questions

- Exact bracket design at the spine/loop.
- Swivel mechanism and motor sizing.
- How the cart passes branches/brackets on loops with the C-clamp opening.
