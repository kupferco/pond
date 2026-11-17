# cad/omni_wheel.py: printable 38 mm double-row omni wheel for the Pond cart (OpenPocket #291).
# Replaces the bought 38 mm omni wheels (about GBP 14 to 19 each, 4 per cart). Every number is a parameter below.
#
# Frame: wheel axis = Z, wheel centre at the origin. Hub half A is the -Z half, half B the +Z half.
# Row 1 rollers (7) sit at z = -ROW_Z, row 2 rollers (7) at z = +ROW_Z, row 2 turned half a pitch, so one
# roller is always under the pipe. The two rows do not overlap in z, so the ears of one row sit under
# the rollers of the other.
# The hub is split along a STEPPED surface: flat at z = 0 in the middle, and at each ear the split drops
# to the plane of that ear's steel pin. So every pin lies exactly between the two halves (half groove in each),
# and the four M3 screws squeeze both halves onto all 14 pins.
# Both rows use the same roller. Two grip variants of the roller: "oring" (groove, O-ring 5 x 1.5 mm) and
# "tube" (straight core, silicone tube 6 x 9 mm, 7 mm long, between two flanges).
# ASSUMED: motor shaft 6 mm with a D flat (set BORE_D / FLAT to your motor); steel pin 2 mm.
import math
import os
import sys
import cadquery as cq

# ---------------- Parameters (mm) ----------------
OD = 38.0                       # wheel outer diameter (the roller crowns touch this circle)
N = 7                           # rollers per row (14 per wheel)
ROLLER_D = 9.0                  # roller barrel diameter, max
ROLLER_L = 9.0                  # roller length
ROLLER_END_D = 5.5              # barrel end diameter
PIN_D = 2.0                     # steel pin (2 mm rod / cut nail)
PIN_L = 14.0                    # pin length
HOLE_D = 2.3                    # hole in the printed roller (running fit on the pin)
ROW_Z = ROLLER_D / 2 + 0.1      # row centre height above/below the mid plane (0.2 mm gap between rows)
AXLE_R = OD / 2 - ROLLER_D / 2  # radius of the pin axis from the wheel axis: 14.5
POCKET_CLEAR = 0.35             # pocket clearance around a roller
EAR_W = 3.0                     # ear wall between two pockets of one row (derived below, checked by assert)
HUB_R = 16.5                    # hub outer radius (rollers stand 2.5 mm above it)
HUB_HALF_T = ROLLER_D + 0.4     # half-hub thickness: hub is z = -9.4 .. +9.4
BORE_D = 6.0                    # motor shaft bore (change to your motor)
FLAT = 0.5                      # D-shaft flat depth (flat sits at BORE_D/2 - FLAT from axis); 0 = round bore
SCREW_N = 4                     # M3 screws
SCREW_R = 6.8                   # screw circle radius
SCREW_D = 3.4                   # clearance hole
HEAD_D = 5.8                    # screw head recess (M3 socket cap 5.5)
HEAD_DEPTH = 3.4
NUT_AF = 5.8                    # M3 nut across flats 5.5 + clearance
NUT_DEPTH = 2.6
SCREW_ANGLES = [12.857 + 25.714 * m for m in (0, 3, 7, 10)]  # midway between ears, clear of the pins
# O-ring variant: ring 5 x 1.5 on a groove of 6.0 mm diameter, ring stands to 9.0 mm
ORING_GROOVE_D = 6.0
ORING_GROOVE_W = 1.8
ORING_BARREL_D = 8.4            # barrel at the middle in the O-ring variant (ring stands 0.3 proud)
# Tube variant: core 6.4 mm, silicone tube 6 x 9 mm, flanges 1 mm thick at 8 mm diameter
TUBE_CORE_D = 6.4
TUBE_L = 7.0
FLANGE_D = 8.0
PIPE_R = 16.0                   # the 32 mm pipe the wheel runs on

PITCH = 360.0 / N
assert 2 * AXLE_R * math.sin(math.radians(PITCH / 2)) - (ROLLER_L + 2 * POCKET_CLEAR) >= EAR_W - 0.3, "ears too thin"
assert PIN_L <= ROLLER_L + 2 * POCKET_CLEAR + 2 * EAR_W - 0.8

