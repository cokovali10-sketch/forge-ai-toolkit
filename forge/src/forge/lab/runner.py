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


def mirror(lab_root: str | Path, server_jar: str, plugin_jar: str,
           java_bin: str = "", timeout_boot: int = 420,
           extra_jars: list | None = None,
           ignore_errors: list | None = None,
           fuzz_commands: list | None = None,
           config_rel: str = "", bad_configs: list | None = None,
           enable_marker: str = "", with_load: bool = False) -> dict:
    """Server mirror: boot + scenarios + perf + fuzz + soak + config reboot.

    - fuzz_commands: base commands to matrix against junk args.
    - config_rel: plugin config path inside server dir (e.g.
      plugins/AuctionHouse/config.yml); bad_configs: list of full-file
      contents to try, rebooting each time, asserting enable_marker.
    - with_load: spawn 50-zombie crowd and measure TPS.
    Returns the standard report dict.
    """
    from . import fuzz as _fz
    from . import perf as _pf
    rep = _report.RunReport(run_id="pending")
    t = time.time()
    profile = _env.ServerProfile(server_jar=server_jar, timeout_sec=timeout_boot)
    environment = _env.create(lab_root, profile)
    rep.run_id = environment.run_id
    srv = _srv.ServerProc(environment, _srv.find_java(java_bin))
    try:
        _env.install_plugin(environment, plugin_jar)
        for dep in extra_jars or []:
            _env.install_plugin(environment, dep)
        rep.add("install", True, f"plugin + {len(extra_jars or [])} deps")
    except Exception as e:
        rep.add("install", False, f"{type(e).__name__}: {e}")
        return _finish(environment, srv, rep, t)
    st = srv.start()
    rep.add("start-server", st["ok"], str(st.get("pid", st.get("error", ""))))
    if not st["ok"]:
        return _finish(environment, srv, rep, t)
    wr = srv.wait_ready()
    rep.add("wait-ready", wr["ok"], wr.get("error", "Done seen"))
    if not wr["ok"]:
        return _finish(environment, srv, rep, t)

    base = _pf.measure(srv)
    rep.add("perf-idle", base.get("ok", False),
            f"tps={base.get('tps')} mspt={base.get('mspt')}")
    if with_load:
        load = _pf.load_crowd(srv)
        rep.add("perf-load", load["ok"],
                f"tps={load.get('tps_loaded')} mspt={load.get('mspt_loaded')}")
    if fuzz_commands:
        fz = _fz.fuzz_commands(srv, fuzz_commands, ignore_errors or [])
        rep.add("fuzz-commands", fz["ok"],
                f"{fz['tried']} variants" + ("" if fz["ok"] else
                                             f"; fails: {fz['failed'][:3]}"))
    sk = _fz.soak(srv, "plugins", "", 3, ignore_errors or [])
    rep.add("soak-plugins", sk["ok"], sk["detail"])
    for i, bad in enumerate(bad_configs or []):
        if not config_rel or not enable_marker:
            break
        cfg = environment.server_dir / config_rel
        good = cfg.read_text(encoding="utf-8") if cfg.is_file() else None
        try:
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(bad, encoding="utf-8")
            srv.stop()
            mark = len(srv.lines)
            srv.start()
            wr2 = srv.wait_ready()
            fresh = "\n".join(l for _, l in srv.lines[mark:])
            ok = wr2["ok"] and enable_marker in fresh
            rep.add(f"config-fuzz-{i}", ok,
                    "enabled with garbage config (fresh boot evidence)" if ok else
                    f"boot/log problem: {wr2.get('error', 'marker missing in fresh log')}")
        finally:
            if good is not None:
                cfg.write_text(good, encoding="utf-8")
    errs = srv.errors(ignore_errors)
    parse_note = ""
    if bad_configs:
        joined = " ".join(errs)
        if "config.yml" in joined and ("Parser" in joined or "parsing" in joined):
            errs = [e for e in errs
                    if not ("config.yml" in e or "InvalidConfigurationException" in e
                            or ("Caused by" in e and ("Parser" in e or "parsing" in e
                                                      or "snakeyaml" in e)))]
            parse_note = "config-fuzz parse errors expected (covered) | "
        errs = [e for e in errs if "InvalidConfigurationException" not in e]
        parse_note = "config-fuzz parse errors expected (covered) | "
    rep.add("no-server-errors", not errs,
            (("ignored: " + "; ".join(ignore_errors) + " | ") if ignore_errors else "")
            + parse_note
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
