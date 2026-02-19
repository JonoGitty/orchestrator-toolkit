#!/usr/bin/env python3
# Full-featured Orchestrator:
# - Reads prompt (CLI args > stdin > interactive)
# - Prompts for Save policy (A/S/D/K)
# - Fetches normalized plan from cloud_client.get_plan()
# - Classifies as PROGRAM vs ONE_OFF (simple heuristics)
# - Chooses SAVED/ vs RUNNING/ as root based on policy + classification
# - Applies plan via runtime.plan_runner.apply_plan (multi-stack build/install + launchers)
# - Prints absolute direct command + run.sh hint
# - Autoruns ./run.sh
# - Post-run retention according to policy

from __future__ import annotations
import os, sys, re, argparse, shutil, subprocess, time
from pathlib import Path
from typing import Dict, Any

from cloud_agent.cloud_client import get_plan
from runtime.plan_runner import apply_plan
from utils.backup import create_backup
from utils.runner import run_cmd, spawn_cmd
from utils.ui_dashboard import run_dashboard
from config import get_config_manager
from utils.connected import setup_email, list_inbox, setup_caldav, list_events

# ASCII banner shown in help/menu
BANNER = r"""
 █████╗ ██╗
██╔══██╗██║
███████║██║
██╔══██║██║
██║  ██║██║
╚═╝  ╚═╝╚═╝

 ██████╗ ██████╗  ██████╗ ██╗  ██╗ ███████╗ ███████╗████████╗██████╗  █████╗ ████████╗███████╗
██╔═══██╗██╔══██╗██╔════╝ ██║  ██║ ██╔════╝ ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██║   ██║██████╔╝██║      ███████║ █████╗   ███████╗   ██║   ██████╔╝███████║   ██║   █████╗  
██║   ██║██╔══██╗██║      ██╔══██║ ██╔══╝   ╚════██║   ██║   ██╔══██╗██╔══██║   ██║   ██╔══╝  
╚██████╔╝██║  ██║╚██████╗ ██║  ██║ ███████╗ ███████║   ██║   ██║  ██║██║  ██║   ██║   ███████╗
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

AI ORCHESTRATE — AI-powered full system controller
"""

# Universal project root: folder containing orchestrator.py
BASE_DIR = Path(__file__).resolve().parent

RUNNING_DIR = BASE_DIR / "RUNNING"
SAVED_DIR   = BASE_DIR / "SAVED"

RUNNING_DIR.mkdir(exist_ok=True, parents=True)
SAVED_DIR.mkdir(exist_ok=True, parents=True)

# Session state for interactive helpers
LAST_APPS: list[dict] = []
LAST_SERVER: dict = {"pid": 0, "url": ""}
LAST_WINDOWS: list[dict] = []  # [{id, cls, title}]


# ---------- classification heuristics ----------
PROG_HINT_IMPORTS = {"tkinter","flask","fastapi","django","gradio","streamlit","PyQt5","PySide6","wx"}
PROG_PATTERNS = [
    r"\.mainloop\(", r"@app\.route", r"\bFlask\(", r"\bFastAPI\(",
    r"\bargparse\.ArgumentParser\(", r"\buvicorn\.run", r"\bgradio as gr",
    r"\bstreamlit as st", r"\bst\.", r"\bsubprocess\.(run|Popen)\("
]

# Known browsers (native and Flatpak ids)
BROWSER_BIN_CANDIDATES = [
    "brave", "brave-browser", "firefox", "chromium", "google-chrome",
    "microsoft-edge", "chrome", "vivaldi"
]
BROWSER_FLATPAK_APPIDS = [
    "com.brave.Browser", "org.mozilla.firefox", "org.chromium.Chromium",
    "com.google.Chrome", "com.vivaldi.Vivaldi"
]

def classify_code(code: str) -> str:
    if not code: return "PROGRAM"
    if any(re.search(p, code) for p in PROG_PATTERNS):
        return "PROGRAM"
    for m in re.finditer(r'^\s*(?:from|import)\s+([A-Za-z0-9_\.]+)', code, flags=re.MULTILINE):
        mod = (m.group(1) or "").split(".")[0]
        if mod in PROG_HINT_IMPORTS:
            return "PROGRAM"
    if sum(1 for ln in code.splitlines() if ln.strip()) >= 120:
        return "PROGRAM"
    return "ONE_OFF"

# ---------- UI helpers ----------
def read_user_prompt() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    print(">> What would you like me to do?")
    if sys.stdin.isatty():
        try:
            return input("> ").strip()
        except EOFError:
            return ""
    return sys.stdin.read().strip()

def prompt_save_policy(default="A") -> str | None:
    opts = "[A]uto  [S]ave  [D]elete  [K]eep/ask after run  |  [B]ack to cancel"
    try:
        r = input(
            f"Save policy:  {opts}\nChoose [A/S/D/K] or B to go back (default {default}): "
        ).strip().upper()
    except EOFError:
        r = ""
    if not r:
        r = default
    # Allow a quick back-out from generation
    if r in {"B", "BACK", "Q", "QUIT", "C", "CANCEL"}:
        return None
    return r if r in {"A", "S", "D", "K"} else default

def choose_root(policy: str, is_program: bool) -> Path:
    if policy == "S":
        return SAVED_DIR
    if policy == "D":
        return RUNNING_DIR
    if policy == "K":
        return SAVED_DIR  # we’ll ask after run but write to SAVED
    # Auto: program → SAVED, one-off → RUNNING
    return SAVED_DIR if is_program else RUNNING_DIR

# ---------- OS helpers & natural commands ----------
def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def _is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), flags=re.I))

def _normalize_url_or_search(text: str) -> str:
    t = text.strip()
    if _is_url(t):
        return t
    # File path? leave to _open_path caller
    if "/" in t or t.startswith("~"):
        return t
    # Otherwise treat as web search
    q = re.sub(r"\s+", "+", t)
    return f"https://duckduckgo.com/?q={q}"

def _open_url(url: str) -> None:
    try:
        if sys.platform.startswith("linux"):
            spawn_cmd(["xdg-open", url])
        elif sys.platform == "darwin":
            spawn_cmd(["open", url])
        elif os.name == "nt":
            spawn_cmd(["cmd","/c","start","", url])
    except Exception:
        pass

def _open_path(p: Path) -> None:
    try:
        if sys.platform.startswith("linux"):
            spawn_cmd(["xdg-open", str(p)])
        elif sys.platform == "darwin":
            spawn_cmd(["open", str(p)])
        elif os.name == "nt":
            spawn_cmd(["explorer", str(p)])
    except Exception:
        pass

def _gtk_launch(app_id: str) -> bool:
    if not _have("gtk-launch"):
        return False
    try:
        spawn_cmd(["gtk-launch", app_id]); return True
    except Exception:
        return False

def _flatpak_find_app_id(query: str) -> str | None:
    if not _have("flatpak"):
        return None
    try:
        res = run_cmd(["flatpak","list","--app","--columns=name,application"], mode="read")
        out = res.get("stdout", "")
        q = query.lower()
        exact = None
        contains = None
        for ln in out.splitlines():
            parts = ln.split()
            if len(parts) < 2:
                continue
            name = " ".join(parts[:-1])
            appid = parts[-1]
            if name.lower() == q or appid.lower() == q:
                exact = appid
                break
            if q in name.lower() or q in appid.lower():
                if not contains:
                    contains = appid
        return exact or contains
    except Exception:
        return None

def _find_browser(isolated: bool = False) -> tuple[list[str], bool]:
    """Return (argv_prefix, is_flatpak). For isolated, prefer flatpak; else firejail+native.
    If nothing found, return ([], False)."""
    # Prefer Flatpak sandbox for isolated if available
    if _have("flatpak"):
        for appid in BROWSER_FLATPAK_APPIDS:
            try:
                out = subprocess.check_output(["flatpak", "info", appid], text=True, stderr=subprocess.DEVNULL)
                if out:
                    return (["flatpak", "run", appid], True)
            except Exception:
                continue
    # Native binaries
    for bin_name in BROWSER_BIN_CANDIDATES:
        path = shutil.which(bin_name)
        if path:
            if isolated and _have("firejail"):
                return (["firejail", "--private", path], False)
            return ([path], False)
    return ([], False)

def _launch_browser(url_or_query: str, isolated: bool = False) -> None:
    target = _normalize_url_or_search(url_or_query)
    # If given a path-like without schema, delegate to open path
    if not _is_url(target) and ("/" in target or target.startswith("~")):
        _open_path(Path(os.path.expanduser(target)))
        return
    launcher, is_flatpak = _find_browser(isolated=isolated)
    if launcher:
        try:
            spawn_cmd([*launcher, target])
            return
        except Exception:
            pass
    # Fallback to system opener
    _open_url(target)

def _do_openapp(arg: str) -> bool:
    arg = arg.strip()
    if not arg:
        return False
    # Try direct binary
    try:
        if spawn_cmd([arg]) == 0:
            return True
    except Exception:
        pass
    # Try flatpak by id lookup
    app_id = _flatpak_find_app_id(arg)
    if app_id and _have("flatpak"):
        try:
            if spawn_cmd(["flatpak","run", app_id]) == 0:
                return True
        except Exception:
            pass
    # Try gtk-launch
    if _gtk_launch(arg):
        return True
    return False

