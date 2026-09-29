"""Apply explicit, reversible review decisions to the timeline."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from src.longform_ingest import PROJECTS
VALID={'approve','reject','hold','override'}
def apply(project_id,decision_id,status,note='',asset_id=None,projects=PROJECTS):
 if status not in VALID: raise ValueError(status)
 p=projects/project_id; path=p/'analysis/timeline.json'; data=json.loads(path.read_text()); found=None
 for d in data['decisions']:
  if d['decision_id']==decision_id:
   d['status']=status; d['notes'].append(note) if note else None
   if asset_id is not None: d['selected_asset_id']=asset_id
   if status=='approve': d['locked']=True
   found=d; break
 if found is None: raise KeyError(decision_id)
 data['review']['current_revision']+=1; path.write_text(json.dumps(data,indent=2))
 return {'decision_id':decision_id,'status':status,'locked':found['locked'],'revision':data['review']['current_revision']}
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('project_id'); ap.add_argument('decision_id'); ap.add_argument('status',choices=sorted(VALID)); ap.add_argument('--note',default=''); ap.add_argument('--asset-id'); a=ap.parse_args(); print(json.dumps(apply(a.project_id,a.decision_id,a.status,a.note,a.asset_id),indent=2))
