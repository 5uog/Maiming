# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass
import os
import platform
import subprocess
import sys
import time

@dataclass(frozen=True)
class SystemInfo:
    cpu_threads: int
    cpu_name: str
    cpu_speed_ghz: float | None
    total_mem_bytes: int | None

@dataclass(frozen=True)
class ProcessMemorySnapshot:
    rss_bytes: int | None
    total_bytes: int | None

def _safe_float(x: object) -> float | None:
    try:
        return float(x)
    except Exception:
        return None

def _posix_total_mem_bytes_sysconf() -> int | None:
    try:
        sysconf = getattr(os, "sysconf", None)
        if sysconf is None:
            return None

        pg = sysconf("SC_PHYS_PAGES")
        sz = sysconf("SC_PAGE_SIZE")
        if isinstance(pg, int) and isinstance(sz, int) and pg > 0 and sz > 0:
            return int(pg) * int(sz)
    except Exception:
        return None
    return None

def _linux_read_first_cpu_field(key: str) -> str:
    p = "/proc/cpuinfo"
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                if k.strip() == key:
                    return v.strip()
    except Exception:
        return ""
    return ""

def _linux_total_mem_bytes() -> int | None:
    p = "/proc/meminfo"
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return kb * 1024
    except Exception:
        return None
    return None

def _linux_rss_bytes_proc() -> int | None:
    p = "/proc/self/status"
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return kb * 1024
    except Exception:
        return None
    return None

def _posix_rss_bytes_ps() -> int | None:
    try:
        pid = str(os.getpid())
        out = subprocess.check_output(["ps", "-o", "rss=", "-p", pid], stderr=subprocess.DEVNULL, text=True, timeout=0.6)
        s = str(out).strip()
        if not s:
            return None
        kb = int(s.split()[0])
        if kb <= 0:
            return None
        return kb * 1024
    except Exception:
        return None

def _mac_sysctl_str(name: str) -> str:
    try:
        out = subprocess.check_output(["sysctl", "-n", name], stderr=subprocess.DEVNULL, text=True, timeout=0.6)
        return str(out).strip()
    except Exception:
        return ""

def _mac_sysctl_int(name: str) -> int | None:
    s = _mac_sysctl_str(name)
    try:
        return int(s)
    except Exception:
        return None

def _windows_cpu_name() -> str:
    try:
        import winreg  # type: ignore

        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        v, _t = winreg.QueryValueEx(k, "ProcessorNameString")
        return str(v).strip()
    except Exception:
        return ""

def _windows_cpu_mhz() -> int | None:
    try:
        import winreg  # type: ignore

        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        v, _t = winreg.QueryValueEx(k, "~MHz")
        return int(v)
    except Exception:
        return None

def _windows_total_mem_bytes() -> int | None:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_uint32),("dwMemoryLoad", ctypes.c_uint32),("ullTotalPhys", ctypes.c_uint64),("ullAvailPhys", ctypes.c_uint64),("ullTotalPageFile", ctypes.c_uint64),("ullAvailPageFile", ctypes.c_uint64),("ullTotalVirtual", ctypes.c_uint64),("ullAvailVirtual", ctypes.c_uint64),("ullAvailExtendedVirtual", ctypes.c_uint64)]

        ms = MEMORYSTATUSEX()
        ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
        if not ok:
            return None
        return int(ms.ullTotalPhys)
    except Exception:
        return None