def _list_desktop_apps(filter_text: str | None = None) -> None:
    """Scan .desktop files and print a list; store in LAST_APPS for /openapp."""
    LAST_APPS.clear()
    roots = [
        Path.home()/".local/share/applications",
        Path("/usr/share/applications"),
    ]
    flt = (filter_text or "").strip().lower() or None
    seen = set()
    entries: list[tuple[str,str,str]] = []  # (name, app_id, exec)
    for r in roots:
        try:
            for f in r.glob("**/*.desktop"):
                try:
                    txt = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                name = ""
                exec_line = ""
                for ln in txt.splitlines():
                    if ln.startswith("Name=") and not name:
                        name = ln.split("=",1)[1].strip()
                    if ln.startswith("Exec=") and not exec_line:
                        exec_line = ln.split("=",1)[1].strip()
                app_id = f.stem
                if not name and app_id:
                    name = app_id
                if not name:
                    continue
                if flt and flt not in name.lower() and flt not in app_id.lower():
                    continue
                key = (name, app_id)
                if key in seen:
                    continue
                seen.add(key)
                # Strip desktop placeholders like %U %f
                exec_clean = re.sub(r"\s+%[UufF]", "", exec_line).strip()
                entries.append((name, app_id, exec_clean))
        except Exception:
            continue
    # sort and keep up to 200
    entries.sort(key=lambda t: t[0].lower())
    entries = entries[:200]
    for i, (name, app_id, exec_line) in enumerate(entries, 1):
        print(f"  {i:3d}. {name}    ({app_id})")
        LAST_APPS.append({"name": name, "app_id": app_id, "exec": exec_line})

def _openapp_by_index_or_name(tok: str) -> None:
    if tok.isdigit():
        idx = int(tok) - 1
        if 0 <= idx < len(LAST_APPS):
            ent = LAST_APPS[idx]
            # Prefer gtk-launch with app_id
            if ent.get("app_id") and _gtk_launch(ent["app_id"]):
                return
            # Fallback: flatpak run by id
            if ent.get("app_id") and _flatpak_find_app_id(ent["app_id"]):
                try:
                    if spawn_cmd(["flatpak","run", ent["app_id"]]) == 0: return
                except Exception:
                    pass
            # Exec fallback
            exe = (ent.get("exec") or "").split()
            if exe:
                try:
                    if spawn_cmd(exe) == 0: return
                except Exception:
                    pass
        print("Invalid index")
    else:
        if not _do_openapp(tok):
            # Try exact match in LAST_APPS by name
            for ent in LAST_APPS:
                if ent.get("name","" ).lower() == tok.lower():
                    _openapp_by_index_or_name(str(LAST_APPS.index(ent)+1)); return
            print("App not found")

def _audio_volume_set(percent: int) -> None:
    p = max(0, min(100, int(percent)))
    if _have("pactl"):
        run_cmd(["pactl","set-sink-volume","@DEFAULT_SINK@", f"{p}%"], mode="write", confirm=False)
    elif _have("amixer"):
        run_cmd(["amixer","-D","pulse","sset","Master", f"{p}%"], mode="write", confirm=False)

def _audio_volume_change(delta: int) -> None:
    d = int(delta)
    sign = "+" if d >= 0 else "-"
    val = abs(d)
    if _have("pactl"):
        run_cmd(["pactl","set-sink-volume","@DEFAULT_SINK@", f"{sign}{val}%"], mode="write", confirm=False)
    elif _have("amixer"):
        run_cmd(["amixer","-D","pulse","sset","Master", f"{val}%{sign}"], mode="write", confirm=False)

def _audio_mute(mute: bool) -> None:
    if _have("pactl"):
        run_cmd(["pactl","set-sink-mute","@DEFAULT_SINK@", "1" if mute else "0"], mode="write", confirm=False)
    elif _have("amixer"):
        run_cmd(["amixer","-D","pulse","sset","Master", "mute" if mute else "unmute"], mode="write", confirm=False)

def _brightness_set(percent: int) -> None:
    p = max(1, min(100, int(percent)))
    if _have("brightnessctl"):
        run_cmd(["brightnessctl","set", f"{p}%"], mode="write", confirm=False)
    else:
        # Fallback via sysfs (Linux)
        try:
            base = Path("/sys/class/backlight")
            for dev in base.iterdir():
                maxv = int((dev/"max_brightness").read_text().strip())
                val = int(maxv * (p/100.0))
                (dev/"brightness").write_text(str(val))
                break
        except Exception:
            pass

def _brightness_change(delta: int) -> None:
    if _have("brightnessctl"):
        sign = "+" if int(delta) >= 0 else "-"
        run_cmd(["brightnessctl","set", f"{abs(int(delta))}%{sign}"], mode="write", confirm=False)

# ---------- Bluetooth helpers ----------
def _btctl_lines(cmd_args: list[str]) -> list[str]:
    if not _have("bluetoothctl"):
        print("Bluetooth not available (missing bluetoothctl).")
        return []
    try:
        res = run_cmd(["bluetoothctl", *cmd_args], mode="read")
        return [ln.strip() for ln in res.get("stdout", "").splitlines() if ln.strip()]
    except Exception:
        return []

def _bluetooth_power(on: bool) -> None:
    if not _have("bluetoothctl"):
        print("Bluetooth not available (missing bluetoothctl).")
        return
    run_cmd(["bluetoothctl","power","on" if on else "off"], mode="write", confirm=False)
    print("Bluetooth:", "ON" if on else "OFF")

def _bluetooth_devices() -> list[tuple[str,str]]:
    # Returns list of (mac, name)
    lines = _btctl_lines(["devices"]) or []
    out: list[tuple[str,str]] = []
    for ln in lines:
        # Device XX:XX:... Name
        parts = ln.split(None, 2)
        if len(parts) >= 3 and parts[0].lower() == "device":
            out.append((parts[1], parts[2]))
    return out

def _bluetooth_print_devices() -> None:
    devs = _bluetooth_devices()
    if not devs:
        print("No Bluetooth devices discovered (try pairing first).")
        return
    print("Bluetooth devices:")
    for mac, name in devs[:50]:
        print(f"  {mac}  {name}")

