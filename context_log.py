import json
from datetime import datetime
import os

LOG_FILE = "context_log.json"

def read_log():
    if not os.path.exists(LOG_FILE):
        return {"history": [], "system_state": {}, "last_errors": []}
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"history": [], "system_state": {}, "last_errors": []}

def write_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def update_state(state):
    log = read_log()
    log["system_state"] = state
    log["history"].append({
        "timestamp": str(datetime.now()),
        "state": state
    })
    write_log(log)

def append_action(plan):
    log = read_log()
    log["history"].append({
        "timestamp": str(datetime.now()),
        "plan": plan
    })
    write_log(log)

