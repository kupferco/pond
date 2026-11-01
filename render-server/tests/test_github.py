"""GitHub client policy and behaviour (against the in-memory fake), plus the MCP tools."""

import json

import pytest

from mcp import types

from pond_render.config import Settings
from pond_render.github import GitHubRepo, RepoAccessError, RepoPolicy, normalise_path, slugify
from tests.conftest import API_TOKEN, make_settings
from tests.fake_github import FakeGitHub
from tests.mcp_helpers import call_tool, list_tools

BOX = 'result = cq.Workplane("XY").box(40, 20, 30)\n'


def _texts(result):
    return [c.text for c in result.content if isinstance(c, types.TextContent)]


# ---------------------------------------------------------------- pure policy


@pytest.mark.parametrize("path,expected", [
    ("cad/part.py", "cad/part.py"),
    ("/cad/part.py", "cad/part.py"),
    ("cad//sub/./part.py", "cad/sub/part.py"),
    ("docs/My Plan v2.md", "docs/My Plan v2.md"),
])
def test_normalise_path_ok(path, expected):
    assert normalise_path(path) == expected


@pytest.mark.parametrize("path", ["", "cad/../.github/workflows/x.yml", "../etc/passwd", "cad/.env", "cad/a;b.py", "cad/\x00.py"])
def test_normalise_path_refuses(path):
    with pytest.raises(RepoAccessError):
        normalise_path(path)


@pytest.mark.parametrize("path", ["README.md", "render-server/pond_render/server.py", ".github/x.yml", "cad", "cad/"])
def test_write_path_outside_allowed_folders_refused(path):
    with pytest.raises(RepoAccessError):
        RepoPolicy().check_write_path(path)


def test_write_path_allowed_folders():
    policy = RepoPolicy()
    assert policy.check_write_path("cad/x.py") == "cad/x.py"
    assert policy.check_write_path("docs/notes/a.md") == "docs/notes/a.md"
    assert policy.check_write_path("sim/pipe_climb.py") == "sim/pipe_climb.py"


@pytest.mark.parametrize("branch", ["main", "master", "release", "claude", "claude/../main", "claude/a b"])
def test_branch_policy_refuses(branch):
    with pytest.raises(RepoAccessError):
        RepoPolicy().check_branch(branch)


def test_branch_policy_default_and_claude_prefix():
    assert RepoPolicy().check_branch(None) == "claude/drafts"
    assert RepoPolicy().check_branch("claude/experiments") == "claude/experiments"


def test_size_cap():
    with pytest.raises(RepoAccessError):
        RepoPolicy(max_bytes=10).check_content("x" * 11)


def test_slugify():
    assert slugify("Hand sleeve v3") == "hand_sleeve_v3"
    assert slugify("  Pipe-Clamp / Sleeve!! ") == "pipe_clamp_sleeve"
    assert slugify("") == "untitled"
    assert slugify("", default="") == ""


def test_settings_require_token_and_repo_together(tmp_path):
    with pytest.raises(ValueError):
        make_settings(tmp_path, 1234, github_token="x")
    with pytest.raises(ValueError):
        make_settings(tmp_path, 1234, github_token="x", github_repo="o/r", github_branch="main")
    s = make_settings(tmp_path, 1234, github_token="x", github_repo="o/r")
    assert s.github_enabled and s.github_branch == "claude/drafts"
    assert not make_settings(tmp_path, 1234).github_enabled


def test_repo_name_validated():
    with pytest.raises(ValueError):
        GitHubRepo(token="t", repo="not-a-repo")


# ---------------------------------------------------------------- client vs fake


def test_write_creates_branch_then_commits():
    fake = FakeGitHub()
    gh = fake.client()
    res = gh.write_file("cad/hand_sleeve.py", "result = 2\n", "first draft")
    assert res.branch == "claude/drafts" and res.created and res.commit_sha
    assert "claude/drafts" in fake.branches
    assert fake.branches["claude/drafts"]["cad/hand_sleeve.py"] == b"result = 2\n"
    assert "cad/hand_sleeve.py" not in fake.branches["main"]
    assert fake.commits[-1]["message"] == "first draft"


def test_write_updates_with_sha_and_skips_identical():
    fake = FakeGitHub()
    gh = fake.client()
    gh.write_file("cad/x.py", "v1\n", "one")
    again = gh.write_file("cad/x.py", "v1\n", "same")
    assert not again.commit_sha and len(fake.commits) == 1
    upd = gh.write_file("cad/x.py", "v2\n", "two")
    assert upd.commit_sha and not upd.created and len(fake.commits) == 2
    assert fake.branches["claude/drafts"]["cad/x.py"] == b"v2\n"


def test_write_never_touches_main():
    fake = FakeGitHub()
    gh = fake.client()
    with pytest.raises(RepoAccessError):
        gh.write_file("cad/x.py", "v1\n", "one", branch="main")
    with pytest.raises(RepoAccessError):
        gh.write_file("README.md", "pwned\n", "one")
    assert not fake.commits
    assert all(m != "PUT" for m, _ in fake.requests)