def _resolve_bt_target(token: str) -> str | None:
    tok = token.strip().lower()
    # If looks like MAC
    if re.match(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$", tok):
        return token.strip()
    # Try fuzzy name match
    best = None; score = -1
    for mac, name in _bluetooth_devices():
        nm = (name or "").lower()
        sc = 0
        if nm == tok: sc = 100
        elif nm.startswith(tok): sc = 80
        elif tok in nm: sc = 60
        if sc > score:
            score = sc; best = mac
    return best

def _bluetooth_connect(token: str) -> None:
    mac = _resolve_bt_target(token)
    if not mac:
        print("Device not found."); return
    run_cmd(["bluetoothctl","connect", mac], mode="write", confirm=False)

def _bluetooth_disconnect(token: str) -> None:
    mac = _resolve_bt_target(token)
    if not mac:
        print("Device not found."); return
    run_cmd(["bluetoothctl","disconnect", mac], mode="write", confirm=False)

# ---------- Screenshot helpers ----------
def _screenshot_dir() -> Path:
    p = Path.home()/"Pictures"/"Screenshots"
    try: p.mkdir(parents=True, exist_ok=True)
    except Exception: pass
    return p

def _timestamp_name(prefix: str = "screenshot") -> str:
    import datetime
    return f"{prefix}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.png"

def _screenshot(mode: str = "full", to_clipboard: bool = False, out_path: Path | None = None) -> None:
    # Prefer Wayland grim/slurp if present on Wayland
    wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    has_grim = _have("grim")
    has_slurp = _have("slurp")
    has_wlcopy = _have("wl-copy")
    has_gs = _have("gnome-screenshot")
    if out_path is None:
        out_path = _screenshot_dir()/ _timestamp_name()

    try:
        if wayland and has_grim:
            if to_clipboard and has_wlcopy:
                if mode == "area" and has_slurp:
                    # grim -g $(slurp) - | wl-copy
                    geom = run_cmd(["slurp"], mode="read").get("stdout", "").strip()
                    if geom:
                        run_cmd(["/bin/sh","-c", f"grim -g '{geom}' - | wl-copy"], shell=False, mode="write", confirm=False)
                        print("Screenshot copied to clipboard.")
                        return
                # full/window to clipboard
                run_cmd(["/bin/sh","-c", "grim - | wl-copy"], shell=False, mode="write", confirm=False)
                print("Screenshot copied to clipboard.")
                return
            # Save to file
            if mode == "area" and has_slurp:
                geom = run_cmd(["slurp"], mode="read").get("stdout", "").strip()
                if geom:
                    run_cmd(["grim","-g", geom, str(out_path)], mode="write", confirm=False)
                    print(f"Saved: {out_path}")
                    return
            # window fallback = area select
            run_cmd(["grim", str(out_path)], mode="write", confirm=False)
            print(f"Saved: {out_path}")
            return
        # Fallback to gnome-screenshot
        if has_gs:
            if to_clipboard:
                args = ["gnome-screenshot","-c"]
                if mode == "area": args += ["-a"]
                if mode == "window": args += ["-w"]
                run_cmd(args, mode="write", confirm=False)
                print("Screenshot copied to clipboard.")
                return
            args = ["gnome-screenshot","-f", str(out_path)]
            if mode == "area": args += ["-a"]
            if mode == "window": args += ["-w"]
            run_cmd(args, mode="write", confirm=False)
            print(f"Saved: {out_path}")
            return
    except Exception as e:
        print(f"Screenshot failed: {e}")
    print("Screenshot tools not available (need grim/slurp on Wayland or gnome-screenshot).")

# ---------- Audio device helpers ----------
def _list_audio_sinks() -> list[dict]:
    if not _have("pactl"):
        print("Audio control not available (missing pactl).")
        return []
    try:
        res = run_cmd(["pactl","list","short","sinks"], mode="read")
        items: list[dict] = []
        for ln in res.get("stdout", "").splitlines():
            parts = ln.split()  # idx, name, state, ...
            if not parts: continue
            idx = parts[0]; name = parts[1] if len(parts) > 1 else ""; items.append({"index": idx, "name": name})
        return items
    except Exception:
        return []

def _print_audio_sinks() -> None:
    sinks = _list_audio_sinks()
    if not sinks:
        print("No sinks found."); return
    print("Audio outputs (sinks):")
    for s in sinks:
        print(f"  {s['index']:>2}  {s['name']}")

def _match_sink(token: str) -> str | None:
    tok = token.strip().lower()
    sinks = _list_audio_sinks()
    # direct index
    if tok.isdigit():
        for s in sinks:
            if s["index"] == tok:
                return s["name"]
    # exact name or fuzzy
    best = None; score = -1
    for s in sinks:
        nm = s["name"].lower()
        sc = 0
        if nm == tok: sc = 100
        elif nm.startswith(tok): sc = 80
        elif tok in nm: sc = 60
        # common shortcuts
        elif tok in {"speakers","speaker"} and ("speaker" in nm or "analog-stereo" in nm): sc = 50
        elif tok in {"headphones","headset"} and ("headphone" in nm or "headset" in nm or "a2dp" in nm): sc = 50
        if sc > score:
            score = sc; best = s["name"]
    return best

def _set_default_sink(sink_name: str) -> None:
    run_cmd(["pactl","set-default-sink", sink_name], mode="write", confirm=False)
    # move running streams
    res = run_cmd(["pactl","list","short","sink-inputs"], mode="read")
    for ln in res.get("stdout", "").splitlines():
        parts = ln.split()
        if not parts: continue
        sid = parts[0]
        run_cmd(["pactl","move-sink-input", sid, sink_name], mode="write", confirm=False)
    print(f"Audio output switched to: {sink_name}")

def _audio_switch_output(token: str) -> None:
    nm = _match_sink(token)
    if not nm:
        print("Audio output not found.")
        return
    _set_default_sink(nm)

# ---------- Display helpers (X11/xrandr) ----------
def _xrandr_lines() -> list[str]:
    if not _have("xrandr"):
        print("Display control not available (missing xrandr).")
        return []
    try:
        res = run_cmd(["xrandr"], mode="read")
        return res.get("stdout", "").splitlines()
    except Exception:
        return []

def _list_displays() -> list[dict]:
    out: list[dict] = []
    cur = None
    for ln in _xrandr_lines():
        if not ln: continue
        if not ln.startswith(" "):
            parts = ln.split()
            if not parts: continue
            name = parts[0]; state = parts[1:3]
            connected = "connected" in state
            cur = {"name": name, "connected": connected, "modes": []}
            out.append(cur)
        else:
            if cur is None: continue
            m = ln.strip().split()[0]
            if "x" in m and m[0].isdigit():
                cur["modes"].append(m)
    return out

def _print_displays() -> None:
    lst = _list_displays()
    if not lst:
        print("No displays found or xrandr not available."); return
    print("Displays:")
    for d in lst:
        flag = "connected" if d["connected"] else "disconnected"
        print(f"  {d['name']}: {flag}  modes: {', '.join(d['modes'][:8])}")

def _set_resolution(output: str, resolution: str) -> None:
    run_cmd(["xrandr","--output", output, "--mode", resolution], mode="write", confirm=False)
    print(f"Resolution set: {output} -> {resolution}")

def _rotate_output(output: str, direction: str) -> None:
    direc = direction.lower()
    if direc in {"left","ccw"}: direc = "left"
    elif direc in {"right","cw"}: direc = "right"
    elif direc in {"inverted","flip"}: direc = "inverted"
    else: direc = "normal"
    run_cmd(["xrandr","--output", output, "--rotate", direc], mode="write", confirm=False)
    print(f"Rotated {output} -> {direc}")

def _display_mirror() -> None:
    # Best effort: choose first two connected outputs and mirror second to first
    ds = [d for d in _list_displays() if d.get("connected")]
    if len(ds) < 2:
        print("Need at least two connected displays."); return
    primary = ds[0]["name"]; other = ds[1]["name"]
    run_cmd(["xrandr","--output", other, "--same-as", primary, "--auto"], mode="write", confirm=False)
    print(f"Mirroring {other} to {primary}")

def _display_extend(direction: str = "right") -> None:
    ds = [d for d in _list_displays() if d.get("connected")]
    if len(ds) < 2:
        print("Need at least two connected displays."); return
    primary = ds[0]["name"]; other = ds[1]["name"]
    posflag = "--right-of" if direction.lower() != "left" else "--left-of"
    run_cmd(["xrandr","--output", other, posflag, primary, "--auto"], mode="write", confirm=False)
    print(f"Extended {other} {('to the right of' if posflag=='--right-of' else 'to the left of')} {primary}")

def _handle_natural_command(s: str) -> bool:
    t = s.strip()
    if not t:
        return True
    low = t.lower()
    # Freeform intent normalization: tolerate greetings/polite chatter
    def _strip_chatter(txt: str) -> str:
        txt2 = txt.strip()
        # Remove common leading chatter
        leaders = [
            r"^(hey|hi|hello|yo|hiya)[,!\s]+",
            r"^(please|pls|plz)\s+",
            r"^(can you|could you|would you|will you|can u|could u|would u|i want you to|i'd like you to|i want to|i need you to)\s+",
            r"^(ok(?:ay)?|alright|so)\s+",
        ]
        for pat in leaders:
            txt2 = re.sub(pat, "", txt2, flags=re.I).strip()
        # Remove inline courtesies
        txt2 = re.sub(r"\bplease\b", "", txt2, flags=re.I)
        txt2 = re.sub(r"\bthanks?\b", "", txt2, flags=re.I)
        txt2 = re.sub(r"\bthank you\b", "", txt2, flags=re.I)
        # Collapse whitespace
        txt2 = re.sub(r"\s+", " ", txt2).strip()
        return txt2
    def _normalize_typos(txt: str) -> str:
        # Common typos and synonyms normalization (case-insensitive)
        pairs = [
            (r"\bpere?cent\b", "percent"),
            (r"\bprecent\b", "percent"),
            (r"\bbrigthness\b", "brightness"),
            (r"\bbrightnes\b", "brightness"),
            (r"\bbrughtness\b", "brightness"),
            (r"\bvolum\b", "volume"),
        ]
        out = txt
        for pat, repl in pairs:
            out = re.sub(pat, repl, out, flags=re.I)
        return out
    t2 = _normalize_typos(_strip_chatter(t))
    low2 = t2.lower()

    # Loose intent extraction anywhere in the sentence
    # e.g., "hello ai, i want you to search for cats on the internet"
    mloose = re.search(r"\b(search|look\s*up|google|duckduckgo)\b.*?\bfor\b\s+(.+)$", t2, flags=re.I)
    if mloose:
        q = mloose.group(2).strip()
        if q:
            _launch_browser(q, isolated=False)
            return True
    mloose2 = re.search(r"\bopen\b.*\b(browser|web\s*page|webpage|site)\b.*\b(to|for|about|at|with)\b\s+(.+)$", t2, flags=re.I)
    if mloose2:
        q = mloose2.group(3).strip()
        if q:
            _launch_browser(q, isolated=False)
            return True
    mloose3 = re.search(r"\bopen\b.*\b(file|folder|directory)\b\s+(.+)$", t2, flags=re.I)
    if mloose3:
        path = mloose3.group(2).strip()
        if path:
            _open_path(Path(os.path.expanduser(path)))
            return True
    # ===== Web & search (rich translator) =====
    # Private/incognito intent
    if re.match(r"^(?:open|launch|start)\s+(?:private|incognito|isolated)\s+(?:browser|web\s*page|webpage|site)\s+(?:to|for|about|at|with)\s+.+$", low):
        q = re.sub(r"^(?:open|launch|start)\s+(?:private|incognito|isolated)\s+(?:browser|web\s*page|webpage|site)\s+(?:to|for|about|at|with)\s+", "", t, flags=re.I)
        _launch_browser(q.strip(), isolated=True); return True
    # "search for X and Y and Z" or comma-separated
    m_multi = re.match(r"^(?:search|websearch|look\s*up|google|duckduckgo)\s+(?:for\s+)?(.+)$", low)
    if m_multi:
        qs_raw = m_multi.group(1)
        parts = [p.strip() for p in re.split(r"\s+and\s+|,", qs_raw) if p.strip()]
        if parts:
            for q in parts[:5]:
                _launch_browser(q, isolated=False)
            return True
    # "open X and Y" where X,Y look like queries (no slash commands)
    m_open_multi = re.match(r"^(?:open|launch|start)\s+(?!app\s)(.+)$", low)
    if m_open_multi and " and " in low and not _is_url(t):
        qs_raw = m_open_multi.group(1)
        parts = [p.strip() for p in re.split(r"\s+and\s+", qs_raw) if p.strip()]
        if len(parts) >= 2:
            for q in parts[:5]:
                _launch_browser(q, isolated=False)
            return True
    # Already added: combo open webpage to X and another searching for Y (kept above)
    # Quick natural synonyms for common slash commands
    if low in {"show windows","list windows","window list"}:
        _wm_list_windows(); return True
    mfocus = re.match(r"^focus\s+(.+)$", low)
    if mfocus:
        _wm_focus(mfocus.group(1).strip()); return True
    mmax = re.match(r"^(?:maximize|maximise)\s+(.+)$", low)
    if mmax:
        _wm_maximize(mmax.group(1).strip()); return True
    mmove = re.match(r"^move\s+(.+)\s+to\s+workspace\s+(\d+)$", low)
    if mmove:
        _wm_move_to_workspace(mmove.group(1).strip(), int(mmove.group(2))); return True
    if low.startswith("list apps") or low.startswith("show apps"):
        flt = t.split(None, 2)[2] if len(t.split()) > 2 else None
        _list_desktop_apps(flt); return True
    mopenapp = re.match(r"^open\s+app\s+(.+)$", low)
    if mopenapp:
        _openapp_by_index_or_name(mopenapp.group(1).strip()); return True
    mwhich = re.match(r"^(?:where is|which)\s+(.+)$", low)
    if mwhich:
        nm = mwhich.group(1).strip()
        path = shutil.which(nm) or ""
        print(path or "Not found"); return True
    if low in {"help","show help","what can you do"}:
        print_commands_help(); return True
    if low in {"open last","open last server","open last url"}:
        url = (LAST_SERVER.get("url") or "").strip()
        if url: _open_url(url)
        else: print("No last server URL saved.")
        return True
    # ===== Bluetooth =====
    if low in {"bluetooth on","enable bluetooth","turn on bluetooth"}:
        _bluetooth_power(True); return True
    if low in {"bluetooth off","disable bluetooth","turn off bluetooth"}:
        _bluetooth_power(False); return True
    if low in {"list bluetooth devices","show bluetooth devices","bluetooth devices"}:
        _bluetooth_print_devices(); return True
    mbtc = re.match(r"^(?:bluetooth\s+connect|connect\s+bluetooth)\s+(.+)$", low)
    if mbtc:
        _bluetooth_connect(mbtc.group(1).strip()); return True
    mbtd = re.match(r"^(?:bluetooth\s+disconnect|disconnect\s+bluetooth)\s+(.+)$", low)
    if mbtd:
        _bluetooth_disconnect(mbtd.group(1).strip()); return True
    # ===== Screenshots =====
    ms = re.match(r"^(?:take\s+)?screenshot(?:\s+(area|window|screen|full))?(?:\s+(?:to\s+clipboard|copy\s+to\s+clipboard))?(?:\s+save\s+to\s+(.+))?$", low)
    if ms:
        mode = ms.group(1) or "full"
        to_clip = bool(re.search(r"\bclipboard\b", low))
        path_raw = ms.group(2)
        outp = None
        if path_raw and not to_clip:
            # Named folders support
            if path_raw.strip() in {"pictures","screenshots"}:
                outp = _screenshot_dir()/ _timestamp_name()
            elif path_raw.strip() in {"desktop"}:
                outp = Path.home()/"Desktop"/ _timestamp_name()
            else:
                outp = Path(os.path.expanduser(path_raw.strip()))
                if outp.is_dir():
                    outp = outp / _timestamp_name()
        _screenshot(mode=mode if mode != "screen" else "full", to_clipboard=to_clip, out_path=outp)
        return True
    if low in {"screenshot","take screenshot","print screen"}:
        _screenshot(mode="full", to_clipboard=False, out_path=None); return True
    # ===== Audio device switching =====
    if low in {"list audio devices","list outputs","show audio devices","show outputs"}:
        _print_audio_sinks(); return True
    msw = re.match(r"^(?:switch|move|set|change)\s+(?:audio|sound|output)\s+(?:to\s+)?(.+)$", low)
    if msw:
        _audio_switch_output(msw.group(1).strip()); return True
    if low in {"use headphones","switch to headphones"}:
        _audio_switch_output("headphones"); return True
    if low in {"use speakers","switch to speakers"}:
        _audio_switch_output("speakers"); return True
    # ===== Displays / Monitors =====
    if low in {"list displays","list monitors","show displays","show monitors"}:
        _print_displays(); return True
    mres = re.match(r"^set\s+resolution\s+(\d{3,4}x\d{3,4})\s+(?:on|for)\s+([A-Za-z0-9-_.:]+)$", low)
    if mres:
        _set_resolution(mres.group(2), mres.group(1)); return True
    mrot = re.match(r"^rotate\s+([A-Za-z0-9-_.:]+)\s+(left|right|normal|inverted|cw|ccw|flip)$", low)
    if mrot:
        _rotate_output(mrot.group(1), mrot.group(2)); return True
    if low in {"mirror displays","mirror screens","enable mirroring"}:
        _display_mirror(); return True
    mext = re.match(r"^(?:extend|arrange)\s+(?:displays|screens)(?:\s+(left|right))?$", low)
    if mext:
        _display_extend(mext.group(1) or "right"); return True
    # Composite: "open a webpage to cats and dogs and do another searching for apricots"
    mcombo = re.match(r"^open\s+(?:a\s+)?(?:web\s*page|webpage|browser|site)\s+(?:to|for|about)\s+(.+?)(?:\s+and\s+(?:do\s+)?another\s+(?:web\s+)?(?:search|searching)\s+(?:for|about|on)\s+(.+))?$", low2)
    if mcombo:
        q1 = mcombo.group(1).strip()
        q2 = (mcombo.group(2) or "").strip()
        if q1:
            _launch_browser(q1, isolated=False)
        if q2:
            _launch_browser(q2, isolated=False)
        return True
    # Natural: "open the browser to X", "open browser at X"
    mb = re.match(r"^open\s+(?:the\s+)?(?:browser|firefox|chrome|chromium|brave|edge|web\s*page|webpage|site)\s+(?:to|at|with|for|about)\s+(.+)$", low2)
    if mb:
        _launch_browser(mb.group(1).strip(), isolated=False)
        return True
    # Natural: "do another search for X" (standalone follow-up)
    manother = re.match(r"^(?:do\s+)?another\s+(?:web\s+)?(?:search|searching)\s+(?:for|about|on)\s+(.+)$", low2)
    if manother:
        _launch_browser(manother.group(1).strip(), isolated=False)
        return True
    # ===== Shortcuts (natural language) =====
    if low in {"list shortcuts","show my shortcuts","show shortcuts"}:
        sc = get_config_manager().get_shortcuts()
        if not sc:
            print("No shortcuts defined. Use /shortcut set NAME URL")
        else:
            print("Shortcuts:")
            for k in sorted(sc.keys(), key=lambda s: s.lower()):
                print(f"  {k:15} -> {sc[k]}")
        return True
    mset2 = re.match(r"^(?:add|create|save|set)\s+shortcut\s+([A-Za-z0-9_-]+)\s*:\s*(\S+)$", low)
    if mset2:
        name = mset2.group(1)
        url = mset2.group(2)
        try:
            mgr = get_config_manager(); cur = mgr.get_shortcuts(); cur[name.lower()] = url
            mgr.update_config({"shortcuts": cur}); print(f"Set shortcut '{name}' -> {url}")
        except Exception as e:
            print(f"Failed to set shortcut: {e}")
        return True
    mrm2 = re.match(r"^(?:remove|delete|rm)\s+shortcut\s+([A-Za-z0-9_-]+)$", low)
    if mrm2:
        name = mrm2.group(1); mgr = get_config_manager(); cur = mgr.get_shortcuts()
        if cur.pop(name.lower(), None) is not None:
            mgr.update_config({"shortcuts": cur}); print(f"Removed shortcut '{name}'.")
        else:
            print("No such shortcut.")
        return True
    # URL shortcut management via natural language (original exact matcher)
    mset = re.match(r"^set\s+shortcut\s+([A-Za-z0-9_-]+)\s+to\s+(\S+)$", low)
    if mset:
        name = mset.group(1)
        # Use original text to preserve URL
        parts = t.split()
        try:
            idx = parts.index("to")
            url = " ".join(parts[idx+1:])
        except Exception:
            url = mset.group(2)
        try:
            mgr = get_config_manager()
            cur = mgr.get_shortcuts()
            cur[name.lower()] = url
            mgr.update_config({"shortcuts": cur})
            print(f"Set shortcut '{name}' -> {url}")
        except Exception as e:
            print(f"Failed to set shortcut: {e}")
        return True
    mrm = re.match(r"^(remove|delete|rm)\s+shortcut\s+([A-Za-z0-9_-]+)$", low)
    if mrm:
        name = mrm.group(2)
        mgr = get_config_manager()
        cur = mgr.get_shortcuts()
        if cur.pop(name.lower(), None) is not None:
            mgr.update_config({"shortcuts": cur})
            print(f"Removed shortcut '{name}'.")
        else:
            print("No such shortcut.")
        return True
    if low in {"list shortcuts","show shortcuts"}:
        sc = get_config_manager().get_shortcuts()
        if not sc:
            print("No shortcuts defined. Use /shortcut set NAME URL")
        else:
            print("Shortcuts:")
            for k in sorted(sc.keys(), key=lambda s: s.lower()):
                print(f"  {k:15} -> {sc[k]}")
        return True
    # Web search / browser open
    if low.startswith("search ") or low.startswith("web ") or low.startswith("browser "):
        q = t.split(None, 1)[1]
        _launch_browser(q, isolated=False)
        return True
    if low.startswith("webiso ") or low.startswith("private search ") or low.startswith("browser iso "):
        q = t.split(None, 1)[1]
        _launch_browser(q, isolated=True)
        return True
    # URLs
    if _is_url(t) or low.startswith("open http"):
        url = t.split(None,1)[1] if low.startswith("open http") and len(t.split())>1 else t
        _open_url(url)
        return True
    # ===== Files & folders =====
    # Friendly folder names
    def _resolve_named_folder(lbl: str) -> Path | None:
        maps = {
            "downloads": Path.home()/"Downloads",
            "documents": Path.home()/"Documents",
            "desktop": Path.home()/"Desktop",
            "pictures": Path.home()/"Pictures",
            "music": Path.home()/"Music",
            "videos": Path.home()/"Videos",
        }
        k = lbl.strip().lower().replace("my ", "").replace(" folder", "").replace(" directory", "")
        return maps.get(k)
    m = re.match(r"^open\s+(file|folder|directory)\s+(.+)$", low)
    if m:
        raw = t.split(None,2)[2]
        named = _resolve_named_folder(raw)
        path = str(named) if named else raw
        _open_path(Path(os.path.expanduser(path)))
        return True
    mls = re.match(r"^(?:list|show)\s+files(?:\s+in\s+(.+))?$", low)
    if mls:
        target = mls.group(1) or str(Path.home())
        named = _resolve_named_folder(target) or Path(os.path.expanduser(target))
        try:
            entries = list(Path(named).iterdir())
            print(f"Listing: {named}")
            for e in sorted(entries, key=lambda x: x.name.lower())[:200]:
                print(("[D]" if e.is_dir() else "[F]"), e.name)
        except Exception as e:
            print(f"ls: {e}")
        return True
    # Open by name / app
    m2 = re.match(r"^open\s+(.+)$", low)
    if m2:
        target = t.split(None,1)[1]
        # path-like
        if "/" in target or target.startswith("~"):
            _open_path(Path(os.path.expanduser(target)))
            return True
        if _do_openapp(target):
            return True
        # last resort: try to open as file
        _open_path(Path(target))
        return True
    # ===== Audio volume =====
    if re.match(r"^volume\s+up$", low):
        _audio_volume_change(+5); return True
    if re.match(r"^volume\s+down$", low):
        _audio_volume_change(-5); return True
    m = re.match(r"^volume\s+(\d{1,3})\s*(?:%|percent)?$", low)
    if m:
        _audio_volume_set(int(m.group(1))); return True
    m = re.match(r"^(?:set\s+)?volume\s+to\s+(\d{1,3})\s*(?:%|percent)?$", low)
    if m:
        _audio_volume_set(int(m.group(1))); return True
    m = re.match(r"^(?:increase|raise)\s+volume\s+(\d{1,2})\s*(?:%|percent)?$", low)
    if m:
        _audio_volume_change(int(m.group(1))); return True
    m = re.match(r"^(?:decrease|lower|reduce)\s+volume\s+(\d{1,2})\s*(?:%|percent)?$", low)
    if m:
        _audio_volume_change(-int(m.group(1))); return True
    if low == "mute":
        _audio_mute(True); return True
    if low == "unmute":
        _audio_mute(False); return True
    # ===== Brightness =====
    m = re.match(r"^brightness\s+(\d{1,3})\s*(?:%|percent)?$", low)
    if m:
        _brightness_set(int(m.group(1))); return True
    if re.match(r"^brightness\s+up$", low):
        _brightness_change(+5); return True
    if re.match(r"^brightness\s+down$", low):
        _brightness_change(-5); return True
    m = re.match(r"^(?:set\s+)?brightness\s+to\s+(\d{1,3})\s*(?:%|percent)?$", low)
    if m:
        _brightness_set(int(m.group(1))); return True
    m = re.match(r"^(?:increase|raise)\s+brightness\s+(\d{1,2})\s*(?:%|percent)?$", low)
    if m:
        _brightness_change(int(m.group(1))); return True
    m = re.match(r"^(?:decrease|lower|reduce)\s+brightness\s+(\d{1,2})\s*(?:%|percent)?$", low)
    if m:
        _brightness_change(-int(m.group(1))); return True
    # ===== DND =====
    if low in {"dnd on", "do not disturb on"}:
        _dnd_set(True); return True
    if low in {"dnd off", "do not disturb off"}:
        _dnd_set(False); return True
    if low in {"enable dnd","turn on dnd","turn on do not disturb","disable notifications"}:
        _dnd_set(True); return True
    if low in {"disable dnd","turn off dnd","turn off do not disturb","enable notifications"}:
        _dnd_set(False); return True
    # ===== Wi‑Fi =====
    if low == "wifi on":
        _wifi_radio(True); return True
    if low == "wifi off":
        _wifi_radio(False); return True
    if low == "wifi list":
        _wifi_list(); return True
    m = re.match(r"^wifi\s+connect\s+([^\s]+)(?:\s+(.+))?$", low)
    if m:
        ssid = m.group(1)
        pwd = m.group(2) if m.lastindex and m.group(2) else None
        _wifi_connect(ssid, pwd); return True
    if re.match(r"^(?:turn|switch|set)\s+wifi\s+on$", low):
        _wifi_radio(True); return True
    if re.match(r"^(?:turn|switch|set)\s+wifi\s+off$", low):
        _wifi_radio(False); return True
    # connect/join wifi SSID [password PASS], SSID/PASS may be quoted or unquoted
    mw = re.match(r'^(?:connect|join)\s+wifi\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))(?:\s+(?:password|pass)\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s]+)))?$', low)
    if mw:
        ssid = mw.group(1) or mw.group(2) or mw.group(3)
        pwd = mw.group(4) or mw.group(5) or mw.group(6)
        _wifi_connect(ssid, pwd); return True
    # ===== Email & Calendar natural phrases =====
    if low in {"read my email","show inbox","check email"}:
        _handle_command("/email inbox default 10", []); return True
    if low in {"show my calendar","today's calendar","calendar today"}:
        _handle_command("/calendar today default", []); return True
    if low in {"calendar this week","show my week","calendar week"}:
        _handle_command("/calendar week default", []); return True
    # Backups
    mtime = re.match(r"^(install|schedule)\s+(nightly|daily)\s+backup(?:\s+at\s+(\d{1,2}):(\d{2}))?$", low)
    if mtime:
        hh = mtime.group(3) or "02"; mm = mtime.group(4) or "30"
        _handle_command(f"/install-nightly-backup {hh}:{mm}", [])
        return True
    if low in {"remove nightly backup","uninstall nightly backup","cancel backup schedule"}:
        _handle_command("/uninstall-nightly-backup", [])
        return True
    if low in {"backup now","create backup","make backup"}:
        _handle_command("/backup", [])
        return True
    # ===== VPN =====
    m = re.match(r"^vpn\s+up\s+(.+)$", low)
    if m:
        _vpn_up(m.group(1).strip()); return True
    m = re.match(r"^vpn\s+down\s+(.+)$", low)
    if m:
        _vpn_down(m.group(1).strip()); return True
    m = re.match(r"^(?:connect|enable)\s+vpn\s+(.+)$", low)
    if m:
        _vpn_up(m.group(1).strip()); return True
    m = re.match(r"^(?:disconnect|disable)\s+vpn\s+(.+)$", low)
    if m:
        _vpn_down(m.group(1).strip()); return True
    # ===== Projects history & actions =====
    if low in {"show history","list projects","recent projects","show recent projects","history"}:
        lst = _list_projects(); _print_history(lst); return True
    mopenproj = re.match(r"^(?:open|launch)\s+(?:project\s+)?(\d+)$", low)
    if mopenproj:
        try:
            idx = int(mopenproj.group(1)) - 1; lst = _list_projects()
            if 0 <= idx < len(lst): _open_path(lst[idx]); _run_launcher(lst[idx])
            else: print("Invalid index")
        except Exception: print("Usage: open project N")
        return True
    mrunproj = re.match(r"^run\s+(?:project\s+)?(\d+)$", low)
    if mrunproj:
        try:
            idx = int(mrunproj.group(1)) - 1; lst = _list_projects()
            if 0 <= idx < len(lst): _run_launcher(lst[idx])
            else: print("Invalid index")
        except Exception: print("Usage: run project N")
        return True
    mprune = re.match(r"^(?:prune|clean)\s+(?:running\s+)?projects?\s+(?:older\s+than\s+)?(\d+)\s+days?$", low)
    if mprune:
        days = int(mprune.group(1)); cutoff = time.time() - days*86400; removed = 0
        for p in RUNNING_DIR.iterdir():
            try:
                if p.is_dir() and p.stat().st_mtime < cutoff:
                    shutil.rmtree(p, ignore_errors=True); removed += 1
            except Exception:
                pass
        print(f"Pruned {removed} projects older than {days} days from RUNNING/."); return True
    # ===== Tools & utilities =====
    if low in {"setup","run setup","detect tools","check tools"}:
        _do_setup(); return True
    if low in {"wizard","first run wizard","first-run wizard"}:
        _do_wizard(); return True
    if low in {"sweep","system sweep","run sweep"}:
        _do_sweep(); return True
    if low in {"backup now","create backup","make backup","backup"}:
        _handle_command("/backup", []); return True
    minsched = re.match(r"^(?:schedule|install|set\s+up)\s+(?:nightly|daily)\s+backup\s+(?:at\s+)?(\d{1,2}):(\d{2})$", low)
    if minsched:
        hh, mm = minsched.group(1), minsched.group(2)
        _handle_command(f"/install-nightly-backup {hh}:{mm}", []); return True
    if low in {"cancel nightly backup","remove nightly backup","uninstall nightly backup"}:
        _handle_command("/uninstall-nightly-backup", []); return True
    if low in {"dashboard","open dashboard","show dashboard"}:
        try: run_dashboard(BASE_DIR)
        except Exception as e: print(f"Dashboard error: {e}")
        return True
    if low in {"open gui","launch gui","start gui","gui"}:
        try: spawn_cmd([sys.executable, str(BASE_DIR / 'gui_shell.py')]); print("Launched GUI shell.")
        except Exception as e: print(f"GUI launch error: {e}")
        return True
    mlog = re.match(r"^(?:show|tail|print)\s+(?:logs?|command\s+log)(?:\s+(\d+))?$", low)
    if mlog:
        try:
            n = int(mlog.group(1)) if mlog.group(1) else 20
        except Exception:
            n = 20
        logp = BASE_DIR / "runtime" / "command_log.jsonl"
        if not logp.exists():
            print("No command log yet."); return True
        try:
            lines = logp.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = lines[-n:] if n > 0 else lines
            for ln in tail: print(ln)
        except Exception as e:
            print(f"log read failed: {e}")
        return True
    return False

# ---------- DND / Wi‑Fi / VPN / Window mgmt ----------
def _dnd_set(on: bool) -> None:
    # GNOME via gsettings
    if _have("gsettings"):
        try:
            run_cmd(["gsettings","set","org.gnome.desktop.notifications","show-banners", "false" if on else "true"], mode="write", confirm=False) 
            print("DND:", "ON" if on else "OFF")
            return
        except Exception:
            pass
    print("DND toggle not supported on this system (missing gsettings).")

def _wifi_radio(on: bool) -> None:
    if _have("nmcli"):
        try:
            run_cmd(["nmcli","radio","wifi", "on" if on else "off"], mode="write", confirm=False) 
            print("Wi‑Fi:", "ON" if on else "OFF")
            return
        except Exception:
            pass
    print("Wi‑Fi control not available (missing nmcli).")

def _wifi_list() -> None:
    if _have("nmcli"):
        try:
            res = run_cmd(["nmcli","-t","-f","SSID,SIGNAL,SECURITY","dev","wifi"], mode="read")
            lines = [ln for ln in res.get("stdout", "").splitlines() if ln.strip()]
            print("Nearby Wi‑Fi networks:")
            for ln in lines[:30]:
                print("  ", ln)
            return
        except Exception as e:
            print(f"wifi list failed: {e}")
            return
    print("Wi‑Fi list not available (missing nmcli).")

def _wifi_connect(ssid: str, password: str | None) -> None:
    if _have("nmcli"):
        try:
            cmd = ["nmcli","dev","wifi","connect", ssid]
            if password:
                cmd += ["password", password]
            run_cmd(cmd, mode="write", confirm=False)
            return
        except Exception as e:
            print(f"wifi connect failed: {e}")
            return
    print("Wi‑Fi connect not available (missing nmcli).")

def _vpn_up(name: str) -> None:
    if _have("nmcli"):
        try:
            run_cmd(["nmcli","con","up","id", name], mode="write", confirm=False)
            return
        except Exception:
            pass
    print("VPN up not available (missing nmcli or bad name).")

def _vpn_down(name: str) -> None:
    if _have("nmcli"):
        try:
            run_cmd(["nmcli","con","down","id", name], mode="write", confirm=False)
            return
        except Exception:
            pass
    print("VPN down not available (missing nmcli or bad name).")

def _collect_windows() -> list[dict]:
    """Collect windows using wmctrl -lx and return list of dicts {id, cls, title}."""
    if not _have("wmctrl"):
        return []
    items: list[dict] = []
    try:
        res = run_cmd(["wmctrl", "-lx"], mode="read")
        out = res.get("stdout", "")
        for ln in out.splitlines():
            # Format: 0x01200007  0 hostname wmclass  title...
            parts = ln.split(None, 4)
            if len(parts) < 5:
                continue
            wid, desk, host, wmclass, title = parts
            items.append({"id": wid, "cls": wmclass, "title": title})
    except Exception:
        pass
    return items

def _wm_list_windows() -> None:
    if not _have("wmctrl"):
        print("wmctrl not installed.")
        return
    try:
        LAST_WINDOWS.clear()
        LAST_WINDOWS.extend(_collect_windows())
        if not LAST_WINDOWS:
            print("No windows found.")
            # Wayland hint: wmctrl only sees X11/XWayland windows
            sess = os.environ.get("XDG_SESSION_TYPE", "").lower()
            if sess == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
                print("Note: On Wayland, wmctrl may not see native Wayland windows.")
                print("- Try listing again after opening an app (e.g. /apps then /openapp 1).")
                print("- If possible, run under an X11 session for full wmctrl support.")
            return
        for i, w in enumerate(LAST_WINDOWS[:50], 1):
            print(f"  {i:2d}. {w['title']}    ({w['cls']})")
        if len(LAST_WINDOWS) > 50:
            print("… (truncated)")
    except Exception as e:
        print(f"wmctrl failed: {e}")

def _resolve_window_token(token: str) -> str | None:
    """Resolve a user token to a window id. Accepts index (e.g. '3' or '#3') or fuzzy title/class.
    Returns the window id (hex like '0x01200007') or None.
    """
    tok = token.strip()
    if tok.startswith('#'):
        tok = tok[1:]
    if tok.isdigit() and LAST_WINDOWS:
        idx = int(tok) - 1
        if 0 <= idx < len(LAST_WINDOWS):
            return LAST_WINDOWS[idx]['id']
    # Fallback: collect fresh list and fuzzy match
    windows = LAST_WINDOWS or _collect_windows()
    if not windows:
        return None
    low = tok.lower()
    best_id = None
    best_score = -1
    for w in windows:
        title = (w.get('title') or '').lower()
        cls = (w.get('cls') or '').lower()
        score = 0
        if title == low or cls == low:
            score = 100
        elif title.startswith(low) or cls.startswith(low):
            score = 80
        elif low in title or low in cls:
            score = 60
        if score > best_score:
            best_score = score
            best_id = w['id']
    return best_id

def _wm_focus(name: str) -> None:
    if _have("wmctrl"):
        try:
            wid = _resolve_window_token(name)
            if wid:
                rc = run_cmd(["wmctrl", "-ia", wid], mode="write", confirm=False).get("rc", 1)
                if rc == 0:
                    print(f"Focused window: {name}")
                    return
            # Fallback: name-based
            rc = run_cmd(["wmctrl", "-a", name], mode="write", confirm=False).get("rc", 1)
            if rc == 0:
                print(f"Focused window: {name}")
            else:
                print("Focus failed (window not found).")
            return
        except Exception:
            pass
    print("Focus failed (wmctrl not available or window not found).")

def _wm_maximize(name: str) -> None:
    if _have("wmctrl"):
        try:
            wid = _resolve_window_token(name)
            if wid:
                rc = run_cmd(["wmctrl", "-ir", wid, "-b", "add,maximized_vert,maximized_horz"], mode="write", confirm=False).get("rc", 1)
                if rc == 0:
                    print(f"Maximized window: {name}")
                    return
            rc = run_cmd(["wmctrl","-r", name, "-b", "add,maximized_vert,maximized_horz"], mode="write", confirm=False).get("rc", 1)
            if rc == 0:
                print(f"Maximized window: {name}")
            else:
                print("Maximize failed (window not found).")
            return
        except Exception:
            pass
    print("Maximize failed (wmctrl not available or window not found).")

def _wm_move_to_workspace(name: str, workspace: int) -> None:
    idx = max(0, workspace - 1)  # 0-indexed
    if _have("wmctrl"):
        try:
            wid = _resolve_window_token(name)
            if wid:
                rc = run_cmd(["wmctrl", "-ir", wid, "-t", str(idx)], mode="write", confirm=False).get("rc", 1)
                if rc == 0:
                    print(f"Moved '{name}' to workspace {workspace}")
                    return
            rc = run_cmd(["wmctrl","-r", name, "-t", str(idx)], mode="write", confirm=False).get("rc", 1)
            if rc == 0:
                print(f"Moved '{name}' to workspace {workspace}")
            else:
                print("Move failed (window not found).")
            return
        except Exception:
            pass
    print("Move failed (wmctrl not available or window not found).")

# ---------- session & commands ----------
def _list_projects(limit: int = 100) -> list[Path]:
    items: list[tuple[float, Path]] = []
    for root in (SAVED_DIR, RUNNING_DIR):
        try:
            for p in root.iterdir():
                if p.is_dir():
                    try:
                        mt = p.stat().st_mtime
                    except Exception:
                        mt = 0.0
                    items.append((mt, p))
        except Exception:
            pass
    items.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in items[:limit]]

