"""FORGE pipe SARIF: findings -> SARIF 2.1.0 for GitHub code scanning.

Only review findings are mapped (they have file/line). Other stages
contribute nothing — and say so honestly instead of inventing results.
Usage: forge pipe run <dir> --sarif report.sarif
"""
from __future__ import annotations

import re
from typing import Any

RULES = {
    "debt-marker": ("Debt marker (TODO/FIXME/XXX/HACK)", "error"),
    "oversized-file": ("File over 800 lines", "warning"),
    "empty-catch": ("Empty catch block", "warning"),
    "debug-leftover": ("Debug output leftover", "warning"),
    "duplicate-block": ("Duplicated 5-line block", "note"),
}

_LINE = re.compile(r"L(\d+)")


def report_to_sarif(report: dict[str, Any], target: str) -> dict[str, Any]:
    results = []
    seen_rules: dict[str, str] = {}
    for s in report.get("stages", []):
        if s.get("name") != "review":
            continue
        data = s.get("data") or {}
        for f in data.get("findings", []) or []:
            if f.get("suppressed"):
                continue
            rule = str(f.get("rule", "unknown"))
            desc, level = RULES.get(rule, (rule, "warning"))
            seen_rules[rule] = desc
            m = _LINE.search(str(f.get("detail", "")))
            line = int(m.group(1)) if m else 1
            results.append({
                "ruleId": f"forge/{rule}",
                "level": level if level in ("error", "warning", "note") else "warning",
                "message": {"text": f"{rule}: {f.get('detail', '')}"[:400]},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": str(f.get("file", ""))},
                        "region": {"startLine": line},
                    }}],
            })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "forge-pipe",
                "version": "1",
                "informationUri": "https://github.com/cokovali10-sketch/forge-ai-toolkit",
                "rules": [{"id": f"forge/{r}", "name": r,
                           "shortDescription": {"text": seen_rules[r]}}
                          for r in sorted(seen_rules)],
            }},
            "results": results,
        }],
    }
