import platform
import time

import psutil


def collect_metrics() -> dict:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    boot = psutil.boot_time()
    return {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "disk_percent": disk.percent,
        "network_in": net.bytes_recv,
        "network_out": net.bytes_sent,
        "load_average": list(load),
        "uptime_seconds": int(time.time() - boot),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def get_os_info() -> str:
    return f"{platform.system()} {platform.release()} ({platform.machine()})"
