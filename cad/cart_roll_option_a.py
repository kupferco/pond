import cadquery as cq
import math

PIPE_R = 8.0
WHEEL_R, WHEEL_W = 19.0, 12.0
HUB_R = 13.0
WC = PIPE_R + WHEEL_R
HOUSING_RI, HOUSING_RO, HOUSING_H = 50.0, 54.0, 130.0

# Build ONE omni wheel (hub + 8 tangential rollers), reuse it everywhere
hub = cq.Workplane("YZ").circle(HUB_R).extrude(WHEEL_W / 2, both=True)
rollers = None
for i in range(8):
    t = 45.0 * i
    r = (cq.Workplane("XY").circle(3.2).extrude(4.5, both=True)
         .rotate((0, 0, 0), (1, 0, 0), t)
         .translate((0, 15.8 * math.cos(math.radians(t)), 15.8 * math.sin(math.radians(t)))))
    rollers = r if rollers is None else rollers.add(r)
OMNI = hub.union(rollers.combine())

MOTOR = (cq.Workplane("XY").box(14, 22, 22).translate((WHEEL_W / 2 + 8, 0, 0))
         .union(cq.Workplane("XY").circle(8).extrude(24).translate((WHEEL_W / 2 + 8, 0, 11))))

def place_drive(obj, a_deg, z):
    a = math.radians(a_deg)
    return obj.rotate((0, 0, 0), (0, 0, 1), a_deg + 90).translate((WC * math.cos(a), WC * math.sin(a), z))

def place_roll(obj, a_deg, z):
    a = math.radians(a_deg)
    return (obj.rotate((0, 0, 0), (0, 1, 0), 90).rotate((0, 0, 0), (0, 0, 1), a_deg)
               .translate((WC * math.cos(a), WC * math.sin(a), z)))

grey = cq.Color(0.72, 0.72, 0.75); glass = cq.Color(0.85, 0.88, 0.92, 0.25)
blue = cq.Color(0.25, 0.45, 0.85); red = cq.Color(0.85, 0.25, 0.2)
dark = cq.Color(0.2, 0.2, 0.22); orange = cq.Color(0.95, 0.55, 0.15)
gold = cq.Color(0.85, 0.7, 0.3); green = cq.Color(0.3, 0.7, 0.35)

asm = cq.Assembly()
asm.add(cq.Workplane("XY").circle(PIPE_R).extrude(320).translate((0, 0, -160)), name="pipe", color=grey)
asm.add(cq.Workplane("XY").circle(HOUSING_RO).circle(HOUSING_RI).extrude(HOUSING_H).translate((0, 0, -HOUSING_H / 2)),
        name="sleeve_housing", color=glass)

for i, a in enumerate((90, 210, 330)):
    asm.add(place_drive(OMNI, a, 38), name=f"drive_top_{i}", color=blue)
    asm.add(place_drive(MOTOR, a, 38), name=f"drive_top_motor_{i}", color=dark)
for i, a in enumerate((210, 330)):
    asm.add(place_drive(OMNI, a, -38), name=f"drive_bot_{i}", color=blue)
    asm.add(place_drive(MOTOR, a, -38), name=f"drive_bot_motor_{i}", color=dark)
asm.add(place_roll(OMNI, 90, -38), name="roll_wheel", color=red)
asm.add(place_roll(MOTOR, 90, -38), name="roll_motor", color=dark)

asm.add(cq.Workplane("XY").box(16, 18, 18).translate((38, 0, 0)).rotate((0, 0, 0), (0, 0, 1), 150), name="brake_solenoid", color=orange)
asm.add(cq.Workplane("XY").box(20, 5, 5).translate((20, 0, 0)).rotate((0, 0, 0), (0, 0, 1), 150), name="brake_rod", color=grey)
asm.add(cq.Workplane("XY").box(4, 14, 14).translate((PIPE_R + 2, 0, 0)).rotate((0, 0, 0), (0, 0, 1), 150), name="brake_pad", color=dark)

asm.add(cq.Workplane("XY").box(4, 110, 130).translate((-(HOUSING_RO + 2), 0, 0)), name="cart_plate", color=gold)
asm.add(cq.Workplane("XY").box(50, 18, 18).translate((-(HOUSING_RO + 29), 0, 30)), name="arm_stub", color=green)

result = asm
