"""Clock domains used by execution, receive deadlines and retry recovery."""
from __future__ import annotations

import ctypes
from functools import cached_property
import subprocess
import sys
import time
from uuid import uuid4


def _boot_event() -> str | None:
    # Read the newest kernel startup event in record order. Its recorded
    # timestamp is an identity component, never an input to elapsed time.
    command = ("$event = Get-WinEvent -LogName System "
               "-FilterXPath \"*[System[Provider[@Name='Microsoft-Windows-Kernel-General'] and EventID=12]]\" "
               "-MaxEvents 1 -ErrorAction Stop; "
               "[Console]::Write($event.RecordId.ToString() + ':' + $event.TimeCreated.ToUniversalTime().Ticks)")
    try:
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, timeout=3, check=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        identity = result.stdout.strip()
        if len(identity.split(":")) == 2 and all(part.isascii() and part.isdecimal() for part in identity.split(":")):
            return "windows-startup:" + identity
    except (OSError, subprocess.SubprocessError):
        pass
    return None


class Clocks:
    def __init__(self, portable=time):
        self.portable = portable
        self.process_basis = "process:" + uuid4().hex
        self.windows = sys.platform == "win32" and portable is time
        if self.windows:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            # The real-time API set exports QueryInterruptTime on Windows 10,
            # including builds where kernel32 does not forward that symbol.
            realtime = ctypes.WinDLL("api-ms-win-core-realtime-l1-1-1")
            self._interrupt = realtime.QueryInterruptTime
            self._interrupt.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]
            self._interrupt.restype = None
            self._working = kernel.QueryUnbiasedInterruptTime
            self._working.argtypes = self._interrupt.argtypes
            self._working.restype = ctypes.c_int

    def wall(self) -> float:
        return self.portable.time()

    def monotonic(self) -> float:
        return self.portable.monotonic()

    def working(self) -> float:
        if not self.windows:
            return self.monotonic()
        ticks = ctypes.c_ulonglong()
        if not self._working(ctypes.byref(ticks)):
            raise ctypes.WinError(ctypes.get_last_error())
        return ticks.value / 10_000_000

    def interrupt(self) -> float:
        if not self.windows:
            return self.monotonic()
        ticks = ctypes.c_ulonglong()
        self._interrupt(ctypes.byref(ticks))
        return ticks.value / 10_000_000

    @cached_property
    def boot_identity(self) -> str | None:
        return _boot_event() if self.windows else None

    def pair(self) -> tuple[float, float]:
        if self.windows:
            return self.working(), self.interrupt()
        now = self.monotonic()
        return now, now


SYSTEM_CLOCKS = Clocks()
