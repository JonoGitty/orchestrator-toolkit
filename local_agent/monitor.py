import psutil

def get_state():
    state = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'ram': dict(psutil.virtual_memory()._asdict()),
        'disk': dict(psutil.disk_usage('/')._asdict()),
        'processes': [p.info for p in psutil.process_iter(['pid', 'name'])],
    }
    return state
