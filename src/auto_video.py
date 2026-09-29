#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

OPENAI_API_BASE = "https://api.openai.com/v1"


def run(cmd: list[str]) -> None:
    print("$", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)


def probe_duration_seconds(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def openai_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def format_openai_error(response: requests.Response) -> str:
    status = response.status_code
    default = response.text.strip()[:300] if response.text else "No response body."
    message = default
    err_type = ""
    err_code = ""
    try:
        payload = response.json()
        err = payload.get("error", {})
        message = err.get("message", message)
        err_type = err.get("type", "")
        err_code = err.get("code", "")
    except ValueError:
        pass

    if status == 401:
        return (
            "OpenAI auth failed (401): invalid or revoked API key.\n"
            "Set a valid OPENAI_API_KEY in .env, then retry.\n"
            f"API says: {message}"
        )
    if status == 429:
        return (
            "OpenAI quota/rate limit hit (429): billing or credits may be exhausted.\n"
            "Check billing and usage limits, then retry.\n"
            f"API says: {message}"
        )
    if status == 403:
        return (
            "OpenAI request forbidden (403): model access or project permissions issue.\n"
            "Check key permissions and model availability for your project.\n"
            f"API says: {message}"
        )
    return f"OpenAI API request failed ({status}): {message} (type={err_type}, code={err_code})"


def openai_post(path: str, api_key: str, payload: dict, timeout: int) -> requests.Response:
    r = requests.post(
        f"{OPENAI_API_BASE}{path}",
        headers=openai_headers(api_key),
        json=payload,
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(format_openai_error(r))
    return r


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response did not contain valid JSON.")
    return json.loads(text[start : end + 1])


def plan_video(topic: str, target_seconds: int, scene_count: int, model: str, api_key: str) -> dict:
    prompt = f"""
Create a short faceless video plan about: {topic}
Target duration: ~{target_seconds} seconds.
Number of scenes: exactly {scene_count}.

Return ONLY valid JSON with this exact schema:
{{
  "title": "string",
  "voiceover": "single full narration text",
  "scenes": [
    {{"image_prompt": "highly visual prompt", "on_screen_text": "short text 3-8 words"}}
  ]
}}

Rules:
- The scenes array length must be exactly {scene_count}.
- Voiceover should flow naturally and match the scene sequence.
- Avoid copyrighted characters and brand logos.
""".strip()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise creative director."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }
    r = openai_post("/chat/completions", api_key, payload, timeout=120)
    text = r.json()["choices"][0]["message"]["content"]
    data = extract_json(text)
    scenes = data.get("scenes", [])
    if len(scenes) != scene_count:
        raise ValueError(f"Expected {scene_count} scenes, got {len(scenes)}")
    return data


def generate_image(prompt: str, out_path: Path, api_key: str, model: str = "gpt-image-1") -> None:
    payload = {
        "model": model,
        "prompt": prompt,
        "size": "1536x1024",
        "quality": "high",
    }
    r = openai_post("/images/generations", api_key, payload, timeout=180)
    data = r.json()["data"][0]

    if "b64_json" in data:
        out_path.write_bytes(base64.b64decode(data["b64_json"]))
        return

    image_url = data.get("url")
    if not image_url:
        raise ValueError("Image response had no b64_json or url")

    img = requests.get(image_url, timeout=120)
    img.raise_for_status()
    out_path.write_bytes(img.content)


def synthesize_voice(text: str, out_path: Path, api_key: str, voice: str, model: str = "gpt-4o-mini-tts") -> None:
    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "format": "mp3",
    }
    r = openai_post("/audio/speech", api_key, payload, timeout=180)
    out_path.write_bytes(r.content)


def make_scene_clip(image_path: Path, text: str, duration: float, out_path: Path) -> None:
    safe_text = text.replace("'", "\\'").replace(":", "\\:")

    vf = (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,"
        "zoompan=z='min(zoom+0.0008,1.08)':d=1:s=1920x1080:fps=30,"
        f"drawtext=text='{safe_text}':fontcolor=white:fontsize=56:"
        "box=1:boxcolor=black@0.45:boxborderw=20:"
        "x=(w-text_w)/2:y=h-160"
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-t",
            f"{duration:.2f}",
            "-vf",
            vf,
            "-r",
            "30",
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ]
    )


def concat_clips(clips: list[Path], out_path: Path) -> None:
    list_file = out_path.parent / "clips.txt"
    list_file.write_text("\n".join([f"file '{c.name}'" for c in clips]) + "\n")

    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(out_path),
        ]
    )


def mux_audio(video_path: Path, audio_path: Path, out_path: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-shortest",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_path),
        ]
    )


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate faceless AI videos automatically.")
    parser.add_argument("topic", help="Video topic")
    parser.add_argument("--seconds", type=int, default=30, help="Target video length")
    parser.add_argument("--scenes", type=int, default=6, help="Number of scenes")
    parser.add_argument("--voice", default="alloy", help="TTS voice")
    parser.add_argument("--model", default="gpt-4o-mini", help="Planning model")
    parser.add_argument("--outdir", default="runs", help="Output directory")
    parser.add_argument("--api-key", default=None, help="Optional API key override")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY in environment or .env", file=sys.stderr)
        return 1

    run_dir = Path(args.outdir) / re.sub(r"[^a-zA-Z0-9_-]+", "_", args.topic.strip())
    run_dir.mkdir(parents=True, exist_ok=True)

    print("Planning video...")
    try:
        plan = plan_video(args.topic, args.seconds, args.scenes, args.model, api_key)
    except requests.Timeout:
        print("OpenAI request timed out. Retry in a moment.", file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"Network error calling OpenAI: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=2))

    try:
        print("Generating voiceover...")
        audio_file = run_dir / "voiceover.mp3"
        synthesize_voice(plan["voiceover"], audio_file, api_key, args.voice)
        audio_duration = probe_duration_seconds(audio_file)

        per_scene = max(2.0, audio_duration / args.scenes)

        print("Generating scene images and clips...")
        clip_paths: list[Path] = []
        for i, scene in enumerate(plan["scenes"], start=1):
            image_path = run_dir / f"scene_{i:02d}.png"
            clip_path = run_dir / f"clip_{i:02d}.mp4"

            prompt = scene.get("image_prompt", "cinematic shot")
            text = scene.get("on_screen_text", "")

            generate_image(prompt, image_path, api_key)
            make_scene_clip(image_path, text, per_scene, clip_path)
            clip_paths.append(clip_path)

        silent_video = run_dir / "video_silent.mp4"
        final_video = run_dir / "video_final.mp4"

        print("Stitching final video...")
        concat_clips(clip_paths, silent_video)
        mux_audio(silent_video, audio_file, final_video)
    except requests.Timeout:
        print("OpenAI request timed out. Retry in a moment.", file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"Network error calling OpenAI: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    print(f"Done: {final_video}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
