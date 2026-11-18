"""Test 1: the cart on a single vertical pipe. Does it hold, and does it climb?

A parameterised MJCF generator. The render server runs `build(**params)` in its sandbox
and simulates the result; `run_sim(model="pipe_climb", params={...})`.

Model: a vertical steel pipe (capsule, fixed to the world). A cart body on a free joint
with three wheels pressing on the pipe: one driven wheel on the outside (-X), two spring
idlers at +/-60 deg on the inside. Wheels collide as spheres (robust contact) and are drawn
as cylinders. The driven wheel has a velocity actuator; idlers free-wheel on sprung radial
slides. Friction is a parameter: dry 0.8, wet 0.3.

Omni cart (OpenPocket #283, wheel="omni"): the driven wheel is the 38 mm rubber-roller omni wheel of the roll redesign (docs/plans/cart-roll-redesign-plan.md) and the two idlers are
printed ball cups. MuJoCo friction is isotropic per geom, so the omni wheel's contact is an explicit geom pair with two sliding coefficients: along the rolling direction (up the pipe) the
rubber's grip mu, across it (round the pipe, over the rollers) mu x omni_cross (0.02). The contact frame of a horizontal normal has tangent 1 horizontal and tangent 2 vertical (checked
in the control-ui MuJoCo build), so the pair's friction is "mu*cross mu". The idlers (balls) grip BALL_FRICTION only. The cart is the whole 3 kg cart.
The wet-pipe test is wet_test(): the cart on a wet vertical pipe with the wheel locked by the worm (drive_rpm 0, drive_torque_nm 5: a locked worm holds far more than the 0.3 N m the motor can drive), at 20 N (design), 40 N (test limit) and 60 N (the old wheels) preload.
`climb_m` in the runner summary (negative = height lost) says whether it holds.

Signals the runner logs: cart height (pos_z) and speed, contact normal force, drive torque
(force.drive), wheel slip (rim speed minus cart speed, from wheel_radius), spring travel
(q.spring_*). `climb_m` in the summary is the net height gained.
"""

from constants import (
    BALL_FRICTION, CART_MASS, DRIVE_RPM, DRIVE_WHEEL_ANGLE, FRICTION, GRAVITY, IDLER_WHEEL_ANGLES, OMNI_CART_MASS, OMNI_CROSS,
    BALL_R, OMNI_PRELOAD_N, OMNI_PRELOAD_TEST_N, OMNI_R, OMNI_W, PAYLOAD_MASS, PIPE_R, SPRING_K, SPRING_PRELOAD_N, SPRING_TRAVEL, WHEEL_R, WHEEL_W,
)
import math

PARAMS = {
    "wheel": ("plain", "plain = the old 20 mm wheel and two idler wheels; omni = 38 mm rubber-roller omni drive wheel (grip along the pipe, near zero across) with ball-cup idlers, 3 kg cart"),
    "omni_cross": (OMNI_CROSS, "omni wheel: friction across the rolling direction as a fraction of the grip along it"),
    "surface": ("dry", "dry or wet: picks the wheel/pipe friction coefficient"),
    "friction": (None, "override the friction coefficient directly (e.g. 0.5)"),
    "spring_preload_n": (None, "force each idler pushes into the pipe at rest, N (default 30 plain, 20 omni: the design value)"),
    "spring_k": (SPRING_K, "idler spring stiffness, N/m"),
    "cart_mass_kg": (None, "cart mass without payload, kg (default 0.6 plain, 3.0 omni: the whole cart)"),
    "payload_kg": (None, "extra mass carried, kg (default 0.4 plain, 0 omni)"),
    "drive_rpm": (DRIVE_RPM, "target wheel speed, rpm (positive = up)"),
    "drive_torque_nm": (0.3, "stall torque the drive can apply at the wheel, N m"),
    "pipe_len_m": (1.2, "length of the vertical pipe"),
    "start_height_m": (0.15, "cart centre height at t=0"),
    "wheel_r_m": (None, "drive wheel radius (default 10 mm plain, 19 mm omni)"),
    "timestep_s": (0.0005, "integrator step; small because contacts are stiff"),
}

TRACK_BODY = "cart"
CAMERAS = ["side", "track"]


def _default_omega(drive_rpm: float) -> float:
    return drive_rpm * 2 * math.pi / 60.0


def wet_test():
    """The wet-pipe test of the omni cart (plan section 6): parameter sets for run_sim, hold on a wet vertical pipe with the drive stalled, at the design, test and old preloads.

    Each case is a dict for run_sim(model="pipe_climb", params=case). The cart holds when `climb_m` in the summary stays about zero; it slides when it is clearly negative.
    """
    base = {"wheel": "omni", "surface": "wet", "drive_rpm": 0.0, "drive_torque_nm": 5.0, "start_height_m": 0.6}   # 5 N m: the worm gear locks the wheel, it holds more than the motor can drive (0.3 N m)
    cases = [dict(base, spring_preload_n=n) for n in (OMNI_PRELOAD_N, OMNI_PRELOAD_TEST_N, 60.0, 100.0, 140.0)]
    cases += [dict(base, surface="dry", spring_preload_n=n) for n in (OMNI_PRELOAD_N, 50.0)]
    return cases


DEFAULT_CONTROLS = {"drive": _default_omega(DRIVE_RPM)}


