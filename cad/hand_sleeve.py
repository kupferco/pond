# Hand sleeve, draft v3 (31 Oct 2026). Designed with Claude via the render server,
# render id 20261031-232037-eaa2. Not yet printed or dimension-checked; see the
# "assumed" comments. Runs with: .venv/bin/python -m pond_render (render_cad) or
# locally via pond_render.sandbox.host.run_cad_script.
import cadquery as cq
import math

# ---------------- Dimensions (mm) ----------------
PIPE_D = 32.0          # outer diameter of the track pipe (assumed)
BORE_CLEAR = 4.0       # radial gap between pipe and sleeve bore
WALL_OUT_R = 34.0      # outer radius of the sleeve body
SLEEVE_L = 94.0        # sleeve length along the pipe
WHEEL_D = 20.0         # wheel diameter
WHEEL_W = 8.0          # wheel width
WHEEL_CLEAR = 1.0      # clearance round each wheel in its pocket
END_WALL = 4.0         # solid material above/below each pocket
AXLE_D = 3.2           # axle hole (M3 / N20 3 mm shaft)
AXLE_OVERRUN = 3.0     # how far each axle hole runs past the outer wall (clears the angled exit)
SPRING_TRAVEL = 2.5    # radial slot travel for spring-loaded wheels
OUTER_WHEEL_ANG = 180.0          # driven wheel, outside of the loop (-X)
INNER_WHEEL_ANGS = (60.0, -60.0) # spring wheels, back and front, towards spine
OPENING_W = 14.0       # width of the C gap facing the spine (+X)
PAD_X0, PAD_X1 = -24.0, 0.0      # base mounting pad extent in X
PAD_Y0, PAD_Y1 = -40.0, -21.0    # pad extent in Y (front = -Y)
PAD_HOLE_D = 4.3       # M4 clearance holes for the cart base
PAD_HOLE_Z = 15.0      # +/- Z spacing of the pad holes from centre

# ---------------- Derived ----------------
R_PIPE = PIPE_D / 2
R_BORE = R_PIPE + BORE_CLEAR
WHEEL_R = WHEEL_D / 2
AXLE_R_POS = R_PIPE + WHEEL_R            # wheel centre radius (touches pipe)
POCKET_H = WHEEL_D + 2 * WHEEL_CLEAR
POCKET_W = WHEEL_W + 2 * WHEEL_CLEAR
RING_Z = SLEEVE_L / 2 - POCKET_H / 2 - END_WALL
AXLE_LEN = 2 * (math.sqrt(WALL_OUT_R**2 - AXLE_R_POS**2) + AXLE_OVERRUN)

# ---------------- Body ----------------
body = (cq.Workplane("XY").circle(WALL_OUT_R).circle(R_BORE)
        .extrude(SLEEVE_L).translate((0, 0, -SLEEVE_L / 2)))

pad = cq.Workplane("XY").box(PAD_X1 - PAD_X0, PAD_Y1 - PAD_Y0, SLEEVE_L).translate(
    ((PAD_X0 + PAD_X1) / 2, (PAD_Y0 + PAD_Y1) / 2, 0))
body = body.union(pad)

def rot(shape, ang):
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)

for z in (RING_Z, -RING_Z):
    for ang, sprung in [(OUTER_WHEEL_ANG, False)] + [(a, True) for a in INNER_WHEEL_ANGS]:
        rad_len = WALL_OUT_R - R_BORE + 6
        pocket = cq.Workplane("XY").box(rad_len, POCKET_W, POCKET_H).translate(
            ((R_BORE + WALL_OUT_R) / 2, 0, z))
        body = body.cut(rot(pocket, ang))
        axle = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            AXLE_D / 2, AXLE_LEN, cq.Vector(AXLE_R_POS, -AXLE_LEN / 2, z), cq.Vector(0, 1, 0)))
        if sprung:
            axle2 = cq.Workplane("XY").add(cq.Solid.makeCylinder(
                AXLE_D / 2, AXLE_LEN, cq.Vector(AXLE_R_POS + SPRING_TRAVEL, -AXLE_LEN / 2, z), cq.Vector(0, 1, 0)))
            bridge = cq.Workplane("XY").box(SPRING_TRAVEL, AXLE_LEN, AXLE_D).translate(
                (AXLE_R_POS + SPRING_TRAVEL / 2, 0, z))
            axle = axle.union(axle2).union(bridge)
        body = body.cut(rot(axle, ang))

opening = cq.Workplane("XY").box(WALL_OUT_R + 10 - 15, OPENING_W, SLEEVE_L + 2).translate(
    ((15 + WALL_OUT_R + 10) / 2, 0, 0))
body = body.cut(opening)

for z in (PAD_HOLE_Z, -PAD_HOLE_Z):
    hole = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        PAD_HOLE_D / 2, PAD_Y1 - PAD_Y0 + 2, cq.Vector((PAD_X0 + PAD_X1) / 2, PAD_Y0 - 1, z), cq.Vector(0, 1, 0)))
    body = body.cut(hole)

result = body
