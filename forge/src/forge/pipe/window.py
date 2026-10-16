"""FORGE pipe window: the human face of the conveyor.

Tkinter only (stdlib, zero deps). NOTHING here runs at import time —
`main()` builds the Tk root, so AI/headless use never opens a window.

- `forge pipe run`  -> headless, JSON, exit codes (for AI/MCP/CI).
- `forge pipe window` -> this window (for humans).
"""
from __future__ import annotations

import json
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

ICON = {"PENDING": "\u25cb", "RUN": "\u25b6", "SUCCESS": "\u2713",
        "FAILED": "\u2717", "ERROR": "\u26a0", "TIMEOUT": "\u23f1",
        "CANCELLED": "\u25a0", "SKIP": "\u21a9", "SKIPPED": "\u23ed"}


def icon(status: str) -> str:
    """Pure helper (unit-tested without any window)."""
    return ICON.get(status, "?")


def fmt_entry(entry: dict) -> str:
    """Pure helper: one-line stage summary for the list."""
    ms = entry.get("duration_ms", 0)
    extra = " (чекпоинт)" if entry.get("resumed") else ""
    extra = " (кэш)" if entry.get("cached") else extra
    return f"{icon(entry.get('status', '?'))} {entry.get('title', entry.get('name', '?'))} — {ms}мс{extra}"


def load_history_rows(target: str, limit: int = 50) -> list[str]:
    """Pure helper: строки истории прогонов (без окна, тестируется)."""
    import datetime as _dt
    p = Path(target) / ".forge-pipe-history.jsonl"
    if not p.is_file():
        return []
    rows = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        ts = _dt.datetime.fromtimestamp(r.get("ts", 0)).strftime("%m-%d %H:%M")
        ok = sum(1 for s in r.get("stages", []) if s.get("status") == "SUCCESS")
        n = len(r.get("stages", []))
        rows.append(f"{ts} · {r.get('status')} · {r.get('duration_ms')}мс · {ok}/{n}")
    return rows


