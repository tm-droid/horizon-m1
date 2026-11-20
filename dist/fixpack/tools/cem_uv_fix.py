"""Rewrite a jem's custom face UVs so Horizon (f42ef42/fdc87ae) bakes them like EMF:
EMF puts uvWest on the max-x face and uvEast on min-x (Horizon: the reverse), and
gives uvUp/uvDown a 180-degree turned rect relative to Horizon's corner order."""
import json,sys
AL={'uvLeft':'uvWest','uvRight':'uvEast'}
n=0
def fix(b):
    global n
    for a,k in AL.items():
        if a in b and k not in b: b[k]=b.pop(a)
    w,e=b.pop('uvWest',None),b.pop('uvEast',None)
    if w is not None: b['uvEast']=w; n+=1
    if e is not None: b['uvWest']=e; n+=1
    for k in ('uvUp','uvDown'):
        if k in b:
            u1,v1,u2,v2=b[k]; b[k]=[u2,v2,u1,v1]; n+=1
def walk(m):
    for b in m.get('boxes',[]):
        if 'textureOffset' not in b: fix(b)
    for s in m.get('submodels',[]): walk(s)
    if 'submodel' in m: walk(m['submodel'])
src,dst=sys.argv[1:3]
j=json.load(open(src))
for m in j.get('models',[]): walk(m)
json.dump(j,open(dst,'w'),indent=1)
print(dst.split('/')[-1],'faces rewritten:',n)
