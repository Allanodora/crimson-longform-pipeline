"""Cheap render preflight; never starts rendering."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from src.longform_ingest import PROJECTS
def run(project_id,projects=PROJECTS):
 p=projects/project_id; t=json.load(open(p/'analysis/timeline.json')); assets=json.load(open(p/'analysis/assets.json'))['assets']; ids={a['asset_id'] for a in assets}; blockers=[]; warnings=[]
 for d in t['decisions']:
  if d['status'] not in ('approve','hold','override'): blockers.append(f"{d['decision_id']}:unreviewed")
  if d.get('selected_asset_id') and d['selected_asset_id'] not in ids: blockers.append(f"{d['decision_id']}:asset_missing")
 if t['format']['aspect']!='16:9': blockers.append('master_aspect_invalid')
 if any(not d['locked'] and d['status']=='approve' for d in t['decisions']): warnings.append('approved_decision_unlocked')
 result={'project_id':project_id,'render_ready':not blockers,'blockers':blockers,'warnings':warnings,'decision_count':len(t['decisions'])}
 out=p/'analysis/render_preflight.json'; out.write_text(json.dumps(result,indent=2)); return result
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('project_id'); a=ap.parse_args(); print(json.dumps(run(a.project_id),indent=2))
