import bpy, bmesh, math, struct, gzip, json
import os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
from mathutils import Matrix, Quaternion, Vector
D=OUT
arm=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.data.name=='Armature'][0]
P=arm.pose.bones
def upd(): bpy.context.view_layer.update()
for pb in P: pb.matrix_basis=Matrix.Identity(4)
upd()

# --- RigKit sample squat (character frame: +Y up, +Z forward, +X character's left)
def jq(rx=0,ry=0,rz=0):
    q=Quaternion((1,0,0),math.radians(rx))
    if ry: q=q@Quaternion((0,1,0),math.radians(ry))
    if rz: q=q@Quaternion((0,0,1),math.radians(rz))
    return q
bar={'leftArm':jq(rz=-75),'leftForeArm':jq(rz=160),'rightArm':jq(rz=75),'rightForeArm':jq(rz=-160)}
def kf(d): r=dict(bar); r.update(d); return r
KF=[(0,kf({})),
    (0.45,kf({'hips':jq(rx=10),'spine':jq(rx=8),'leftUpLeg':jq(rx=-60),'rightUpLeg':jq(rx=-60),'leftLeg':jq(rx=62),'rightLeg':jq(rx=62),'leftFoot':jq(rx=-12),'rightFoot':jq(rx=-12)})),
    (1,kf({'hips':jq(rx=20),'spine':jq(rx=15),'leftUpLeg':jq(rx=-120),'rightUpLeg':jq(rx=-120),'leftLeg':jq(rx=125),'rightLeg':jq(rx=125),'leftFoot':jq(rx=-25),'rightFoot':jq(rx=-25)}))]
PARENT={'hips':None,'spine':'hips','spine1':'spine','spine2':'spine1','neck':'spine2',
 'leftShoulder':'spine2','leftArm':'leftShoulder','leftForeArm':'leftArm','leftHand':'leftForeArm',
 'rightShoulder':'spine2','rightArm':'rightShoulder','rightForeArm':'rightArm','rightHand':'rightForeArm',
 'leftUpLeg':'hips','leftLeg':'leftUpLeg','leftFoot':'leftLeg','rightUpLeg':'hips','rightLeg':'rightUpLeg','rightFoot':'rightLeg'}
ZB={'hips':'Hips','spine':'LowerBack','spine1':'Spine','spine2':'Spine1','neck':'Neck1',
 'leftShoulder':'LeftShoulder','leftArm':'LeftArm','leftForeArm':'LeftForeArm','leftHand':'LeftHand',
 'rightShoulder':'RightShoulder','rightArm':'RightArm','rightForeArm':'RightForeArm','rightHand':'RightHand',
 'leftUpLeg':'LeftUpLeg','leftLeg':'LeftLeg','leftFoot':'LeftFoot','rightUpLeg':'RightUpLeg','rightLeg':'RightLeg','rightFoot':'RightFoot'}
ORDER=['hips','spine','spine1','spine2','neck','leftShoulder','rightShoulder','leftArm','rightArm','leftForeArm','rightForeArm','leftHand','rightHand','leftUpLeg','rightUpLeg','leftLeg','rightLeg','leftFoot','rightFoot']
ARMS={'leftArm':Vector((1,0,0)),'leftForeArm':Vector((1,0,0)),'rightArm':Vector((-1,0,0)),'rightForeArm':Vector((-1,0,0))}
# character -> Blender basis: x->x, y(up)->z, z(fwd)->-y
M=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
def to_bl(q): return (M@q.to_matrix()@M.transposed())
REST={k:arm.matrix_world@P[v].matrix for k,v in ZB.items()}

