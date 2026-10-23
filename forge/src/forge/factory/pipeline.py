"""FORGE Factory: intent -> scaffold -> build -> live server -> zip.

Every stage is explicit. A missing toolchain or server jar is reported as
SKIPPED with a reason, never silently replaced by a fake success.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

from . import intent as _intent
from . import templates as _tpl

FORGE_ROOT = Path(__file__).resolve().parents[3]   # .../Forge-Factority/forge
REPO_ROOT = FORGE_ROOT.parent                      # .../Forge-Factority


def _stage(name: str, status: str, detail: str = "", ms: int = 0,
           required: bool = True) -> dict:
    return {"name": name, "status": status, "detail": detail[:2000],
            "ms": int(ms), "required": required}


def _find_api_jars(api_jar: str = "") -> list[str]:
    out: list[str] = []
    if api_jar:
        p = Path(api_jar)
        if p.is_dir():
            out += [str(x) for x in sorted(p.glob("*.jar"))]
        elif p.is_file():
            out.append(str(p))
    env = os.environ.get("FORGE_PAPER_API", "")
    if env:
        p = Path(env)
        if p.is_dir():
            out += [str(x) for x in sorted(p.glob("*.jar"))]
        elif p.is_file():
            out.append(str(p))
    for base in (REPO_ROOT / "lab-servers" / "api",
                 FORGE_ROOT / "lab-servers" / "api"):
        if base.is_dir():
            out += [str(x) for x in sorted(base.glob("*.jar"))]
    return sorted(set(out))


def _find_server_jar(server_jar: str = "") -> str:
    if server_jar and Path(server_jar).is_file():
        return str(Path(server_jar))
    env = os.environ.get("FORGE_SERVER_JAR", "")
    if env and Path(env).is_file():
        return env
    for base in (REPO_ROOT / "lab-servers", FORGE_ROOT / "lab-servers"):
        if not base.is_dir():
            continue
        jar = next((p for p in sorted(base.glob("*.jar"))
                    if "api" not in p.name.lower()), None)
        if jar:
            return str(jar)
    return ""


def _javac(java_bin: str = "") -> str:
    if java_bin:
        p = Path(java_bin)
        if p.name.lower().startswith("javac") and p.is_file():
            return str(p)
        cand = p.with_name("javac.exe" if os.name == "nt" else "javac")
        if cand.is_file():
            return str(cand)
    return shutil.which("javac") or ""


def _write_resourcepack(spec: dict, dest: Path) -> dict:
    from forge.webstudio.presets import get as _preset
    from forge.ui import assets as _assets
    colors = _preset(spec["preset"])["colors"]
    system = {
        "name": f"{spec['name']}-theme",
        "version": spec["version"],
        "colors": {
            "accent": colors["accent"],
            "accent_bright": colors["accent2"],
            "panel": colors["bg"],
            "row": colors["bg2"],
            "border": colors["border"].split(")")[0][:7]
            if colors["border"].startswith("#") else colors["accent"],
            "text": colors["text"],
            "text_dim": colors["muted"],
        },
        "spacing": {"xs": 2, "s": 4, "m": 8, "l": 16, "xl": 24},
        "radius": {"s": 2, "m": 4, "l": 8},
        "typography": {"font": "minecraft:default", "title_size": 14,
                       "body_size": 9, "max_title_chars": 32},
        "components": {"button": {"h": 20, "pad": 6},
                       "row": {"h": 20}, "panel": {"border": 1}},
    }
    pack = dest / "resourcepack"
    manifest = _assets.build_pack(system, pack)
    _assets.pack_mcmeta(f"{spec['name']} theme (FORGE Factory)", pack)
    return {"pack": str(pack), "assets": len(manifest["assets"])}


def _validate(spec: dict, dest: Path) -> dict:
    src_dir = dest / "src"
    main = src_dir.joinpath(*spec["package"].split("."), f"{spec['class']}.java")
    meta = src_dir / "plugin.yml"
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("main-class", main.is_file(), str(main))
    add("plugin-yml", meta.is_file(), str(meta))
    if main.is_file():
        code = main.read_text(encoding="utf-8")
        add("on-enable", "onEnable" in code, "lifecycle present")
        add("command", "onCommand" in code and spec["command"] in code,
            f"/{spec['command']} wired")
        add("no-placeholders", "__PKG__" not in code and "__CLS__" not in code,
            "template fully rendered")
        if spec["gui"]:
            add("gui", "openInventory" in code
                and "InventoryClickEvent" in code,
                "menu + click handler")
    if meta.is_file():
        text = meta.read_text(encoding="utf-8")
        add("metadata", f"name: {spec['name']}" in text
            and "main:" in text and "api-version:" in text, "plugin.yml lint")
    failed = [c for c in checks if not c["ok"]]
    return {"ok": not failed, "checks": checks,
            "problems": [f"{c['name']}: {c['detail']}" for c in failed]}


def _zip_project(spec: dict, dest: Path, archive: Path) -> dict:
    archive.parent.mkdir(parents=True, exist_ok=True)
    skipped_dirs = {".factory-lab", "dist", "__pycache__"}
    count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dest.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(dest)
            if any(part in skipped_dirs for part in rel.parts):
                continue
            if f.suffix.lower() == ".zip":
                continue
            z.write(f, arcname=str(Path(spec["name"]) / rel))
            count += 1
    return {"zip": str(archive), "files": count,
            "bytes": archive.stat().st_size}


def _render_report(result: dict) -> str:
    s = result["spec"]
    lines = [f"# FORGE Factory: {s['name']}", "",
             f"Intent: {s['intent']}", "",
             f"Status: **{result['status']}**", "",
             "| Stage | Status | Detail |", "|---|---|---|"]
    for st in result["stages"]:
        lines.append(f"| {st['name']} | {st['status']} | "
                     f"{st['detail'][:180]} |")
    for note in result["notes"]:
        lines.append(f"- {note}")
    lines += ["", f"Artifacts: `{result['dir']}`"]
    if result.get("jar"):
        lines.append(f"Jar: `{result['jar']}`")
    if result.get("zip"):
        lines.append(f"Zip: `{result['zip']}`")
    return "\n".join(lines) + "\n"


def run(intent: str, out: str | Path = ".", name: str = "",
        package: str = "", command: str = "", build: bool = True,
        e2e: bool = True, server_jar: str = "", api_jar: str = "",
        java_bin: str = "", timeout_boot: int = 420,
        build_timeout: int = 600, lab_root: str | Path = "") -> dict:
    """Run the full factory pipeline and return a verifiable report."""
    started = time.time()
    spec = _intent.plan(intent, name=name, package=package, command=command)
    out_path = Path(out)
    dest = out_path if out_path.name == spec["name"] else out_path / spec["name"]
    dest.mkdir(parents=True, exist_ok=True)
    stages: list[dict] = []
    notes: list[str] = []
    jar_path = ""
    pack_info: dict = {}

    # 1. generate
    t = time.time()
    try:
        from forge.gen import paper_plugin as _pp
        _pp.generate(dest, spec["name"], spec["package"], spec["command"],
                     spec["description"], spec["api"], spec["version"])
        src = dest / "src"
        main = src.joinpath(*spec["package"].split("."),
                            f"{spec['class']}.java")
        if spec["gui"]:
            main.write_text(_tpl.main_source(spec), encoding="utf-8")
            (src / "config.yml").write_text(_tpl.config_yaml(spec),
                                            encoding="utf-8")
        (dest / "README.md").write_text(_tpl.readme(spec), encoding="utf-8")
        (dest / "factory.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        stages.append(_stage("generate", "PASS",
                             f"{spec['class']}.java + plugin.yml + config",
                             (time.time() - t) * 1000))
    except Exception as e:
        stages.append(_stage("generate", "FAIL", f"{type(e).__name__}: {e}",
                             (time.time() - t) * 1000))
        notes.append("Generation failed; nothing was built.")
        return _finish(spec, dest, stages, notes, started, "", "")

    # 2. validate
    t = time.time()
    val = _validate(spec, dest)
    stages.append(_stage("validate", "PASS" if val["ok"] else "FAIL",
                         "checks: " + ", ".join(
                             f"{c['name']}={'ok' if c['ok'] else 'fail'}"
                             for c in val["checks"]),
                         (time.time() - t) * 1000))
    if not val["ok"]:
        notes.append("; ".join(val["problems"]))
        return _finish(spec, dest, stages, notes, started, "", "")

    # 3. resourcepack (optional, honest if PIL is absent)
    if spec["resourcepack"]:
        t = time.time()
        try:
            pack_info = _write_resourcepack(spec, dest)
            stages.append(_stage("resourcepack", "PASS",
                                 f"{pack_info['assets']} PNG assets + manifest",
                                 (time.time() - t) * 1000))
        except ImportError as e:
            stages.append(_stage("resourcepack", "SKIPPED",
                                 f"Pillow not installed: {e}",
                                 (time.time() - t) * 1000))
            notes.append("Resourcepack requested but Pillow is unavailable.")
        except Exception as e:
            stages.append(_stage("resourcepack", "FAIL",
                                 f"{type(e).__name__}: {e}",
                                 (time.time() - t) * 1000))

    # 4. build
    if not build:
        stages.append(_stage("build", "SKIPPED", "disabled by --no-build",
                             required=False))
    else:
        t = time.time()
        apis = _find_api_jars(api_jar)
        javac = _javac(java_bin)
        if not apis:
            stages.append(_stage("build", "SKIPPED",
                                 "paper-api jars not found; set --api-jar "
                                 "or FORGE_PAPER_API",
                                 (time.time() - t) * 1000))
            notes.append("Build skipped: no paper-api classpath available.")
        elif not javac:
            stages.append(_stage("build", "SKIPPED",
                                 "javac not found; set --java or PATH",
                                 (time.time() - t) * 1000))
            notes.append("Build skipped: no javac on this machine.")
        else:
            from forge.lab.build import compile_fixture
            jar_path = str(dest / "build" /
                           f"{spec['name']}-{spec['version']}.jar")
            comp = compile_fixture(dest / "src", jar_path, apis, javac,
                                   timeout=build_timeout)
            stages.append(_stage("build", "PASS" if comp["ok"] else "FAIL",
                                 comp["jar"] or "; ".join(comp["errors"]),
                                 (time.time() - t) * 1000))
            if not comp["ok"]:
                notes.append("Compilation failed; see the detail above.")
                return _finish(spec, dest, stages, notes, started, "", "")

    # 5. live e2e on a real server
    if not e2e:
        stages.append(_stage("e2e", "SKIPPED", "disabled by --no-e2e",
                             required=False))
    elif not jar_path:
        stages.append(_stage("e2e", "SKIPPED", "needs a built jar"))
        notes.append("E2E skipped because the plugin was not built.")
    else:
        srv_jar = _find_server_jar(server_jar)
        if not srv_jar:
            stages.append(_stage("e2e", "SKIPPED",
                                 "no server jar; set --server-jar "
                                 "or FORGE_SERVER_JAR"))
            notes.append("E2E skipped: no Purpur/Paper server jar found.")
        else:
            t = time.time()
            from forge.lab import runner as _runner
            from forge.lab import scenarios as _sc
            lab = Path(lab_root) if lab_root else dest / ".factory-lab"
            scenarios = [
                _sc.plugin_load(spec["name"], spec["name"]),
                _sc.log_contains("factory-marker",
                                 "enabled (forge-factory)"),
                _sc.command_check(spec["command"],
                                  f"{spec['name']} console-ok"),
                _sc.command_check(f"{spec['command']} reload",
                                  f"{spec['name']} reloaded"),
            ]
            try:
                res = _runner.e2e_jar(
                    lab, srv_jar, jar_path, scenarios,
                    java_bin=_javac_java(java_bin),
                    timeout_boot=timeout_boot)
                failed = [c for c in res.get("checks", []) if not c.get("ok")]
                detail = (f"{len(res.get('checks', [])) - len(failed)}/"
                          f"{len(res.get('checks', []))} checks; "
                          f"report: {res.get('report', '')}")
                if failed:
                    detail += " | " + "; ".join(
                        f"{c['stage']}: {c['detail'][:120]}"
                        for c in failed[:4])
                stages.append(_stage("e2e", "PASS" if res.get("ok") else "FAIL",
                                     detail, (time.time() - t) * 1000))
            except Exception as e:
                stages.append(_stage("e2e", "FAIL",
                                     f"{type(e).__name__}: {e}",
                                     (time.time() - t) * 1000))

    # 6. package
    t = time.time()
    archive = dest / "dist" / f"{spec['name']}-{spec['version']}-forge.zip"
    stages.append(_stage("package", "PASS", archive.name,
                         (time.time() - t) * 1000))
    result = _finish(spec, dest, stages, notes, started, jar_path,
                     str(archive))
    zip_info = _zip_project(spec, dest, archive)
    result["zip_files"] = zip_info["files"]
    result["zip_bytes"] = zip_info["bytes"]
    return result


def _javac_java(java_bin: str) -> str:
    if java_bin:
        p = Path(java_bin)
        if p.name.lower().startswith("java") and p.is_file():
            return str(p)
        cand = p.with_name("java.exe" if os.name == "nt" else "java")
        if cand.is_file():
            return str(cand)
    return shutil.which("java") or ""


def _finish(spec: dict, dest: Path, stages: list[dict], notes: list[str],
            started: float, jar_path: str, zip_path: str) -> dict:
    if any(s["status"] == "FAIL" and s["required"] for s in stages):
        status = "FAIL"
    elif any(s["status"] == "SKIPPED" and s["required"] for s in stages):
        status = "PARTIAL"
    elif any(s["status"] == "FAIL" for s in stages):
        status = "FAIL"
    else:
        status = "PASS"
    result: dict[str, Any] = {
        "ok": status == "PASS",
        "status": status,
        "intent": spec["intent"],
        "spec": spec,
        "dir": str(dest),
        "jar": jar_path,
        "zip": zip_path,
        "stages": stages,
        "notes": notes,
        "duration_ms": int((time.time() - started) * 1000),
    }
    report_json = dest / "factory-report.json"
    report_md = dest / "FACTORY.md"
    report_json.write_text(
        json.dumps({**result, "report": str(report_md)},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(_render_report(result), encoding="utf-8")
    result["report"] = str(report_md)
    return result
