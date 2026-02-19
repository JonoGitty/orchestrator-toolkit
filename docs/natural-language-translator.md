# Natural-Language Command Translator (AI Orchestrate)

This document lists natural phrases the orchestrator understands and the actions they trigger. All phrases are case‑insensitive and flexible; words in parentheses are optional, pipes separate alternatives, and examples show typical usage.

Notes
- Most actions call the existing command integrations (window control, wifi, etc.).
- Some features rely on optional tools: bluetoothctl, grim/slurp/wl-copy (Wayland), gnome-screenshot, xrandr, pactl, wmctrl, nmcli.
- If nothing matches, the orchestrator falls back to project generation.
 - You can chain actions with then, and then, ; or &&. Example: "wifi on; open the browser to apricots and then screenshot area to clipboard".
 - Freeform chatter is OK. Examples like "hello ai, can you please search for cats on the internet" are understood and executed as searches.

Web and Search
- Open browser/search
  - "open the browser to X" | "open webpage for X" | "open site about X"
  - "search for cats and dogs, apricots" (comma or "and" separated)
  - "open X and Y" (opens two searches)
  - "do another search for X"
- Private/incognito
  - "open private browser to X" | "launch isolated browser for X"

Shortcuts (URL aliases)
- List: "list shortcuts" | "show my shortcuts"
- Add: "add shortcut news: https://news.ycombinator.com" | "set shortcut docs to https://…"
- Remove: "remove shortcut news" | "delete shortcut docs"

Files and Folders
- Open:
  - "open folder Downloads" | "open directory Documents" | "open file ~/notes.txt"
  - Named folders supported: Downloads, Documents, Desktop, Pictures, Music, Videos
- List files:
  - "list files" | "list files in Downloads" | "show files in ~/Projects"

Applications
- List apps: "list apps" | "list apps browser"
- Open app: "open app firefox" | "open app 1"
- Which: "where is node" | "which python"

Windows and Workspaces (wmctrl)
- List windows: "show windows" | "list windows"
- Focus: "focus 2" | "focus Firefox"
- Maximize: "maximize 3" | "maximize Terminal"
- Move to workspace: "move Firefox to workspace 2"

Audio Volume
- "volume up" | "volume down" | "volume 25"
- "set volume to 30%"
- "increase volume 10" | "reduce volume 5%"
- "mute" | "unmute"

Brightness
- "brightness 50%" | "brightness up" | "brightness down"
- "set brightness to 60%"
- "increase brightness 10" | "decrease brightness 5%"

Do Not Disturb
- On: "dnd on" | "do not disturb on" | "enable dnd" | "disable notifications"
- Off: "dnd off" | "do not disturb off" | "disable dnd" | "enable notifications"

Wi‑Fi (nmcli)
- Radio: "wifi on" | "wifi off" | "turn wifi on" | "switch wifi off"
- List networks: "wifi list"
- Connect: "wifi connect MySSID password secretpass" | "connect wifi MySSID password pass123"

VPN (nmcli)
- "vpn up WorkVPN" | "vpn down WorkVPN"
- "connect vpn WorkVPN" | "disconnect vpn WorkVPN"

Email & Calendar
- Inbox: "read my email" | "show inbox" | "check email"
- Calendar today: "show my calendar" | "today's calendar" | "calendar today"
- Calendar week: "calendar this week" | "show my week" | "calendar week"

Projects
- History: "show history" | "list projects" | "recent projects"
- Open/run by index: "open project 3" | "run project 2"
- Prune: "prune projects older than 7 days" | "clean projects 14 days"

Tools & Utilities
- Setup/tools: "setup" | "detect tools" | "check tools"
- Wizard: "wizard" | "first run wizard"
- Sweep: "sweep" | "system sweep"
- Backup now: "backup now" | "create backup" | "backup"
- Nightly backup: "schedule nightly backup at 02:30" | "cancel nightly backup"
- Dashboard: "dashboard" | "open dashboard"
- GUI shell: "open gui" | "launch gui"
- Logs: "show command log 50" | "tail command log"

Web helpers
- Open last dev URL: "open last" | "open last server" | "open last url"

Bluetooth (bluetoothctl)
- Power: "bluetooth on" | "bluetooth off" | "enable/disable bluetooth" | "turn on/off bluetooth"
- List: "list bluetooth devices" | "show bluetooth devices"
- Connect/Disconnect: "bluetooth connect WH-1000XM4" | "connect bluetooth 00:11:22:33:44:55" | "bluetooth disconnect WH-1000XM4"

Screenshots
- Full/area/window:
  - "screenshot" | "take screenshot" | "print screen"
  - "take screenshot area" | "take screenshot window"
- Clipboard/file:
  - "screenshot area to clipboard"
  - "screenshot window save to Desktop" | "take screenshot full save to Pictures"
  - On Wayland, uses grim/slurp/wl-copy if available; on GNOME, gnome-screenshot

Audio Output Switching (pactl)
- List outputs: "list audio devices" | "list outputs"
- Switch output:
  - "switch audio to headphones" | "switch audio to speakers"
  - "set output to alsa_output.pci-0000_00_1b.0.analog-stereo" | "change sound to 1"

Displays / Monitors (xrandr)
- List: "list displays" | "show monitors"
- Set resolution: "set resolution 1920x1080 on HDMI-1"
- Rotate: "rotate eDP-1 left" | "rotate HDMI-1 normal"
- Mirror: "mirror displays" | "enable mirroring"
- Extend: "extend displays right" | "arrange displays left"

Help & Misc
- Help: "help" | "show help" | "what can you do"
- Which: "where is node" | "which python"

Fallback to project generation
- Any request not matching these translations will trigger the normal plan generation/install/run flow after confirming save policy.
