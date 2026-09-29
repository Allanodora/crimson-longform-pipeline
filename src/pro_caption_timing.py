#!/usr/bin/env python3
import argparse
import json
import math
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


SPECIAL_TOKEN_RE = re.compile(r"^\[[_A-Z0-9?]+\]$")
ALNUM_RE = re.compile(r"[A-Za-z0-9]")
PROJECT_DIR = Path(__file__).resolve().parents[1]
AUTOCORRECT_OVERRIDES_DEFAULT = PROJECT_DIR / "autocorrect_terms.json"
DEFAULT_WORD_OVERRIDES = {
    "im": "I'm",
    "ive": "I've",
    "ill": "I'll",
    "id": "I'd",
    "dont": "don't",
    "doesnt": "doesn't",
    "didnt": "didn't",
    "isnt": "isn't",
    "arent": "aren't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "cant": "can't",
    "couldnt": "couldn't",
    "wouldnt": "wouldn't",
    "shouldnt": "shouldn't",
    "wont": "won't",
    "thats": "that's",
    "theres": "there's",
    "heres": "here's",
    "whats": "what's",
    "youre": "you're",
    "youve": "you've",
    "youll": "you'll",
    "theyre": "they're",
    "weve": "we've",
    "we're": "we're",
    "i": "I",
    "ai": "AI",
    "usa": "USA",
    "nba": "NBA",
    "nfl": "NFL",
    "mlb": "MLB",
    "nhl": "NHL",
    "ncaa": "NCAA",
    "ufc": "UFC",
    "espn": "ESPN",
}


