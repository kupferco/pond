import cadquery as cq
import math

PIPE_R = 8.0      # 16 mm track tube
SLEEVE_RI, SLEEVE_RO, SLEEVE_H = 22.0, 26.0, 80.0
WR, WW = 10.0, 6.0  # wheel radius, width

def pipe():
    return cq.Workplane("XY").circle(PIPE_R).extrude(300).translate((0, 0, -150))

def tube(ri, ro, h, z=0):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((0, 0, z - h / 2))

def wheel(omni=False):
    w = cq.Workplane("YZ").circle(WR).extrude(WW / 2, both=True)
    if omni:
        for i in range(10):
            t = 2 * math.pi * i / 10
            w = w.union(cq.Workplane("XY").sphere(2.2).translate((0, WR * math.cos(t), WR * math.sin(t))))
    return w

def drive_wheel(a_deg, z, omni):
    a = math.radians(a_deg)
    c = ((PIPE_R + WR) * math.cos(a), (PIPE_R + WR) * math.sin(a), z)
    return wheel(omni).rotate((0, 0, 0), (0, 0, 1), a_deg + 90).translate(c)

def roll_wheel(a_deg, z):
    a = math.radians(a_deg)
    c = ((PIPE_R + WR) * math.cos(a), (PIPE_R + WR) * math.sin(a), z)
    return wheel().rotate((0, 0, 0), (0, 1, 0), 90).translate(c)

asm = cq.Assembly()
grey, red, blue, green, gold = (cq.Color(0.7, 0.7, 0.72), cq.Color(0.85, 0.25, 0.2),
                                cq.Color(0.25, 0.45, 0.85), cq.Color(0.3, 0.7, 0.35), cq.Color(0.85, 0.7, 0.3))

# ---------- Option A: omni drive wheels + one roll wheel (at x = 0) ----------
A = (0, 0, 0)
asm.add(pipe().translate(A), name="A_pipe", color=grey)
asm.add(tube(SLEEVE_RI, SLEEVE_RO, SLEEVE_H).translate(A), name="A_sleeve", color=cq.Color(0.9, 0.9, 0.9, 0.35))
for i, ang in enumerate((0, 120, 240)):
    asm.add(drive_wheel(ang, 25, True).translate(A), name=f"A_omni_{i}", color=blue)
asm.add(roll_wheel(60, -25).translate(A), name="A_roll_wheel", color=red)
asm.add(cq.Workplane("XY").box(20, 20, 30).translate((36 * math.cos(math.radians(60)), 36 * math.sin(math.radians(60)), -25)).translate(A),
        name="A_roll_motor", color=red)
asm.add(cq.Workplane("XY").box(4, 80, 80).translate((-28, 0, 0)).translate(A), name="A_plate", color=gold)
asm.add(cq.Workplane("XY").box(40, 14, 14).translate((-50, 0, 20)).translate(A), name="A_arm_stub", color=green)

# ---------- Option B: fixed sleeve + slewing ring (at x = 220) ----------
B = (220, 0, 0)
asm.add(pipe().translate(B), name="B_pipe", color=grey)
asm.add(tube(SLEEVE_RI, SLEEVE_RO, SLEEVE_H).translate(B), name="B_sleeve", color=cq.Color(0.9, 0.9, 0.9, 0.35))
for i, ang in enumerate((0, 120, 240)):
    asm.add(drive_wheel(ang, 25, False).translate(B), name=f"B_drive_{i}", color=blue)
ring = tube(SLEEVE_RO, 40, 12)
for i in range(36):
    t = 360 * i / 36
    ring = ring.union(cq.Workplane("XY").box(4, 3, 12).translate((41.5, 0, 0)).rotate((0, 0, 0), (0, 0, 1), t))
asm.add(ring.translate(B), name="B_slew_ring", color=red)
asm.add(cq.Workplane("XY").circle(8).extrude(12).translate((0, 52, -6)).translate(B), name="B_pinion", color=red)
asm.add(cq.Workplane("XY").box(20, 20, 30).translate((0, 52, 22)).translate(B), name="B_ring_motor", color=red)
asm.add(cq.Workplane("XY").box(4, 80, 80).translate((-46, 0, 0)).translate(B), name="B_plate", color=gold)
asm.add(cq.Workplane("XY").box(40, 14, 14).translate((-68, 0, 20)).translate(B), name="B_arm_stub", color=green)

result = asm
