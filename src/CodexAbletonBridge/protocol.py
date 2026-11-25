"""Exchange request and reply files between the MCP server and Live."""
import json
import os
import stat
from pathlib import Path
from tempfile import NamedTemporaryFile

EFFECTS = ("EQ Three", "Auto Filter", "Reverb", "Delay", "Compressor", "Utility")


def inbox(base=Path("/tmp")):
    if not hasattr(os, "getuid"):
        raise RuntimeError("The Live bridge requires a POSIX per-user directory. Use macOS for Live.")
    uid = os.getuid()
    path = base / ("codex-ableton-bridge-v1-%d" % uid)
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077:
        raise RuntimeError("The bridge directory must be owned by the current user and private.")
    return path


def write_json(path, data):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(data, handle, allow_nan=False)
            handle.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
