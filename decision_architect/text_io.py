"""Canonical UTF-8/LF writing for deterministic text artifacts."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def canonical_lf_text(value: str) -> str:
    """Normalize newline bytes and retain exactly one final LF newline."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n") + "\n"


def atomic_write_bytes(path: str | Path, content: bytes) -> Path:
    """Atomically replace a file with exact bytes."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary_path, target)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise
    return target


def atomic_write_utf8_lf(path: str | Path, value: str) -> Path:
    """Atomically write UTF-8 text with canonical LF and one final newline."""

    return atomic_write_bytes(path, canonical_lf_text(value).encode("utf-8"))
