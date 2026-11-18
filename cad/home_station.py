# cad/home_station.py: the HOME STATION on the track pipe and the HALL SENSOR on each hand (OpenPocket #286, plan task 265 part 12, Q3 addendum).
# docs/plans/cart-roll-redesign-plan.md. The control side is control-ui/src/cart/homing.ts (ring, point magnet, lost-cart recipe).
#
# What is drawn, all in the hand_sleeve.py frame (pipe along Z, sleeve centred on z = 0, hand B as drawn; hand C is the true mirror):
#   - on the pipe: a RING of magnet tape all the way round at 10 cm from the bottom of the leg ("you are at home", cannot be missed) and,
#     6 cm further up, ONE point magnet (a small disc) at the pipe's roll zero. Ring and point are what the hall sensor reads.
#   - on the hand: a hall sensor board (PCB with the sensor chip) in a pocket cut into the sleeve wall at the END that faces the base,
#     between the 180 deg omni lobe and the -60 deg cup lobe, chip face looking at the pipe through a window in the bore wall.
# check(): sensor-to-pipe gaps, ring and point seen at the right places, nothing the sensor board touches, the sleeve wall left round the pocket.
#
# ASSUMED (undecided, marked where used): 1. the pocket angle SENSOR_ANG (the first free wall between the lobes, found by probing the sleeve);
# 2. tape 10 mm wide x 1.0 mm thick, point magnet a 6 x 1.5 mm disc (6 mm is 21 deg wide on the R16 pipe, as POINT_WINDOW_DEG in homing.ts;
# a 10 x 3 mm disc would stand 3 mm proud and touch the sensor and the ball-cup lips); 3. a generic 10 x 12 x 1.6 mm hall board, chip 4 x 3 x 1.5;
# 4. ring at 10 cm and point at 16 cm are placeholders until the track is built (homing.ts). The real sensor board is not chosen yet.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cart_omni as co
import hand_sleeve as hs

# ---------------- On the pipe (numbers mirror control-ui/src/cart/homing.ts; the test compares them) ----------------
RING_CM = 10.0                     # centre of the ring of tape, from the bottom of the leg
RING_W = 10.0                      # mm, tape width (RING_W_CM 1.0)
POINT_CM = 16.0                    # the point magnet, 6 cm beyond the ring centre
TAPE_T = 1.0                       # ASSUMED tape thickness
POINT_D = 6.0                    
POINT_T = 1.5        # ASSUMED point magnet disc (6 mm = 21 deg of the R16 pipe)
POINT_ANG = 240.0                  # deg round pipe B (hand frame) where the zero magnet sits: under the sensor at roll 0 (pipe C: mirrored, 300)
HOME_Z = 0.0                       # where the bottom of the leg is drawn: z of position 0 on the pipe stub (hand frame centre is s = 0 + sensor offset)

# ---------------- On the hand ----------------
SENSOR_ANG = 240.0                 # deg: pocket centre angle in the hand frame (probe: solid wall r 23..34.5 from z = -60 to -50 between the lobes)
SENSOR_Z = -55.0                   # sensor chip centre, 55 mm from the sleeve centre towards the base end (the -Z end is the one that faces down the leg)
PCB_L, PCB_W, PCB_T = 14.0, 12.0, 1.6      # PCB: along Z, tangential, thickness (radial)
CHIP_L, CHIP_W, CHIP_T = 3.0, 4.0, 1.5     # sensor chip stands on the pipe side of the PCB
FACE_R = 19.5                      # chip face from the pipe axis: bore wall is R20, so the chip stands 0.5 proud of it, 3.5 off the pipe
PCB_R0 = FACE_R + CHIP_T           # inner face of the PCB: 21.0
PCB_R1 = PCB_R0 + PCB_T
POCKET_R1 = PCB_R1 + 3.0           # pocket depth (room for solder and a connector), still inside the wall (wall ends at 34.5)
WINDOW_W, WINDOW_L = CHIP_W + 2.0, CHIP_L + 3.0
CABLE_D = 2.0
SENSOR_COL, PCB_COL, TAPE_COL, MAG_COL = (0.15, 0.15, 0.17, 1), (0.1, 0.5, 0.25, 1), (0.55, 0.15, 0.15, 1), (0.8, 0.1, 0.1, 1)


