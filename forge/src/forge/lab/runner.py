"""End-to-end lab run: fixture compile -> env -> boot -> command -> report.

Proves levels 2-5 on a real server for real. GUI/client steps stay
NOT_IMPLEMENTED (no Mineflayer here) and are reported as such.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import build as _build
from . import env as _env
from . import report as _report
from . import scenarios as _sc
from . import server as _srv


def e2e_fixture(lab_root: str | Path, server_jar: str, fixture_src: str | Path,
                java_bin: str = "", timeout_boot: int = 420,
                api_jar: str = "") -> dict:
    rep = _report.RunReport(run_id="pending")
    t = time.time()
    profile = _env.ServerProfile(server_jar=server_jar, timeout_sec=timeout_boot)
    environment = _env.create(lab_root, profile)
    rep.run_id = environment.run_id
    srv = _srv.ServerProc(environment, _srv.find_java(java_bin))

    # 1. compile fixture (against paper-api, never the bootstrapper)
    out_jar = environment.artifacts_dir / "labping-0.1.0.jar"
    api = api_jar or str(Path(server_jar).parent / "api" /
                         f"paper-api-{profile.minecraft}.jar")
    if not Path(api).is_file():
        rep.add("compile-fixture", False,
                f"paper-api missing: {api} (fetch from repo.papermc.io first)")
        return _finish(environment, srv, rep, t)
    api_dir = str(Path(api).parent)
    import glob as _glob
    cp = sorted(set(_glob.glob(api_dir + "/*.jar")))
    comp = _build.compile_fixture(
        fixture_src, out_jar, sorted(set(cp)),
        "javac" if not java_bin else str(Path(java_bin).parent / "javac.exe"))
    rep.add("compile-fixture", comp["ok"],
            comp["jar"] or "; ".join(comp["errors"]), comp["ms"])
    if not comp["ok"]:
        return _finish(environment, srv, rep, t)

    # 2. install + boot
    try:
        name = _env.install_plugin(environment, comp["jar"])
        rep.add("install-plugin", True, name)
    except Exception as e:
        rep.add("install-plugin", False, f"{type(e).__name__}: {e}")
        return _finish(environment, srv, rep, t)
    st = srv.start()
    rep.add("start-server", st["ok"], str(st.get("pid", st.get("error", ""))))
    if not st["ok"]:
        return _finish(environment, srv, rep, t)
    wr = srv.wait_ready()
    rep.add("wait-ready", wr["ok"], wr.get("error", "Done seen"))
    if not wr["ok"]:
        return _finish(environment, srv, rep, t)

    # 3. scenarios: plugin load + command roundtrip
    for sc in (_sc.plugin_load("LabPing", "LabPing"),
               _sc.command_check("labping hello", "labpong hello")):
        r = _sc.run(srv, sc)
        rep.add(f"scenario:{r.name}", r.status == "PASS",
                (r.actual or "")[:800] + (" | " + r.expected if r.status != "PASS" else ""), r.ms)

    # 4. server errors observed during run
    errs = srv.errors()
    rep.add("no-server-errors", not errs, "; ".join(errs[:5]) or "log clean")
    return _finish(environment, srv, rep, t)


def e2e_jar(lab_root: str | Path, server_jar: str, plugin_jar: str,
            scenarios: list, java_bin: str = "", timeout_boot: int = 420,
            extra_jars: list | None = None,
            ignore_errors: list | None = None) -> dict:
    """Boot a prebuilt plugin jar and run scenarios against it."""
    rep = _report.RunReport(run_id="pending")
    t = time.time()
    profile = _env.ServerProfile(server_jar=server_jar, timeout_sec=timeout_boot)
    environment = _env.create(lab_root, profile)
    rep.run_id = environment.run_id
    srv = _srv.ServerProc(environment, _srv.find_java(java_bin))
    try:
        name = _env.install_plugin(environment, plugin_jar)
        rep.add("install-plugin", True, name)
        for dep in extra_jars or []:
            _env.install_plugin(environment, dep)
        rep.add("install-deps", True, str(len(extra_jars or [])))
    except Exception as e:
        rep.add("install-plugin", False, f"{type(e).__name__}: {e}")
        return _finish(environment, srv, rep, t)
    st = srv.start()
    rep.add("start-server", st["ok"], str(st.get("pid", st.get("error", ""))))
    if not st["ok"]:
        return _finish(environment, srv, rep, t)
    wr = srv.wait_ready()
    rep.add("wait-ready", wr["ok"], wr.get("error", "Done seen"))
    if not wr["ok"]:
        return _finish(environment, srv, rep, t)
    for sc in scenarios:
        r = _sc.run(srv, sc)
        rep.add(f"scenario:{r.name}", r.status == "PASS",
                (r.actual or "")[:800] + (" | " + r.expected if r.status != "PASS" else ""), r.ms)
    errs = srv.errors(ignore_errors)
    rep.add("no-server-errors", not errs,
            (("ignored: " + "; ".join(ignore_errors) + " | ") if ignore_errors else "")
            + ("; ".join(errs[:5]) or "log clean"))
    return _finish(environment, srv, rep, t)


def _finish(environment, srv, rep, t0) -> dict:
    logs = ""
    try:
        logs = srv.full_log()
        (environment.artifacts_dir / "server.log").write_text(logs[-200000:], encoding="utf-8")
    except Exception:
        pass
    try:
        st = srv.stop()
        rep.add("stop-server", st["ok"], str(st))
    except Exception as e:
        rep.add("stop-server", False, f"{type(e).__name__}: {e}")
    try:
        _env.destroy(environment, keep_artifacts=True)
        rep.add("destroy-env", True, "server dir removed, artifacts kept")
    except Exception as e:
        rep.add("destroy-env", False, f"{type(e).__name__}: {e}")
    total = int((time.time() - t0) * 1000)
    path = rep.save(environment.artifacts_dir)
    return {"ok": rep.passed(), "run_id": environment.run_id,
            "report": path, "artifacts": str(environment.artifacts_dir),
            "ms": total, "checks": rep.checks}