def _print_history(lst: list[Path]) -> None:
    if not lst:
        print("No projects found.")
        return
    print("Recent projects:")
    for i, p in enumerate(lst, 1):
        print(f"  {i:2d}. {p}")

def print_commands_help() -> None:
    print(BANNER)
    print()
    print("Commands:")
    print("  Projects:")
    print("    /history             List recent projects")
    print("    /open N              Open AND run recent project N")
    print("    /run N               Run recent project N (./run.sh)")
    print("    /prune N             Delete RUNNING/ older than N days")
    print("  Files & Apps:")
    print("    /ls [PATH]          List files (default: $HOME)")
    print("    /openfile PATH       Open a file or folder")
    print("    /openpath NAME       Find a file in home and open it")
    print("    /apps [FILTER]      List installed GUI apps")
    print("    /openapp X|NAME     Open app by index or name")
    print("    /which NAME         Show path of an executable")
    print("    open NAME           Natural: honors your saved shortcuts")
    print("  Web & Shortcuts:")
    print("    /web QUERY|URL      Open browser with URL or search")
    print("    /webiso QUERY|URL   Open isolated browser")
    print("    /shortcuts          List URL shortcuts")
    print("    /shortcut set NAME URL   Define/update a shortcut")
    print("    /shortcut rm NAME        Remove a shortcut")
    print("    /openlast           Open the last dev server URL")
    print("  Windows & System:")
    print("    /winlist            List windows (wmctrl)")
    print("    /focus NAME|N       Focus window")
    print("    /max NAME|N         Maximize window  (aliases: /winmax, /maximize)")
    print("    /movews NAME N      Move window to workspace N")
    print("    /dnd on|off         Toggle Do Not Disturb")
    print("    /wifi on|off        Toggle Wi‑Fi radio")
    print("    /wifi list          List nearby Wi‑Fi networks")
    print("    /wifi connect SSID [PASSWORD]")
    print("    /vpn up NAME        VPN up")
    print("    /vpn down NAME      VPN down")
    print("    /ps                 Show a short process list")
    print("    /stop               Stop the last started dev server")
    print("  Tools:")
    print("    /setup              Detect tools and suggest installs")
    print("    /wizard             First-run checklist")
    print("    /sweep              System sweep and suggestions")
    print("    /backup             Create a backup snapshot now")
    print("    /install-nightly-backup [HH:MM]  Install daily backup")
    print("    /uninstall-nightly-backup        Remove daily backup entry")
    print("    /dashboard          Open the log dashboard (terminal UI)")
    print("    /gui                Launch the desktop GUI shell")
    print("    /log [N]            Show last N command-runner logs")
    print("  Connected services:")
    print("    /email setup ALIAS               Configure IMAP account")
    print("    /email inbox [ALIAS] [N]         Show last N messages (default 10)")
    print("    /calendar setup ALIAS            Configure CalDAV calendar")
    print("    /calendar today [ALIAS]          Show today's events")
    print("    /calendar week [ALIAS]           Show next 7 days")
    print("    /help               Show this help")
    print("    /quit               Exit")

