import bpy, bmesh, math, struct, gzip, json
import os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
import numpy as np
from mathutils import Matrix, Quaternion, Vector
D=OUT
arm=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.data.name=='Armature'][0]
P=arm.pose.bones
def upd(): bpy.context.view_layer.update()
for pb in P: pb.matrix_basis=Matrix.Identity(4)
upd()
def jq(rx=0,ry=0,rz=0):
    q=Quaternion((1,0,0),math.radians(rx))
    if ry: q=q@Quaternion((0,1,0),math.radians(ry))
    if rz: q=q@Quaternion((0,0,1),math.radians(rz))
    return q
fwd={'leftArm':jq(ry=-90),'rightArm':jq(ry=90)}
def kf(d): r=dict(fwd); r.update(d); return r
KF=[(0,kf({})),
    (0.45,kf({'hips':jq(rx=10),'spine':jq(rx=8),'leftUpLeg':jq(rx=-60),'rightUpLeg':jq(rx=-60),'leftLeg':jq(rx=62),'rightLeg':jq(rx=62),'leftFoot':jq(rx=-12),'rightFoot':jq(rx=-12)})),
    (1,kf({'hips':jq(rx=20),'spine':jq(rx=15),'leftUpLeg':jq(rx=-120),'rightUpLeg':jq(rx=-120),'leftLeg':jq(rx=125),'rightLeg':jq(rx=125),'leftFoot':jq(rx=-25),'rightFoot':jq(rx=-25)}))]
PARENT={'hips':None,'spine':'hips','spine1':'spine','spine2':'spine1','neck':'spine2','leftShoulder':'spine2','leftArm':'leftShoulder','leftForeArm':'leftArm','leftHand':'leftForeArm','rightShoulder':'spine2','rightArm':'rightShoulder','rightForeArm':'rightArm','rightHand':'rightForeArm','leftUpLeg':'hips','leftLeg':'leftUpLeg','leftFoot':'leftLeg','rightUpLeg':'hips','rightLeg':'rightUpLeg','rightFoot':'rightLeg'}
ZB={'hips':'Hips','spine':'LowerBack','spine1':'Spine','spine2':'Spine1','neck':'Neck1','leftShoulder':'LeftShoulder','leftArm':'LeftArm','leftForeArm':'LeftForeArm','leftHand':'LeftHand','rightShoulder':'RightShoulder','rightArm':'RightArm','rightForeArm':'RightForeArm','rightHand':'RightHand','leftUpLeg':'LeftUpLeg','leftLeg':'LeftLeg','leftFoot':'LeftFoot','rightUpLeg':'RightUpLeg','rightLeg':'RightLeg','rightFoot':'RightFoot'}
ORDER=['hips','spine','spine1','spine2','neck','leftShoulder','rightShoulder','leftArm','rightArm','leftForeArm','rightForeArm','leftHand','rightHand','leftUpLeg','rightUpLeg','leftLeg','rightLeg','leftFoot','rightFoot']
ARMS={'leftArm':Vector((1,0,0)),'leftForeArm':Vector((1,0,0)),'rightArm':Vector((-1,0,0)),'rightForeArm':Vector((-1,0,0))}
M=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
def to_bl(q): return M@q.to_matrix()@M.transposed()
REST={k:arm.matrix_world@P[v].matrix for k,v in ZB.items()}
def pose(deltas):
    for pb in P: pb.matrix_basis=Matrix.Identity(4)
    upd(); A={}
    for j in ORDER:
        par=PARENT[j]; A[j]=(A[par] if par else Quaternion())@deltas.get(j,Quaternion())
        if j not in deltas and not (par and A[par]!=Quaternion()): continue
        pb=P[ZB[j]]; cur=arm.matrix_world@pb.matrix
        if j in ('leftForeArm','rightForeArm'):
            tgt=(M@(A[j]@ARMS[j])).normalized(); ax=(cur.to_3x3()@Vector((0,0,1))).normalized(); d0=(cur.to_3x3()@Vector((0,1,0))).normalized()
            a=(d0-ax*d0.dot(ax)).normalized(); b=(tgt-ax*tgt.dot(ax)).normalized(); th=math.atan2(ax.dot(a.cross(b)),a.dot(b))
            lim=[c for c in pb.constraints if c.type=='LIMIT_ROTATION' and not c.mute][0]; th=max(lim.min_z,min(lim.max_z,th))
            pb.rotation_mode='YZX'; pb.rotation_euler=(0,0,th); upd(); continue
        if j in ARMS:
            tgt=(M@(A[j]@ARMS[j])).normalized(); curdir=(cur.to_3x3()@Vector((0,1,0))).normalized(); R=curdir.rotation_difference(tgt).to_matrix()
        else:
            R=to_bl(A[j])@(REST[j].to_3x3()@cur.to_3x3().inverted())
        new=(R@cur.to_3x3()).to_4x4(); new.translation=cur.translation.copy(); pb.matrix=arm.matrix_world.inverted()@new; upd()

C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==arm and o.parent_type=='BONE' and len(o.data.polygons)>0]
bones=sorted({o.parent_bone for o in meshes}); bidx={b:i for i,b in enumerate(bones)}
def bone_world(n): return arm.matrix_world@P[n].matrix
def feet(): return (arm.matrix_world@P['LeftFoot'].head+arm.matrix_world@P['RightFoot'].head)/2
pose({}); restB={b:bone_world(b) for b in bones}; restFeet=feet()
# rest bone segments in three coords
seg=np.array([[*(C@(arm.matrix_world@P[b].head)), *(C@(arm.matrix_world@P[b].tail))] for b in bones],dtype=np.float64)
# skeleton geometry (25%), per-vertex bone
for o in meshes:
    md=o.modifiers.new('dec','DECIMATE'); md.ratio=0.25
