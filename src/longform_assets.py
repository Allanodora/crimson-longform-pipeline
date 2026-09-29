"""Index local reference assets without making editorial selections."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from src.longform_ingest import PROJECTS

EXTS={'.mp4','.mov','.mkv','.webm','.mp3','.wav','.m4a','.png','.jpg','.jpeg','.webp','.gif','.pdf','.html'}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def index(project_id:str, asset_root:Path, projects:Path=PROJECTS):
    project=projects/project_id; records=[]
    if asset_root.exists():
        for p in sorted(asset_root.rglob('*')):
            if p.is_file() and p.suffix.lower() in EXTS:
                records.append({'asset_id':'asset_'+sha(p)[:16],'path':str(p),'filename':p.name,'kind':p.suffix.lower().lstrip('.'),'sha256':sha(p),'selected':False,'locked':False,'rights_status':'LOCAL_REFERENCE_REVIEW'})
    out=project/'analysis/assets.json'; out.write_text(json.dumps({'schema':'crimson.longform.assets.v1','root':str(asset_root),'assets':records},indent=2))
    return {'assets':str(out),'asset_count':len(records)}
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('project_id'); ap.add_argument('asset_root',type=Path); ap.add_argument('--projects',type=Path,default=PROJECTS)
    a=ap.parse_args(); print(json.dumps(index(a.project_id,a.asset_root,a.projects),indent=2))
