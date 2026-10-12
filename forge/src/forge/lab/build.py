"""Build detection + execution. Supports gradle, maven, and plain javac.

Result shape: {"ok": bool, "system": str, "jar": str|None,
"log": str, "errors": [str], "ms": int}
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path


def detect(project: str | Path) -> str:
    p = Path(project)
    if (p / "gradlew").is_file() or (p / "gradlew.bat").is_file():
        return "gradle-wrapper"
    if (p / "build.gradle").is_file() or (p / "build.gradle.kts").is_file():
        return "gradle"
    if (p / "pom.xml").is_file():
        return "maven"
    if (p / "plugin.yml").is_file() or (p / "src").is_dir():
        return "javac"
    return "unknown"


def _run(cmd: list[str], cwd: str | Path, timeout: int) -> tuple[int, str, int]:
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=str(cwd))
        return r.returncode, (r.stdout or "") + (r.stderr or ""), int((time.time() - t) * 1000)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace") if e.stdout else ""
        return 124, out + f"\n[TIMEOUT after {timeout}s]", int((time.time() - t) * 1000)
    except FileNotFoundError:
        return 127, f"executable not found: {cmd[0]}", 0


def _find_jar(project: Path) -> str | None:
    cands = sorted(project.glob("build/libs/*.jar"))
    cands = [c for c in cands if "sources" not in c.name and "javadoc" not in c.name]
    if cands:
        return str(cands[0])
    cands = sorted(project.glob("target/*.jar"))
    cands = [c for c in cands if "sources" not in c.name]
    return str(cands[0]) if cands else None


def _errors(log: str) -> list[str]:
    out = []
    for line in log.splitlines():
        if re.search(r"error:|FAILED|BUILD FAILED|COMPILATION ERROR|ERROR\]",
                     line, re.IGNORECASE):
            out.append(line.strip()[:300])
    return out[:20]


def build_plugin(project: str | Path, timeout: int = 900,
                 gradle_bin: str = "gradle") -> dict:
    """Clean build. Never claims success without a real jar on disk."""
    p = Path(project)
    system = detect(p)
    if system == "unknown":
        return {"ok": False, "system": system, "jar": None, "log": "",
                "errors": ["no build system detected"], "ms": 0}
    if system == "gradle-wrapper":
        exe = str(p / "gradlew.bat") if (p / "gradlew.bat").is_file() else str(p / "gradlew")
        code, log, ms = _run([exe, "clean", "build", "--no-daemon"], p, timeout)
    elif system == "gradle":
        exe = gradle_bin if not Path(gradle_bin).is_dir() else str(Path(gradle_bin) / "bin" / "gradle.bat")
        code, log, ms = _run([exe, "clean", "build", "--no-daemon"], p, timeout)
    elif system == "maven":
        mvn = shutil.which("mvn") or "mvn"
        code, log, ms = _run([mvn, "-B", "clean", "package"], p, timeout)
    else:
        return {"ok": False, "system": system, "jar": None, "log": "",
                "errors": ["javac-direct builds need explicit sources; "
                           "use compile_fixture() or add gradle/maven"], "ms": 0}
    jar = _find_jar(p) if code == 0 else None
    ok = code == 0 and jar is not None and Path(jar).stat().st_size > 0
    return {"ok": ok, "system": system, "jar": jar, "log": log[-20000:],
            "errors": [] if ok else (_errors(log) or [f"exit code {code}, no jar"]),
            "ms": ms}


def compile_fixture(src_dir: str | Path, out_jar: str | Path,
                    classpath: list[str], java_bin: str = "javac",
                    timeout: int = 300) -> dict:
    """Compile a fixture plugin directly with javac (no build system needed)."""
    import tempfile
    import zipfile
    src = Path(src_dir)
    java_files = sorted(src.rglob("*.java"))
    resources = [f for f in sorted(src.rglob("*"))
                 if f.is_file() and f.suffix in (".yml", ".yaml", ".json")]
    if not java_files:
        return {"ok": False, "jar": None, "log": "", "errors": ["no .java sources"], "ms": 0}
    t = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [java_bin, "-encoding", "UTF-8", "-d", tmp]
        if classpath:
            cmd += ["-cp", ";".join(classpath)]
        cmd += [str(f) for f in java_files]
        code, log, _ = _run(cmd, src, timeout)
        if code != 0:
            return {"ok": False, "jar": None, "log": log[-8000:],
                    "errors": _errors(log) or [f"javac exit {code}"], "ms": 0}
        for f in resources:
            dst = Path(tmp) / f.relative_to(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
        out = Path(out_jar)
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(Path(tmp).rglob("*")):
                if f.is_file():
                    z.write(f, str(f.relative_to(tmp)))
    ms = int((time.time() - t) * 1000)
    return {"ok": True, "jar": str(out), "log": log[-8000:], "errors": [], "ms": ms}
