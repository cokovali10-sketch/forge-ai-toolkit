"""Tests for the FORGE kit: project map, test runner, CI generator, secrets."""
from pathlib import Path


def _py_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"demo\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import b\n\n\ndef run():\n    return b.helper()\n",
                                   encoding="utf-8")
    (tmp_path / "test_a.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8")
    return tmp_path


def test_build_map_languages_and_imports(tmp_path):
    from forge.kit import build_map, render_text
    _py_project(tmp_path)
    m = build_map(tmp_path)
    assert m["ok"] is True
    assert m["code_loc"] >= 3
    assert any(l["lang"] == "python" and l["files"] >= 3 for l in m["languages"])
    edges = {(e["from"], e["to"]) for e in m["imports"]["edges"]}
    assert ("a", "b") in edges
    assert "pyproject.toml" in m["build_files"]
    assert isinstance(render_text(m), str)


def test_build_map_bad_dir(tmp_path):
    from forge.kit import build_map
    assert build_map(tmp_path / "nope")["ok"] is False


def test_detect_test_command(tmp_path):
    from forge.kit import detect_test_command
    py = tmp_path / "py"
    py.mkdir()
    (py / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert detect_test_command(py)["kind"] == "python"

    node = tmp_path / "node"
    node.mkdir()
    (node / "package.json").write_text('{"scripts": {"test": "jest"}}',
                                       encoding="utf-8")
    assert detect_test_command(node)["kind"] == "node"

    go = tmp_path / "go"
    go.mkdir()
    (go / "go.mod").write_text("module x\n", encoding="utf-8")
    assert detect_test_command(go)["kind"] == "go"

    rs = tmp_path / "rs"
    rs.mkdir()
    (rs / "Cargo.toml").write_text("[package]\nname=\"x\"\n", encoding="utf-8")
    assert detect_test_command(rs)["kind"] == "rust"

    empty = tmp_path / "empty"
    empty.mkdir()
    assert detect_test_command(empty) is None


def test_run_tests_executes_pytest(tmp_path):
    from forge.kit import run_tests
    _py_project(tmp_path)
    out = run_tests(tmp_path, timeout=120)
    assert out["ran"] is True
    assert out["kind"] == "python"
    assert out["ok"] is True


def test_run_tests_missing_stack(tmp_path):
    from forge.kit import run_tests
    out = run_tests(tmp_path)
    assert out["ok"] is True and out["ran"] is False


def test_generate_ci_and_guard(tmp_path):
    from forge.kit import generate_ci
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
    res = generate_ci(tmp_path)
    assert res["ok"] is True
    assert res["ecosystems"] == ["python", "go"]
    wf = Path(res["path"])
    assert wf.is_file() and wf.name == "forge-ci.yml"
    text = wf.read_text(encoding="utf-8")
    assert "python -m pytest -q" in text and "go test ./..." in text
    # без force не перезаписываем
    again = generate_ci(tmp_path)
    assert again["ok"] is False and again.get("exists") is True


def test_generate_ci_no_stack(tmp_path):
    from forge.kit import generate_ci
    assert generate_ci(tmp_path)["ok"] is False


def test_scan_secrets_detects_and_masks(tmp_path):
    from forge.kit import scan_secrets
    key = "AKIA" + "ABCDEFGHIJKLMNOP"  # AKIA + 16 uppercase
    (tmp_path / "conf.py").write_text(
        f'aws_key = "{key}"\n'
        'api_key = "your_key_here"\n'
        'password = "hunter2secret"\n'  # forge:allow-secret
        , encoding="utf-8")
    out = scan_secrets(tmp_path)
    assert out["ok"] is True
    kinds = {f["kind"] for f in out["findings"]}
    assert "aws-access-key" in kinds
    assert "password-assign" in kinds
    # полный секрет и плейсхолдер не должны попасть в отчёт
    blob = str(out)
    assert key not in blob
    assert "hunter2secret" not in blob
    assert all("your_key_here" != f["preview"] for f in out["findings"])


def test_scan_secrets_private_key(tmp_path):
    from forge.kit import scan_secrets
    (tmp_path / "id_rsa").write_text(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n", encoding="utf-8")  # forge:allow-secret
    out = scan_secrets(tmp_path)
    assert any(f["kind"] == "private-key" for f in out["findings"])


def test_allow_marker_suppresses(tmp_path):
    from forge.kit import scan_secrets
    (tmp_path / "c.py").write_text(
        'aws = "AKIAABCDEFGHIJKLMNOP"  # forge:allow-secret\n', encoding="utf-8")
    out = scan_secrets(tmp_path)
    assert out["count"] == 0


def test_doctor_reports_tools_and_capabilities():
    from forge.kit import doctor
    d = doctor()
    assert d["ok"] is True
    names = [t["name"] for t in d["tools"]]
    assert "git" in names and "python" in names
    py = d["tools"][names.index("python")]
    assert py["present"] is True and py["version"]
    assert d["capabilities"]["stages"] >= 8
    assert "python" in d["capabilities"]["languages"]


def test_doctor_with_project(tmp_path):
    from forge.kit import doctor
    _py_project(tmp_path)
    d = doctor(tmp_path)
    assert d["project"]["exists"] is True
    assert d["project"]["test_command"]["kind"] == "python"


def test_cli_and_mcp_wired(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    _py_project(tmp_path)
    assert main(["map", str(tmp_path), "--json"]) == 0
    assert main(["secrets", str(tmp_path)]) == 0
    assert main(["doctor", "--json"]) == 0
    assert main(["deps", str(tmp_path), "--json"]) == 0
    assert main(["audit", str(tmp_path), "--json"]) == 0
    assert main(["init", str(tmp_path), "--json"]) == 0
    reg = build_default_registry("")
    for tool in ("map.project", "test.detect", "test.run", "ci.generate",
                 "secrets.scan", "doctor.check", "deps.scan", "audit.run",
                 "init.project"):
        assert tool in reg.tool_owner, tool
    r = reg.call("map.project", {"root": str(tmp_path)})
    assert r["ok"] is True


def test_init_creates_and_is_idempotent(tmp_path):
    from forge.kit import init_project
    _py_project(tmp_path)
    out = init_project(tmp_path)
    assert out["ok"] is True
    assert (tmp_path / ".forge-suppress.json").is_file()
    wf = tmp_path / ".github" / "workflows" / "forge-ci.yml"
    assert wf.is_file()
    assert ".forge-suppress.json" in out["created"]
    assert "forge-ci.yml" in out["created"]
    assert out["next"]
    again = init_project(tmp_path)
    assert again["ok"] is True and again["created"] == []
    assert set(again["skipped"]) >= {".forge-suppress.json", "forge-ci.yml"}
    out2 = init_project(tmp_path, force=True)
    assert "forge-ci.yml" in out2["created"]


def test_audit_scores_and_sections(tmp_path):
    from forge.kit import audit, render_audit
    _py_project(tmp_path)
    (tmp_path / "conf.py").write_text('password = "hunter2secret"\n',  # forge:allow-secret
                                      encoding="utf-8")
    out = audit(tmp_path)
    assert out["ok"] is True
    assert 0 <= out["score"] <= 100
    for sec in ("map", "secrets", "deps", "quality"):
        assert sec in out["sections"]
    assert out["counts"]["medium"] >= 1
    assert isinstance(render_audit(out), str)


def test_audit_high_secret_lowers_score(tmp_path):
    from forge.kit import audit
    _py_project(tmp_path)
    clean = audit(tmp_path)["score"]
    (tmp_path / "k.py").write_text('x = "AKIAABCDEFGHIJKLMNOP"\n',  # forge:allow-secret
                                   encoding="utf-8")
    dirty = audit(tmp_path)
    assert dirty["counts"]["high"] >= 1
    assert dirty["score"] < clean


def test_audit_deep_runs_native_tests(tmp_path):
    from forge.kit import audit
    _py_project(tmp_path)
    out = audit(tmp_path, deep=True)
    assert out["sections"]["tests"]["ran"] is True
    assert out["sections"]["tests"]["ok"] is True


def test_audit_missing_dir(tmp_path):
    from forge.kit import audit
    assert audit(tmp_path / "nope")["ok"] is False
