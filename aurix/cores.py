"""Keeping the work on the fast cores.

Newer Intel processors have two kinds of core - big fast ones and small slow
ones - and Windows will quietly move onnxruntime's threads onto the small ones
part way through and then leave them there. Measured on this machine, speaking
sat at 3.4x realtime while it was on the fast cores and 0.7x once it had
drifted, and it never came back without a restart. That reads as Aurix hanging,
not as it being slow, and it hits the wake word and the speech model too since
all three are the same library.

Windows will say which cores are the fast ones, so this asks and pins to those.
On a processor where every core is the same - which is most of them - the mask
covers everything and this changes nothing.
"""

import ctypes
import struct
from ctypes import wintypes

_RELATION_PROCESSOR_CORE = 0
_ERROR_INSUFFICIENT_BUFFER = 122

# Offsets into SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX. Each record says its own
# length, because the group masks on the end are variable.
_SIZE_AT = 4
_EFFICIENCY_AT = 9  # 0 is the slowest kind of core, higher is faster
_MASK_AT = 32


def use_the_fast_ones() -> str:
    """Pin this process to the fastest cores. Returns what it did, for the log.

    Never throws. Being stuck on the wrong cores is bad but it still works, and
    refusing to start over it would be worse.
    """
    try:
        cores = _cores()
    except OSError as error:
        return f"could not ask about the cores ({error})"

    if not cores:
        return "no core information, left alone"

    fastest = max(speed for speed, _mask in cores)
    if all(speed == fastest for speed, _mask in cores):
        return "every core is the same, nothing to pin to"

    wanted = 0
    for speed, mask in cores:
        if speed == fastest:
            wanted |= mask

    if not _pin(wanted):
        return f"could not pin to 0x{wanted:X}"
    return f"pinned to the {bin(wanted).count('1')} fast cores of {_count(cores)}"


def _count(cores) -> int:
    return sum(bin(mask).count("1") for _speed, mask in cores)


def _cores():
    """Every physical core, as (how fast, which logical processors)."""
    kernel32 = ctypes.windll.kernel32
    kernel32.GetLogicalProcessorInformationEx.argtypes = [
        ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)
    ]
    kernel32.GetLogicalProcessorInformationEx.restype = wintypes.BOOL

    length = wintypes.DWORD(0)
    kernel32.GetLogicalProcessorInformationEx(
        _RELATION_PROCESSOR_CORE, None, ctypes.byref(length)
    )
    if kernel32.GetLastError() != _ERROR_INSUFFICIENT_BUFFER:
        raise OSError(f"asking how much room to make failed ({kernel32.GetLastError()})")

    buffer = ctypes.create_string_buffer(length.value)
    if not kernel32.GetLogicalProcessorInformationEx(
        _RELATION_PROCESSOR_CORE, buffer, ctypes.byref(length)
    ):
        raise OSError(f"reading the core list failed ({kernel32.GetLastError()})")

    return list(_read(buffer.raw[: length.value]))


def _read(raw: bytes):
    """Walk the records, each of which says how long it is."""
    at = 0
    while at + _MASK_AT <= len(raw):
        size = struct.unpack_from("<I", raw, at + _SIZE_AT)[0]
        if size == 0:
            return
        speed = raw[at + _EFFICIENCY_AT]
        mask = struct.unpack_from("<Q", raw, at + _MASK_AT)[0]
        yield speed, mask
        at += size


def _pin(mask: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    kernel32.SetProcessAffinityMask.restype = wintypes.BOOL
    return bool(kernel32.SetProcessAffinityMask(kernel32.GetCurrentProcess(), mask))
