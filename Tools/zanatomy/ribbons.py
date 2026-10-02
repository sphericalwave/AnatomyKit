import bpy, json, gzip, re, os
import numpy as np
from mathutils import Matrix
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.environ.get('RES') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
arm=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.data.name=='Armature'][0]
for pb in arm.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==arm and o.parent_type=='BONE' and len(o.data.polygons)>0]
bones=sorted({o.parent_bone for o in meshes})
assert bones==json.load(open(OUT+'rig.json'))['bones'], 'bone order must match rig.json'
P=arm.pose.bones
seg=np.array([[*(C@(arm.matrix_world@P[b].head)), *(C@(arm.matrix_world@P[b].tail))] for b in bones])
A_=seg[:,:3]; AB=seg[:,3:]-A_; AB2=np.maximum((AB*AB).sum(1),1e-12)
ARMB=re.compile(r'Radius|Ulna|carpal|Metacarpal|of hand|Hand|Thumb|FingerBase|Offset')
LEGB=re.compile(r'UpLeg|LeftLeg$|RightLeg$|Knee|Tibia|Patella|Foot|Calcaneus|Navicular|Cuboid|Cuneiform|Metatarsal|of foot|ToeBase|Fibula|Femur|Talus')
armBone=np.array([bool(ARMB.search(b)) for b in bones]); legBone=np.array([bool(LEGB.search(b)) for b in bones])
def weights(pts, isArm):
    p=pts[:,None,:]; t=np.clip(((p-A_)*AB).sum(2)/AB2,0,1); d=np.linalg.norm(p-(A_+t[...,None]*AB),axis=2)
    d=np.where(isArm[:,None]&legBone[None,:],np.inf,d); d=np.where(~isArm[:,None]&armBone[None,:],np.inf,d)
    nn=np.argsort(d,1)[:,:4]; dn=np.take_along_axis(d,nn,1); w=1/(dn+0.01)**4; w/=w.sum(1,keepdims=True)
    return nn, w
# line mesh vertices
lm=json.load(open(OUT+'out_lines.json')); raw=gzip.decompress(open(OUT+'out_lines.bin','rb').read())
nv=lm['verts']; q=np.frombuffer(raw,dtype='<u2',count=nv*3).reshape(-1,3).astype(float)
pos=np.array(lm['lo'])+q/65535*(np.array(lm['hi'])-np.array(lm['lo']))
idx=np.frombuffer(raw,dtype='<u4',offset=nv*6)
vr={}
for name,start,count in lm['ranges']:
    v=idx[start:start+count]; vr[name]=(int(v.min()),int(v.max())+1)
meshmap=json.load(open(RES+'meshes-zanatomy.json'))['meshes']
region={m['id']:m['region'] for m in json.load(open(RES+'muscles.json'))}; region.update({t['id']:t['region'] for t in json.load(open(RES+'tissues.json'))})
lines=json.load(open(RES+'lines.json'))
def verts(ids, side):
    out=[]
    for cid in ids:
        for b in meshmap.get(cid,[]):
            n=f'{b}.{side[0]}'
            n=n if n in vr else (b if b in vr else None)
            if n: out.append(pos[vr[n][0]:vr[n][1]])
    return np.concatenate(out) if out else np.zeros((0,3))
def sub(v,n=2500):
    return v if len(v)<=n else v[np.linspace(0,len(v)-1,n).astype(int)]