class PipeWindow:
    def __init__(self, target: str, forge_root: str, resume: bool = False):
        from forge.pipe.runner import PipeRunner
        from forge.pipe.stages import DEFAULT_STAGES
        self.target = target
        self.events: queue.Queue = queue.Queue()
        self.report_path = str(Path(target) / "forge-pipe-report.json")
        self.runner = PipeRunner(
            DEFAULT_STAGES,
            {"target": target, "forge_root": forge_root},
            checkpoint=str(Path(target) / "forge-pipe-checkpoint.json"),
            on_event=self.events.put,
        )
        self.titles = {s.name: s.title for s in DEFAULT_STAGES}
        self._resume = resume  # стартовый флаг (CLI --resume); кнопки меняют его в start()
        self._t0 = 0.0
        self.thread: threading.Thread | None = None
        self.states: dict[str, str] = {s.name: "PENDING" for s in DEFAULT_STAGES}
        self._build()

    # ---------- UI construction (window opens HERE, nowhere else) ----------
    def _build(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"FORGE конвейер — {self.target}")
        self.root.geometry("920x640")
        self.root.minsize(760, 520)
        # тёмная тема premium developer studio (графит + фиолет/циан)
        bg, fg, acc, acc2 = "#16161e", "#e2e8f0", "#8b5cf6", "#22d3ee"
        self.root.configure(bg=bg)
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TFrame", background=bg)
        st.configure("TLabel", background=bg, foreground=fg)
        st.configure("TButton", background="#23232e", foreground=fg)
        st.configure("Horizontal.TProgressbar", background=acc2)
        st.configure("TNotebook", background=bg)
        st.configure("TNotebook.Tab", background="#23232e", foreground=fg,
                     padding=(10, 4))
        st.map("TNotebook.Tab",
               background=[("selected", "#8b5cf6")],
               foreground=[("selected", "white")])
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=f"Проект: {self.target}").pack(side="left")
        self.status = ttk.Label(top, text="готов")
        self.status.pack(side="right")
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)
        tab_pipe = ttk.Frame(nb, padding=2)
        tab_hist = ttk.Frame(nb, padding=8)
        nb.add(tab_pipe, text="Конвейер")
        nb.add(tab_hist, text="История")
        self.nb = nb
        mid = ttk.Frame(tab_pipe, padding=8)
        mid.pack(fill="both", expand=True)
        self.stages = tk.Listbox(mid, width=34, font=("Consolas", 11),
                                 bg="#1e1e28", fg=fg, selectbackground=acc,
                                 highlightthickness=0, borderwidth=0)
        self.stages.pack(side="left", fill="y")
        self.stages.bind("<<ListboxSelect>>", lambda _e: self._show_details())
        self.log = scrolledtext.ScrolledText(mid, font=("Consolas", 10),
                                             bg="#101016", fg=fg,
                                             insertbackground=fg,
                                             state="disabled")
        self.log.pack(side="left", fill="both", expand=True, padx=(8, 0))
        bot = ttk.Frame(tab_pipe, padding=8)
        bot.pack(fill="x")
        self.bar = ttk.Progressbar(bot, maximum=len(self.states), value=0)
        self.bar.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(bot)
        row.pack()
        self.btn_run = ttk.Button(row, text="▶ Запустить", command=lambda: self.start(resume=False))
        self.btn_run.pack(side="left", padx=4)
        self.btn_cont = ttk.Button(row, text="⏵ Продолжить", command=lambda: self.start(resume=True))
        self.btn_cont.pack(side="left", padx=4)
        self.btn_stop = ttk.Button(row, text="■ Стоп", command=self.stop,
                                   state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        self.btn_watch = ttk.Button(row, text="👁 Следить", command=self.toggle_watch)
        self.btn_watch.pack(side="left", padx=4)
        ttk.Button(row, text="Отчёт", command=self.open_report).pack(side="left", padx=4)
        ttk.Button(row, text="Закрыть", command=self._close).pack(side="left", padx=4)
        self.watcher = None
        self.last_report: dict = {}
        # вкладка истории
        self.hist = tk.Listbox(tab_hist, font=("Consolas", 10),
                               bg="#101016", fg=fg,
                               highlightthickness=0, borderwidth=0)
        self.hist.pack(fill="both", expand=True)
        hrow = ttk.Frame(tab_hist)
        hrow.pack(fill="x", pady=(8, 0))
        ttk.Button(hrow, text="↻ Обновить", command=self._refresh_history).pack(side="left")
        nb.bind("<<NotebookTabChanged>>", lambda _e: self._refresh_history())
        self._preload()
        self._refresh_stages()
        self._refresh_cont()
        self._refresh_history()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        # БЕЗ topmost: окно не ворует фокус (особенно у полноэкранной игры).
        # Кто запустил — тот и выведет на передний план сам.
        self.root.after(120, self._poll)

    def _has_checkpoint(self) -> bool:
        return Path(self.target, "forge-pipe-checkpoint.json").is_file()

    def _refresh_cont(self) -> None:
        if hasattr(self, "btn_cont"):
            self.btn_cont.configure(state="normal" if self._has_checkpoint() else "disabled")

    # ---------- runtime ----------
    def _say(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _refresh_history(self) -> None:
        if not hasattr(self, "hist"):
            return
        self.hist.delete(0, "end")
        rows = load_history_rows(self.target)
        if not rows:
            self.hist.insert("end", "(истории пока нет — запусти конвейер)")
            return
        for r in rows:
            self.hist.insert("end", r)

    def _refresh_stages(self) -> None:
        self.stages.delete(0, "end")
        for name, st in self.states.items():
            self.stages.insert("end", f"{icon(st)} {self.titles.get(name, name)}")
        if hasattr(self, "bar"):  # страховка от порядка создания виджетов
            self.bar["value"] = sum(1 for s in self.states.values()
                                    if s not in ("PENDING", "RUN"))

    def start(self, resume: bool = False) -> None:
        if self.thread and self.thread.is_alive():
            return
        self._resume = resume and self._has_checkpoint()
        self.states = {k: "PENDING" for k in self.states}
        self._refresh_stages()
        self._refresh_cont()
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._t0 = time.time()
        self.status.configure(text="продолжаю с чекпоинта…" if self._resume else "работает…")
        self.thread = threading.Thread(target=self._work, daemon=True)
        self.thread.start()

    def _work(self) -> None:
        try:
            report = self.runner.run(resume=self._resume)
            Path(self.report_path).write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception as e:  # noqa: BLE001 - must not kill the UI thread
            self.events.put(("log", f"ОШИБКА раннера: {e}"))

    def stop(self) -> None:
        self.runner.stop()
        self._say("стоп запрошен (остановится между стадиями)")

    def toggle_watch(self) -> None:
        from forge.pipe.watch import Watcher
        if self.watcher and self.watcher.running:
            self.watcher.stop()
            self.watcher = None
            self.btn_watch.configure(text="👁 Следить")
            self._say("слежка выключена")
            return
        self.watcher = Watcher(self.target, lambda files: self.events.put(("watch", files)))
        self.watcher.start()
        self.btn_watch.configure(text="👁 Не следить")
        self._say(f"слежу за изменениями в {self.target} — прогон сам перезапустится")

    def _close(self) -> None:
        _wlog("close requested")
        try:
            if self.watcher:
                self.watcher.stop()
            self.runner.stop()
        except Exception:
            pass
        self.root.destroy()

    def open_report(self) -> None:
        p = Path(self.report_path)
        if not p.is_file():
            self._say("отчёта пока нет — запусти конвейер")
            return
        try:
            if os.name == "nt":
                os.startfile(p)  # noqa: S606 - user explicitly pressed the button
            elif sys_platform() == "darwin":
                __import__("subprocess").run(["open", str(p)])
            else:
                __import__("subprocess").run(["xdg-open", str(p)])
        except Exception as e:  # noqa: BLE001
            self._say(f"не открыл отчёт: {e}")

    def _preload(self) -> None:
        """Подхватить прошлый отчёт/чекпоинт: окно сразу показывает историю."""
        p = Path(self.report_path)
        if p.is_file():
            try:
                self.last_report = json.loads(p.read_text(encoding="utf-8"))
                for s in self.last_report.get("stages", []):
                    if s.get("name") in self.states:
                        self.states[s["name"]] = s.get("status", "?")
                self._refresh_stages()
                self._say(f"загружен прошлый отчёт: {self.last_report.get('status')} "
                          f"за {self.last_report.get('duration_ms')}мс — кликни стадию для деталей")
                return
            except (OSError, ValueError):
                pass
        cp = Path(self.target) / "forge-pipe-checkpoint.json"
        if cp.is_file():
            try:
                done = json.loads(cp.read_text(encoding="utf-8")).get("done", {})
                for name, info in done.items():
                    if name in self.states:
                        self.states[name] = info.get("status", "?")
                self._refresh_stages()
                self._say("найден чекпоинт: кнопка «Запустить» продолжит с него "
                          "(или добавь --resume в CLI)")
            except (OSError, ValueError):
                pass

    def _show_details(self) -> None:
        """Клик по стадии: детали из последнего отчёта прямо в лог."""
        sel = self.stages.curselection()
        if not sel or not self.last_report:
            return
        name = list(self.states)[sel[0] % len(self.states)]
        for s in self.last_report.get("stages", []):
            if s.get("name") == name:
                self._say(f"—— {s.get('title', name)}: {s.get('status')} ——")
                data = s.get("data") or s.get("error") or {}
                text = json.dumps(data, ensure_ascii=False, indent=2)
                self._say(text[:3000])
                if s.get("warnings"):
                    self._say("предупреждения: " + "; ".join(s["warnings"]))
                return
        self._say(f"{name}: деталей пока нет — запусти конвейер")

    def _poll(self) -> None:
        if self.thread and self.thread.is_alive() and self._t0:
            self.status.configure(text=f"работает… {int(time.time() - self._t0)}с")
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "stage_start":
                    self.states[ev[1]] = "RUN"
                    self._say(f"▶ {ev[1]}…")
                elif kind == "stage_done":
                    _, name, status = ev
                    self.states[name] = status
                    self._say(f"  {icon(status)} {name}: {status}")
                elif kind == "log":
                    self._say(str(ev[1]))
                elif kind == "watch":
                    files = ev[1]
                    self._say(f"👁 изменено файлов: {len(files)} — автопрогон")
                    if not (self.thread and self.thread.is_alive()):
                        self.start()
                elif kind == "finished":
                    rep = ev[1]
                    self.last_report = rep  # детали доступны сразу, без переоткрытия
                    self.status.configure(text=f"готово: {rep['status']} за {rep['duration_ms']}мс")
                    self._say(f"== {rep['status']} за {rep['duration_ms']}мс; отчёт: {self.report_path}")
                    self.btn_run.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                    self._refresh_cont()
                    self._refresh_history()
                self._refresh_stages()
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(120, self._poll)

    def run_ui(self) -> None:
        self.root.mainloop()


def sys_platform() -> str:
    import sys
    return sys.platform


def _wlog(msg: str) -> None:
    """Журнал жизни окна (диагностика самопроизвольных закрытий)."""
    try:
        import datetime as _dt
        import tempfile as _tf
        with open(Path(_tf.gettempdir()) / "forge-pipe-window.log",
                  "a", encoding="utf-8") as f:
            f.write(f"{_dt.datetime.now():%H:%M:%S} {msg}\n")
    except Exception:
        pass


def main(target: str, forge_root: str, resume: bool = False) -> int:
    """Entry point: window is created ONLY here."""
    _wlog(f"open target={target}")
    try:
        w = PipeWindow(target, forge_root, resume)
    except tk.TclError as e:
        print(f"нет дисплея для окна: {e}")
        print("используй headless-режим: forge pipe run <dir>")
        return 2
    w.run_ui()
    _wlog("mainloop exited")
    return 0