def load_autocorrect_overrides(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    if not path.exists():
        return {}, {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "word_overrides" not in payload and "chunk_overrides" not in payload:
        return (
            {str(k).lower(): str(v) for k, v in payload.items()},
            {},
        )

    word_overrides = {
        str(k).lower(): str(v)
        for k, v in dict(payload.get("word_overrides", {})).items()
    }
    chunk_overrides = {
        str(k).lower(): str(v)
        for k, v in dict(payload.get("chunk_overrides", {})).items()
    }
    return word_overrides, chunk_overrides


def apply_word_autocorrect(words: list[dict[str, Any]], word_overrides: dict[str, str]) -> int:
    changes = 0
    overrides = dict(DEFAULT_WORD_OVERRIDES)
    overrides.update(word_overrides)

    for w in words:
        original = str(w["text"])
        lowered = original.lower()
        replacement = overrides.get(lowered)
        if replacement and replacement != original:
            w["text"] = replacement
            changes += 1
    return changes


def capitalize_chunk_text(text: str) -> str:
    text = re.sub(r"\bi\b", "I", text)
    for idx, ch in enumerate(text):
        if ch.isalpha():
            return text[:idx] + ch.upper() + text[idx + 1 :]
    return text


def apply_chunk_autocorrect(chunks: list[dict[str, Any]], chunk_overrides: dict[str, str]) -> int:
    changes = 0
    normalized_overrides = {k.lower(): v for k, v in chunk_overrides.items()}

    for chunk in chunks:
        original = str(chunk["text"]).strip()
        updated = normalized_overrides.get(original.lower(), original)
        updated = capitalize_chunk_text(updated.strip())
        if updated != original:
            chunk["text"] = updated
            changes += 1
    return changes


def tool_path(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    # Homebrew defaults on Apple Silicon / Intel
    for candidate in [f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}"]:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f"{name} not found in PATH.")


def resolve_whisper_bin(whisper_bin_arg: str) -> str:
    # If user passes an explicit path, honor it.
    p = Path(whisper_bin_arg).expanduser()
    if p.exists():
        return str(p)

    # If a command name is provided, resolve via PATH/Homebrew fallbacks.
    if whisper_bin_arg == "whisper-cli":
        found = shutil.which("whisper-cli")
        if found:
            return found
        for candidate in [
            "/opt/homebrew/bin/whisper-cli",
            "/usr/local/bin/whisper-cli",
            "/opt/homebrew/Cellar/whisper-cpp/1.7.6/bin/whisper-cli",
        ]:
            if Path(candidate).exists():
                return candidate
        raise FileNotFoundError("whisper-cli not found. Install whisper-cpp or pass --whisper-bin /full/path/to/whisper-cli")

    # Non-default binary name; try generic resolver.
    return tool_path(whisper_bin_arg)


def run(cmd: list[str]) -> None:
    print("$", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)


def ffprobe_channels(path: Path) -> int:
    out = subprocess.check_output(
        [
            tool_path("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return int(out or "1")


def sec_to_srt(ts: float) -> str:
    if ts < 0:
        ts = 0.0
    total_ms = int(round(ts * 1000.0))
    h = total_ms // 3600000
    rem = total_ms % 3600000
    m = rem // 60000
    rem %= 60000
    s = rem // 1000
    ms = rem % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def model_name_for_dtw(model_path: Path) -> str:
    name = model_path.name.lower()
    for key in ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]:
        if key in name:
            return key
    return "small"


def extract_audio(video: Path, mono_wav: Path, stereo_wav: Path, duration: Optional[float]) -> None:
    ffmpeg = tool_path("ffmpeg")
    common = [ffmpeg, "-y", "-i", str(video)]
    if duration and duration > 0:
        common.extend(["-t", f"{duration}"])

    run(common + ["-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(mono_wav)])
    run(common + ["-vn", "-ar", "16000", "-ac", "2", "-c:a", "pcm_s16le", str(stereo_wav)])


def run_whisper_json(
    whisper_bin: str,
    model: Path,
    audio_wav: Path,
    out_prefix: Path,
    language: str,
    vad: bool,
    vad_model: Optional[Path],
    dtw_model: Optional[str],
    diarize: bool,
) -> Path:
    cmd = [
        whisper_bin,
        "-ng",
        "-m",
        str(model),
        "-f",
        str(audio_wav),
        "-l",
        language,
        "-ojf",
        "-of",
        str(out_prefix),
    ]
    if vad:
        cmd.append("--vad")
        if vad_model:
            cmd.extend(["-vm", str(vad_model)])
    if dtw_model:
        cmd.extend(["-dtw", dtw_model])
    if diarize:
        cmd.append("-di")

    try:
        run(cmd)
    except subprocess.CalledProcessError:
        # Some whisper-cli builds require an explicit VAD model path.
        # Fallback to non-VAD run so timing pipeline still works end-to-end.
        if vad:
            retry: list[str] = []
            skip_next = False
            for i, c in enumerate(cmd):
                if skip_next:
                    skip_next = False
                    continue
                if c == "--vad":
                    continue
                if c == "-vm":
                    skip_next = True
                    continue
                retry.append(c)
            run(retry)
        else:
            raise
    return out_prefix.with_suffix(".json")


def parse_words(json_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    tx = payload.get("transcription", [])
    words: list[dict[str, Any]] = []

    for seg in tx:
        speaker = seg.get("speaker", "?")
        cur: Optional[dict[str, Any]] = None

        def flush_cur() -> None:
            nonlocal cur
            if not cur:
                return
            txt = str(cur["text"]).strip()
            # guard against empty/punctuation-only tokens
            if txt and ALNUM_RE.search(txt):
                words.append(cur)
            cur = None

        for tok in seg.get("tokens", []):
            raw = str(tok.get("text", ""))
            clean = raw.strip()
            if not clean:
                continue
            if SPECIAL_TOKEN_RE.match(clean):
                continue

            off = tok.get("offsets", {})
            start_ms = int(off.get("from", 0))
            end_ms = int(off.get("to", start_ms))
            p = float(tok.get("p", 0.0))

            # Whisper tokens use leading space to indicate a new word.
            starts_new_word = raw.startswith(" ")

            # Keep only word-safe chars and join token fragments to avoid broken words.
            piece = re.sub(r"[^A-Za-z0-9'’\-]", "", clean)
            if not piece:
                continue

            s = max(0.0, start_ms / 1000.0)
            e = max(s, end_ms / 1000.0)

            if starts_new_word or cur is None:
                flush_cur()
                cur = {
                    "text": piece,
                    "start": s,
                    "end": e,
                    "confidence": p,
                    "speaker": speaker,
                    "_n": 1,
                }
            else:
                cur["text"] = str(cur["text"]) + piece
                cur["end"] = max(float(cur["end"]), e)
                n = int(cur.get("_n", 1))
                cur["confidence"] = (float(cur["confidence"]) * n + p) / (n + 1)
                cur["_n"] = n + 1

        flush_cur()

    words.sort(key=lambda w: (w["start"], w["end"]))
    for w in words:
        w.pop("_n", None)
    return words


def apply_confidence_fallback(words: list[dict[str, Any]], threshold: float, min_word_ms: int = 80) -> None:
    if not words:
        return

    min_d = min_word_ms / 1000.0

    for i, w in enumerate(words):
        s = float(w["start"])
        e = float(w["end"])
        if e <= s:
            e = s + min_d

        if w["confidence"] < threshold:
            prev_end = words[i - 1]["end"] if i > 0 else s
            next_start = words[i + 1]["start"] if i + 1 < len(words) else e
            local_span = max(min_d, float(next_start) - float(prev_end))
            mid = max(float(prev_end), min(float(next_start), (s + e) / 2.0))
            e = min(float(next_start), mid + local_span * 0.35)
            s = max(float(prev_end), e - max(min_d, local_span * 0.25))

        w["start"] = s
        w["end"] = max(s + min_d, e)

    for i in range(1, len(words)):
        if words[i]["start"] < words[i - 1]["end"]:
            words[i]["start"] = words[i - 1]["end"]
        if words[i]["end"] <= words[i]["start"]:
            words[i]["end"] = words[i]["start"] + min_d


def apply_global_offset(words: list[dict[str, Any]], offset_ms: int) -> None:
    if not words or offset_ms == 0:
        return
    d = offset_ms / 1000.0
    for w in words:
        w["start"] = max(0.0, w["start"] + d)
        w["end"] = max(w["start"] + 0.05, w["end"] + d)


def group_karaoke_words(
    words: list[dict[str, Any]],
    max_words: int,
    max_chunk_seconds: float,
    max_chars: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    cur: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal cur
        if not cur:
            return
        txt = " ".join(x["text"] for x in cur)
        chunks.append(
            {
                "start": cur[0]["start"],
                "end": cur[-1]["end"],
                "text": txt,
                "speaker": cur[0]["speaker"],
                "confidence": sum(x["confidence"] for x in cur) / len(cur),
            }
        )
        cur = []

    for w in words:
        if not cur:
            cur = [w]
            continue

        next_count = len(cur) + 1
        next_text = " ".join(x["text"] for x in cur + [w])
        next_duration = w["end"] - cur[0]["start"]
        same_speaker = w["speaker"] == cur[0]["speaker"]

        if (
            next_count > max_words
            or len(next_text) > max_chars
            or next_duration > max_chunk_seconds
            or not same_speaker
        ):
            flush()
            cur = [w]
        else:
            cur.append(w)

    flush()

    # Merge ultra-short flashes into adjacent chunks for cleaner, polished rhythm.
    i = 0
    min_chunk_d = 0.22
    while i < len(chunks):
        d = chunks[i]["end"] - chunks[i]["start"]
        if d >= min_chunk_d or len(chunks) == 1:
            i += 1
            continue

        if i + 1 < len(chunks):
            chunks[i + 1]["start"] = min(chunks[i]["start"], chunks[i + 1]["start"])
            chunks[i + 1]["text"] = f"{chunks[i]['text']} {chunks[i + 1]['text']}".strip()
            chunks[i + 1]["confidence"] = (chunks[i]["confidence"] + chunks[i + 1]["confidence"]) / 2.0
            chunks.pop(i)
            continue
        if i - 1 >= 0:
            chunks[i - 1]["end"] = max(chunks[i - 1]["end"], chunks[i]["end"])
            chunks[i - 1]["text"] = f"{chunks[i - 1]['text']} {chunks[i]['text']}".strip()
            chunks[i - 1]["confidence"] = (chunks[i - 1]["confidence"] + chunks[i]["confidence"]) / 2.0
            chunks.pop(i)
            i -= 1
            continue
        i += 1

    for i in range(1, len(chunks)):
        if chunks[i]["start"] < chunks[i - 1]["end"]:
            chunks[i]["start"] = chunks[i - 1]["end"]
        if chunks[i]["end"] <= chunks[i]["start"]:
            chunks[i]["end"] = chunks[i]["start"] + 0.08

    return chunks


def write_srt(chunks: list[dict[str, Any]], out_srt: Path) -> None:
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        lines.append(str(i))
        lines.append(f"{sec_to_srt(c['start'])} --> {sec_to_srt(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    out_srt.write_text("\n".join(lines), encoding="utf-8")


def summarize(words: list[dict[str, Any]], chunks: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    low = [w for w in words if w["confidence"] < threshold]
    speakers = sorted(set(str(w.get("speaker", "?")) for w in words))
    return {
        "word_count": len(words),
        "chunk_count": len(chunks),
        "low_confidence_words": len(low),
        "low_confidence_ratio": (len(low) / len(words)) if words else 0.0,
        "speakers_detected": speakers,
        "min_start": words[0]["start"] if words else 0.0,
        "max_end": words[-1]["end"] if words else 0.0,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Pro timing pass for karaoke captions using local whisper-cli")
    p.add_argument("video", type=Path, help="Input video file")
    p.add_argument("--model", type=Path, default=Path("/Users/allanodora/Downloads/small.bin"))
    p.add_argument("--out-prefix", type=Path, default=None, help="Output prefix path (without extension)")
    p.add_argument("--whisper-bin", default="whisper-cli")
    p.add_argument("--language", default="en")
    p.add_argument("--duration", type=float, default=0.0, help="Optional quick-test duration in seconds")
    p.add_argument("--max-words", type=int, default=3)
    p.add_argument("--max-chunk-seconds", type=float, default=1.2)
    p.add_argument("--max-chars", type=int, default=22)
    p.add_argument("--confidence-threshold", type=float, default=0.60)
    p.add_argument("--offset-ms", type=int, default=0)
    p.add_argument("--no-vad", action="store_true")
    p.add_argument("--vad-model", type=Path, default=None, help="Optional whisper.cpp VAD model path")
    p.add_argument("--no-diarize", action="store_true")
    p.add_argument(
        "--autocorrect-overrides",
        type=Path,
        default=AUTOCORRECT_OVERRIDES_DEFAULT,
        help="Optional JSON file with word_overrides and chunk_overrides for transcript cleanup",
    )
    args = p.parse_args()

    video = args.video.expanduser().resolve()
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video}")

    model = args.model.expanduser().resolve()
    if not model.exists():
        raise FileNotFoundError(f"Model not found: {model}")

    out_prefix = args.out_prefix
    if out_prefix is None:
        out_prefix = video.parent / f"{video.stem}_protiming"
    out_prefix = out_prefix.expanduser().resolve()
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    mono_wav = out_prefix.with_name(out_prefix.name + "_mono.wav")
    stereo_wav = out_prefix.with_name(out_prefix.name + "_stereo.wav")

    extract_audio(video, mono_wav, stereo_wav, args.duration if args.duration > 0 else None)

    dtw_model = model_name_for_dtw(model)
    whisper_bin = resolve_whisper_bin(args.whisper_bin)

    raw_json = run_whisper_json(
        whisper_bin=whisper_bin,
        model=model,
        audio_wav=mono_wav,
        out_prefix=out_prefix.with_name(out_prefix.name + "_raw"),
        language=args.language,
        vad=not args.no_vad,
        vad_model=args.vad_model.expanduser().resolve() if args.vad_model else None,
        dtw_model=dtw_model,
        diarize=False,
    )

    diar_json = None
    can_diarize = (not args.no_diarize) and ffprobe_channels(stereo_wav) >= 2
    if can_diarize:
        diar_json = run_whisper_json(
            whisper_bin=whisper_bin,
            model=model,
            audio_wav=stereo_wav,
            out_prefix=out_prefix.with_name(out_prefix.name + "_diar"),
            language=args.language,
            vad=not args.no_vad,
            vad_model=args.vad_model.expanduser().resolve() if args.vad_model else None,
            dtw_model=None,
            diarize=True,
        )

    words = parse_words(raw_json)

    # If diarization produced known speaker labels, project them by overlap.
    if diar_json and diar_json.exists() and words:
        diar = json.loads(diar_json.read_text(encoding="utf-8"))
        segs = diar.get("transcription", [])
        diar_segments = []
        for s in segs:
            spk = s.get("speaker", "?")
            off = s.get("offsets", {})
            diar_segments.append((float(off.get("from", 0)) / 1000.0, float(off.get("to", 0)) / 1000.0, spk))
        if diar_segments:
            for w in words:
                mid = (w["start"] + w["end"]) / 2.0
                for ds, de, spk in diar_segments:
                    if ds <= mid <= de and spk != "?":
                        w["speaker"] = spk
                        break

    apply_confidence_fallback(words, threshold=args.confidence_threshold)
    apply_global_offset(words, offset_ms=args.offset_ms)
    word_overrides, chunk_overrides = load_autocorrect_overrides(
        args.autocorrect_overrides.expanduser().resolve()
    )
    word_change_count = apply_word_autocorrect(words, word_overrides)

    chunks = group_karaoke_words(
        words,
        max_words=max(1, args.max_words),
        max_chunk_seconds=max(0.2, args.max_chunk_seconds),
        max_chars=max(8, args.max_chars),
    )
    chunk_change_count = apply_chunk_autocorrect(chunks, chunk_overrides)

    words_json = out_prefix.with_suffix(".words.json")
    srt_out = out_prefix.with_suffix(".aligned.srt")
    report_out = out_prefix.with_suffix(".timing_report.json")

    words_json.write_text(json.dumps(words, indent=2), encoding="utf-8")
    write_srt(chunks, srt_out)
    report = summarize(words, chunks, args.confidence_threshold)
    report["autocorrect_word_changes"] = word_change_count
    report["autocorrect_chunk_changes"] = chunk_change_count
    report["autocorrect_overrides_file"] = str(args.autocorrect_overrides.expanduser())
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Keep WAVs for debugging only if needed; default clean up.
    mono_wav.unlink(missing_ok=True)
    stereo_wav.unlink(missing_ok=True)

    print(f"raw_json: {raw_json}")
    if diar_json:
        print(f"diar_json: {diar_json}")
    print(f"words_json: {words_json}")
    print(f"aligned_srt: {srt_out}")
    print(f"timing_report: {report_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