def ends(v):
    c=v.mean(0); u,s,vt=np.linalg.svd(v-c,full_matrices=False); ax=vt[0]; pr=(v-c)@ax
    k=max(3,len(v)//50); lo=v[np.argsort(pr)[:k]].mean(0); hi=v[np.argsort(pr)[-k:]].mean(0); return lo,hi
def contact(a,b,prev):
    """Where track a hands over to track b: among points where the two meshes
    touch, the ones farthest along from the previous station (adjacent muscles
    often touch along their whole length; the station is at the far end)."""
    a,b=sub(a),sub(b); d=np.linalg.norm(a[:,None,:]-b[None,:,:],axis=2)
    for r in (0.015,0.03,0.05):
        ma=d.min(1)<r; mb=d.min(0)<r
        if ma.sum()+mb.sum()>=4:
            c=np.concatenate([a[ma],b[mb]])
            if prev is None: return c.mean(0)
            far=np.linalg.norm(c-prev,axis=1); return c[far>=np.quantile(far,0.75)].mean(0)
    i,j=np.unravel_index(d.argmin(),d.shape); return (a[i]+b[j])/2
# --- landmark positions on the rig's bone meshes (rest pose, three.js coords)
RULES=json.load(open(os.environ.get('LANDMARK_RULES') or os.path.join(os.path.dirname(os.path.abspath(__file__)),'landmark_rules.json')))
bone_vs={}
for o in meshes:
    me=o.data; W=C@o.matrix_world
    bone_vs[o.name]=np.array([tuple(W@v.co) for v in me.vertices])
def landmark(lid, side):
    r=RULES[lid]; sgn=1.0 if side=='left' else -1.0
    if 'lineMesh' in r:
        n=r['lineMesh']; v=pos[vr[n][0]:vr[n][1]]
    else:
        rx=re.compile(r['meshes']); v=np.concatenate([bv for n,bv in bone_vs.items() if rx.search(n)])
    if not r.get('midline'):
        v=v[v[:,0]*sgn>0.005]
    if 'within' in r:
        y0,y1=v[:,1].min(),v[:,1].max(); a,b=r['within']; v=v[(v[:,1]>=y0+a*(y1-y0))&(v[:,1]<=y0+b*(y1-y0))]
    if 'dir' in r:
        d=np.array(r['dir'],float); d[0]*=sgn; d/=np.linalg.norm(d)
        pr=v@d; k=max(3,int(len(v)*r.get('pct',0.03))); pt=v[np.argsort(pr)[-k:]].mean(0)
    else:
        pt=v.mean(0)
    if r.get('midline'): pt=pt.copy(); pt[0]=0.0
    return pt

def path_points(steps, start):
    """Stations sit on their landmark's bone; points between follow the centre
    of the track's muscles along the station-to-station direction."""
    side=start; pts=[]; kinds=[]; arm=[]; prev=None
    seq=[]
    for st in steps:
        if 'at' in st:
            if st.get('crosses') and side!='both': side='right' if side=='left' else 'left'
            seq.append(('s', landmark(st['at'], side), bool(st.get('crosses'))))
        else:
            seq.append(('t', st['via'], side))
    for k,item in enumerate(seq):
        if item[0]=='s':
            pts.append(item[1]); kinds.append('x' if item[2] else 's'); arm.append(arm[-1] if arm else False)
        else:
            ids,sd=item[1],item[2]; isArm=any(region.get(c) in ('arm','hand') for c in ids)
            arm[-1]=arm[-1] or isArm
            A=seq[k-1][1]; B=seq[k+1][1]; v=verts(ids,sd)
            if len(v):
                ab=B-A; L2=max(ab@ab,1e-9); tt=((v-A)@ab)/L2
                for c in (0.25,0.5,0.75):
                    m=np.abs(tt-c)<0.09
                    if m.sum()>=3: pts.append(v[m].mean(0)); kinds.append('t'); arm.append(isArm)
    pts=np.array(pts); nn,w=weights(pts,np.array(arm))
    wq=np.round(w*255).astype(int); wq[:,0]+=255-wq.sum(1)
    return {"p":np.round(pts,4).flatten().tolist(),"k":''.join(kinds),"b":nn.flatten().tolist(),"w":wq.flatten().tolist()}
out={}
for l in lines:
    out[l['id']]={}
    for s_ in ('left','right'):
        res=[]
        for p in l['paths']:
            res.append(path_points(p['steps'],s_))
        out[l['id']][s_]=res
json.dump(out,open(OUT+'ribbons.json','w'))
print('RIBBONS',sum(len(pp['k']) for v in out.values() for s in v.values() for pp in s),'points')
