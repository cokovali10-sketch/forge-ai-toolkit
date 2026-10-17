"""FORGE secrets: сканер утечек секретов в исходниках.

Ищет ключи, токены, приватные ключи и пароли по регуляркам. В вывод НИКОГДА
не попадает полный секрет — только маскированное начало. Это эвристика
(не заменяет полноценный сканер), но ловит типовые утечки до публикации.

Только чтение, гигантские/бинарные файлы пропускаются.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist",
        "build", "target", "out", ".gradle", ".mypy_cache", ".pytest_cache"}

TEXT_EXT = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs",
            ".java", ".kt", ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".hpp",
            ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env", ".sh",
            ".ps1", ".bat", ".xml", ".properties", ".txt", ".md", ".conf",
            ".tf", ".tfvars", ".pem", ".key"}

# Файлы без расширения, которые почти всегда содержат секреты.
SECRET_FILENAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
                    "credentials", "keystore", ".netrc", ".htpasswd"}

# (kind, severity, regex)
PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("private-key", "high",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("aws-access-key", "high", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", "high",
     re.compile(r"\b(?:ghp|gho|ghu|ghs)_[0-9A-Za-z]{36}\b|github_pat_[0-9A-Za-z_]{22,}")),
    ("google-api-key", "high", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("slack-token", "high", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("stripe-secret", "high", re.compile(r"\bsk_live_[0-9A-Za-z]{24}\b")),
    ("openai-key", "high", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("jwt", "medium",
     re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("password-assign", "medium",
     re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|apikey|"
                r"access[_-]?key|auth[_-]?token|token)\b\s*[:=]\s*"
                r"[\"']([^\"'\s]{6,})[\"']")),
]

# Значения-заглушки, которые не считаем утечкой.
_PLACEHOLDER = re.compile(
    r"(?i)^(?:x{3,}|\*{3,}|changeme|change_me|example|placeholder|your[_-]?"
    r"|todo|none|null|test|dummy|sample|\$\{|\{\{|<|\.\.\.)")

MAX_BYTES = 2_000_000

# Строка с этим маркером не считается утечкой (осознанные тестовые значения).
ALLOW_MARKER = "forge:allow-secret"


def _mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 6:
        return "***"
    return value[:4] + "***" + value[-2:]


def _looks_placeholder(value: str) -> bool:
    return bool(_PLACEHOLDER.match(value.strip())) or value.strip() == ""


def scan_text(text: str) -> list[dict[str, Any]]:
    """Сканирует один текст. Возвращает находки (с маскировкой)."""
    out: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        for kind, sev, rx in PATTERNS:
            for m in rx.finditer(line):
                secret = m.group(1) if m.groups() else m.group(0)
                if _looks_placeholder(secret):
                    continue
                out.append({"kind": kind, "severity": sev,
                            "preview": _mask(secret)})
    return out


def scan_secrets(root: str | Path, max_files: int = 5000) -> dict[str, Any]:
    """Сканирует директорию. Возвращает отчёт без полных секретов."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}
    findings: list[dict[str, Any]] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(base, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP and not d.startswith(".")]
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            ext = p.suffix.lower()
            if (ext not in TEXT_EXT and p.name != ".env"
                    and p.name.lower() not in SECRET_FILENAMES):
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
                text = p.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue
            scanned += 1
            for hit in scan_text(text):
                hit["file"] = str(p.relative_to(base)).replace("\\", "/")
                findings.append(hit)
            if scanned >= max_files:
                break
        if scanned >= max_files:
            break
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    return {"ok": True, "root": str(base), "files_scanned": scanned,
            "count": len(findings), "by_severity": counts,
            "findings": findings[:200]}