def _run_launcher(p: Path) -> None:
    runner = p / "run.sh"
    if runner.exists():
        try:
            print(f"▶ Running project via ./run.sh (cwd={p}) …")
            subprocess.Popen(["bash", str(runner)], cwd=str(p))
        except Exception as e:
            print(f"Run failed: {e}")

def _search_file_in_home(name: str) -> Path | None:
    name = name.strip()
    home = Path.home()
    try:
        for root, dirs, files in os.walk(home):
            if name in files:
                return Path(root) / name
    except Exception:
        return None
    return None

def _handle_command(line: str, cache: list[Path]) -> tuple[bool, list[Path]]:
    # Shorthand patterns (accept with or without slash and without spaces)
    s = line.strip()
    m = re.match(r"^/?openapp\s*(\d+)$", s, flags=re.I)
    if m:
        _openapp_by_index_or_name(m.group(1)); return True, cache
    m = re.match(r"^/?open\s*(\d+)$", s, flags=re.I)
    if m:
        try:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(cache):
                _open_path(cache[idx]); _run_launcher(cache[idx])
            else:
                print("Invalid index")
        except Exception:
            print("Usage: /open N")
        return True, cache
    m = re.match(r"^/?run\s*(\d+)$", s, flags=re.I)
    if m:
        try:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(cache):
                _run_launcher(cache[idx])
            else:
                print("Invalid index")
        except Exception:
            print("Usage: /run N")
        return True, cache
    m = re.match(r"^/?max\s*(\d+)$", s, flags=re.I)
    if m:
        _wm_maximize(m.group(1)); return True, cache
    m = re.match(r"^/?focus\s*(\d+)$", s, flags=re.I)
    if m:
        _wm_focus(m.group(1)); return True, cache
    if line == "/help":
        print_commands_help(); return True, cache
    if line == "/history":
        cache = _list_projects(); _print_history(cache); return True, cache
    if line == "/setup":
        _do_setup(); return True, cache
    if line == "/wizard":
        _do_wizard(); return True, cache
    if line == "/sweep":
        _do_sweep(); return True, cache
    if line == "/backup":
        try:
            snap = create_backup(retain=14)
            print(f"Backup created: {snap}")
        except Exception as e:
            print(f"Backup failed: {e}")
        return True, cache
    if line.startswith("/install-nightly-backup"):
        try:
            parts = line.split()
            when = parts[1] if len(parts) > 1 else "02:30"
            hh, mm = when.split(":", 1)
            hh_i = max(0, min(23, int(hh)))
            mm_i = max(0, min(59, int(mm)))
            cron_line = f"{mm_i} {hh_i} * * * {sys.executable} {BASE_DIR / 'scripts' / 'backup_now.py'} >/dev/null 2>&1"
            try:
                existing = subprocess.check_output(["crontab", "-l"], text=True)
            except Exception:
                existing = ""
            filtered = []
            for ln in existing.splitlines():
                if "scripts/backup_now.py" in ln:
                    continue
                filtered.append(ln)
            new_tab = "\n".join([*(l for l in filtered if l.strip()), cron_line]) + "\n"
            p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
            p.communicate(new_tab)
            if p.returncode == 0:
                print(f"Installed nightly backup at {hh_i:02d}:{mm_i:02d}.")
            else:
                print("Failed to install crontab entry.")
        except Exception as e:
            print(f"Install failed: {e}")
        return True, cache
    if line == "/uninstall-nightly-backup":
        try:
            try:
                existing = subprocess.check_output(["crontab", "-l"], text=True)
            except Exception:
                existing = ""
            filtered = [ln for ln in existing.splitlines() if "scripts/backup_now.py" not in ln]
            new_tab = "\n".join([l for l in filtered if l.strip()]) + ("\n" if filtered else "")
            p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
            p.communicate(new_tab)
            if p.returncode == 0:
                print("Removed nightly backup entry.")
            else:
                print("Failed to update crontab.")
        except Exception as e:
            print(f"Uninstall failed: {e}")
        return True, cache
    if line.startswith("/open "):
        try:
            idx = int(line.split()[1]) - 1
            if 0 <= idx < len(cache):
                _open_path(cache[idx]); _run_launcher(cache[idx])
            else:
                print("Invalid index")
        except Exception:
            print("Usage: /open N")
        return True, cache
    if line.startswith("/run "):
        try:
            idx = int(line.split()[1]) - 1
            if 0 <= idx < len(cache):
                _run_launcher(cache[idx])
            else:
                print("Invalid index")
        except Exception:
            print("Usage: /run N")
        return True, cache
    if line.startswith("/ls"):
        parts = line.split(None, 1)
        target = parts[1] if len(parts) > 1 else str(Path.home())
        p = Path(os.path.expanduser(target))
        try:
            entries = list(p.iterdir())
            print(f"Listing: {p}")
            for e in sorted(entries, key=lambda x: x.name.lower())[:200]:
                print(("[D]" if e.is_dir() else "[F]"), e.name)
        except Exception as e:
            print(f"ls: {e}")
        return True, cache
    if line.startswith("/openfile "):
        target = line.split(None,1)[1]
        _open_path(Path(os.path.expanduser(target))); return True, cache
    if line.startswith("/openpath "):
        nm = line.split(None,1)[1]
        p = _search_file_in_home(nm)
        if p: _open_path(p)
        else: print(f"File '{nm}' not found in home.")
        return True, cache
    if line == "/dnd on":
        _dnd_set(True); return True, cache
    if line == "/dnd off":
        _dnd_set(False); return True, cache
    if line == "/wifi on":
        _wifi_radio(True); return True, cache
    if line == "/wifi off":
        _wifi_radio(False); return True, cache
    if line == "/wifi list":
        _wifi_list(); return True, cache
    if line.startswith("/wifi connect "):
        parts = line.split()
        ssid = parts[2] if len(parts) >= 3 else ""
        pwd = parts[3] if len(parts) >= 4 else None
        if ssid:
            _wifi_connect(ssid, pwd)
        else:
            print("Usage: /wifi connect SSID [PASSWORD]")
        return True, cache
    if line.startswith("/vpn up "):
        _vpn_up(line.split(None,2)[2]); return True, cache
    if line.startswith("/vpn down "):
        _vpn_down(line.split(None,2)[2]); return True, cache
    if line == "/winlist":
        _wm_list_windows(); return True, cache
    if line.startswith("/focus "):
        _wm_focus(line.split(None,1)[1]); return True, cache
    if line.startswith("/max "):
        _wm_maximize(line.split(None,1)[1]); return True, cache
    if line.lower().startswith("/winmax ") or line.lower().startswith("/maximize "):
        _wm_maximize(line.split(None,1)[1]); return True, cache
    if line.startswith("/movews "):
        try:
            _, name, n = line.split(None,2)
            _wm_move_to_workspace(name, int(n))
        except Exception:
            print("Usage: /movews NAME N")
        return True, cache
    if line.startswith("/apps"):
        flt = None
        parts = line.split(None, 1)
        if len(parts) > 1:
            flt = parts[1]
        _list_desktop_apps(flt); return True, cache
    if line.startswith("/openapp "):
        tok = line.split(None,1)[1].strip()
        _openapp_by_index_or_name(tok); return True, cache
    if line.startswith("/which "):
        nm = line.split(None,1)[1].strip()
        path = shutil.which(nm) or ""
        print(path or "Not found"); return True, cache
    if line == "/ps":
        try:
            res = run_cmd(["ps","-e","-o","pid,comm,etime","--sort=-etime"], mode="read")
            print("\n".join(res.get("stdout", "").splitlines()[:25]))
        except Exception as e:
            print(f"ps failed: {e}")
        return True, cache
    if line == "/stop":
        pid = int(LAST_SERVER.get("pid") or 0)
        if not pid:
            print("No running server recorded."); return True, cache
        try:
            if os.name == "nt":
                subprocess.call(["taskkill","/PID", str(pid), "/F"])  
            else:
                os.kill(pid, 15)
            print(f"Stopped server pid {pid}.")
        except Exception as e:
            print(f"Failed to stop server pid {pid}: {e}")
        finally:
            LAST_SERVER["pid"] = 0
        return True, cache
    if line == "/openlast":
        url = (LAST_SERVER.get("url") or "").strip()
        if url:
            _open_url(url)
        else:
            print("No last server URL saved.")
        return True, cache
    if line.startswith("/webiso"):
        parts = line.split(None, 1)
        if len(parts) > 1:
            _launch_browser(parts[1], isolated=True)
        else:
            print("Usage: /webiso QUERY|URL")
        return True, cache
    if line.startswith("/web"):
        parts = line.split(None, 1)
        if len(parts) > 1:
            _launch_browser(parts[1], isolated=False)
        else:
            print("Usage: /web QUERY|URL")
        return True, cache
    if line.startswith("/email"):
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "setup":
            alias = parts[2]
            try:
                host = input("IMAP server (e.g., imap.gmail.com): ").strip()
                user = input("Username (email address): ").strip()
                pwd = input("App password (not stored in config): ").strip()
                setup_email(alias, host, user, pwd)
                print(f"Email '{alias}' configured.")
            except Exception as e:
                print(f"Setup failed: {e}")
            return True, cache
        if len(parts) >= 2 and parts[1] == "inbox":
            alias = parts[2] if len(parts) >= 3 else "default"
            try:
                n = int(parts[3]) if len(parts) >= 4 else 10
            except Exception:
                n = 10
            try:
                rows = list_inbox(alias, n)
                if not rows:
                    print("No messages or alias not configured.")
                else:
                    for d, frm, sub in rows:
                        print(f"- {d}  {frm}  {sub}")
            except Exception as e:
                print(f"Inbox error: {e}")
            return True, cache
        print("Usage: /email setup ALIAS | /email inbox [ALIAS] [N]")
        return True, cache
    if line.startswith("/calendar"):
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "setup":
            alias = parts[2]
            try:
                url = input("CalDAV server URL: ").strip()
                user = input("Username: ").strip()
                pwd = input("Password/App password: ").strip()
                setup_caldav(alias, url, user, pwd)
                print(f"Calendar '{alias}' configured.")
            except Exception as e:
                print(f"Setup failed: {e}")
            return True, cache
        if len(parts) >= 2 and parts[1] in {"today","week"}:
            alias = parts[2] if len(parts) >= 3 else "default"
            days = 1 if parts[1] == "today" else 7
            try:
                events = list_events(alias, days)
                if not events:
                    print("No events or alias not configured.")
                else:
                    for ln in events:
                        print(ln)
            except Exception as e:
                print(f"Calendar error: {e}")
            return True, cache
        print("Usage: /calendar setup ALIAS | /calendar today [ALIAS] | /calendar week [ALIAS]")
        return True, cache
    if line == "/shortcuts":
        sc = get_config_manager().get_shortcuts()
        if not sc:
            print("No shortcuts defined. Use /shortcut set NAME URL")
        else:
            print("Shortcuts:")
            for k in sorted(sc.keys(), key=lambda s: s.lower()):
                print(f"  {k:15} -> {sc[k]}")
        return True, cache
    if line.startswith("/shortcut "):
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "set":
            try:
                name = parts[2]
                url = " ".join(parts[3:]) if len(parts) > 3 else ""
                if not url:
                    print("Usage: /shortcut set NAME URL"); return True, cache
                mgr = get_config_manager()
                cur = mgr.get_shortcuts()
                cur[name.lower()] = url
                mgr.update_config({"shortcuts": cur})
                print(f"Set shortcut '{name}' -> {url}")
            except Exception as e:
                print(f"Failed to set shortcut: {e}")
            return True, cache
        if len(parts) == 3 and parts[1] in {"rm","del","remove"}:
            name = parts[2]
            mgr = get_config_manager()
            cur = mgr.get_shortcuts()
            if cur.pop(name.lower(), None) is not None:
                mgr.update_config({"shortcuts": cur})
                print(f"Removed shortcut '{name}'.")
            else:
                print("No such shortcut.")
            return True, cache
        print("Usage: /shortcut set NAME URL | /shortcut rm NAME")
        return True, cache
    if line == "/dashboard":
        try:
            run_dashboard(BASE_DIR)
        except Exception as e:
            print(f"Dashboard error: {e}")
        return True, cache
    if line == "/gui":
        try:
            spawn_cmd([sys.executable, str(BASE_DIR / 'gui_shell.py')])
            print("Launched GUI shell.")
        except Exception as e:
            print(f"GUI launch error: {e}")
        return True, cache
    if line.startswith("/log"):
        try:
            parts = line.split()
            n = int(parts[1]) if len(parts) > 1 else 20
        except Exception:
            n = 20
        logp = BASE_DIR / "runtime" / "command_log.jsonl"
        if not logp.exists():
            print("No command log yet.")
            return True, cache
        try:
            lines = logp.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = lines[-n:] if n > 0 else lines
            for ln in tail:
                print(ln)
        except Exception as e:
            print(f"log read failed: {e}")
        return True, cache
    if line.startswith("/prune "):
        try:
            days = int(line.split()[1])
            cutoff = time.time() - days*86400
            removed = 0
            for p in RUNNING_DIR.iterdir():
                try:
                    if p.is_dir() and p.stat().st_mtime < cutoff:
                        shutil.rmtree(p, ignore_errors=True)
                        removed += 1
                except Exception:
                    pass
            print(f"Pruned {removed} projects older than {days} days from RUNNING/.")
        except Exception:
            print("Usage: /prune N")
        return True, cache
    # If it looks like a slash command but wasn't recognized, don't treat it as a prompt
    if line.startswith("/"):
        print("Unknown command. Type /help."); return True, cache
    return False, cache

