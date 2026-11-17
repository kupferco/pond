# cad/cart_omni.py: the wheel parts of the Pond cart hand, v5 (OpenPocket #278, plan task 265 part 4, docs/plans/cart-roll-redesign-plan.md).
# One file owns every wheel number, so hand_sleeve.py, cart_sleeves.py and cart_wheel_pairs.py do not repeat them:
#   1. the 38 mm DRIVEN omni wheel (drive wheel and roll wheel): the printable rubber-roller wheel of cad/omni_wheel.py (#291), with
#      its envelope for interference checks;
#   2. the PASSIVE ball cup: a printed cup with a stainless or Delrin ball, a PVC-shaped face, a dirt lip and a drain hole;
#   3. the worm-motor placeholder with its shaft at a right angle, and place_drive / place_roll to put wheel and motor on a sleeve.
# Frames. Wheel frame: axle = Z, wheel centre at the origin. Cup frame: x = radial outward, ball centre at the origin, the pipe
# axis along Z through x = -(R_PIPE + ball radius). Motor frame: output shaft = Z at the origin, shaft goes -Z from the gearbox face,
# gearbox on z = 0 .. GB_T, motor body along +X. Hand frame: pipe along Z (see hand_sleeve.py).
# ASSUMED (every one marked ASSUMED, to be fixed by the bench test and the real parts): ball 11 mm, cup wall, lip and face gaps,
# 2 mm drain hole, motor 28 mm x 65 mm with a 22 mm gearbox, 6 mm D-shaft. Wheel size: 38 mm is the plan's choice; a common 48 or
# 58 mm size would change OMNI_R only (omni_wheel.py then needs its own OD), nothing else here.
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_wheel as ow

# ---------------- Pipe and wheel numbers (mm) ----------------
PIPE_D = 32.0                    # track pipe OD: standard PVC (owner answer Q1), thinnest standard pipe that does not sag
R_PIPE = PIPE_D / 2
OMNI_R = ow.OD / 2               # 19: driven omni wheel radius
OMNI_W = 2 * ow.HUB_HALF_T       # 18.8: its width along the axle (hub; the rollers stand 0.6 inside it)
OMNI_HUB_R = ow.HUB_R            # 16.5
OMNI_BORE_D = ow.BORE_D          # 6: motor D-shaft
OMNI_AXLE_R = R_PIPE + OMNI_R    # 35: wheel centre radius when the wheel touches the pipe
OMNI_REACH = OMNI_AXLE_R + OMNI_R     # 54: furthest wheel point from the pipe axis
OMNI_RATING_N = 20.0             # about 2 kg each: design preload. The bench test may go to 40 N (owner answer Q4)

# ---------------- Ball cup ----------------
BALL_D = 11.0                    # ASSUMED 10 to 12 mm; a parameter of ball_cup() so the sleeve can be drawn with either size
BALL_CLEAR = 0.15                # ASSUMED radial clearance of the ball in its printed seat
CUP_WALL = 3.5                   # ASSUMED wall round and behind the seat (printable in PETG or nylon)
FACE_GAP = 1.5                   # ASSUMED: the cup's pipe-shaped face stands this far off the pipe, so the ball stands proud by it
LIP_H = 0.8                      # ASSUMED: the dirt lip stands this far off the cup face towards the pipe
LIP_W = 2.2                      # ASSUMED lip ring width
LIP_BORE_ADD = 0.2               # lip bore = seat opening + this
DRAIN_D = 2.0                    # ASSUMED drain hole through the back of the cup
BALLS = {"stainless": (0.72, 0.74, 0.78, 1), "delrin": (0.93, 0.93, 0.9, 1)}   # AISI 304/316 (not chrome steel: it rusts) or acetal
SPRING_TRAVEL = 2.5              # same as hand_sleeve v4: slot travel of a sprung station
PIPE_BUMP = 1.5                  # joint rings stand this far proud of the tube (track_joint.py): the lip must clear them at rest