# ---------------- Roller ----------------
def roller(variant="oring"):
    """Roller with its axis along X, centred on the origin. Printed standing on one end (axis up)."""
    h = ROLLER_L / 2
    if variant == "oring":
        pts = [(0, -h), (ROLLER_END_D / 2, -h), (ROLLER_D / 2 - 0.3, -h * 0.55), (ORING_BARREL_D / 2, -ORING_GROOVE_W / 2 - 0.5),
               (ORING_BARREL_D / 2, -ORING_GROOVE_W / 2), (ORING_GROOVE_D / 2, -ORING_GROOVE_W / 2),
               (ORING_GROOVE_D / 2, ORING_GROOVE_W / 2), (ORING_BARREL_D / 2, ORING_GROOVE_W / 2),
               (ORING_BARREL_D / 2, ORING_GROOVE_W / 2 + 0.5), (ROLLER_D / 2 - 0.3, h * 0.55),
               (ROLLER_END_D / 2, h), (0, h)]
    else:  # tube
        t = (ROLLER_L - TUBE_L) / 2
        pts = [(0, -h), (FLANGE_D / 2, -h), (FLANGE_D / 2, -h + t), (TUBE_CORE_D / 2, -h + t),
               (TUBE_CORE_D / 2, h - t), (FLANGE_D / 2, h - t), (FLANGE_D / 2, h), (0, h)]
    # sketch in the (radius, axial) plane: XY with x = radius, y = axial; revolve about Y, then turn axis to X
    body = cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    body = body.cut(cq.Workplane("XZ").circle(HOLE_D / 2).extrude(h + 1, both=True))
    return body.rotate((0, 0, 0), (0, 0, 1), -90)   # axial Y -> X


def oring():
    """The O-ring on the roller (reference geometry for the assembly picture only)."""
    r = (ORING_GROOVE_D + 1.5) / 2
    return cq.Workplane("XY").add(cq.Solid.makeTorus(r, 0.75, cq.Vector(0, 0, 0), cq.Vector(1, 0, 0)))


def tube():
    return (cq.Workplane("YZ").circle(4.5).circle(3.0).extrude(TUBE_L / 2, both=True))


def pin():
    return cq.Workplane("YZ").circle(PIN_D / 2).extrude(PIN_L / 2, both=True)


# ---------------- Placement ----------------
def place_row(shape, row):
    """All N copies of a shape built along X at the origin: moved to radius AXLE_R at +Y... then rotated."""
    out = []
    z = -ROW_Z if row == 1 else ROW_Z
    off = 0.0 if row == 1 else PITCH / 2
    for k in range(N):
        a = off + k * PITCH
        out.append((a, z, shape.translate((0, AXLE_R, z)).rotate((0, 0, 0), (0, 0, 1), a)))
    return out


def envelope(row):
    """Pocket: roller body inflated, plus the pin slot, for every roller of one row."""
    env = None
    for a, z, _ in place_row(cq.Workplane("XY").box(1, 1, 1), row):
        pk = (cq.Workplane("YZ").circle(ROLLER_D / 2 + POCKET_CLEAR).extrude((ROLLER_L + 2 * POCKET_CLEAR) / 2, both=True)
              .translate((0, AXLE_R, z)).rotate((0, 0, 0), (0, 0, 1), a))
        env = pk if env is None else env.union(pk)
    return env


def pins_cut(row):
    cut = None
    for a, z, _ in place_row(cq.Workplane("XY").box(1, 1, 1), row):
        p = (cq.Workplane("YZ").circle(PIN_D / 2 + 0.05).extrude((PIN_L + 0.6) / 2, both=True)
             .translate((0, AXLE_R, z)).rotate((0, 0, 0), (0, 0, 1), a))
        cut = p if cut is None else cut.union(p)
    return cut


def wedge(angle, z0, z1, r0=7.5, r1=17.0, half=7.0):
    """Sector from r0 to r1 around `angle`, between heights z0 and z1 (a piece of the stepped split)."""
    a0, a1 = math.radians(angle - half), math.radians(angle + half)
    am = math.radians(angle)
    pts = [(r0 * math.cos(a0), r0 * math.sin(a0)), (r1 * math.cos(a0) * 1.05, r1 * math.sin(a0) * 1.05),
           (r1 * 1.1 * math.cos(am), r1 * 1.1 * math.sin(am)),
           (r1 * math.cos(a1) * 1.05, r1 * math.sin(a1) * 1.05), (r0 * math.cos(a1), r0 * math.sin(a1))]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def ear_angle(row, k):
    # ears of a row sit midway between its rollers; the roller turned +PITCH/2 from the ear is the other row's roller
    off = 0.0 if row == 1 else PITCH / 2
    return off + k * PITCH + PITCH / 2


def hub_blank():
    hub = cq.Workplane("XY").circle(HUB_R).extrude(2 * HUB_HALF_T).translate((0, 0, -HUB_HALF_T))
    hub = hub.cut(envelope(1)).cut(envelope(2)).cut(pins_cut(1)).cut(pins_cut(2))
    # bore with D flat
    bore = cq.Workplane("XY").circle(BORE_D / 2).extrude(4 * HUB_HALF_T).translate((0, 0, -2 * HUB_HALF_T))
    if FLAT > 0:
        bore = bore.cut(cq.Workplane("XY").center(-(BORE_D / 2 - FLAT) - 5, 0).rect(10, BORE_D + 2).extrude(4 * HUB_HALF_T)
                        .translate((0, 0, -2 * HUB_HALF_T)))
    hub = hub.cut(bore)
    for ang in SCREW_ANGLES:
        x, y = SCREW_R * math.cos(math.radians(ang)), SCREW_R * math.sin(math.radians(ang))
        hub = hub.cut(cq.Workplane("XY").center(x, y).circle(SCREW_D / 2).extrude(4 * HUB_HALF_T).translate((0, 0, -2 * HUB_HALF_T)))
        hub = hub.cut(cq.Workplane("XY").center(x, y).circle(HEAD_D / 2).extrude(HEAD_DEPTH).translate((0, 0, HUB_HALF_T - HEAD_DEPTH)))
        hub = hub.cut(cq.Workplane("XY").center(x, y).polygon(6, NUT_AF / math.cos(math.radians(30)))
                      .extrude(NUT_DEPTH).translate((0, 0, -HUB_HALF_T)))
    return hub


