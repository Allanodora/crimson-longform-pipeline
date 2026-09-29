"""Fast structural health checks for a long-form project."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.longform_ingest import PROJECTS

def check(project_id: str, projects: Path = PROJECTS) -> dict:
    project=projects/project_id; issues=[]
    def read(rel):
        p=project/rel
        if not p.exists(): issues.append(f'missing:{rel}'); return {}
        try: return json.loads(p.read_text())
        except Exception as e: issues.append(f'invalid_json:{rel}'); return {}
    manifest=read('manifest.json'); moments=read('analysis/moment_map.json').get('moments',[])
    briefs=read('analysis/visual_briefs.json').get('briefs',[]); timeline=read('analysis/timeline.json')
    assets=read('analysis/assets.json').get('assets',[]); discovery=read('analysis/discovery_queue.json'); matches=read('analysis/matches.json').get('matches',[])
    source=Path(manifest.get('source',{}).get('path',''))
    if not source.exists(): issues.append('source_unavailable')
    if manifest.get('source',{}).get('immutable') is not True: issues.append('source_not_immutable')
    if len(moments)!=len(briefs) or len(moments)!=len(timeline.get('decisions',[])): issues.append('count_mismatch')
    ids={m.get('moment_id') for m in moments}
    if any(b.get('moment_id') not in ids for b in briefs): issues.append('brief_link_broken')
    if any(d.get('moment_id') not in ids for d in timeline.get('decisions',[])): issues.append('decision_link_broken')
    if timeline.get('format',{}).get('aspect')!='16:9': issues.append('master_aspect_invalid')
    if any(d.get('source_preservation',{}).get('replace_without_review') for d in timeline.get('decisions',[])): issues.append('unsafe_replacement_rule')
    if discovery and discovery.get('rules',{}).get('review_required') is not True: issues.append('discovery_review_disabled')
    if discovery and discovery.get('rules',{}).get('auto_insert') is True: issues.append('discovery_auto_insert_enabled')
    if matches and len(matches)!=len(moments): issues.append('match_count_mismatch')
    for key in ('proxy','waveform','thumbnails','transcript','moment_map','visual_briefs','timeline'):
        if manifest.get('processing',{}).get(key,{}).get('status')!='complete': issues.append(f'processing_incomplete:{key}')
    return {'project_id':project_id,'healthy':not issues,'issues':issues,'counts':{'moments':len(moments),'briefs':len(briefs),'decisions':len(timeline.get('decisions',[])),'assets':len(assets),'matches':len(matches)}}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('project_id'); ap.add_argument('--projects',type=Path,default=PROJECTS)
    a=ap.parse_args(); print(json.dumps(check(a.project_id,a.projects),indent=2))