def ball_cup(ball_d=BALL_D, material="stainless"):
    """The passive ball roller in the cup frame (x radial outward, ball centre at the origin).
    Returns dict: cup, ball, ball_colour, plus numbers: centre_r (ball centre from the pipe axis), cup_r, back_x (cup back face),
    lip_gap_pipe (lip tip to pipe), lip_gap_ball (lip bore to ball), drain_x (hole axis start)."""
    rb = ball_d / 2
    c = R_PIPE + rb                                   # ball centre from the pipe axis
    seat_r = rb + BALL_CLEAR
    face_x = -(c - (R_PIPE + FACE_GAP))               # cup face at the middle: -(rb - FACE_GAP)
    cup_r = rb + CUP_WALL                             # cup outer radius
    back_x = seat_r + CUP_WALL                        # cup back face
    body = cq.Workplane("YZ").workplane(offset=face_x - 4.0).circle(cup_r).extrude(back_x - face_x + 4.0)
    # PVC-shaped (concave) face: a cylinder along Z round the pipe axis, FACE_GAP off the pipe
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(R_PIPE + FACE_GAP, 4 * cup_r, cq.Vector(-c, 0, -2 * cup_r), cq.Vector(0, 0, 1))))
    # dirt lip: a ring round the ball opening, its tip concentric with the pipe, standing LIP_H off the cup face
    seat_open = math.sqrt(seat_r ** 2 - face_x ** 2)  # radius of the seat circle on the face at the middle
    lip_in = seat_open + LIP_BORE_ADD
    lip_out = lip_in + LIP_W
    lip = cq.Workplane("YZ").workplane(offset=face_x - 3.0).circle(lip_out).circle(lip_in).extrude(3.0 + 2.0)
    lip = lip.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(R_PIPE + FACE_GAP - LIP_H, 4 * cup_r, cq.Vector(-c, 0, -2 * cup_r), cq.Vector(0, 0, 1))))
    body = body.union(lip)
    body = body.cut(cq.Workplane("XY").add(cq.Solid.makeSphere(seat_r)))                       # the seat
    body = body.cut(cq.Workplane("YZ").workplane(offset=face_x - 4.0).circle(lip_in).extrude(4.05))  # lip bore, up to the face
    body = body.cut(cq.Workplane("YZ").circle(DRAIN_D / 2).extrude(back_x + 1.0))               # drain: seat back to the cup back, radial
    ball = cq.Workplane("XY").add(cq.Solid.makeSphere(rb))
    # clearances (computed, asserted by hand_sleeve.py)
    lip_tip_x = -(c - (R_PIPE + FACE_GAP - LIP_H))    # x of the lip tip plane's lowest point
    ball_r_at_tip = math.sqrt(max(rb ** 2 - lip_tip_x ** 2, 0.0))
    ball_r_at_face = math.sqrt(rb ** 2 - face_x ** 2)
    return {"cup": body, "ball": ball, "ball_colour": BALLS[material], "centre_r": c, "cup_r": cup_r, "back_x": back_x,
            "face_x": face_x, "ball_r": rb, "seat_r": seat_r, "lip_in": lip_in, "lip_out": lip_out,
            "lip_gap_pipe": FACE_GAP - LIP_H, "lip_gap_ball": lip_in - ball_r_at_face, "seat_opening": seat_open,
            "stands_proud": FACE_GAP, "ball_retained": seat_open < rb}


# ---------------- Driven omni wheel ----------------
_OMNI = {}


def omni_parts():
    """Dict name -> (shape, colour) in the wheel frame (axle Z). Built once: hub halves, rollers with O-rings, pins and screws."""
    if not _OMNI:
        assy = ow.assembly("oring", with_pipe=False)
        groups = {"hub": ([], (0.20, 0.45, 0.70, 1)), "rollers": ([], (0.15, 0.15, 0.15, 1)),
                  "o_rings": ([], (0.85, 0.30, 0.10, 1)), "pins_screws": ([], (0.75, 0.75, 0.78, 1))}
        for ch in assy.children:
            n = ch.name
            key = "hub" if n.startswith("hub") else "rollers" if n.startswith("roller") else "o_rings" if n.startswith("oring") else "pins_screws"
            for o in (ch.obj.vals() if hasattr(ch.obj, "vals") else [ch.obj]):
                groups[key][0].append(o.moved(ch.loc) if ch.loc else o)
        for k, (shapes, col) in groups.items():
            _OMNI[k] = (cq.Workplane("XY").add(cq.Compound.makeCompound(shapes)), col)
    return dict(_OMNI)


