"""Optional ffmpeg compression helpers for H264/H265 post-processing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def compress_clip(input_path: str | Path, codec: str = "libx264", crf: int = 28, preset: str = "veryfast") -> Path | None:
    """Compress a clip in-place via a temporary file when ffmpeg is installed."""

    source = Path(input_path)
    if not source.exists() or not ffmpeg_available():
        return None
    target = source.with_name(f"{source.stem}.compressed{source.suffix}")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-c:v",
        codec,
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-an",
        str(target),
    ]
    subprocess.run(command, check=True, capture_output=True)
    target.replace(source)
    return source
