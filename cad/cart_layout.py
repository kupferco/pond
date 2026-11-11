# cad/cart_layout.py: layout numbers shared by cart_assembly.py (drawing 1) and cart_base.py (drawing 2).
# One place for them, so the two drawings cannot drift apart. Frame: the hand_sleeve.py frame
# (track pipe along Z, mounting pads face -Y, the base sits on the -Y side of the pipe).
# Every value marked ASSUMED is undecided; change it here and both drawings follow.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_sleeve as hs   # pad position and M4 pattern come from here (not changed)

HAND_SPACING = 220.0                    # ASSUMED: centre-to-centre along the pipe
HAND_Z = HAND_SPACING / 2
PLATE_T = 6.0                           # ASSUMED
PLATE_W = 100.0                         # ASSUMED: X extent
PLATE_X0 = hs.PAD_X0 - 38.0             # ASSUMED: plate centred a little off the pads towards -X
PLATE_L = HAND_SPACING + hs.SLEEVE_L + 2 * 11.0   # ASSUMED: 332 mm, a margin beyond each sleeve
PLATE_Y1 = hs.PAD_Y0                    # plate sits on the pads' outer (-Y) face
PLATE_Y0 = PLATE_Y1 - PLATE_T
PLATE_CY = (PLATE_Y0 + PLATE_Y1) / 2
PAD_CX = (hs.PAD_X0 + hs.PAD_X1) / 2
BATT = (70.0, 50.0, 70.0)               # ASSUMED: X, Y (out from plate), Z (along pipe)
BATT_Z = -75.0                          # ASSUMED: clear of the centred arm base (z +/-35)
BATT_X = -27.0                          # ASSUMED: towards -X so the motors keep +X
MOTOR_R, MOTOR_L = 14.0, 55.0           # ASSUMED worm-gear motor placeholder
MOTOR_X = 24.0                          # ASSUMED: beside the pad, on +X of the plate
ARM_Z = 0.0                             # ASSUMED: arm base in the middle of the plate
ARM_X = PLATE_X0 + PLATE_W / 2          # ASSUMED: arm on the plate centre (x = -12)
# Frame cut-outs (ASSUMED)
RIM, BOSS_HW, BOSS_HL, ARM_BLOCK_HL = 10.0, 18.0, 28.0, 42.0