def hubs():
    hub = hub_blank()
    big = 100
    low = cq.Workplane("XY").rect(big, big).extrude(big).translate((0, 0, -big))     # z < 0
    high = cq.Workplane("XY").rect(big, big).extrude(big)                             # z > 0
    # A (z < 0) loses the row-1 ear covers (z -ROW_Z..0) and gains the row-2 ear feet (z 0..ROW_Z)
    A = hub.intersect(low)
    B = hub.intersect(high)
    for k in range(N):
        a1, a2 = ear_angle(1, k), ear_angle(2, k)
        w1 = hub.intersect(wedge(a1, -ROW_Z, 0.0))      # row-1 ear, above its pin: belongs to B
        w2 = hub.intersect(wedge(a2, 0.0, ROW_Z))       # row-2 ear, below its pin: belongs to A
        A = A.cut(wedge(a1, -ROW_Z, 0.0)).union(w2)
        B = B.cut(wedge(a2, 0.0, ROW_Z)).union(w1)
    return A.clean(), B.clean()


def build(variant="oring"):
    A, B = hubs()
    return A, B, roller(variant)


# ---------------- Assembly ----------------
def assembly(variant="oring", with_pipe=True):
    A, B, R = build(variant)
    assy = cq.Assembly(name="omni_wheel_" + variant)
    assy.add(A, name="hub_A", color=cq.Color(0.20, 0.45, 0.70))
    assy.add(B, name="hub_B", color=cq.Color(0.30, 0.65, 0.85))
    for row in (1, 2):
        for k, (a, z, rr) in enumerate(place_row(R, row)):
            assy.add(rr, name="roller_r%d_%d" % (row, k), color=cq.Color(0.15, 0.15, 0.15))
            if variant == "oring":
                _, _, ring = place_row(oring(), row)[k]
                assy.add(ring, name="oring_r%d_%d" % (row, k), color=cq.Color(0.85, 0.30, 0.10))
            else:
                _, _, tb = place_row(tube(), row)[k]
                assy.add(tb, name="tube_r%d_%d" % (row, k), color=cq.Color(0.85, 0.30, 0.10))
            _, _, p = place_row(pin(), row)[k]
            assy.add(p, name="pin_r%d_%d" % (row, k), color=cq.Color(0.75, 0.75, 0.78))
    for ang in SCREW_ANGLES:
        x, y = SCREW_R * math.cos(math.radians(ang)), SCREW_R * math.sin(math.radians(ang))
        floor = HUB_HALF_T - HEAD_DEPTH
        s = (cq.Workplane("XY").circle(1.5).extrude(14).translate((x, y, floor - 14))
             .union(cq.Workplane("XY").circle(2.75).extrude(3).translate((x, y, floor))))
        assy.add(s, name="screw_%d" % SCREW_ANGLES.index(ang), color=cq.Color(0.55, 0.55, 0.6))
    if with_pipe:
        # pipe along Y under the wheel (wheel runs along the pipe: wheel axis Z, pipe axis Y, pipe top at x = -(OD/2 + PIPE_R))
        pipe = (cq.Workplane("XZ").circle(PIPE_R).extrude(40, both=True).translate((-(OD / 2 + PIPE_R - 0.0), 0, 0)))
        assy.add(pipe, name="pipe", color=cq.Color(0.80, 0.80, 0.82, 0.55))
    return assy


def compound(assy):
    shapes = []
    for ch in assy.children:
        for o in (ch.obj.vals() if hasattr(ch.obj, "vals") else [ch.obj]):
            shapes.append(o.moved(ch.loc) if ch.loc else o)
    return cq.Compound.makeCompound(shapes)


result = assembly("oring")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    A, B, R_o = build("oring")
    R_t = roller("tube")
    cq.exporters.export(A, os.path.join(out, "omni_hub_A.stl"))
    cq.exporters.export(B.rotate((0, 0, 0), (1, 0, 0), 180), os.path.join(out, "omni_hub_B.stl"))   # flat face down to print
    cq.exporters.export(R_o.rotate((0, 0, 0), (0, 1, 0), 90), os.path.join(out, "omni_roller_oring.stl"))  # axis up
    cq.exporters.export(R_t.rotate((0, 0, 0), (0, 1, 0), 90), os.path.join(out, "omni_roller_tube.stl"))
    print("wrote STLs to", out)
