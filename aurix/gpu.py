"""How much of the graphics card everything else is using.

Windows keeps this in a performance counter, so there is nothing to install and
nothing vendor specific - it reads the same on AMD, Intel and NVIDIA. The
alternative was shelling out to Get-Counter, which would mean starting a
PowerShell process every few seconds for the life of the app.

Nothing here throws. A machine that will not report its video memory should
mean gaming mode never triggers, not that Aurix falls over.
"""

import ctypes
from ctypes import wintypes

_COUNTER = r"\GPU Adapter Memory(*)\Dedicated Usage"
_PDH_FMT_LARGE = 0x00000400
_PDH_MORE_DATA = 0x800007D2

_pdh = None
_query = None
_counter = None
_broken = False


class _Value(ctypes.Structure):
    # the union in PDH_FMT_COUNTERVALUE is 8 bytes and 8-aligned, so the 4 byte
    # status is followed by 4 bytes of padding - getting this wrong reads
    # plausible nonsense rather than failing
    _fields_ = [("status", ctypes.c_ulong), ("large", ctypes.c_longlong)]


class _Item(ctypes.Structure):
    _fields_ = [("name", ctypes.c_wchar_p), ("value", _Value)]


def _open() -> bool:
    """Set the query up once. False means this machine cannot answer."""
    global _pdh, _query, _counter, _broken
    if _broken:
        return False
    if _counter is not None:
        return True

    try:
        _pdh = ctypes.WinDLL("pdh.dll")
        # unsigned, or every status comes back signed and the PDH_MORE_DATA
        # check silently never matches - 0x800007D2 reads as -2147481134
        for name in ("PdhOpenQueryW", "PdhAddEnglishCounterW",
                     "PdhCollectQueryData", "PdhGetFormattedCounterArrayW"):
            getattr(_pdh, name).restype = ctypes.c_ulong

        query = wintypes.LPVOID()
        if _pdh.PdhOpenQueryW(None, 0, ctypes.byref(query)) != 0:
            _broken = True
            return False

        counter = wintypes.LPVOID()
        # the English name, so it still works on a machine running in another
        # language - the localised counter names differ
        if _pdh.PdhAddEnglishCounterW(
            query, _COUNTER, 0, ctypes.byref(counter)
        ) != 0:
            _pdh.PdhCloseQuery(query)
            _broken = True
            return False

        _query, _counter = query, counter
        return True
    except OSError:
        _broken = True
        return False


def in_use_mb() -> float | None:
    """Dedicated video memory in use on the busiest adapter, in MB.

    Everything on the card, Aurix included. None when it cannot be read.
    """
    if not _open():
        return None

    try:
        if _pdh.PdhCollectQueryData(_query) != 0:
            return None

        size = wintypes.DWORD(0)
        count = wintypes.DWORD(0)
        # first call fails on purpose, to say how much room the answer needs
        status = _pdh.PdhGetFormattedCounterArrayW(
            _counter, _PDH_FMT_LARGE, ctypes.byref(size), ctypes.byref(count), None
        )
        if status != _PDH_MORE_DATA or not size.value:
            return None

        buffer = (ctypes.c_byte * size.value)()
        if _pdh.PdhGetFormattedCounterArrayW(
            _counter, _PDH_FMT_LARGE, ctypes.byref(size), ctypes.byref(count),
            ctypes.byref(buffer),
        ) != 0:
            return None

        items = ctypes.cast(
            ctypes.byref(buffer), ctypes.POINTER(_Item * count.value)
        ).contents
        # the busiest adapter, because a laptop reports its integrated one too
        # and the one being fought over is the one that matters
        biggest = max((item.value.large for item in items), default=0)
        return biggest / 1024 / 1024
    except OSError:
        return None
