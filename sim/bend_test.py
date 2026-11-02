"""Bend test: can a two-row hand drive round a loop corner?

Gravity off (pure geometry and drive). Pipe: straight along +x, then a 90 deg bend of
centreline radius bend_r_mm turning toward +y, then straight along +y. The bend is built
from short capsule chords (3 deg each). One hand on a free joint, pipe along its local x,
two rings of three wheels row_spacing_mm apart. Drive wheels sit on the OUTSIDE of the
bend (-y), sprung idlers at +/-60 deg toward the inside, as on the loop corners.

Pass = the hand reaches the far straight (pos_y > bend_r) without jamming.
Watch q.spring_* (how far the idlers are pushed) and contacts (wheels lifting).
"""

from constants import FRICTION, PIPE_R, SPRING_K, SPRING_PRELOAD_N, SPRING_TRAVEL, WHEEL_R, WHEEL_W, DRIVE_RPM
import math

PARAMS = {
    "row_spacing_mm": (40.0, "axial distance between the two rings, mm"),
    "bend_r_mm": (150.0, "bend centreline radius, mm (loop corners: 150)"),
    "surface": ("dry", "dry or wet"),
    "travel_mm": (SPRING_TRAVEL * 1000, "idler slot travel each way, mm (hard stop)"),
    "timestep_s": (0.0005, "integrator step"),
}
TRACK_BODY = "hand"
CAMERAS = ["top"]
OMEGA = DRIVE_RPM * 2 * math.pi / 60.0
DEFAULT_CONTROLS = {"drive": OMEGA}


def build(**p) -> str:
    mu = FRICTION[p["surface"]]
    L = float(p["row_spacing_mm"]) / 1000
    R = float(p["bend_r_mm"]) / 1000
    travel = float(p["travel_mm"]) / 1000
    k = SPRING_K
    preload = SPRING_PRELOAD_N / 2
    ring = PIPE_R + WHEEL_R
    pipe = f'size="{PIPE_R}" friction="{mu} 0.005 0.0001" rgba="0.55 0.57 0.6 1"'
    g = [f'<geom type="capsule" fromto="-0.25 0 0 0 0 0" {pipe}/>']
    n = 30
    pts = [(R * math.sin(math.radians(90 * i / n)), R - R * math.cos(math.radians(90 * i / n))) for i in range(n + 1)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        g.append(f'<geom type="capsule" fromto="{x1:.5f} {y1:.5f} 0 {x2:.5f} {y2:.5f} 0" {pipe}/>')
    g.append(f'<geom type="capsule" fromto="{R:.4f} {R:.4f} 0 {R:.4f} {R+0.25:.4f} 0" {pipe}/>')

    wheels, drives = "", []
    for r, x in enumerate((L / 2, -L / 2)):
        for nm, ang, driven in (("drive", 180.0, True), ("idler1", 60.0, False), ("idler2", -60.0, False)):
            a = math.radians(ang)
            radial = (0.0, math.cos(a), math.sin(a))
            s = -1.0 if driven else 1.0
            tan = f"0 {s*-math.sin(a):.6f} {s*math.cos(a):.6f}"
            name = f"{nm}{r}"
            sp = "" if driven else (
                f'<joint name="spring_{name}" type="slide" axis="0 {radial[1]:.6f} {radial[2]:.6f}" '
                f'range="{-travel:.5f} {travel:.5f}" limited="true" stiffness="{k}" '
                f'springref="{-preload/k:.6f}" damping="4" solreflimit="0.002 1"/>')
            if driven:
                drives.append(f"wheel_{name}")
            wheels += f"""
      <body name="{name}" pos="{x:.4f} {ring*radial[1]:.6f} {ring*radial[2]:.6f}">
        {sp}
        <joint name="wheel_{name}" type="hinge" axis="{tan}" damping="0.0005"/>
        <geom type="sphere" size="{WHEEL_R}" mass="0.02" friction="{mu} 0.005 0.0001" condim="3"
              solref="0.005 1" solimp="0.95 0.99 0.001" rgba="0.15 0.15 0.15 1"/>
        <geom type="cylinder" size="{WHEEL_R} {WHEEL_W/2}" zaxis="{tan}" contype="0" conaffinity="0" mass="0" rgba="0.2 0.2 0.25 1"/>
      </body>"""

    return f"""<mujoco model="bend_test">
  <option timestep="{p['timestep_s']}" gravity="0 0 0" integrator="implicitfast"/>
  <visual><global offwidth="960" offheight="720"/><headlight ambient="0.5 0.5 0.5" diffuse="0.5 0.5 0.5"/></visual>
  <custom><numeric name="wheel_radius" data="{WHEEL_R}"/></custom>
  <worldbody>
    <light pos="0 0 2" dir="0 0 -1"/>
    {''.join(g)}
    <camera name="top" pos="0.05 0.12 0.9" xyaxes="1 0 0 0 1 0" fovy="40"/>
    <body name="hand" pos="-0.12 0 0">
      <freejoint/>
      <geom type="box" size="{L/2+0.012:.4f} 0.004 0.004" pos="0 0 {ring+0.012:.4f}" mass="0.6" contype="0" conaffinity="0" rgba="0.2 0.45 0.85 1"/>
      {wheels}
    </body>
  </worldbody>
  <equality><joint joint1="{drives[1]}" joint2="{drives[0]}" polycoef="0 1 0 0 0"/></equality>
  <actuator>
    <velocity name="drive" joint="{drives[0]}" kv="1.0" ctrlrange="-20 20" forcerange="-0.3 0.3" ctrllimited="true" forcelimited="true"/>
  </actuator>
  <sensor>
    <framepos name="hand_pos" objtype="body" objname="hand"/>
  </sensor>
</mujoco>"""
