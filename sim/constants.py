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