def _windows_rss_bytes_psapi() -> int | None:
    try:
        import ctypes
        import ctypes.wintypes as wt

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [("cb", wt.DWORD),("PageFaultCount", wt.DWORD),("PeakWorkingSetSize", ctypes.c_size_t),("WorkingSetSize", ctypes.c_size_t),("QuotaPeakPagedPoolUsage", ctypes.c_size_t),("QuotaPagedPoolUsage", ctypes.c_size_t),("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),("QuotaNonPagedPoolUsage", ctypes.c_size_t),("PagefileUsage", ctypes.c_size_t),("PeakPagefileUsage", ctypes.c_size_t)]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)

        hproc = ctypes.windll.kernel32.GetCurrentProcess()

        psapi = ctypes.WinDLL("psapi")
        ok = psapi.GetProcessMemoryInfo(hproc, ctypes.byref(counters), counters.cb)
        if not ok:
            return None

        value = int(counters.WorkingSetSize)
        return value if value > 0 else None
    except Exception:
        return None

def _windows_rss_bytes_tasklist() -> int | None:
    try:
        pid = str(os.getpid())
        out = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], stderr=subprocess.DEVNULL, text=True, timeout=0.8)
        line = str(out).strip()
        if not line or "INFO:" in line:
            return None

        parts = [p.strip().strip('"') for p in line.split('","')]
        if len(parts) < 5:
            parts = [p.strip().strip('"') for p in line.split(",")]

        mem_field = parts[-1] if parts else ""
        digits = "".join(ch for ch in mem_field if ch.isdigit())
        if not digits:
            return None

        kb = int(digits)
        if kb <= 0:
            return None
        return kb * 1024
    except Exception:
        return None

def read_system_info() -> SystemInfo:
    threads = int(os.cpu_count() or 0)

    cpu_name = ""
    cpu_ghz: float | None = None
    total_mem: int | None = None

    plat = sys.platform

    if plat.startswith("win"):
        cpu_name = _windows_cpu_name()
        mhz = _windows_cpu_mhz()
        if mhz is not None:
            cpu_ghz = float(mhz) / 1000.0
        total_mem = _windows_total_mem_bytes()

    elif plat.startswith("linux"):
        cpu_name = _linux_read_first_cpu_field("model name")
        mhz_s = _linux_read_first_cpu_field("cpu MHz")
        mhz = _safe_float(mhz_s)
        if mhz is not None:
            cpu_ghz = float(mhz) / 1000.0
        total_mem = _linux_total_mem_bytes()

    elif plat.startswith("darwin"):
        cpu_name = _mac_sysctl_str("machdep.cpu.brand_string")
        hz = _mac_sysctl_int("hw.cpufrequency")
        if hz is not None and hz > 0:
            cpu_ghz = float(hz) / 1e9
        total_mem = _mac_sysctl_int("hw.memsize")

    if total_mem is None:
        total_mem = _posix_total_mem_bytes_sysconf()

    if not cpu_name:
        cpu_name = str(platform.processor() or "").strip()

    return SystemInfo(cpu_threads=int(max(0, threads)), cpu_name=str(cpu_name), cpu_speed_ghz=cpu_ghz, total_mem_bytes=total_mem)

def read_process_memory(total_mem_bytes: int | None = None) -> ProcessMemorySnapshot:
    plat = sys.platform

    rss: int | None = None
    total: int | None = total_mem_bytes

    if plat.startswith("win"):
        rss = _windows_rss_bytes_psapi()
        if rss is None:
            rss = _windows_rss_bytes_tasklist()
        if total is None:
            total = _windows_total_mem_bytes()

    elif plat.startswith("linux"):
        rss = _linux_rss_bytes_proc()
        if rss is None:
            rss = _posix_rss_bytes_ps()
        if total is None:
            total = _linux_total_mem_bytes()

    elif plat.startswith("darwin"):
        rss = _posix_rss_bytes_ps()
        if total is None:
            total = _mac_sysctl_int("hw.memsize")

    if total is None:
        total = _posix_total_mem_bytes_sysconf()

    return ProcessMemorySnapshot(rss_bytes=rss, total_bytes=total)

def _nvidia_smi_util_percent() -> float | None:
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], stderr=subprocess.DEVNULL, text=True, timeout=0.8)
        line = str(out).strip().splitlines()[0].strip()
        value = float(line)
        if value < 0.0:
            return 0.0
        if value > 100.0:
            return 100.0
        return float(value)
    except Exception:
        return None

@dataclass
class GpuUtilizationSampler:
    min_interval_s: float = 1.0
    _last_t: float = 0.0
    _last: float | None = None

    def sample(self) -> float | None:
        now = time.perf_counter()
        if (now - float(self._last_t)) < float(self.min_interval_s):
            return self._last
        self._last_t = now
        self._last = _nvidia_smi_util_percent()
        return self._last