def _radial(shape, ang):
    """Rotate a shape built along +X (radial direction) about the pipe axis to angle ang."""
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)


def _box(r0, r1, w, z0, z1):
    """A box between radii r0..r1 (along +X before rotating), width w (Y), z0..z1."""
    return cq.Workplane("XY").box(r1 - r0, w, z1 - z0, centered=False).translate((r0, -w / 2, z0))


def pocket():
    """Cut into the sleeve wall: the board pocket open to the end face (so the board slides in from the end), the chip window through to the bore,
    and a cable slot out of the end face."""
    zend = -hs.SLEEVE_L / 2 - 1.0
    z0, z1 = SENSOR_Z - PCB_L / 2 - 0.3, SENSOR_Z + PCB_L / 2 + 0.3
    board = _box(PCB_R0 - 0.2, POCKET_R1, PCB_W + 0.6, zend, z1)
    window = _box(hs.R_BORE - 2.0, PCB_R0 + 0.5, WINDOW_W, SENSOR_Z - WINDOW_L / 2, SENSOR_Z + WINDOW_L / 2)
    cable = _box(PCB_R1 + 0.5, PCB_R1 + 0.5 + CABLE_D + 1.0, CABLE_D + 1.0, zend, z1)
    return _radial(board.union(window).union(cable), SENSOR_ANG)


def sensor_parts():
    """dict name -> (shape, colour) in the hand frame: PCB, the chip, and the cable end."""
    pcb = _radial(_box(PCB_R0, PCB_R1, PCB_W, SENSOR_Z - PCB_L / 2, SENSOR_Z + PCB_L / 2), SENSOR_ANG)
    chip = _radial(_box(FACE_R, PCB_R0, CHIP_W, SENSOR_Z - CHIP_L / 2, SENSOR_Z + CHIP_L / 2), SENSOR_ANG)
    cab = cq.Workplane("XY").add(cq.Solid.makeCylinder(CABLE_D / 2, 14.0, cq.Vector(PCB_R1 + 1.5 + CABLE_D / 2, 0, SENSOR_Z), cq.Vector(0, 0, -1)))
    return {"hall_pcb": (pcb, PCB_COL), "hall_chip": (chip, SENSOR_COL), "hall_cable": (_radial(cab, SENSOR_ANG), (0.1, 0.1, 0.1, 1))}


# ---------------- The home station on a pipe stub ----------------
def station(length=250.0, z_bottom=-125.0, point_ang=POINT_ANG):
    """Pipe stub with the ring and the point magnet. z_bottom = z of the bottom of the leg (position 0). Returns dict name -> (shape, colour)."""
    r = co.R_PIPE
    pipe = cq.Workplane("XY").add(cq.Solid.makeCylinder(r, length, cq.Vector(0, 0, z_bottom), cq.Vector(0, 0, 1)))
    zr = z_bottom + RING_CM * 10.0
    ring = (cq.Workplane("XY").add(cq.Solid.makeCylinder(r + TAPE_T, RING_W, cq.Vector(0, 0, zr - RING_W / 2), cq.Vector(0, 0, 1)))
            .cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(r - 0.1, RING_W + 2, cq.Vector(0, 0, zr - RING_W / 2 - 1), cq.Vector(0, 0, 1)))))
    zp = z_bottom + POINT_CM * 10.0
    disc = cq.Workplane("XY").add(cq.Solid.makeCylinder(POINT_D / 2, POINT_T + 1.0, cq.Vector(r - 1.0, 0, zp), cq.Vector(1, 0, 0)))
    disc = _radial(disc, point_ang)
    return {"track_pipe": (pipe, (0.75, 0.78, 0.8, 1)), "home_ring_tape": (ring, TAPE_COL), "home_point_magnet": (disc, MAG_COL)}


def pos_of_z(z, z_bottom=-125.0):
    return (z - z_bottom) / 10.0


