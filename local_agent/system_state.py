import psutil
import platform
from datetime import datetime

def get_state():
    """Collects current system state."""
    return {
        "time": str(datetime.now()),
        "platform": platform.system(),
        "platform-release": platform.release(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "running_processes": len(psutil.pids())
    }

