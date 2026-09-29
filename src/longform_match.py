"""Linear-time token matching for discovery candidates and spoken moments."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from collections import defaultdict
from src.longform_ingest import PROJECTS
STOP={'the','a','an','and','or','of','to','we','i','it','is','are','was','for','in','on','that','this','so','what'}
def toks(s): return {x for x in re.findall(r'[a-z0-9]+',s.lower()) if x not in STOP and len(x)>2}
def match(project_id,projects=PROJECTS):
 p=projects/project_id; moments=json.load(open(p/'analysis/moment_map.json'))['moments']; q=json.load(open(p/'analysis/discovery_queue.json')); out=[]
 inv=defaultdict(set)
 for c in q['candidates']:
  for t in toks(c.get('title','')+' '+c.get('summary','')): inv[t].add(c.get('candidate_id'))
 byid={c.get('candidate_id'):c for c in q['candidates']}
 for m in moments:
  scores=defaultdict(int)
  for t in toks(m['text']):
   for cid in inv.get(t,()): scores[cid]+=1
  ranked=sorted(scores,key=lambda cid:(-scores[cid],cid))[:10]
  out.append({'moment_id':m['moment_id'],'candidates':[{'candidate_id':cid,'score':scores[cid],'review_required':True} for cid in ranked]})
 dest=p/'analysis/matches.json'; dest.write_text(json.dumps({'schema':'crimson.longform.matches.v1','matches':out},indent=2)); return {'matches':str(dest),'moments':len(out)}
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('project_id'); a=ap.parse_args(); print(json.dumps(match(a.project_id),indent=2))
