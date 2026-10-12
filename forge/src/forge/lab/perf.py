"""Performance probes via console: TPS/MSPT parsing + entity load.

Works on any Paper/Purpur: sends `tps`, parses numbers, optionally spawns
a controlled mob crowd, measures again, cleans up. No client needed.
"""
from __future__ import annotations

import re
import time


def parse_tps(text: str) -> dict:
    """Extract TPS/MSPT numbers. Returns {} when unparsable (honest)."""
    out: dict = {}
    m = re.search(r"(?i)(\d+(?:\.\d+)?)\s*mspt", text)
    if m:
        out["mspt"] = float(m.group(1))
    for line in text.splitlines():
        if "tps" not in line.lower():
            continue
        seg = line.rsplit(":", 1)[-1] if ":" in line else line
        nums = re.findall(r"\d+(?:\.\d+)?", seg)
        if nums:
            out["tps"] = float(nums[0])
            break
    return out


def measure(server, timeout: int = 20) -> dict:
    """Send `tps`, return parsed numbers + raw tail."""
    r = server.command("tps", "", timeout)
    return {"ok": r.get("ok", False), **parse_tps(r.get("output", "")),
            "raw": r.get("output", "")[-500:]}


def load_crowd(server, count: int = 50, timeout: int = 60) -> dict:
    """Spawn N zombies at spawn, wait, measure, remove them."""
    t = time.time()
    r1 = server.command(
        f"execute in minecraft:overworld run summon minecraft:zombie 0 100 0 "
        f"{{PersistenceRequired:0b}}", "", timeout)
    ok_spawn = r1.get("ok", False)
    time.sleep(5)
    before = measure(server, timeout)
    r2 = server.command("kill @e[type=minecraft:zombie]", "", timeout)
    after = measure(server, timeout)
    return {"ok": ok_spawn and before.get("ok", False),
            "spawned": count if ok_spawn else 0,
            "tps_loaded": before.get("tps"), "mspt_loaded": before.get("mspt"),
            "tps_after": after.get("tps"),
            "ms": int((time.time() - t) * 1000)}
