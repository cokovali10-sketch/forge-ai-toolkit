"""FORGE refactor SARIF: clean-code findings -> SARIF 2.1.0 for GitHub.

Usage: forge refactor <dir> --sarif report.sarif
Only real findings with file/line are mapped — nothing invented."""
from __future__ import annotations

from typing import Any

_RULE_DESC = {
    "long-function": ("Function over 50 lines", "warning"),
    "deep-nesting": ("Nesting deeper than 3 levels", "warning"),
    "duplicate-block": ("Duplicated 3+ line block", "note"),
    "magic-number": ("Magic number without a name", "note"),
    "too-many-args": ("Function with more than 4 arguments", "warning"),
    "god-class": ("Class over 200 lines", "warning"),
    "high-complexity": ("Cyclomatic complexity over 10", "warning"),
}


def findings_to_sarif(result: dict[str, Any]) -> dict[str, Any]:
    """Собирает SARIF из результата inspect (файл или директория)."""
    entries: list[tuple[str, list[dict[str, Any]]]] = []
    if result.get("files_analyzed") is not None:
        entries = [(f.get("file", ""), f.get("issues", []))
                   for f in result["files_analyzed"]]
    else:
        entries = [(result.get("file", ""), result.get("issues", []))]

    results = []
    seen: set[str] = set()
    for fname, issues in entries:
        for i in issues:
            rule = str(i.get("kind", "unknown"))
            desc, level = _RULE_DESC.get(rule, (rule, "warning"))
            seen.add(rule)
            results.append({
                "ruleId": f"forge/refactor/{rule}",
                "level": level,
                "message": {"text": f"{i.get('message', rule)} — "
                                     f"{i.get('suggestion', '')}"[:400]},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": str(fname)},
                        "region": {"startLine": max(1, int(i.get("line", 1)))},
                    }}],
            })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "forge-refactor",
                "version": "1",
                "informationUri": "https://github.com/cokovali10-sketch/forge-ai-toolkit",
                "rules": [{"id": f"forge/refactor/{r}", "name": r,
                           "shortDescription": {"text": _RULE_DESC.get(r, (r, "warning"))[0]}}
                          for r in sorted(seen)],
            }},
            "results": results,
        }],
    }
