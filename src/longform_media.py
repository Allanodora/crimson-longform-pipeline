"""Generate bounded analysis media for a long-form project manifest."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from src.longform_ingest import PROJECTS


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def media_paths(project_dir: Path) -> dict[str, Path]:
    media = project_dir / "media"
    return {
        "proxy": media / "proxy_540p.mp4",
        "waveform": media / "waveform.npz",
        "thumbnails": media / "thumbnails.jpg",
    }


def build_proxy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-vf", "scale=-2:540", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
        str(target),
    ])


def build_waveform(source: Path, target: Path, bins: int = 2400) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(source), "-vn", "-ac", "1",
        "-ar", "16000", "-f", "f32le", "-",
    ])
    audio = np.frombuffer(raw, dtype="<f4")
    chunks = np.array_split(audio, min(bins, max(1, len(audio))))
    peaks = np.asarray([np.max(np.abs(chunk)) if len(chunk) else 0.0 for chunk in chunks], dtype=np.float32)
    rms = np.asarray([
        float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2))) if len(chunk) else 0.0
        for chunk in chunks
    ], dtype=np.float32)
    np.savez_compressed(target, sample_rate=16000, peaks=peaks, rms=rms, duration=len(audio) / 16000)


def build_thumbnails(source: Path, target: Path, count: int = 12) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(source),
    ], text=True))
    duration = float(probe["format"]["duration"])
    times = np.linspace(0, max(0.0, duration - 0.5), count)
    tiles: list[Image.Image] = []
    for index, timestamp in enumerate(times):
        raw = subprocess.check_output([
            "ffmpeg", "-v", "error", "-i", str(source), "-ss", f"{timestamp:.3f}",
            "-frames:v", "1", "-vf", "scale=240:-2", "-f", "image2pipe", "-vcodec", "png", "-",
        ])
        tile = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
        tile.thumbnail((240, 240))
        canvas = Image.new("RGB", (240, 270), "#101524")
        canvas.paste(tile, ((240 - tile.width) // 2, 0))
        ImageDraw.Draw(canvas).text((8, 248), f"{timestamp:.2f}s", fill="white")
        tiles.append(canvas)
    sheet = Image.new("RGB", (240 * 4, 270 * 3), "#101524")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 4) * 240, (index // 4) * 270))
    sheet.save(target, quality=88)


def prepare(project_id: str, projects: Path = PROJECTS) -> dict[str, Any]:
    project_dir = projects / project_id
    manifest_path = project_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = Path(manifest["source"]["path"])
    paths = media_paths(project_dir)
    build_proxy(source, paths["proxy"])
    build_waveform(source, paths["waveform"])
    build_thumbnails(source, paths["thumbnails"])
    manifest["processing"]["proxy"] = {"status": "complete", "path": str(paths["proxy"])}
    manifest["processing"]["waveform"] = {"status": "complete", "path": str(paths["waveform"])}
    manifest["processing"]["thumbnails"] = {"status": "complete", "path": str(paths["thumbnails"])}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare bounded long-form analysis media")
    parser.add_argument("project_id")
    parser.add_argument("--projects", type=Path, default=PROJECTS)
    args = parser.parse_args()
    manifest = prepare(args.project_id, args.projects)
    print(json.dumps(manifest["processing"], indent=2))


if __name__ == "__main__":
    main()
