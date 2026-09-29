"""Single compact status report for a long-form project."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from src.longform_health import check
from src.longform_preflight import run
from src.longform_ingest import PROJECTS
def status(project_id,projects=PROJECTS):
 p=projects/project_id; timeline=json.load(open(p/'analysis/timeline.json')); decisions=timeline['decisions']
 reviewed=sum(d['status'] in ('approve','reject','hold','override') for d in decisions)
 return {'project_id':project_id,'health':check(project_id,projects),'review':{'total':len(decisions),'reviewed':reviewed,'approved':sum(d['status']=='approve' for d in decisions)},'preflight':run(project_id,projects)}
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('project_id'); a=ap.parse_args(); print(json.dumps(status(a.project_id),indent=2))
