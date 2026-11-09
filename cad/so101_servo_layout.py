import cadquery as cq
# Simplified SO-101 follower arm showing where the six STS3215 servos sit.
# Servo body approx 45 x 24 x 35 mm. Arm links approx: base 60 tall, upper arm 115, forearm 135, wrist 60.
assy = cq.Assembly()
def add(o, n, c): assy.add(o, name=n, color=cq.Color(*c))
def box(sx, sy, sz, cx, cy, cz):
    return cq.Workplane("XY").box(sx, sy, sz).translate((cx, cy, cz))
def cyl(r, h, axis, c):
    d = {"x": (1,0,0), "y": (0,1,0), "z": (0,0,1)}[axis]
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*[c[i]-d[i]*h/2 for i in range(3)]), cq.Vector(*d)))
grey = (0.85, 0.85, 0.85, 1)
# base plate
add(box(120, 120, 8, 0, 0, 4), "base_plate", (0.3, 0.3, 0.3, 1))
# 1 base rotation servo (vertical axis)
add(box(45, 24, 35, 0, 0, 26), "servo1_base_rotation", (0.9, 0.2, 0.2, 1))
add(cyl(10, 8, "z", (0, 0, 48)), "joint1_turntable", (0.2, 0.2, 0.2, 1))
# shoulder bracket
add(box(50, 40, 30, 0, 0, 67), "shoulder_bracket", grey)
# 2 shoulder servo (pitch axis along Y)
S = (0, 0, 95)
add(box(45, 35, 24, S[0], S[1], S[2]), "servo2_shoulder", (1.0, 0.55, 0.1, 1))
add(cyl(8, 50, "y", S), "joint2_shoulder_axis", (0.2, 0.2, 0.2, 1))
# upper arm going up and forward
E = (40, 0, 200)
add(box(30, 20, 115, 20, 0, 147).rotate((20,0,147), (20,1,147), 20), "upper_arm", grey)
# 3 elbow servo
add(box(45, 35, 24, E[0], E[1], E[2]), "servo3_elbow", (0.95, 0.85, 0.1, 1))
add(cyl(8, 50, "y", E), "joint3_elbow_axis", (0.2, 0.2, 0.2, 1))
# forearm going forward
W = (175, 0, 200)
add(box(135, 20, 25, (E[0]+W[0])/2, 0, 200), "forearm", grey)
# 4 wrist flex servo (pitch)
add(box(24, 35, 45, W[0], W[1], W[2]), "servo4_wrist_flex", (0.2, 0.7, 0.3, 1))
add(cyl(8, 50, "y", W), "joint4_wrist_flex_axis", (0.2, 0.2, 0.2, 1))
# 5 wrist roll servo (roll axis along X)
R = (225, 0, 200)
add(box(35, 24, 45, R[0], R[1], R[2]), "servo5_wrist_roll", (0.2, 0.45, 0.95, 1))
add(cyl(10, 8, "x", (247, 0, 200)), "joint5_roll_disc", (0.2, 0.2, 0.2, 1))
# 6 gripper servo + jaws
G = (275, 0, 200)
add(box(45, 24, 35, G[0], G[1], G[2]), "servo6_gripper", (0.6, 0.25, 0.85, 1))
add(box(50, 8, 10, 320, 0, 212), "jaw_fixed", grey)
add(box(50, 8, 10, 320, 0, 186), "jaw_moving", grey)
result = assy
