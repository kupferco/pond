"""Test 1: the cart on a single vertical pipe. Does it hold, and does it climb?

A parameterised MJCF generator. The render server runs `build(**params)` in its sandbox
and simulates the result; `run_sim(model="pipe_climb", params={...})`.

Model: a vertical steel pipe (capsule, fixed to the world). A cart body on a free joint
with three wheel stations pressing on the pipe: one driven station on the outside (-X), two
spring idler stations at +/-60 deg on the inside. Wheels collide as spheres (robust contact)
and are drawn as cylinders. Friction is a parameter: dry 0.8, wet 0.3.

Wheel layouts:
- wheel_rows=1: one wheel per station (a single ring of three).
- wheel_rows=2, rocker=false: two wheels per station, row_spacing_mm apart, rigidly mounted
  (each wheel on its own spring, spring_preload_n split between them).
- wheel_rows=2, rocker=true: hand v6 style. Each station is a rocker that pivots about an
  axis parallel to the wheel axles and carries the two wheels; one spring per station with
  the full spring_preload_n. A free rocker shares load between its wheels but cannot resist
  a moment about its pivot.
The two drive wheels are coupled by a joint equality (the belt).

Note: sphere wheels give point contact, so sideways (axial-to-wheel) grip is probably
understated compared with a real rubber tyre's contact patch.

Signals the runner logs: cart height (pos_z) and speed, contact normal force, drive torque
(force.drive), wheel slip (rim speed minus cart speed, from wheel_radius), spring travel
(q.spring_*), rocker angle (q.rock_*), roll/pitch/yaw. `climb_m` is the net height gained.
"""

from constants import (
    CART_MASS, DRIVE_RPM, DRIVE_WHEEL_ANGLE, FRICTION, GRAVITY, IDLER_WHEEL_ANGLES, PAYLOAD_MASS,
    PIPE_R, SPRING_K, SPRING_PRELOAD_N, SPRING_TRAVEL, WHEEL_R, WHEEL_W,
)
import math

PARAMS = {
    "surface": ("dry", "dry or wet: picks the wheel/pipe friction coefficient"),
    "friction": (None, "override the friction coefficient directly (e.g. 0.5)"),
    "spring_preload_n": (SPRING_PRELOAD_N, "clamp force per idler station at rest, N"),
    "spring_k": (SPRING_K, "idler spring stiffness, N/m"),
    "cart_mass_kg": (CART_MASS, "cart mass without payload, kg"),
    "payload_kg": (PAYLOAD_MASS, "extra mass carried, kg"),
    "mass_offset_mm": (0.0, "sideways (tangential, +Y) offset of the cart's centre of mass, mm"),
    "wheel_rows": (1, "1 = single ring of 3 wheels; 2 = two wheels per station along the pipe"),
    "row_spacing_mm": (40.0, "axial distance between the two wheels of a station, mm (hand v6: 24)"),
    "rocker": (False, "wheel_rows=2 only: true = each wheel pair rocks on a pivot (hand v6)"),
    "rocker_range_deg": (20.0, "rocker travel each way, degrees"),
    "drive_rpm": (DRIVE_RPM, "target wheel speed, rpm (positive = up)"),
    "drive_torque_nm": (0.3, "stall torque the drive can apply at the wheel, N m"),
    "pipe_len_m": (1.2, "length of the vertical pipe"),
    "start_height_m": (0.15, "cart centre height at t=0"),
    "wheel_r_m": (WHEEL_R, "wheel radius"),
    "timestep_s": (0.0005, "integrator step; small because contacts are stiff"),
}

TRACK_BODY = "cart"
CAMERAS = ["side", "track"]


def _default_omega(drive_rpm: float) -> float:
    return drive_rpm * 2 * math.pi / 60.0


DEFAULT_CONTROLS = {"drive": _default_omega(DRIVE_RPM)}


