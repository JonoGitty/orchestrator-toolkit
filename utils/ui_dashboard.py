#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


URL_RE = re.compile(r"https?://[^\s'\"]+", re.I)


def _tail_lines(p: Path, n: int = 50) -> List[str]:
    try:
        data = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        return data[-n:]
    except Exception:
        return []


def _render(stdscr, base_dir: Path) -> None:
    import curses

    curses.curs_set(0)
    stdscr.nodelay(True)  # non-blocking for auto-refresh
    stdscr.keypad(True)

    logp = base_dir / "runtime" / "command_log.jsonl"
    offset = 0
    auto = True
    refresh_ms = 1000
    last_draw = 0.0
    filter_text: Optional[str] = None

    def open_url(url: str) -> None:
        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", url])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            elif os.name == "nt":
                subprocess.Popen(["cmd", "/c", "start", "", url])
        except Exception:
            pass

    def draw() -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        title = (
            "AI Orchestrator — Dashboard  "
            + "(q: quit, r: refresh, a: auto, f: filter, o: open URL, ↑/↓: scroll)"
        )
        stdscr.addnstr(0, 0, title.ljust(w), w, curses.A_REVERSE)
        stdscr.addnstr(1, 0, f"Workspace: {base_dir}", w)
        stdscr.addnstr(2, 0, f"Log: {logp}", w)
        stdscr.hline(3, 0, ord('-'), w)

        # Content area: show recent log entries decoded
        lines = _tail_lines(logp, 600)
        # Attempt to show friendly summary per line
        rows: List[str] = []
        for ln in lines:
            try:
                obj = json.loads(ln)
                cmd = " ".join(str(x) for x in obj.get("cmd", []))
                rc = obj.get("rc", "")
                ts = obj.get("ts", "")
                mode = obj.get("mode", "")
                rows.append(f"{ts}  rc={rc:>3}  {mode:<6}  {cmd}")
            except Exception:
                rows.append(ln)

        # Apply filter
        if filter_text:
            ft = filter_text.lower()
            rows = [r for r in rows if ft in r.lower()]

        start = max(0, min(max(0, len(rows) - (h - 5)), offset))
        view = rows[start:start + (h - 5)]
        for i, row in enumerate(view, 4):
            stdscr.addnstr(i, 0, row, w)
        # Footer
        auto_txt = "ON" if auto else "OFF"
        filt_txt = filter_text or "(none)"
        stdscr.hline(h - 2, 0, ord('-'), w)
        stdscr.addnstr(h - 1, 0, f"Auto-refresh: {auto_txt}   Filter: {filt_txt}", w)
        stdscr.refresh()

    draw()
    while True:
        # Auto-refresh
        now = time.time()
        if auto and (now - last_draw) >= (refresh_ms / 1000.0):
            last_draw = now
            draw()

        ch = stdscr.getch()
        if ch == -1:
            time.sleep(0.05)
            continue
        if ch in (ord('q'), ord('Q')):
            break
        elif ch in (ord('r'), ord('R')):
            draw()
        elif ch in (ord('a'), ord('A')):
            auto = not auto
            draw()
        elif ch in (ord('f'), ord('F')):
            # Prompt for filter
            curses.echo()
            h, w = stdscr.getmaxyx()
            stdscr.addnstr(h - 1, 0, "Filter text (empty to clear): ".ljust(w), w)
            stdscr.clrtoeol()
            try:
                s = stdscr.getstr(h - 1, len("Filter text (empty to clear): "), 200)
                filter_text = (s.decode("utf-8", errors="ignore").strip() or None) if s else None
            except Exception:
                filter_text = None
            curses.noecho()
            draw()
        elif ch in (ord('o'), ord('O')):
            # Try to extract the last URL from the log and open it
            text = "\n".join(_tail_lines(logp, 200))
            m = None
            for m in URL_RE.finditer(text):
                pass
            if m:
                url = m.group(0).replace("0.0.0.0", "localhost")
                open_url(url)
            draw()
        elif ch in (259,):  # KEY_UP
            offset = max(0, offset - 1)
            draw()
        elif ch in (258,):  # KEY_DOWN
            offset = offset + 1
            draw()
        elif ch in (338,):  # KEY_NPAGE
            offset = offset + 10
            draw()
        elif ch in (339,):  # KEY_PPAGE
            offset = max(0, offset - 10)
            draw()


def run_dashboard(base_dir: Path) -> None:
    """Launch a minimal curses dashboard that tails the command runner log."""
    try:
        import curses  # noqa: F401
    except Exception:
        print("Dashboard requires a real terminal with curses support.")
        print("Tip: Run in a terminal (not in an IDE output panel).")
        return
    import curses
    curses.wrapper(_render, base_dir)
