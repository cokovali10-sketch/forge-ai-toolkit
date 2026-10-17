"""Tests for forge deps: dependency inventory + hygiene across ecosystems."""
from pathlib import Path


def _w(p: Path, name: str, text: str) -> None:
    (p / name).write_text(text, encoding="utf-8")


def test_scan_deps_missing_dir(tmp_path):
    from forge.kit import scan_deps
    assert scan_deps(tmp_path / "nope")["ok"] is False


def test_scan_deps_python(tmp_path):
    from forge.kit import scan_deps
    _w(tmp_path, "requirements.txt", "requests==2.31.0\nflask>=3\n# c\n")
    _w(tmp_path, "pyproject.toml",
       '[project]\nname = "d"\ndependencies = ["click>=8", "tomli==2.0.1"]\n')
    out = scan_deps(tmp_path)
    assert out["ok"] is True
    names = {d["name"] for d in out["dependencies"]}
    assert {"requests", "flask", "click", "tomli"} <= names
    kinds = {f["kind"] for f in out["findings"]}
    assert "loose-range" in kinds


def test_scan_deps_node_wildcard(tmp_path):
    from forge.kit import scan_deps
    _w(tmp_path, "package.json",
       '{"dependencies": {"left-pad": "*", "express": "^4.18.0"}}')
    out = scan_deps(tmp_path)
    assert out["by_ecosystem"].get("node") == 2
    kinds = {f["kind"] for f in out["findings"]}
    assert "wildcard-version" in kinds and "loose-range" in kinds


def test_scan_deps_go(tmp_path):
    from forge.kit import scan_deps
    _w(tmp_path, "go.mod",
       "module x\n\ngo 1.21\n\nrequire (\n"
       "\tgithub.com/pkg/errors v0.9.1\n"
       "\tgolang.org/x/text v0.14.0\n)\n")
    out = scan_deps(tmp_path)
    assert out["by_ecosystem"].get("go") == 2
    assert any(d["name"] == "github.com/pkg/errors" for d in out["dependencies"])


def test_scan_deps_rust_sections(tmp_path):
    from forge.kit import scan_deps
    _w(tmp_path, "Cargo.toml",
       '[package]\nname = "d"\n\n[dependencies]\nserde = "1.0"\n'
       'rand = { version = "0.8", features = ["small_rng"] }\n\n'
       '[dev-dependencies]\ncriterion = "0.5"\n')
    out = scan_deps(tmp_path)
    assert out["by_ecosystem"].get("rust") == 3
    by = {d["name"]: d for d in out["dependencies"]}
    assert by["serde"]["spec"] == "1.0"
    assert by["rand"]["spec"] == "0.8"
    assert by["criterion"]["dev"] is True


def test_scan_deps_java(tmp_path):
    from forge.kit import scan_deps
    _w(tmp_path, "build.gradle",
       "dependencies {\n"
       "    implementation 'com.google.guava:guava:32.0.0-jre'\n"
       "    testImplementation 'junit:junit:4.13.2'\n}\n")
    _w(tmp_path, "pom.xml",
       "<dependency><groupId>org.slf4j</groupId>"
       "<artifactId>slf4j-api</artifactId><version>2.0.9</version></dependency>")
    out = scan_deps(tmp_path)
    assert out["by_ecosystem"].get("java") == 3
    names = {d["name"] for d in out["dependencies"]}
    assert "com.google.guava:guava" in names and "org.slf4j:slf4j-api" in names


def test_scan_deps_duplicate(tmp_path):
    from forge.kit import scan_deps
    _w(tmp_path, "requirements.txt", "rich==13.0.0\n")
    _w(tmp_path, "requirements-dev.txt", "rich==13.0.0\n")
    out = scan_deps(tmp_path)
    assert any(f["kind"] == "duplicate" for f in out["findings"])


def test_deps_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    _w(tmp_path, "requirements.txt", "requests==2.31.0\n")
    assert main(["deps", str(tmp_path), "--json"]) == 0
    reg = build_default_registry("")
    assert "deps.scan" in reg.tool_owner
    r = reg.call("deps.scan", {"root": str(tmp_path)})
    assert r["ok"] is True and r["count"] == 1