def pose(deltas):
    for pb in P: pb.matrix_basis=Matrix.Identity(4)
    upd()
    A={}
    for j in ORDER:
        par=PARENT[j]
        A[j]=(A[par] if par else Quaternion())@deltas.get(j,Quaternion())
        if j not in deltas and not (par and A[par]!=Quaternion()): continue
        pb=P[ZB[j]]; cur=arm.matrix_world@pb.matrix
        if j in ('leftForeArm','rightForeArm'):
            # Elbow is a hinge about the bone's local Z (rig limit -140..18 deg).
            tgt=(M@(A[j]@ARMS[j])).normalized()
            ax=(cur.to_3x3()@Vector((0,0,1))).normalized()
            d0=(cur.to_3x3()@Vector((0,1,0))).normalized()
            a=(d0-ax*d0.dot(ax)).normalized(); b=(tgt-ax*tgt.dot(ax)).normalized()
            th=math.atan2(ax.dot(a.cross(b)), a.dot(b))
            lim=[c for c in pb.constraints if c.type=='LIMIT_ROTATION' and not c.mute][0]
            th=max(lim.min_z, min(lim.max_z, th))
            pb.rotation_mode='YZX'; pb.rotation_euler=(0,0,th); upd(); continue
        if j in ARMS:
            tgt=(M@(A[j]@ARMS[j])).normalized()
            curdir=(cur.to_3x3()@Vector((0,1,0))).normalized()
            R=curdir.rotation_difference(tgt).to_matrix()
        else:
            R=to_bl(A[j])@ (REST[j].to_3x3()@cur.to_3x3().inverted())
        head=cur.translation.copy()
        new=(R@cur.to_3x3()).to_4x4(); new.translation=head
        pb.matrix=arm.matrix_world.inverted()@new
        upd()

# meshes rigidly attached to bones
meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==arm and o.parent_type=='BONE' and len(o.data.polygons)>0]
def feet():
    return (arm.matrix_world@P['LeftFoot'].head + arm.matrix_world@P['RightFoot'].head)/2
def snapshot():
    upd(); return {o.name:o.matrix_world.copy() for o in meshes}, feet(), [arm.matrix_world@P[n].head for n in ('LeftHand','RightHand')]
pose({}); rest,restFeet,_=snapshot()

# geometry at 25%, in rest world coords
C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))  # Blender -> three.js
dg=bpy.context.evaluated_depsgraph_get()
pos=[];idx=[];ranges=[]
for o in meshes:
    md=o.modifiers.new('dec','DECIMATE'); md.ratio=0.25
upd(); dg=bpy.context.evaluated_depsgraph_get()
for o in meshes:
    ev=o.evaluated_get(dg); me=ev.to_mesh()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm,faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    W=C@rest[o.name]; base=len(pos)//3; i0=len(idx)
    for v in me.vertices:
        p=W@v.co; pos+= [p.x,p.y,p.z]
    for f in me.polygons: idx+= [base+i for i in f.vertices]
    ranges.append([o.name,i0,len(idx)-i0]); ev.to_mesh_clear()
for o in meshes: o.modifiers.remove(o.modifiers['dec'])

# bake frames
N=25; frames=[]; bar=[]
def interp(t):
    for (t0,a),(t1,b) in zip(KF,KF[1:]):
        if t<=t1:
            u=(t-t0)/(t1-t0); keys=set(a)|set(b)
            return {k:a.get(k,Quaternion()).slerp(b.get(k,Quaternion()),u) for k in keys}
    return KF[-1][1]
for f in range(N):
    t=f/(N-1); pose(interp(t)); mats,ft,hands=snapshot()
    off=Matrix.Translation(restFeet-ft)
    row=[]
    for o in meshes:
        Dm=C@(off@mats[o.name]@rest[o.name].inverted())@C.inverted()
        l,q,s=Dm.decompose(); row+= [l.x,l.y,l.z,q.x,q.y,q.z,q.w]
    frames.append(row)
    hb=[C@(off@h) for h in hands]; bar.append([c for h in hb for c in h])
# report knee angle at bottom for sanity
print('KNEE_LIMITS',[ (c.type, round(math.degrees(c.min_x)), round(math.degrees(c.max_x))) for c in P['LeftLeg'].constraints if c.type=='LIMIT_ROTATION'])
lo=[min(pos[i::3]) for i in range(3)]; hi=[max(pos[i::3]) for i in range(3)]
nv=len(pos)//3
q=[int(round((pos[i]-lo[i%3])/(hi[i%3]-lo[i%3])*65535)) for i in range(len(pos))]
buf=struct.pack(f'<{len(q)}H',*q)+struct.pack(f'<{len(idx)}I',*idx)
anim=struct.pack(f'<{N*len(meshes)*7}f',*[x for r in frames for x in r])
open(D+'out_squat_geo.bin','wb').write(gzip.compress(buf,9))
open(D+'out_squat_anim.bin','wb').write(gzip.compress(anim,9))
json.dump(dict(verts=nv,tris=len(idx)//3,lo=lo,hi=hi,ranges=ranges,frames=N,bar=bar),open(D+'out_squat.json','w'))
print('SQUAT',len(meshes),'meshes',nv,'verts',len(idx)//3,'tris')
