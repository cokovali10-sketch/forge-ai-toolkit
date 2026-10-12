"""Isolated test environments. One dir per run, always destroyable.

Layout per run: <lab_root>/<run_id>/{server/,artifacts/}
server/: server jar, eula.txt, server.properties, plugins/
artifacts/: config snapshot, build log, server log, report.md
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerProfile:
    minecraft: str = "1.21.11"
    flavor: str = "purpur"  # purpur | paper
    server_jar: str = ""  # full path to a pre-downloaded server jar
    java_bin: str = ""  # java executable; "" = current interpreter's java
    xmx_mb: int = 1024
    xms_mb: int = 512
    timeout_sec: int = 300
    online_mode: bool = False


@dataclass
class TestEnv:
    root: Path
    run_id: str
    profile: ServerProfile
    server_dir: Path = field(init=False)
    artifacts_dir: Path = field(init=False)
    created_at: float = field(init=False)

    def __post_init__(self) -> None:
        self.server_dir = self.root / self.run_id / "server"
        self.artifacts_dir = self.root / self.run_id / "artifacts"
        self.created_at = time.time()


def create(root: str | Path, profile: ServerProfile) -> TestEnv:
    """Create dirs + eula + server.properties. No server started."""
    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    env = TestEnv(Path(root), run_id, profile)
    plugins = env.server_dir / "plugins"
    plugins.mkdir(parents=True)
    (env.server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (env.server_dir / "server.properties").write_text(
        "online-mode=false\nmotd=FORGE Testing Lab\n"
        "max-players=5\nspawn-protection=0\n",
        encoding="utf-8",
    )
    env.artifacts_dir.mkdir(parents=True)
    (env.artifacts_dir / "profile.json").write_text(
        json.dumps({"minecraft": profile.minecraft, "flavor": profile.flavor,
                    "xmx_mb": profile.xmx_mb, "timeout_sec": profile.timeout_sec,
                    "run_id": run_id}, indent=2),
        encoding="utf-8",
    )
    return env


def install_plugin(env: TestEnv, jar: str | Path) -> str:
    """Copy a plugin jar into the env. Returns installed file name."""
    src = Path(jar)
    if not src.is_file():
        raise FileNotFoundError(f"plugin jar not found: {jar}")
    dst = env.server_dir / "plugins" / src.name
    shutil.copy2(src, dst)
    return src.name


def destroy(env: TestEnv, keep_artifacts: bool = True) -> None:
    """Remove the server dir. Artifacts survive only if requested."""
    shutil.rmtree(env.server_dir, ignore_errors=True)
    if not keep_artifacts:
        shutil.rmtree(env.artifacts_dir, ignore_errors=True)
