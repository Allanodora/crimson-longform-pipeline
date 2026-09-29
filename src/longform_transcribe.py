"""Cached transcription and first-pass moment mapping."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from src.longform_ingest import PROJECTS

VISUAL_TERMS = re.compile(r"\b(video|clip|picture|photo|image|screenshot|comment|tweet|post|article|quote|stat|goal|match|press conference|said|says)\b", re.I)
EMOTION_TERMS = re.compile(r"\b(what|wow|crazy|ridiculous|awful|brilliant|unbelievable|fuming|love|hate|joke|funny|insane|disaster|terrible|beautiful)\b", re.I)


def run_whisper(source: Path, output_dir: Path, model: str = "small.en") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / (source.stem + ".json")
    if output.exists():
        return output
    command = [
        "/Users/allanodora/.local/bin/whisper", str(source),
        "--model", model, "--language", "en", "--output_dir", str(output_dir),
        "--output_format", "json", "--fp16", "False", "--word_timestamps", "True",
    ]
    subprocess.run(command, check=True)
    if not output.exists():
        raise FileNotFoundError(output)
    return output


def segment_words(segment: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"word": word.get("word", "").strip(), "start": word.get("start"), "end": word.get("end")}
        for word in segment.get("words", [])
    ]


def make_moments(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    moments: list[dict[str, Any]] = []
    for index, segment in enumerate(transcript.get("segments", [])):
        text = " ".join(segment.get("text", "").split())
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        words = segment_words(segment)
        intensity = 0.35
        if len(words) >= 12 or (end - start) > 4:
            intensity += 0.1
        if "!" in text or EMOTION_TERMS.search(text):
            intensity += 0.25
        visual = bool(VISUAL_TERMS.search(text))
        moments.append({
            "moment_id": f"moment_{index:04d}",
            "start": start,
            "end": end,
            "text": text,
            "words": words,
            "topic": None,
            "entities": [],
            "signals": {
                "visual_reference": visual,
                "emotion": round(min(1.0, intensity), 3),
                "claim": any(token in text.lower() for token in ["is", "are", "was", "were", "will"]),
                "quote_or_report": any(token in text.lower() for token in ["said", "says", "according", "report"]),
            },
            "visual_mode": "SOURCE_CANDIDATE" if visual else "HOST_PRIMARY",
            "audio_opportunity": "emphasis" if intensity >= 0.6 else None,
            "edit_priority": round(min(1.0, intensity + (0.15 if visual else 0.0)), 3),
            "locked": False,
        })
    return moments


def process(project_id: str, projects: Path = PROJECTS) -> dict[str, Any]:
    project = projects / project_id
    manifest_path = project / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = Path(manifest["source"]["path"])
    transcript_path = run_whisper(source, project / "analysis" / "transcript")
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    moments = make_moments(transcript)
    moment_path = project / "analysis" / "moment_map.json"
    moment_path.write_text(json.dumps({"schema": "crimson.longform.moments.v1", "moments": moments}, indent=2), encoding="utf-8")
    manifest["processing"]["transcript"] = {"status": "complete", "path": str(transcript_path)}
    manifest["processing"]["moment_map"] = {"status": "complete", "path": str(moment_path), "count": len(moments)}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"transcript": str(transcript_path), "moment_map": str(moment_path), "moment_count": len(moments)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe and map long-form moments")
    parser.add_argument("project_id")
    parser.add_argument("--projects", type=Path, default=PROJECTS)
    args = parser.parse_args()
    print(json.dumps(process(args.project_id, args.projects), indent=2))


if __name__ == "__main__":
    main()
