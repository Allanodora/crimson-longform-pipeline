"""Create a review-first discovery queue for RSS/API/search candidates."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.longform_ingest import PROJECTS

DEFAULT_CHANNELS=[
    {'channel_id':'rss_news','kind':'rss','enabled':True,'topics':['football','press conference','match report']},
    {'channel_id':'official_media','kind':'api_or_feed','enabled':True,'topics':['club','league','player']},
    {'channel_id':'saved_searches','kind':'search_queue','enabled':True,'topics':['viral comment','meme','stat','quote']},
    {'channel_id':'manual_capture','kind':'drop_folder','enabled':True,'topics':['user supplied asset']},
]
def create(project_id:str,projects:Path=PROJECTS):
    project=projects/project_id
    out=project/'analysis/discovery_queue.json'
    data={'schema':'crimson.longform.discovery.v1','channels':DEFAULT_CHANNELS,'candidates':[],
          'rules':{'review_required':True,'auto_insert':False,'store_source_metadata':True,'respect_access_controls':True}}
    out.write_text(json.dumps(data,indent=2))
    return {'discovery_queue':str(out),'channels':len(DEFAULT_CHANNELS),'candidates':0}
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('project_id'); ap.add_argument('--projects',type=Path,default=PROJECTS)
    a=ap.parse_args(); print(json.dumps(create(a.project_id,a.projects),indent=2))
