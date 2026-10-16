"""Tests for the universal object editor (JSON engine + YAML bridge + API/CLI/MCP)."""
import json as _json
from pathlib import Path


def _doc(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(_json.dumps({"server": {"port": 8080, "host": "x"},
                              "mods": ["a", "b"]}), encoding="utf-8")
    return p


def test_json_get_set_roundtrip(tmp_path):
    from forge.edit import api
    p = _doc(tmp_path)
    assert api.get(str(p), "server.port")["value"] == 8080
    assert api.get(str(p), "mods.1")["value"] == "b"
    assert api.get(str(p), "nope")["ok"] is False
    r = api.set(str(p), "server.port", "9090")
    assert r["ok"] is True and r["old"] == 8080 and r["new"] == 9090
    assert api.get(str(p), "server.port")["value"] == 9090
    assert Path(str(p) + ".forge-bak").is_file()
    assert api.rollback(str(p))["ok"] is True
    assert api.get(str(p), "server.port")["value"] == 8080
    assert api.rollback(str(tmp_path / "missing.json"))["ok"] is False


def test_json_dry_and_coercion(tmp_path):
    from forge.edit import api
    p = _doc(tmp_path)
    r = api.set(str(p), "server.host", "example", dry=True)
    assert r["ok"] is True and r["dry"] is True
    assert api.get(str(p), "server.host")["value"] == "x"  # не записалось
    r2 = api.set(str(p), "nick", "plain-word")
    assert r2["ok"] is True and r2["coerced_to_string"] is True


def test_json_validate_schema(tmp_path):
    from forge.edit import api
    p = _doc(tmp_path)
    sch = {"type": "object", "required": ["server"],
           "properties": {"server": {"type": "object", "required": ["port"],
                                     "properties": {"port": {"type": "integer",
                                                             "min": 1, "max": 65535}}}}}
    assert api.validate(str(p), "")["ok"] is False  # схемы нет
    sp = tmp_path / "s.json"
    sp.write_text(_json.dumps(sch), encoding="utf-8")
    assert api.validate(str(p), str(sp))["ok"] is True
    bad = api.set(str(p), "server.port", "99999", schema=str(sp))
    assert bad["ok"] is False and "max" in bad["error"]
    assert api.get(str(p), "server.port")["value"] == 8080  # откат не нужен — не писалось


def test_builtin_plugin_schema():
    from forge.edit import api
    assert (Path(api.__file__).parent / "schemas" / "plugin-yml.json").is_file()


def test_yaml_bridge(tmp_path):
    from forge.edit import api
    y = tmp_path / "plugin.yml"
    y.write_text("name: Demo\nversion: 1.0\nmain: com.Demo\n", encoding="utf-8")
    ins = api.inspect(str(y))
    assert ins["format"] == "yaml" and "name" in str(ins.get("sections"))
    assert str(api.get(str(y), "version")["value"]) == "1.0"
    r = api.set(str(y), "version", "2.0")
    assert r["ok"] is True
    assert str(api.get(str(y), "version")["value"]) == "2.0"
    assert api.rollback(str(y))["ok"] is True
    assert str(api.get(str(y), "version")["value"]) == "1.0"


def test_edit_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    p = _doc(tmp_path)
    assert main(["edit", "get", str(p), "server.port"]) == 0
    assert main(["edit", "set", str(p), "server.port", "1"]) == 0
    assert main(["edit", "bogus", str(p)]) == 2
    reg = build_default_registry("")
    assert "edit.inspect" in reg.tool_owner and "edit.set" in reg.tool_owner
    got = reg.call("edit.get", {"file": str(p), "path": "mods.0"})
    assert got["value"] == "a"
