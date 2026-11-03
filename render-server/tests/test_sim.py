"""MuJoCo sim runner, the sim model source, the pipe-climb model, and the MCP tools."""

import csv
import json
import math
from pathlib import Path

import pytest

from mcp import types

from pond_render.sandbox.host import run_sim_job
from pond_render.sim_models import SimModelSource, describe_source
from tests.conftest import API_TOKEN
from tests.fake_github import FakeGitHub
from tests.mcp_helpers import call_tool, list_tools

SIM_DIR = Path(__file__).resolve().parents[2] / "sim"

BALL = """<mujoco><option gravity="0 0 -9.81" timestep="0.002"/><worldbody><light pos="0 0 3"/>
<geom name="floor" type="plane" size="1 1 .1"/>
<body name="ball" pos="0 0 .5"><freejoint/><geom type="sphere" size=".05" rgba="1 0 0 1"/></body>
<camera name="cam" pos="1 -1 .6" xyaxes="1 1 0 0 0 1"/></worldbody></mujoco>"""


def _texts(result):
    return [c.text for c in result.content if isinstance(c, types.TextContent)]


def _images(result):
    return [c for c in result.content if isinstance(c, types.ImageContent)]


# ---------------------------------------------------------------- runner


def test_ball_drop_runner(tmp_path):
    r = run_sim_job(out_dir=tmp_path, mjcf=BALL, duration_s=1.0, cameras=["cam", "track", "free"], record=True, frames=4)
    assert r.ok, r.error
    assert {"model.xml", "signals.csv", "sheet_cam.png", "sheet_track.png", "sheet_free.png", "clip_cam.mp4"} <= set(r.files)
    assert all(p.stat().st_size > 0 for p in r.files.values())
    s = r.summary
    assert s["track_body"] == "ball"
    assert s["start_pos"][2] == pytest.approx(0.5, abs=1e-3)  # logged after mj_forward, not zeros
    assert s["end_pos"][2] == pytest.approx(0.05, abs=0.01)  # resting on the floor
    assert s["climb_m"] < -0.4 and s["max_contacts"] >= 1
    assert s["signals"]["contact_normal_N"]["max"] > 0
    header = r.files["signals.csv"].read_text().splitlines()[0]
    assert header.startswith("t,pos_x,pos_y,pos_z,vel_x,vel_y,vel_z,speed,contacts,contact_normal_N")


def test_attitude_counts_full_turns_from_start(tmp_path):
    spinner = """<mujoco><option gravity="0 0 0" timestep="0.002"/><worldbody>
    <body name="spinner" euler="0 0 45"><joint name="hinge" type="hinge" axis="0 0 1"/>
    <geom type="box" size=".1 .02 .02" mass="1"/></body></worldbody>
    <actuator><motor name="spin" joint="hinge"/></actuator></mujoco>"""
    r = run_sim_job(out_dir=tmp_path, mjcf=spinner, duration_s=2.0, controls={"spin": 0.05}, cameras=["free"])
    assert r.ok, r.error
    rows = list(csv.DictReader(r.files["signals.csv"].read_text().splitlines()))
    assert float(rows[0]["yaw_deg"]) == pytest.approx(0, abs=1e-6)  # measured from the start, not from the world axes
    yaw = [float(x["yaw_deg"]) for x in rows]
    assert yaw == sorted(yaw) and yaw[-1] > 360  # keeps counting through each full turn
    for row in rows:
        one_step = math.degrees(abs(float(row["qd.hinge"])) * 0.002)  # body poses lag joint values by a step
        assert float(row["yaw_deg"]) == pytest.approx(math.degrees(float(row["q.hinge"])), abs=one_step + 0.01)
        assert float(row["roll_deg"]) == pytest.approx(0, abs=0.01)
        assert float(row["pitch_deg"]) == pytest.approx(0, abs=0.01)


def test_runner_refuses_files_and_includes(tmp_path):
    for xml in ['<mujoco><asset><mesh file="/etc/passwd"/></asset></mujoco>',
                '<mujoco><include file="x.xml"/></mujoco>',
                '<mujoco><compiler meshdir="/"/></mujoco>']:
        r = run_sim_job(out_dir=tmp_path / str(abs(hash(xml))), mjcf=xml, duration_s=0.1)
        assert not r.ok and "not allowed" in r.error


