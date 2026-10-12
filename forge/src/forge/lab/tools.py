"""MCP tool surface for Testing Lab.

Implemented tools do real work. Client/GUI tools are NOT_IMPLEMENTED
(honest status, per spec) until Mineflayer/Node and screenshot harnesses
exist in this environment.
"""
from __future__ import annotations

NOT_IMPLEMENTED = {"ok": False, "status": "NOT_IMPLEMENTED"}

TOOLS = [
    ("lab.create_environment", "Create isolated env for a server jar",
     {"server_jar": "path (required)", "minecraft": "e.g. 1.21.11",
      "xmx_mb": "default 1024"}),
    ("lab.detect_build", "Detect gradle/maven/javac in a project",
     {"project": "dir (required)"}),
    ("lab.build_plugin", "Clean build a plugin project",
     {"project": "dir (required)", "timeout": "sec, default 900"}),
    ("lab.run_unit_tests", "Run gradle/pytest suite, parse results",
     {"project": "dir (required)", "timeout": "sec, default 900"}),
    ("lab.start_server", "Launch test server, return pid",
     {"run_id": "env id (required)"}),
    ("lab.wait_ready", "Block until Done markers or timeout",
     {"run_id": "env id (required)", "timeout": "sec"}),
    ("lab.server_command", "Send console command, verify output",
     {"run_id": "env id (required)", "command": "no leading slash",
      "expect": "text to observe", "timeout": "sec"}),
    ("lab.read_logs", "Errors + tail of server log",
     {"run_id": "env id (required)", "tail": "lines, default 60"}),
    ("lab.plugin_status", "Load lines for a plugin name",
     {"run_id": "env id (required)", "plugin": "name (required)"}),
    ("lab.stop_server", "Send stop, wait, kill on timeout",
     {"run_id": "env id (required)"}),
    ("lab.collect_artifacts", "Copy logs+report into artifacts dir",
     {"run_id": "env id (required)"}),
    ("lab.destroy_environment", "Remove server dir (keep artifacts)",
     {"run_id": "env id (required)"}),
    ("lab.connect_client", "Attach automated game client",
     {"run_id": "env id (required)"}),
    ("lab.client_action", "Drive the attached client",
     {"run_id": "env id (required)", "action": "description"}),
    ("lab.inspect_inventory", "Read a player inventory via client",
     {"run_id": "env id (required)", "player": "name"}),
    ("lab.gui_check", "Open GUI and verify contents",
     {"run_id": "env id (required)", "target": "menu/block"}),
]


def not_implemented(name: str, why: str) -> dict:
    out = dict(NOT_IMPLEMENTED)
    out["tool"] = name
    out["reason"] = why
    return out


CLIENT_GUI_WHY = ("needs Mineflayer/Node (absent) and a screenshot harness; "
                  "declared, not faked")