# ---------- pretty printing ----------
def _absolutize_main_cmd(project_dir: str, run_cmd: str) -> str:
    """
    Best-effort: make the first file-like arg absolute (keeps python/node/etc unchanged).
    """
    import shlex
    if not run_cmd: return ""
    parts = shlex.split(run_cmd)
    if not parts: return ""
    # if using -m/-c, nothing to absolutize reliably
    for i in range(1, len(parts)):
        tok = parts[i]
        if tok in {"-m","-c"}:  # module/code modes
            return run_cmd
        if tok.startswith("-"):
            continue
        # treat as a file/path
        if "/" in tok or "\\" in tok or Path(tok).suffix:
            parts[i] = str(Path(project_dir, tok).resolve())
            break
    return " ".join(shlex.quote(p) for p in parts)

def autorun(project_dir: Path) -> int:
    runner = project_dir / "run.sh"
    if not runner.exists():
        print("No run.sh created; nothing to run.")
        return 0
    print(f"▶ Running project via ./run.sh (cwd={project_dir}) …")
    return subprocess.run([str(runner)], cwd=str(project_dir)).returncode

def _generate_and_apply(user_prompt: str, policy: str) -> None:
    bad_path = SAVED_DIR / "bad_reply.json"
    plan: Dict[str, Any] = get_plan(user_prompt, bad_reply_path=str(bad_path))
    first_code = ""
    if isinstance(plan, dict):
        files = plan.get("files") or []
        if files and isinstance(files[0], dict):
            first_code = files[0].get("code", "") or ""
    is_program = classify_code(first_code) == "PROGRAM"
    root = choose_root(policy, is_program)
    result = apply_plan(plan, root, is_app=is_program)
    project_dir = Path(result["project_dir"])  # type: ignore
    run_cmd = result.get("run_cmd", "")
    abs_direct = _absolutize_main_cmd(str(project_dir), run_cmd)
    print("\n" + "="*66)
    print("✅ Project ready")
    print("📂 Directory:", project_dir)
    if result.get("stack"): print("📦 Stack:   ", result["stack"])
    if result.get("venv"):  print("🐍 venv:   ", result["venv"])
    if run_cmd:
        print("▶ Direct (absolute):", abs_direct or "(n/a)")
        print("▶ Direct (relative):", run_cmd)
        print("▶ Launcher:          ./run.sh   (or ./run.command / run.bat)")
    print("="*66 + "\n")
    try:
        rc = autorun(project_dir)
        print(f"↩︎ Return code: {rc}")
    except Exception as ex:
        print(f"❌ Run error: {ex}")
    if policy == "D":
        shutil.rmtree(project_dir, ignore_errors=True)
        print(f"🗑️  Deleted: {project_dir}")
    elif policy == "K":
        try:
            ans = input(f"Keep project at '{project_dir}'? [y/N]: ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y","yes"):
            shutil.rmtree(project_dir, ignore_errors=True)
            print(f"🗑️  Deleted: {project_dir}")
        else:
            print(f"💾 Kept: {project_dir}")
    else:
        print(f"💾 Saved: {project_dir}")

