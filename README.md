# Crimson Long-Form Pipeline

Current Sunday build for turning a natural talking-head or livestream recording into an editable long-form episode and later short derivatives.

## Workflow

`raw recording → ingest → proxy/waveform/thumbnails → transcript → moment map → visual briefs → asset registry/discovery → candidate matching → review decisions → preflight → preview render → final render`

The timeline preserves existing useful visuals and does not replace anything without an explicit review decision. The current fixture contains 9 decisions from the initial test recording.

## Input

Required: one local video file (`.mp4`, `.mov`, or `.mkv`) with speech audio. Optional: an asset folder containing screenshots, images, clips, memes, saved posts, articles, and sound effects. Keep external assets in a separate folder; the registry stores paths and hashes and does not upload them.

For the first real test, place the Manchester City recording in `input/` and use its absolute path with `longform_ingest`.

## Run

Use the bundled Python runtime if the system Python lacks dependencies:

```bash
PY=/Users/allanodora/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
$PY -m src.longform_ingest /absolute/path/to/manchester-city-recording.mp4
$PY -m src.longform_media <project_id>
$PY -m src.longform_transcribe <project_id>
$PY -m src.longform_visual_briefs <project_id>
$PY -m src.longform_timeline <project_id>
$PY -m src.longform_assets <project_id> /absolute/path/to/assets
$PY -m src.longform_discovery <project_id>
$PY -m src.longform_match <project_id>
$PY -m src.longform_review_export <project_id>
$PY -m src.longform_status <project_id>
```

Rendering is intentionally not wired to run automatically. Review decisions and run preflight first:

```bash
$PY -m src.longform_preflight <project_id>
```

## Current status

The Sunday fixture is healthy, with 9 moments, 9 visual briefs, 9 timeline decisions, 9 match records, and no imported external assets. The first Manchester City test is blocked only until its recording is supplied and the generated decisions are reviewed.
