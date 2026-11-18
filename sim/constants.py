"""Shared physical constants for the Pond sim models (SI units: metres, kilograms, seconds).

The CAD scripts in /cad work in millimetres and keep their own copies of the geometry
numbers, because render_cad scripts cannot import repo modules inside the sandbox. Keep
the two in step by hand: the names below match the CAD constants with the unit changed.
"""

MM = 0.001  # millimetres to metres

# Track pipe (matches cad/hand_sleeve.py PIPE_D)
PIPE_D = 32 * MM
PIPE_R = PIPE_D / 2

# Wheels (matches cad/hand_sleeve.py WHEEL_D / WHEEL_W)
WHEEL_D = 20 * MM
WHEEL_R = WHEEL_D / 2
WHEEL_W = 8 * MM

# Wheel layout around the pipe, degrees from +X (matches OUTER_WHEEL_ANG / INNER_WHEEL_ANGS)
DRIVE_WHEEL_ANGLE = 180.0
IDLER_WHEEL_ANGLES = (60.0, -60.0)

# Cart body
CART_MASS = 0.6  # kg, sleeve + motor + electronics, without payload
PAYLOAD_MASS = 0.4  # kg, what the arm is rated to hold

# Drive: N20 gear motor, 12 V STS3215-class torque numbers are for the arm, not the wheel.
DRIVE_RPM = 60.0

# Surface friction coefficients (wheel rubber on painted steel pipe, rough values)
FRICTION = {"dry": 0.8, "wet": 0.3}

# Spring idlers
SPRING_PRELOAD_N = 30.0  # force each idler pushes into the pipe at rest (15 N could not hold 1 kg in sim)
SPRING_K = 2000.0  # N/m
SPRING_TRAVEL = 2.5 * MM  # radial slot travel (matches cad SPRING_TRAVEL)

GRAVITY = 9.81


# ---- Omni cart (OpenPocket #283, docs/plans/cart-roll-redesign-plan.md): 38 mm rubber-roller omni wheels, printed ball cups, whole cart 3 kg ----
# The old wheel numbers above stay for bend_test.py and guide_test.py (they still model the hinge-era 20 x 8 wheels); pipe_climb.py and unit_change.py use these.
OMNI_R = 19 * MM  # driven omni wheel radius (cad/cart_omni.py OMNI_D = 38)
OMNI_W = 18.8 * MM  # double-row omni wheel width (cad/cart_omni.py OMNI_W)
OMNI_CROSS = 0.02  # friction across the roller axis as a fraction of the grip along the rolling direction (cart/omni.ts omniContact)
OMNI_CART_MASS = 3.0  # kg, the whole cart with arm and battery (plan section 3)
OMNI_RATING_N = 20.0  # a 38 mm omni wheel is rated 2 kg (about 20 N)
OMNI_PRELOAD_N = 20.0  # design preload on the driven wheel (owner answer Q4); bench tests go to 40 N, never the 60 N of the old wheels
OMNI_PRELOAD_TEST_N = 40.0
BALL_R = 5.5 * MM  # 11 mm ball (cad/cart_omni.py BALL_D)
BALL_FRICTION = 0.05  # a printed cup with a steel or Delrin ball: rolls both ways, grips almost nothing
JAW_A1_DEG = 110.0  # the jaw wedge as drawn (cad/cart_sleeves.py JAW_A1); the transfer needs at least 140 (control-ui/scripts/search-swing.ts), 150 proposed
JAW_A1_PROPOSED_DEG = 150.0
SWING_DEG = 90.0  # roll of the whole cart about the riding pipe in a transfer (control-ui TRANSFER_ROLL_DEG), plate side
PIPE_SPACING = 120 * MM  # the two hands (cad/cart_dims.py PIPE_SPACING)
SLEEVE_BORE_R = 20 * MM  # hand_sleeve.py R_BORE
SLEEVE_OUT_R = 34.5 * MM  # hand_sleeve.py TUBE_R_MIN