def test_runner_reports_bad_names(tmp_path):
    r = run_sim_job(out_dir=tmp_path / "a", mjcf=BALL, duration_s=0.1, controls={"nope": 1.0})
    assert not r.ok and "No actuator named 'nope'" in r.error
    r = run_sim_job(out_dir=tmp_path / "b", mjcf=BALL, duration_s=0.1, cameras=["nope"])
    assert not r.ok and "No camera named 'nope'" in r.error
    r = run_sim_job(out_dir=tmp_path / "c", mjcf=BALL, duration_s=0.1, track_body="nope")
    assert not r.ok and "No body named 'nope'" in r.error


def test_generator_import_guard(tmp_path):
    gen = "import os\nPARAMS = {}\ndef build(**p):\n    return '<mujoco/>'\n"
    r = run_sim_job(out_dir=tmp_path, generator=gen, duration_s=0.1)
    assert not r.ok and "not allowed" in r.error and "os" in r.error


def test_generator_unknown_param(tmp_path):
    gen = "PARAMS = {'a': (1, 'x')}\ndef build(**p):\n    return '<mujoco/>'\n"
    r = run_sim_job(out_dir=tmp_path, generator=gen, params={"b": 2}, duration_s=0.1)
    assert not r.ok and "Unknown params ['b']" in r.error


# ---------------------------------------------------------------- model source


def test_local_model_source_lists_and_loads():
    src = SimModelSource(None, SIM_DIR)
    infos = src.list()
    names = [i.name for i in infos]
    assert "pipe_climb" in names and "constants" not in names
    pc = next(i for i in infos if i.name == "pipe_climb")
    assert pc.params["surface"]["default"] == "dry" and "friction" in pc.params["surface"]["help"]
    assert pc.doc.startswith("Test 1")
    m = src.load("pipe_climb")
    assert "def build(" in m.source and "constants" in m.support
    with pytest.raises(FileNotFoundError):
        src.load("nope")
    with pytest.raises(ValueError):
        src.load("../etc")


def test_github_model_source_prefers_drafts():
    fake = FakeGitHub()
    fake.branches["main"]["sim/constants.py"] = b"X = 1\n"
    fake.branches["main"]["sim/demo.py"] = b'"""Demo on main."""\nPARAMS = {"a": (1, "one")}\ndef build(**p):\n    return "<mujoco/>"\n'
    gh = fake.client()
    gh.write_file("sim/demo.py", '"""Demo on drafts."""\nPARAMS = {"a": (2, "two")}\ndef build(**p):\n    return "<mujoco/>"\n', "draft")
    src = SimModelSource(gh, None)
    infos = src.list()
    assert [i.name for i in infos] == ["demo"] and infos[0].doc == "Demo on drafts." and infos[0].params["a"]["default"] == 2
    m = src.load("demo")
    assert "drafts" in m.source and m.support["constants"] == "X = 1\n" and m.origin == "github:claude/drafts"


def test_describe_source_static():
    doc, params = describe_source('"""Hi there.\n\nMore."""\nfrom constants import K\nPARAMS = {"k": (K, "uses a constant"), "n": 3}\n')
    assert doc == "Hi there." and params["k"] == {"default": "K", "help": "uses a constant"} and params["n"]["default"] == 3


# ---------------------------------------------------------------- the pipe-climb model (test 1)


def _climb(tmp_path, **params):
    src = SimModelSource(None, SIM_DIR)
    m = src.load("pipe_climb")
    r = run_sim_job(out_dir=tmp_path, generator=m.source, support=m.support, params=params, duration_s=2.0, frames=3)
    assert r.ok, r.error
    return r.summary


