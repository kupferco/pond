# cad/cart_dims.py: the cart's shared layout numbers, in one place (Viber #66).
# cart_assembly.py (whole cart), cart_arm.py (arm on cart) and cart_sleeves.py import these, so the pipe
# spacing, plate size, battery, motors and arm position cannot drift apart between drawings.
# Frame: the hand_sleeve.py frame (pipes along Z, plate on the -Y side). Two parallel pipes, pipe B at
# x = -PIPE_SPACING/2 and pipe C at x = +PIPE_SPACING/2, one hand on each, plate running across (X).
# Everything below is ASSUMED unless a comment says otherwise.
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs

PIPE_SPACING = 280.0                    # ASSUMED: pipe B to pipe C, centre to centre (two neighbouring units)
HX = PIPE_SPACING / 2                   # each pipe's x offset from the cart centre line
PLATE_T = 6.0                           # ASSUMED
PLATE_MARGIN_NEG = 62.0                 # ASSUMED: plate beyond pipe B's axis on -X (as the 100 mm pad plate)
PLATE_MARGIN_POS = 38.0                 # ASSUMED: plate beyond pipe C's axis on +X
PLATE_X0 = -HX - PLATE_MARGIN_NEG
PLATE_X1 = HX + PLATE_MARGIN_POS
PLATE_ZH = (hs.SLEEVE_L + 22.0) / 2     # ASSUMED: half height, 11 mm margin beyond each sleeve end (112 mm)
PLATE_Y1 = hs.PAD_Y0                    # plate sits on the pads' outer (-Y) face
PLATE_Y0 = PLATE_Y1 - PLATE_T
RIM, BOSS_HX, BOSS_HZ, ARM_BLOCK_HX = 10.0, 18.0, 28.0, 42.0   # ASSUMED open-frame details
ARM_X = (PLATE_X0 + PLATE_X1) / 2       # ASSUMED: arm on the plate centre (x = -12)
ARM_Z = 0.0
BATT = (70.0, 50.0, 70.0)               # ASSUMED: X, Y (out from plate), Z
BATT_X = 70.0                           # ASSUMED: between the arm block and pipe C's boss
MOTOR_R, MOTOR_L = 14.0, 55.0           # ASSUMED worm-gear motor placeholder, 28 x 55 mm
MOTOR_DX = 24.0                         # ASSUMED: motor beside each pad, on +X of its pipe
PIPE_STUB_L = 330.0                     # ASSUMED: pipe stub length in the assembly
