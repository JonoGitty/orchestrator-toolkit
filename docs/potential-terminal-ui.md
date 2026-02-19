```
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

AI ORCHESTRATE
AI-powered full system controller
```

POTENTIAL IDEA: Terminal UI Sketches

Status: Concept sketch only. Not implemented.

Overview
These are text-only mockups for a clearer, more structured terminal UI. They
retain the existing commands and behavior, but present them with consistent
sections and status lines.

Logo integration (potential)
The logo appears at the top of the main UI screen to brand the session without
changing any functionality.

Potential down the line
- A cinematic "Iron Man" / "Quantum of Solace" style HUD: layered panels,
  fast-scanning data blocks, and decisive visual grouping.
- Expandable UI regions that reveal detail only when needed, keeping focus on
  the current task and reducing clutter.

Main screen (potential)
```
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

AI ORCHESTRATE
AI-powered full system controller
```

Main screen (potential)
AI ORCHESTRATOR  v0.9.0                                     [Linux] [online]
──────────────────────────────────────────────────────────────────────────────
Status: idle   Save policy: Auto   Last run: 12s ago   Cache: ON   Model: gpt-5

Prompt
> make me a lightweight pomodoro app with tray controls

Plan
- Stack: python
- Files: 6
- Post-install: pip install -r requirements.txt
- Run: ./.venv/bin/python main.py

Actions
✔ Parsed LLM plan
✔ Wrote files to SAVED/pomodoro-app
✔ Created venv
✔ Installed dependencies
▶ Running… (pid 4242)

Output (tail)
[app] Starting tray UI…
[app] Ready on port 5073
[info] Open: http://localhost:5073
──────────────────────────────────────────────────────────────────────────────
Commands: /help /history /open N /run N /apps /openapp /wifi /dnd /quit

Help screen (potential)
AI ORCHESTRATOR — HELP
──────────────────────────────────────────────────────────────────────────────
Core
  /help                     Show this screen
  /quit, /exit               Exit orchestrator
  /history                   List recent projects
  /open N                    Open project N
  /run N                     Run project N (./run.sh)
  /prune N                   Delete RUNNING projects older than N days

System
  /apps [FILTER]             List installed apps
  /openapp X|NAME            Open app by index or name
  /openfile PATH             Open file/folder
  /openpath NAME             Search $HOME and open file
  /which NAME                Show executable path
  /ps                        Show top processes
  /dnd on|off                Toggle Do Not Disturb
  /wifi on|off|list           Wi-Fi controls
  /wifi connect SSID [PASS]  Connect to Wi-Fi
  /vpn up NAME               VPN up
  /vpn down NAME             VPN down
  /winlist                   List windows
  /focus NAME                Focus window
  /max NAME                  Maximize window
  /movews NAME N             Move window to workspace N

Project
  /setup                     Detect tools + suggest installs
  /wizard                    First-run checks
  /sweep                     System sweep summary

Notes
  - Natural commands also work (e.g., "open chrome", "volume 40").
  - Risky commands can be set to confirm in config.

History screen (potential)
Recent Projects
──────────────────────────────────────────────────────────────────────────────
  1. SAVED/pomodoro-app            2 min ago   [python]
  2. RUNNING/todo-cli              14 min ago  [python]
  3. SAVED/weather-dashboard       1 hour ago  [node]
  4. SAVED/notes-app               yesterday  [python]

Tip: /open 1  or  /run 2

Apps screen (potential)
Installed Apps (filter: "code")
──────────────────────────────────────────────────────────────────────────────
  1. Visual Studio Code (code)
  2. Code - Insiders     (code-insiders)

Tip: /openapp 1

System status screen (potential)
System Status
──────────────────────────────────────────────────────────────────────────────
Platform: linux  |  Desktop: GNOME  |  Shell: /bin/bash
CPU: 12%   RAM: 5.8/32 GB   Disk: 128/512 GB   Battery: 82%
Wi-Fi: ON  |  VPN: OFF  |  DND: OFF  |  Brightness: 70%

Tools
  nmcli: yes   wmctrl: no   gsettings: yes   brightnessctl: yes
  pactl: yes   amixer: no   flatpak: yes

Command output screen (potential)
Command Log (tail)
──────────────────────────────────────────────────────────────────────────────
▶ nmcli dev wifi list
✔ exit=0  (0.4s)
SSID: MyNetwork   SIGNAL: 80  SECURITY: WPA2

▶ wmctrl -l
✖ exit=127  (0.0s)
wmctrl: command not found