def test_read_and_list():
    fake = FakeGitHub()
    gh = fake.client()
    data, sha = gh.read_file("cad/pipe.py", ref="main")
    assert data == b"result = 1\n" and sha
    assert gh.read_file("cad/missing.py", ref="main") is None
    entries = gh.list_dir("", ref="main")
    assert {e.path for e in entries} == {"README.md", "cad"}
    assert [e.path for e in gh.list_dir("cad", ref="main")] == ["cad/pipe.py"]
    assert gh.list_dir("nope", ref="main") is None


def test_open_pr_once():
    fake = FakeGitHub()
    gh = fake.client()
    gh.write_file("docs/a.md", "hi\n", "add a")
    pr = gh.open_pr("Drafts", "please review")
    assert pr["number"] == 1 and not pr["existing"]
    same = gh.open_pr("Drafts again")
    assert same["number"] == 1 and same["existing"]
    with pytest.raises(RepoAccessError):
        gh.open_pr("x", head="main")


# ---------------------------------------------------------------- through MCP


def test_github_tools_hidden_without_config(token_server):
    names = {t.name for t in list_tools(token_server.mcp_url, API_TOKEN).tools}
    assert not any(n.startswith("repo_") for n in names)


def test_github_tools_listed(github_server):
    names = {t.name for t in list_tools(github_server.mcp_url, API_TOKEN).tools}
    assert {"repo_write", "repo_read", "repo_list", "repo_open_pr"} <= names


def test_repo_write_read_list_tools(github_server):
    url = github_server.mcp_url
    out = json.loads(_texts(call_tool(url, API_TOKEN, "repo_write",
                                      {"path": "docs/note.md", "content": "# note\n", "message": "add note"}))[0])
    assert out["changed"] and out["created"] and out["branch"] == "claude/drafts"
    text = _texts(call_tool(url, API_TOKEN, "repo_read", {"path": "docs/note.md"}))[0]
    assert text.startswith("# docs/note.md @ claude/drafts") and "# note" in text
    # falls back to main when the drafts branch does not have it
    github_server.fake.branches["main"]["cad/later.py"] = b"result = 3\n"
    text = _texts(call_tool(url, API_TOKEN, "repo_read", {"path": "cad/later.py"}))[0]
    assert "@ main" in text and "result = 3" in text
    listing = _texts(call_tool(url, API_TOKEN, "repo_list", {"dir": "docs"}))[0]
    assert "docs/note.md" in listing
    refused = _texts(call_tool(url, API_TOKEN, "repo_write",
                               {"path": "README.md", "content": "x", "message": "m"}))[0]
    assert refused.startswith("WRITE REFUSED")
    refused = _texts(call_tool(url, API_TOKEN, "repo_write",
                               {"path": "docs/x.md", "content": "x", "message": "m", "branch": "main"}))[0]
    assert refused.startswith("WRITE REFUSED")
    pr = json.loads(_texts(call_tool(url, API_TOKEN, "repo_open_pr", {"title": "Notes", "body": "b"}))[0])
    assert pr["number"] == 1


def test_render_cad_auto_saves_script(github_server):
    url = github_server.mcp_url
    fake = github_server.fake
    result = call_tool(url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"], "title": "Box v1", "name": "box"})
    assert not result.is_error
    summary = json.loads(_texts(result)[0])
    assert summary["repo"]["saved"] and summary["repo"]["path"] == "cad/box.py"
    assert fake.branches["claude/drafts"]["cad/box.py"] == BOX.encode()
    assert fake.commits[-1]["message"].startswith(f"render {summary['id']}: Box v1")

    # title-only falls back to a slug; identical content is not re-committed
    result = call_tool(url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"], "title": "Box v1"})
    summary = json.loads(_texts(result)[0])
    assert summary["repo"]["path"] == "cad/box_v1.py" and summary["repo"]["changed"]
    n = len(fake.commits)
    result = call_tool(url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"], "name": "box"})
    assert not json.loads(_texts(result)[0])["repo"]["changed"] and len(fake.commits) == n

    # opt-out and no-name cases
    result = call_tool(url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"], "name": "box", "save_to_repo": False})
    assert json.loads(_texts(result)[0])["repo"]["saved"] is False
    result = call_tool(url, API_TOKEN, "render_cad", {"script": BOX, "views": ["iso"]})
    assert json.loads(_texts(result)[0])["repo"]["saved"] is False
    assert len(fake.commits) == n

    # failed renders are never saved
    result = call_tool(url, API_TOKEN, "render_cad", {"script": "result = nope\n", "views": ["iso"], "name": "bad"})
    assert "RENDER FAILED" in _texts(result)[0]
    assert "cad/bad.py" not in fake.branches["claude/drafts"]
