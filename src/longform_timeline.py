"""Create the non-destructive, reviewable long-form decision timeline."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.longform_ingest import PROJECTS

def build_timeline(project: Path) -> dict:
    manifest = json.loads((project/'manifest.json').read_text())
    moments = json.loads((project/'analysis/moment_map.json').read_text())['moments']
    briefs = {b['moment_id']: b for b in json.loads((project/'analysis/visual_briefs.json').read_text())['briefs']}
    decisions = []
    for m in moments:
        b = briefs[m['moment_id']]
        decisions.append({
            'decision_id': f"decision_{m['moment_id'].split('_')[-1]}",
            'moment_id': m['moment_id'], 'start': m['start'], 'end': m['end'],
            'source_preservation': {'preserve_existing_visual': True, 'replace_without_review': False},
            'visual_brief_id': b['brief_id'], 'selected_asset_id': None,
            'treatment': 'enhance_existing' if b['source_type'] != 'host_primary' else 'host_primary',
            'overlays': [], 'audio_cues': [], 'caption_style': 'crimson_default',
            'status': 'needs_review', 'locked': False, 'notes': [],
        })
    timeline = {
        'schema': 'crimson.longform.timeline.v1', 'project_id': manifest['project_id'],
        'format': {'master': '1920x1080', 'aspect': '16:9', 'derivatives': ['9:16']},
        'source': {'path': manifest['source']['path'], 'immutable': True},
        'decisions': decisions,
        'review': {'current_revision': 1, 'render_requested': False, 'last_render': None},
        'qa': {'timing': 'pending', 'source_preservation': 'pending', 'rights': 'pending'},
    }
    return timeline

def process(project_id: str, projects: Path = PROJECTS) -> dict:
    project = projects / project_id
    out = project/'analysis/timeline.json'
    timeline = build_timeline(project)
    out.write_text(json.dumps(timeline, indent=2))
    manifest_path = project/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['processing']['timeline'] = {'status':'complete','path':str(out),'count':len(timeline['decisions'])}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return {'timeline':str(out),'decision_count':len(timeline['decisions'])}

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('project_id'); ap.add_argument('--projects',type=Path,default=PROJECTS)
    a=ap.parse_args(); print(json.dumps(process(a.project_id,a.projects),indent=2))