def _truthy(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


def build(**p) -> str:
    mu = p["friction"] if p["friction"] is not None else FRICTION[p["surface"]]
    wheel_r = float(p["wheel_r_m"])
    ring_r = PIPE_R + wheel_r  # wheel centre radius when touching the pipe
    pipe_len = float(p["pipe_len_m"])
    z0 = float(p["start_height_m"])
    omega = _default_omega(float(p["drive_rpm"]))
    cart_mass = float(p["cart_mass_kg"]) + float(p["payload_kg"])
    offset_y = float(p["mass_offset_mm"]) / 1000.0
    rows = 2 if int(p["wheel_rows"]) >= 2 else 1
    rocker = rows == 2 and _truthy(p["rocker"])
    spacing = float(p["row_spacing_mm"]) / 1000.0
    rock_rng = float(p["rocker_range_deg"])
    k = float(p["spring_k"])
    preload = float(p["spring_preload_n"])
    travel = SPRING_TRAVEL

    def wheel_geoms(name, tangent):
        return f"""
          <joint name="wheel_{name}" type="hinge" axis="{tangent}" damping="0.0005"/>
          <geom name="{name}_col" type="sphere" size="{wheel_r:.5f}" mass="0.02" friction="{mu} 0.005 0.0001"
                rgba="0.15 0.15 0.15 1" condim="3" solref="0.005 1" solimp="0.95 0.99 0.001"/>
          <geom name="{name}_vis" type="cylinder" size="{wheel_r:.5f} {WHEEL_W/2:.5f}" zaxis="{tangent}"
                contype="0" conaffinity="0" mass="0" rgba="0.2 0.2 0.25 1"/>"""

    def spring(name, radial, load):
        ref = -load / k
        return (f'<joint name="spring_{name}" type="slide" axis="{radial}" range="{-travel:.5f} {travel:.5f}" '
                f'stiffness="{k:.1f}" springref="{ref:.6f}" damping="4" limited="true"/>')

    def station(name, angle_deg, driven):
        a = math.radians(angle_deg)
        cx, cy = ring_r * math.cos(a), ring_r * math.sin(a)
        radial = f"{math.cos(a):.6f} {math.sin(a):.6f} 0"
        # Hinge axis is the horizontal tangent. The sign is chosen so that a positive wheel
        # speed moves the cart UP the pipe (rolling without slip: v_cart = -omega x r_contact).
        sgn = -1.0 if driven else 1.0
        tangent = f"{sgn*-math.sin(a):.6f} {sgn*math.cos(a):.6f} 0"
        if rows == 1:
            sp = "" if driven else spring(name, radial, preload)
            return f"""
      <body name="{name}" pos="{cx:.6f} {cy:.6f} 0">
        {sp}{wheel_geoms(name, tangent)}
      </body>"""
        if not rocker:
            out = ""
            for z, sfx in ((spacing / 2, ""), (-spacing / 2, "2")):
                sp = "" if driven else spring(name + sfx, radial, preload / 2)
                out += f"""
      <body name="{name}{sfx}" pos="{cx:.6f} {cy:.6f} {z:.5f}">
        {sp}{wheel_geoms(name + sfx, tangent)}
      </body>"""
            return out
        # Rocker: one sprung carrier per station, pivoting about the axle direction.
        sp = "" if driven else spring(name, radial, preload)
        return f"""
      <body name="{name}_rk" pos="{cx:.6f} {cy:.6f} 0">
        {sp}
        <joint name="rock_{name}" type="hinge" axis="{tangent}" range="{-rock_rng} {rock_rng}" limited="true" damping="0.002"/>
        <geom type="box" size="0.003 0.003 {spacing/2:.5f}" mass="0.01" contype="0" conaffinity="0" rgba="0.6 0.6 0.65 1"/>
        <body name="{name}" pos="0 0 {spacing/2:.5f}">{wheel_geoms(name, tangent)}
        </body>
        <body name="{name}2" pos="0 0 {-spacing/2:.5f}">{wheel_geoms(name + "2", tangent)}
        </body>
      </body>"""

    wheels_xml = station("drive", DRIVE_WHEEL_ANGLE, True)
    for i, ang in enumerate(IDLER_WHEEL_ANGLES):
        wheels_xml += station(f"idler{i+1}", ang, False)

    equality_xml = (
        '<equality><joint joint1="wheel_drive2" joint2="wheel_drive" polycoef="0 1 0 0 0"/></equality>'
        if rows == 2 else ""
    )

    collar_r = ring_r + wheel_r * 0.6
    collar_h = 0.03 if rows == 1 else max(0.03, spacing / 2 + 0.015)
    collar_xml = "".join(
        f'<geom type="box" size="0.006 0.012 {collar_h:.4f}" pos="{collar_r*math.cos(math.radians(a)):.5f} '
        f'{collar_r*math.sin(math.radians(a)):.5f} 0" euler="0 0 {a}" contype="0" conaffinity="0" '
        f'mass="0" rgba="0.85 0.85 0.9 1"/>'
        for a in (120, 150, 180, 210, 240, 90, -90, 60, -60)
    )

    return f"""<mujoco model="pipe_climb">
  <option timestep="{p['timestep_s']}" gravity="0 0 -{GRAVITY}" integrator="implicitfast"/>
  <visual><global offwidth="960" offheight="720"/><headlight ambient="0.4 0.4 0.4" diffuse="0.6 0.6 0.6"/></visual>
  <custom>
    <numeric name="wheel_radius" data="{wheel_r:.6f}"/>
    <numeric name="friction" data="{mu}"/>
  </custom>
  <worldbody>
    <light pos="0.5 -0.5 2" dir="-0.3 0.3 -1"/>
    <geom name="floor" type="plane" size="1 1 0.1" rgba="0.3 0.32 0.35 1"/>
    <geom name="pipe" type="capsule" fromto="0 0 0 0 0 {pipe_len:.4f}" size="{PIPE_R:.5f}"
          friction="{mu} 0.005 0.0001" rgba="0.55 0.57 0.6 1"/>
    <camera name="side" pos="0.45 -0.45 {z0+0.1:.3f}" xyaxes="0.707 0.707 0 0 0 1" fovy="35"/>
    <camera name="top" pos="0 0 {pipe_len+0.4:.3f}" xyaxes="1 0 0 0 1 0" fovy="45"/>
    <body name="cart" pos="0 0 {z0:.4f}">
      <freejoint name="cart_free"/>
      <geom name="cart_mass" type="sphere" size="0.005" pos="{-ring_r*0.5:.5f} {offset_y:.5f} 0" mass="{cart_mass:.4f}"
            contype="0" conaffinity="0" rgba="1 0.4 0.2 1"/>
      {collar_xml}
      {wheels_xml}
    </body>
  </worldbody>
  {equality_xml}
  <actuator>
    <velocity name="drive" joint="wheel_drive" kv="1.0" ctrlrange="-{max(3*omega, 1.0):.3f} {max(3*omega, 1.0):.3f}"
              forcerange="-{p['drive_torque_nm']} {p['drive_torque_nm']}" ctrllimited="true" forcelimited="true"/>
  </actuator>
  <sensor>
    <framepos name="cart_pos" objtype="body" objname="cart"/>
    <framelinvel name="cart_vel" objtype="body" objname="cart"/>
    <actuatorfrc name="drive_torque" actuator="drive"/>
    <framexaxis name="cart_xaxis" objtype="body" objname="cart"/>
    <framezaxis name="cart_zaxis" objtype="body" objname="cart"/>
  </sensor>
</mujoco>"""
