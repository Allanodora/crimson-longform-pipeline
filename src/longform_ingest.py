"""Source-safe ingest for the long-form Crimson Chin pipeline.

This stage is intentionally small: it creates a stable project manifest without
copying or modifying source media. Later stages consume the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "data" / "longform_projects"
MEDIA_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".wav", ".mp3", ".m4a", ".flac"}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path)
    ]
    try:
        return json.loads(subprocess.check_output(command, text=True))
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


def stable_project_id(source_hash: str) -> str:
    return f"longform_{source_hash[:16]}"


def stream_summary(probe: dict[str, Any]) -> dict[str, Any]:
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "video": {
            "present": video is not None,
            "width": video.get("width") if video else None,
            "height": video.get("height") if video else None,
            "fps": video.get("r_frame_rate") if video else None,
            "codec": video.get("codec_name") if video else None,
            "duration": video.get("duration") if video else None,
        },
        "audio": {
            "present": audio is not None,
            "channels": audio.get("channels") if audio else None,
            "sample_rate": audio.get("sample_rate") if audio else None,
            "codec": audio.get("codec_name") if audio else None,
            "duration": audio.get("duration") if audio else None,
        },
        "format": probe.get("format", {}).get("format_name"),
        "duration": probe.get("format", {}).get("duration"),
    }


def ingest(source: Path, project_root: Path = PROJECTS) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError(f"Unsupported media extension: {source.suffix}")

    stat = source.stat()
    source_hash = sha256_file(source)
    project_id = stable_project_id(source_hash)
    project_dir = project_root / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    probe = ffprobe(source)
    summary = stream_summary(probe)
    manifest = {
        "schema": "crimson.longform.project.v1",
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "path": str(source),
            "filename": source.name,
            "sha256": source_hash,
            "bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "immutable": True,
        },
        "media": summary,
        "processing": {
            "proxy": {"status": "pending", "path": None},
            "waveform": {"status": "pending", "path": None},
            "thumbnails": {"status": "pending", "path": None},
            "transcript": {"status": "pending", "path": None},
            "moment_map": {"status": "pending", "path": None},
        },
        "timeline": {"version": 0, "locked_moments": [], "decisions": []},
        "assets": [],
        "rights": {"unresolved_count": 0},
        "qa": {"status": "pending", "checks": []},
    }
    (project_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a source-safe long-form project manifest")
    parser.add_argument("source", type=Path)
    parser.add_argument("--projects", type=Path, default=PROJECTS)
    args = parser.parse_args()
    manifest = ingest(args.source, args.projects)
    print(json.dumps({
        "project_id": manifest["project_id"],
        "manifest": str(args.projects / manifest["project_id"] / "manifest.json"),
        "source_sha256": manifest["source"]["sha256"],
        "media": manifest["media"],
    }, indent=2))


if __name__ == "__main__":
    main()