def _split_actions(line: str) -> list[str]:
    """Split a line into sequential actions on safe delimiters without breaking common queries.
    Delimiters: ';', '&&', ' and then ', ' then '.
    """
    s = line.strip()
    if not s:
        return []
    # Normalize spacing around delimiters
    parts: list[str] = []
    tmp = re.split(r"\s*(?:;|&&|\band then\b|\bthen\b)\s*", s, flags=re.IGNORECASE)
    for p in tmp:
        p = p.strip()
        if p:
            parts.append(p)
    return parts

def _process_actions(line: str, cache: list[Path] | None = None) -> bool:
    """Process a possibly multi-action line by splitting and running each as a command or natural action.
    Returns True if at least one action was handled.
    """
    actions = _split_actions(line)
    if not actions:
        return False
    handled_any = False
    for act in actions:
        # Try slash/explicit commands first
        if act.startswith("/") and cache is not None:
            handled, cache = _handle_command(act, cache)
            handled_any = handled_any or handled
            continue
        # Natural translator
        if _handle_natural_command(act):
            handled_any = True
            continue
        # If it looks like a slash without cache context
        if act.startswith("/"):
            # Try with a throwaway cache
            _handle_command(act, []);
            handled_any = True
    return handled_any

def _do_setup() -> None:
    print("Detecting tools…")
    nice: list[tuple[str,str]] = []
    for c in ("nmcli","wmctrl","gsettings","brightnessctl","pactl","amixer","gtk-launch","flatpak"):
        if not _have(c):
            nice.append((c, c))
    if nice:
        print("Missing optional tools:")
        for cmd, pkg in nice:
            print(f"  - {cmd} (install package: {pkg})")
    else:
        print("Looks good — common tools present.")
    print("\nHint Fedora: sudo dnf install -y wmctrl brightnessctl pavucontrol NetworkManager-wifi")
    print("Hint Ubuntu: sudo apt-get install -y wmctrl brightnessctl pulseaudio-utils network-manager")