def scene(at="ring", roll=0.0):
    """Hand B on the pipe with the home station; the cart (sleeve and sensor) moved along the pipe so the sensor chip is over `at` ("ring" or
    "point"), and rolled `roll` degrees. Lazy import of cart_sleeves (it imports this file)."""
    import cart_sleeves as cs
    zb = -125.0
    st = station(z_bottom=zb)
    target = zb + (RING_CM if at == "ring" else POINT_CM) * 10.0
    dz = target - SENSOR_Z
    a = cq.Assembly()
    for n, (s, c) in st.items():
        a.add(s, name=n, color=cq.Color(*c))
    for n, (s, c) in cs.hand_parts().items():
        sh = s.translate((0, 0, dz))
        if roll:
            sh = sh.rotate((0, 0, 0), (0, 0, 1), roll)
        a.add(sh, name="hand_" + n, color=cq.Color(*c))
    return a


def hall_reads(sensor_z, roll, z_bottom=-125.0):
    """What a chip at z = sensor_z reads over this pipe at this roll (from the drawn geometry): ring (tape under the chip) and point (magnet
    within the chip's window along Z and round)."""
    pos = pos_of_z(sensor_z, z_bottom)
    ang = ((roll + SENSOR_ANG - POINT_ANG + 540) % 360) - 180      # chip angle relative to the point magnet
    return {"ring": abs(pos - RING_CM) <= RING_W / 20.0, "point": abs(pos - POINT_CM) <= 0.5 and abs(ang) <= 6.0}


def _vol(a, b):
    i = a.intersect(b)
    return sum(s.Volume() for s in i.solids().vals()) if i.solids().vals() else 0.0


def check():
    import cart_sleeves as cs
    pipe = cq.Workplane("XY").add(cq.Solid.makeCylinder(co.R_PIPE, 250.0, cq.Vector(0, 0, -125), cq.Vector(0, 0, 1)))
    sp = sensor_parts()
    out = {}
    out["chip_gap_to_pipe_mm"] = FACE_R - co.R_PIPE
    out["chip_gap_to_tape_mm"] = FACE_R - (co.R_PIPE + TAPE_T)
    out["chip_gap_to_point_magnet_mm"] = FACE_R - (co.R_PIPE + POINT_T)
    out["joint_ring_gap_mm"] = FACE_R - (co.R_PIPE + co.PIPE_BUMP)
    out["chip_proud_of_bore_mm"] = hs.R_BORE - FACE_R
    # the sensor parts must not touch the pipe or the home station, and not any other part of the hand
    st = station()
    out["sensor_vs_pipe_mm3"] = sum(_vol(s, st["track_pipe"][0]) for n, (s, _) in sp.items() if n != "hall_cable")
    others = {n: s for n, (s, _) in cs.hand_parts().items() if not n.startswith("hall_")}
    hit = {}
    for n, (s, _) in sp.items():
        for m, o in others.items():
            v = _vol(s, o)
            if v > 1e-3:
                hit["%s vs %s" % (n, m)] = v
    out["hand_clashes_mm3"] = hit
    # the sleeve wall is intact round the pocket: radial wall left outside the pocket, and the pocket is inside the tube
    out["wall_left_mm"] = hs.TUBE_R_MIN - POCKET_R1
    # the ring and point read at the right places: the chip over the ring sees the ring at any roll, over the point at roll 0 only
    r1 = all(hall_reads(RING_CM * 10 - 125, rr)["ring"] for rr in range(0, 360, 30))
    r2 = hall_reads(POINT_CM * 10 - 125, 0)["point"] and not hall_reads(POINT_CM * 10 - 125, 90)["point"]
    out["reads_ok"] = bool(r1 and r2)
    out["ok"] = (out["chip_gap_to_pipe_mm"] > 2.0 and out["chip_gap_to_point_magnet_mm"] >= 1.5 and out["joint_ring_gap_mm"] >= 1.5 and out["sensor_vs_pipe_mm3"] < 1e-3
                 and not hit and out["wall_left_mm"] >= 3.0 and out["reads_ok"])
    return out


result = None
if __name__ == "__main__":
    r = check()
    for k, v in r.items():
        print(k, v)
    print("home station check:", "OK" if r["ok"] else "FAILS")