def omni_envelope():
    """Solid cylinder R19 x OMNI_W (axle Z): the wheel for interference checks."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(OMNI_R, OMNI_W, cq.Vector(0, 0, -OMNI_W / 2), cq.Vector(0, 0, 1)))


# ---------------- Worm motor with the shaft at a right angle (placeholder) ----------------
MOTOR_R = 14.0                   # ASSUMED 28 mm diameter
MOTOR_L = 55.0                   # ASSUMED motor body length (the part list says real ones are 60 to 75 mm long with the gearbox)
GB_T = 22.0                      # ASSUMED gearbox thickness along the output shaft
GB_L = 30.0                      # ASSUMED gearbox length along the motor axis
SHAFT_D = OMNI_BORE_D            # 6 mm D-shaft


def motor():
    """Motor frame: shaft on Z through the origin (shaft goes -Z from the gearbox face at z = 0), gearbox z = 0..GB_T, motor body along +X."""
    gb = cq.Workplane("XY").box(GB_L, 2 * MOTOR_R, GB_T).translate((GB_L / 2 - MOTOR_R, 0, GB_T / 2))
    body = cq.Workplane("XY").add(cq.Solid.makeCylinder(MOTOR_R, MOTOR_L, cq.Vector(GB_L - MOTOR_R, 0, GB_T / 2), cq.Vector(1, 0, 0)))
    return {"gearbox": (gb, (0.85, 0.25, 0.25, 1)), "motor": (body, (0.85, 0.25, 0.25, 1))}


def _shaft(length):
    """Shaft from the gearbox face (z = 0) going -Z by `length`."""
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(SHAFT_D / 2, length, cq.Vector(0, 0, -length), cq.Vector(0, 0, 1)))


def _spin(shape, ang):
    return shape.rotate((0, 0, 0), (0, 0, 1), ang)


def place_drive(shape, z, ang=180.0, centre_r=OMNI_AXLE_R):
    """Put a WHEEL-frame shape (axle Z) on the sleeve as the DRIVE wheel: axle tangential (along Y at ang 0), rolling along the pipe.
    The wheel centre sits centre_r from the pipe axis at angle ang, row height z."""
    return _spin(shape.rotate((0, 0, 0), (1, 0, 0), -90).translate((centre_r, 0, z)), ang)


def place_roll(shape, z, ang=180.0, centre_r=OMNI_AXLE_R):
    """Put a WHEEL-frame shape on the sleeve as the ROLL wheel: axle along the pipe (Z), rolling round the pipe."""
    return _spin(shape.translate((centre_r, 0, z)), ang)


def drive_motor_parts(z, wall_y, ang=180.0, centre_r=OMNI_AXLE_R, shaft_to=-12.0):
    """Motor, gearbox and shaft of the drive wheel, on the +Y side of the wall face at y = wall_y (+ 1 mm gap). Dict name -> (shape, colour)."""
    out = {}
    for k, (s, col) in motor().items():
        out["drive_" + k] = (_spin(s.rotate((0, 0, 0), (1, 0, 0), -90).translate((centre_r, wall_y + 1.0, z)), ang), col)
    out["drive_shaft"] = (_spin(_shaft(wall_y + 1.0 - shaft_to).rotate((0, 0, 0), (1, 0, 0), -90).translate((centre_r, wall_y + 1.0, z)), ang),
                          (0.8, 0.8, 0.82, 1))
    return out


def roll_motor_parts(z, wall_z, ang=180.0, centre_r=OMNI_AXLE_R, shaft_to=None):
    """Motor, gearbox and shaft of the roll wheel, on the -Z side below the end face at z = wall_z (negative; + 1 mm gap)."""
    out = {}
    top = (z + OMNI_W / 2 + 3.0) if shaft_to is None else shaft_to
    for k, (s, col) in motor().items():
        out["roll_" + k] = (_spin(s.rotate((0, 0, 0), (1, 0, 0), 180).translate((centre_r, 0, wall_z - 1.0)), ang), col)
    out["roll_shaft"] = (_spin(_shaft(top - (wall_z - 1.0)).rotate((0, 0, 0), (1, 0, 0), 180).translate((centre_r, 0, wall_z - 1.0)), ang),
                         (0.8, 0.8, 0.82, 1))
    return out


if __name__ == "__main__":
    for mat in BALLS:
        n = ball_cup(BALL_D, mat)
        print("ball cup %s: ball %.1f mm, centre %.1f mm from the pipe axis, stands %.1f mm proud, lip %.1f mm off the pipe, lip %.2f mm off the ball, "
              "retained %s" % (mat, BALL_D, n["centre_r"], n["stands_proud"], n["lip_gap_pipe"], n["lip_gap_ball"], n["ball_retained"]))
    print("omni wheel %.0f mm x %.1f mm, reaches %.0f mm from the pipe axis" % (2 * OMNI_R, OMNI_W, OMNI_REACH))