def _do_wizard() -> None:
    print("Wizard: quick checks")
    print("- Wi‑Fi control:", "OK" if _have("nmcli") else "missing nmcli")
    print("- Window control:", "OK" if _have("wmctrl") else "missing wmctrl")
    print("- Brightness:", "OK" if _have("brightnessctl") else "missing brightnessctl")
    print("- Audio:", "OK" if (_have("pactl") or _have("amixer")) else "missing pactl/amixer")

def _do_sweep() -> None:
    print("System sweep:")
    print(f"- Platform: {sys.platform}")
    print(f"- Desktop: {os.environ.get('XDG_CURRENT_DESKTOP','')} {os.environ.get('DESKTOP_SESSION','')}")
    print(f"- Shell: {os.environ.get('SHELL','')}")
    print("- Tools:")
    for c in ("nmcli","wmctrl","gsettings","brightnessctl","pactl","amixer","gtk-launch","flatpak"):
        print(f"    {c:12}: {'yes' if _have(c) else 'no'}")

def main() -> None:
    # If arguments provided or stdin piped, do one-shot
    if len(sys.argv) > 1 or not sys.stdin.isatty():
        user_prompt = read_user_prompt()
        if not user_prompt:
            print("No prompt provided. Exiting.")
            return
        # First: try to translate and execute as natural commands (including chains)
        if _process_actions(user_prompt):
            return
        # Otherwise fall back to code generation flow
        policy = prompt_save_policy(default="A")
        if policy is None:
            print("Cancelled.")
            return
        _generate_and_apply(user_prompt, policy)
        return

    # Interactive session
    print("Entering interactive session. Type /help for commands. Use /quit to exit.\n")
    cache: list[Path] = _list_projects()
    while True:
        print("(Type /help for commands)")
        print(">> What would you like me to do?")
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line in {"/quit", "/exit"}:
            break
        # Try multi-action natural translation and slash commands
        if _process_actions(line, cache):
            continue
        # Otherwise, generate project via cloud LLM
        policy = prompt_save_policy(default="A")
        if policy is None:
            print("Cancelled. Returning to main menu.")
            continue
        _generate_and_apply(line, policy)
        # Refresh history after generating
        cache = _list_projects()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        raise SystemExit(1)