def test_pipe_climb_dry_climbs(tmp_path):
    s = _climb(tmp_path)
    assert s["climb_m"] > 0.02, s["climb_m"]
    assert s["signals"]["vel_z"]["final"] > 0
    assert s["max_contacts"] >= 3 and s["wheel_radius_m"] == pytest.approx(0.01)
    assert "slip.wheel_drive" in s["signals"] and "q.spring_idler1" in s["signals"]
    assert "sensor.cart_pos[2]" in s["signals"]
    assert abs(s["signals"]["yaw_deg"]["final"]) < 90, s["signals"]["yaw_deg"]  # still on the pipe, not spun round


def test_pipe_climb_wet_slides(tmp_path):
    s = _climb(tmp_path, surface="wet")
    assert s["climb_m"] < 0, s["climb_m"]


def test_pipe_climb_more_preload_holds_wet(tmp_path):
    s = _climb(tmp_path, surface="wet", spring_preload_n=60)
    assert s["climb_m"] > 0, s["climb_m"]


# ---------------------------------------------------------------- MCP tools


def test_sim_tools_listed(token_server):
    names = {t.name for t in list_tools(token_server.mcp_url, API_TOKEN).tools}
    assert {"run_sim", "get_sim", "list_models"} <= names


def test_list_models_tool(token_server):
    out = json.loads(_texts(call_tool(token_server.mcp_url, API_TOKEN, "list_models", {}))[0])
    assert any(m["name"] == "pipe_climb" and "surface" in m["params"] for m in out)


def test_run_sim_model_and_get_sim(token_server):
    url = token_server.mcp_url
    result = call_tool(url, API_TOKEN, "run_sim", {"model": "pipe_climb", "params": {"surface": "dry"}, "duration_s": 1.0,
                                                   "frames": 3, "title": "climb test"})
    assert not result.is_error, result
    images = _images(result)
    assert len(images) == 2 and all(i.mime_type == "image/png" for i in images)  # side + track cameras
    summary = json.loads(_texts(result)[0])
    assert summary["kind"] == "sim" and summary["model"] == "pipe_climb" and summary["params"]["surface"] == "dry"
    assert summary["sim"]["climb_m"] is not None and "signals" in summary["sim"]
    assert {"model.xml", "signals.csv", "sheet_side.png", "sheet_track.png"} <= set(summary["files"])
    assert summary["views"] == ["side", "track"]

    again = call_tool(url, API_TOKEN, "get_sim", {"sim_id": summary["id"]})
    s2 = json.loads(_texts(again)[0])
    assert s2["id"] == summary["id"] and s2["sim"]["climb_m"] == summary["sim"]["climb_m"]
    assert len(_images(again)) == 2
    assert "No simulation" in _texts(call_tool(url, API_TOKEN, "get_sim", {"sim_id": "nope"}))[0]

    listed = json.loads(_texts(call_tool(url, API_TOKEN, "list_renders", {"limit": 5}))[0])
    assert any(r["id"] == summary["id"] and r["kind"] == "sim" for r in listed)


def test_run_sim_raw_mjcf_and_errors(token_server):
    url = token_server.mcp_url
    result = call_tool(url, API_TOKEN, "run_sim", {"mjcf_xml": BALL, "duration_s": 0.5, "cameras": ["cam"], "record": True})
    summary = json.loads(_texts(result)[0])
    assert summary["sim"]["climb_m"] < -0.3 and "clip_cam.mp4" in summary["files"] and "input.xml" in summary["files"]
    assert len(_images(result)) == 1

    assert _texts(call_tool(url, API_TOKEN, "run_sim", {}))[0].startswith("SIM FAILED")
    assert _texts(call_tool(url, API_TOKEN, "run_sim", {"model": "nope"}))[0].startswith("SIM FAILED: no sim model")
    bad = _texts(call_tool(url, API_TOKEN, "run_sim", {"model": "pipe_climb", "params": {"bogus": 1}, "duration_s": 0.2}))[0]
    assert bad.startswith("SIM FAILED") and "Unknown params" in bad


def test_run_sim_duration_is_capped(tmp_path, token_server):
    result = call_tool(token_server.mcp_url, API_TOKEN, "run_sim", {"mjcf_xml": BALL, "duration_s": 999, "frames": 2})
    summary = json.loads(_texts(result)[0])
    assert summary["sim"]["sim_time_s"] <= 30.0 + 0.01