def build(**p) -> str:
    omni = p["wheel"] == "omni"
    mu = p["friction"] if p["friction"] is not None else FRICTION[p["surface"]]
    wheel_r = float(p["wheel_r_m"] if p["wheel_r_m"] is not None else (OMNI_R if omni else WHEEL_R))
    wheel_w = OMNI_W if omni else WHEEL_W
    preload = float(p["spring_preload_n"] if p["spring_preload_n"] is not None else (OMNI_PRELOAD_N if omni else SPRING_PRELOAD_N))
    idler_mu = BALL_FRICTION if omni else mu
    ring_r = PIPE_R + wheel_r  # wheel centre radius when touching the pipe
    pipe_len = float(p["pipe_len_m"])
    z0 = float(p["start_height_m"])
    omega = _default_omega(float(p["drive_rpm"]))
    cart_mass = float(p["cart_mass_kg"] if p["cart_mass_kg"] is not None else (OMNI_CART_MASS if omni else CART_MASS)) \
        + float(p["payload_kg"] if p["payload_kg"] is not None else (0.0 if omni else PAYLOAD_MASS))
    # Spring: zero-length at springref so the preload comes out right. The slide joint moves
    # the idler along its radial axis; negative = towards the pipe. With the idler sitting at
    # the touching radius, springref = -preload/k (it "wants" to be further in).
    k = float(p["spring_k"])
    springref = -preload / k
    travel = SPRING_TRAVEL

    wheels = []

    def wheel(name, angle_deg, driven):
        a = math.radians(angle_deg)
        r_wheel = wheel_r if driven or not omni else BALL_R   # idlers of the omni cart are ball cups
        rr = PIPE_R + r_wheel   # this wheel's centre radius when it touches the pipe
        cx, cy = rr * math.cos(a), rr * math.sin(a)
        radial = f"{math.cos(a):.6f} {math.sin(a):.6f} 0"
        # Hinge axis is the horizontal tangent. The sign is chosen so that a positive wheel
        # speed moves the cart UP the pipe (rolling without slip: v_cart = -omega x r_contact).
        sgn = -1.0 if driven else 1.0
        tangent = f"{sgn*-math.sin(a):.6f} {sgn*math.cos(a):.6f} 0"
        slide = "" if driven else (
            f'<joint name="spring_{name}" type="slide" axis="{radial}" range="{-travel:.5f} {travel:.5f}" '
            f'stiffness="{k:.1f}" springref="{springref:.6f}" damping="4" limited="true"/>'
        )
        # zaxis of the cylinder along the hinge (tangent) axis
        # the omni drive wheel collides only through the explicit anisotropic pair below (contype 2 / conaffinity 0 switches the default pipe contact off)
        anis = ' contype="2" conaffinity="0"' if (omni and driven) else ""
        w_mu = idler_mu if not driven else mu
        return f"""
      <body name="{name}" pos="{cx:.6f} {cy:.6f} 0">
        {slide}
        <joint name="wheel_{name}" type="hinge" axis="{tangent}" damping="0.0005"/>
        <geom name="{name}_col" type="sphere" size="{r_wheel:.5f}" mass="0.02" friction="{w_mu} 0.005 0.0001"{anis}
              rgba="0.15 0.15 0.15 1" condim="3" solref="0.005 1" solimp="0.95 0.99 0.001"/>
        <geom name="{name}_vis" type="cylinder" size="{r_wheel:.5f} {wheel_w/2:.5f}" zaxis="{tangent}"
              contype="0" conaffinity="0" mass="0" rgba="0.2 0.2 0.25 1"/>
      </body>"""

    wheels.append(wheel("drive", DRIVE_WHEEL_ANGLE, True))
    for i, ang in enumerate(IDLER_WHEEL_ANGLES):
        wheels.append(wheel(f"idler{i+1}", ang, False))
    wheels_xml = "".join(wheels)

    # Cart body visual: a C-shaped collar around the pipe (no collision with the pipe; the
    # wheels are the only contacts). Mass sits at the cart origin.
    collar_r = ring_r + wheel_r * 0.6
    collar_xml = "".join(
        f'<geom type="box" size="0.006 0.012 0.03" pos="{collar_r*math.cos(math.radians(a)):.5f} '
        f'{collar_r*math.sin(math.radians(a)):.5f} 0" euler="0 0 {a}" contype="0" conaffinity="0" '
        f'mass="0" rgba="0.85 0.85 0.9 1"/>'
        for a in (120, 150, 180, 210, 240, 90, -90, 60, -60)
    )

    # omni drive wheel: grip mu along the rolling direction (tangent 2, up the pipe), mu x cross across it (tangent 1, round the pipe)
    pair_xml = (f'<contact><pair geom1="drive_col" geom2="pipe" condim="3" friction="{mu * float(p["omni_cross"]):.6f} {mu} 0.005 0.0001 0.0001"/></contact>'
                if omni else "")
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
      <geom name="cart_mass" type="sphere" size="0.005" pos="{-ring_r*0.5:.5f} 0 0" mass="{cart_mass:.4f}"
            contype="0" conaffinity="0" rgba="1 0.4 0.2 1"/>
      {collar_xml}
      {wheels_xml}
    </body>
  </worldbody>
  {pair_xml}
  <actuator>
    <velocity name="drive" joint="wheel_drive" kv="1.0" ctrlrange="-{max(3*omega, 1.0):.3f} {max(3*omega, 1.0):.3f}"
              forcerange="-{p['drive_torque_nm']} {p['drive_torque_nm']}" ctrllimited="true" forcelimited="true"/>
  </actuator>
  <sensor>
    <framepos name="cart_pos" objtype="body" objname="cart"/>
    <framelinvel name="cart_vel" objtype="body" objname="cart"/>
    <actuatorfrc name="drive_torque" actuator="drive"/>
  </sensor>
</mujoco>"""