upd(); dg=bpy.context.evaluated_depsgraph_get()
spos=[]; sidx=[]; sbone=[]
for o in meshes:
    ev=o.evaluated_get(dg); me=ev.to_mesh(); bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm,faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    W=C@o.matrix_world; base=len(spos)//3
    for v in me.vertices: p=W@v.co; spos+=[p.x,p.y,p.z]; sbone.append(bidx[o.parent_bone])
    for f in me.polygons: sidx+=[base+i for i in f.vertices]
    ev.to_mesh_clear()
for o in meshes: o.modifiers.remove(o.modifiers['dec'])
# muscle weights from the Z-Anatomy line meshes
lm=json.load(open(D+'out_lines.json')); raw=gzip.decompress(open(D+'out_lines.bin','rb').read())
nv=lm['verts']; q=np.frombuffer(raw,dtype='<u2',count=nv*3).reshape(-1,3).astype(np.float64)
lo=np.array(lm['lo']); hi=np.array(lm['hi']); mpos=lo+q/65535*(hi-lo)
a=seg[:,:3]; ab=seg[:,3:]-a; ab2=np.maximum((ab*ab).sum(1),1e-12)
# Keep weights anatomical: the hands hang beside the thighs at rest, so leg and
# trunk structures must not follow forearm/hand bones, and arm structures must
# not follow leg bones.
import re
ARMB=re.compile(r'Radius|Ulna|carpal|Metacarpal|of hand|Hand|Thumb|FingerBase|Offset')
LEGB=re.compile(r'UpLeg|LeftLeg$|RightLeg$|Knee|Tibia|Patella|Foot|Calcaneus|Navicular|Cuboid|Cuneiform|Metatarsal|of foot|ToeBase|Fibula|Femur|Talus')
armBone=np.array([bool(ARMB.search(b)) for b in bones]); legBone=np.array([bool(LEGB.search(b)) for b in bones])
R=RES
region={m['id']:m['region'] for m in json.load(open(R+'muscles.json'))}
region.update({t['id']:t['region'] for t in json.load(open(R+'tissues.json'))})
base2id={b:cid for cid,bs in json.load(open(R+'meshes-zanatomy.json'))['meshes'].items() for b in bs}
idxAll=np.frombuffer(raw,dtype='<u4',offset=nv*6)
isArm=np.zeros(nv,bool)
for name,start,count in lm['ranges']:
    base=re.sub(r'\.(l|r)$','',name); reg=region.get(base2id.get(base,''),'trunk')
    vs=idxAll[start:start+count]; isArm[vs.min():vs.max()+1]=reg in ('arm','hand')
K=4; widx=np.zeros((nv,K),np.uint8); wval=np.zeros((nv,K),np.uint8)
for s in range(0,nv,20000):
    p=mpos[s:s+20000,None,:]; t=np.clip(((p-a)*ab).sum(2)/ab2,0,1)
    d=np.linalg.norm(p-(a+t[...,None]*ab),axis=2)
    arm_v=isArm[s:s+20000,None]
    d=np.where(arm_v & legBone[None,:], np.inf, d); d=np.where(~arm_v & armBone[None,:], np.inf, d)
    nn=np.argsort(d,axis=1)[:,:K]; dn=np.take_along_axis(d,nn,1)
    w=1/(dn+0.01)**4; w/=w.sum(1,keepdims=True)
    wq=np.round(w*255).astype(int); wq[:,0]+=255-wq.sum(1)
    widx[s:s+20000]=nn; wval[s:s+20000]=np.clip(wq,0,255)
# per-frame bone deltas (three coords, feet planted)
N=25; frames=[]
def interp(t):
    for (t0,a_),(t1,b_) in zip(KF,KF[1:]):
        if t<=t1:
            u=(t-t0)/(t1-t0); keys=set(a_)|set(b_)
            return {k:a_.get(k,Quaternion()).slerp(b_.get(k,Quaternion()),u) for k in keys}
    return KF[-1][1]
for f in range(N):
    pose(interp(f/(N-1))); off=Matrix.Translation(restFeet-feet()); row=[]
    for b in bones:
        Dm=C@(off@bone_world(b)@restB[b].inverted())@C.inverted(); l,qq,_=Dm.decompose(); row+=[l.x,l.y,l.z,qq.x,qq.y,qq.z,qq.w]
    frames.append(row)
slo=[min(spos[i::3]) for i in range(3)]; shi=[max(spos[i::3]) for i in range(3)]
sq=[int(round((spos[i]-slo[i%3])/(shi[i%3]-slo[i%3])*65535)) for i in range(len(spos))]
open(D+'rig_skel.bin','wb').write(gzip.compress(struct.pack(f'<{len(sq)}H',*sq)+struct.pack(f'<{len(sidx)}I',*sidx)+bytes(sbone),9))
open(D+'rig_weights.bin','wb').write(gzip.compress(widx.tobytes()+wval.tobytes(),9))
open(D+'rig_frames.bin','wb').write(gzip.compress(struct.pack(f'<{len(frames)*len(bones)*7}f',*[x for r in frames for x in r]),9))
json.dump(dict(bones=bones,frames=N,skel=dict(verts=len(spos)//3,tris=len(sidx)//3,lo=slo,hi=shi),muscleVerts=nv,K=K),open(D+'rig.json','w'))
print('RIG bones',len(bones),'skelverts',len(spos)//3,'muscleverts',nv)
