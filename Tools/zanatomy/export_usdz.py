"""Rigged USDZ layers for the in-app viewer.

  ZANATOMY_BLEND=Z-Anatomy/Startup.blend OUT=out \
    blender -b Z-Biomechanics/Startup.blend --python export_usdz.py

Writes $OUT/usdz/:
  skeleton.usdz                 bones (+ teeth, cartilage), shipped in the app
  fascia.usdz                   fascia sheets, shipped in the app
  muscles-<chunk>.usdz          muscles, delivered as On-Demand Resources
  manifest.json                 prim name -> catalog ID, side, layer, chunk

Every file carries the full Z-Biomechanics skeleton and the same baked squat
animation (rig constraints baked to keyframes), so RealityKit can play each
layer and they stay in step. Bones are rigidly skinned to their rig bone;
muscles and fascia follow their four nearest bones (as in rig_lines.py).
Geometry is decimated to 25%. Y-up, metres, body facing +Z.
"""
import bpy, bmesh, json, math, os, re
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(HERE, '../../Sources/AnatomyKit/Resources/')
ZA = os.environ['ZANATOMY_BLEND']
DST = OUT + 'usdz/'; os.makedirs(DST, exist_ok=True)
RATIO = 0.25

arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.name == 'Armature'][0]
P = arm.pose.bones
def upd(): bpy.context.view_layer.update()
for pb in P: pb.matrix_basis = Matrix.Identity(4)
upd()

# ---------------------------------------------------------------- catalog names
bones_z = json.load(open(RES + 'bones-zanatomy.json'))['bones']
mesh_to_bone = {}
for bid, sides in bones_z.items():
    for side, part in sides.items():
        for m in part['meshes']:
            mesh_to_bone[m] = (bid, {'left': 'l', 'right': 'r', 'midline': ''}[side])
meshmap = json.load(open(RES + 'meshes-zanatomy.json'))['meshes']
base_to_struct = {b: cid for cid, bs in meshmap.items() for b in bs}

def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def side_of(name, x):
    m = re.search(r'\.(l|r)$', name)
    if m: return m.group(1)
    return '' if abs(x) < 0.01 else ('l' if x > 0 else 'r')

used_names = set()
def prim_name(cid, side, raw):
    """`<catalog id>__<l|r>`; structures split over several meshes get a part
    suffix; meshes outside the catalog are `za_<slug of Z-Anatomy name>`."""
    base = f'{cid}__{side}' if side else cid
    if base in used_names:
        base = f"{base}__{slug(re.sub(r'.(l|r|001)$', '', raw))}"
    n, k = base, 2
    while n in used_names: n = f'{base}_{k}'; k += 1
    used_names.add(n)
    return n

# ---------------------------------------------------------------- geometry helpers
def bake_mesh(src, name):
    """A decimated, modifier-applied copy of `src` in world space, unparented."""
    md = src.modifiers.new('dec', 'DECIMATE'); md.ratio = RATIO
    upd(); dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    # RealityKit merges every skinned mesh under the SkelRoot into one model and
    # keys each part by its mesh prim's name, so the mesh data carries the
    # catalog name too.
    me.name = name
    src.modifiers.remove(md)
    me.transform(src.matrix_world)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def skin_rigid(ob, bone):
    vg = ob.vertex_groups.new(name=bone); vg.add(range(len(ob.data.vertices)), 1.0, 'REPLACE')
    ob.modifiers.new('Armature', 'ARMATURE').object = arm

deform = sorted({o.parent_bone for o in bpy.data.objects
                 if o.type == 'MESH' and o.parent == arm and o.parent_type == 'BONE'})
seg = np.array([[*(arm.matrix_world @ P[b].head), *(arm.matrix_world @ P[b].tail)] for b in deform])
A_ = seg[:, :3]; AB = seg[:, 3:] - A_; AB2 = np.maximum((AB * AB).sum(1), 1e-12)
ARMB = re.compile(r'Radius|Ulna|carpal|Metacarpal|of hand|Hand|Thumb|FingerBase|Offset')
LEGB = re.compile(r'UpLeg|LeftLeg$|RightLeg$|Knee|Tibia|Patella|Foot|Calcaneus|Navicular|Cuboid|Cuneiform|Metatarsal|of foot|ToeBase|Fibula|Femur|Talus')
armBone = np.array([bool(ARMB.search(b)) for b in deform]); legBone = np.array([bool(LEGB.search(b)) for b in deform])

def skin_nearest(ob, is_arm):
    """Four nearest bone segments, weights 1/(d + 1 cm)^4. Arm structures can't
    follow leg bones and vice versa (the hands hang beside the thighs at rest)."""
    v = np.array([tuple(x.co) for x in ob.data.vertices])  # world space already
    groups = {}
    for s in range(0, len(v), 20000):
        p = v[s:s + 20000, None, :]; t = np.clip(((p - A_) * AB).sum(2) / AB2, 0, 1)
        d = np.linalg.norm(p - (A_ + t[..., None] * AB), axis=2)
        d[:, legBone if is_arm else armBone] = np.inf
        nn = np.argsort(d, 1)[:, :4]; dn = np.take_along_axis(d, nn, 1)
        w = 1 / (dn + 0.01) ** 4; w /= w.sum(1, keepdims=True)
        for i in range(len(nn)):
            for k in range(4):
                groups.setdefault(int(nn[i, k]), []).append((s + i, float(w[i, k])))
    for b, items in groups.items():
        vg = ob.vertex_groups.new(name=deform[b])
        for i, w in items: vg.add([i], w, 'REPLACE')
    ob.modifiers.new('Armature', 'ARMATURE').object = arm

def chunk_of(x, y):
    """On-Demand Resource chunk by where the mesh sits in the rest pose."""
    if abs(x) > 0.19 and y > 0.55: return 'upper-limb'
    if y < 0.9: return 'lower-limb'
    if y > 1.42 and abs(x) < 0.16: return 'head-neck'
    return 'trunk'

manifest = []
layers = {'skeleton': [], 'fascia': []}

# ---------------------------------------------------------------- skeleton layer
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm
          and o.parent_type == 'BONE' and len(o.data.polygons) > 0]:
    cx = sum((o.matrix_world @ v.co).x for v in o.data.vertices) / len(o.data.vertices)
    if o.name in mesh_to_bone:
        cid, sd = mesh_to_bone[o.name]
    else:
        cid, sd = 'za_' + slug(re.sub(r'\.(l|r|001)$', '', o.name)), side_of(o.name, cx)
    n = prim_name(cid, sd, o.name)
    ob = bake_mesh(o, n); skin_rigid(ob, o.parent_bone); layers['skeleton'].append(ob)
    manifest.append({'prim': n, 'id': cid, 'kind': 'bone' if o.name in mesh_to_bone else 'other',
                     'side': sd, 'layer': 'skeleton', 'chunk': 'bundle', 'source': o.name})

# ---------------------------------------------------------------- muscles + fascia from Z-Anatomy
with bpy.data.libraries.load(ZA, link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c in ('Superficial muscles', 'Muscles', 'Fascia')]
loaded = {}
for coll in dst.collections:
    for o in coll.all_objects:
        if o.type == 'MESH' and len(o.data.polygons) > 0 and not any(m.type == 'WIREFRAME' for m in o.modifiers):
            loaded.setdefault(o.name, (o, coll.name))
for o, _ in loaded.values():
    if o.name not in bpy.context.scene.objects: bpy.context.scene.collection.objects.link(o)
upd()
for name, (o, cname) in sorted(loaded.items()):
    layer = 'fascia' if cname == 'Fascia' else 'muscle'
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    cx = sum(v.x for v in vs) / len(vs); cz = sum(v.z for v in vs) / len(vs)
    base = re.sub(r'\.(l|r)$', '', name)
    cid = base_to_struct.get(base) or 'za_' + slug(base)
    sd = side_of(name, cx); chunk = 'bundle' if layer == 'fascia' else chunk_of(cx, cz)
    n = prim_name(cid, sd, name)
    ob = bake_mesh(o, n); skin_nearest(ob, chunk == 'upper-limb')
    layers.setdefault('fascia' if layer == 'fascia' else f'muscles-{chunk}', []).append(ob)
    manifest.append({'prim': n, 'id': cid, 'kind': 'catalog' if cid in meshmap else 'other',
                     'side': sd, 'layer': layer, 'chunk': chunk, 'source': name})
for o, _ in loaded.values():
    bpy.data.objects.remove(o)

# ---------------------------------------------------------------- bake the squat
def jq(rx=0, ry=0, rz=0):
    q = Quaternion((1, 0, 0), math.radians(rx))
    if ry: q = q @ Quaternion((0, 1, 0), math.radians(ry))
    if rz: q = q @ Quaternion((0, 0, 1), math.radians(rz))
    return q
fwd = {'leftArm': jq(ry=-90), 'rightArm': jq(ry=90)}
def kf(d): r = dict(fwd); r.update(d); return r
KF = [(0, kf({})),
      (0.45, kf({'hips': jq(rx=10), 'spine': jq(rx=8), 'leftUpLeg': jq(rx=-60), 'rightUpLeg': jq(rx=-60), 'leftLeg': jq(rx=62), 'rightLeg': jq(rx=62), 'leftFoot': jq(rx=-12), 'rightFoot': jq(rx=-12)})),
      (1, kf({'hips': jq(rx=20), 'spine': jq(rx=15), 'leftUpLeg': jq(rx=-120), 'rightUpLeg': jq(rx=-120), 'leftLeg': jq(rx=125), 'rightLeg': jq(rx=125), 'leftFoot': jq(rx=-25), 'rightFoot': jq(rx=-25)}))]
PARENT = {'hips': None, 'spine': 'hips', 'spine1': 'spine', 'spine2': 'spine1', 'neck': 'spine2', 'leftShoulder': 'spine2', 'leftArm': 'leftShoulder', 'leftForeArm': 'leftArm', 'leftHand': 'leftForeArm', 'rightShoulder': 'spine2', 'rightArm': 'rightShoulder', 'rightForeArm': 'rightArm', 'rightHand': 'rightForeArm', 'leftUpLeg': 'hips', 'leftLeg': 'leftUpLeg', 'leftFoot': 'leftLeg', 'rightUpLeg': 'hips', 'rightLeg': 'rightUpLeg', 'rightFoot': 'rightLeg'}
ZB = {'hips': 'Hips', 'spine': 'LowerBack', 'spine1': 'Spine', 'spine2': 'Spine1', 'neck': 'Neck1', 'leftShoulder': 'LeftShoulder', 'leftArm': 'LeftArm', 'leftForeArm': 'LeftForeArm', 'leftHand': 'LeftHand', 'rightShoulder': 'RightShoulder', 'rightArm': 'RightArm', 'rightForeArm': 'RightForeArm', 'rightHand': 'RightHand', 'leftUpLeg': 'LeftUpLeg', 'leftLeg': 'LeftLeg', 'leftFoot': 'LeftFoot', 'rightUpLeg': 'RightUpLeg', 'rightLeg': 'RightLeg', 'rightFoot': 'RightFoot'}
ORDER = ['hips', 'spine', 'spine1', 'spine2', 'neck', 'leftShoulder', 'rightShoulder', 'leftArm', 'rightArm', 'leftForeArm', 'rightForeArm', 'leftHand', 'rightHand', 'leftUpLeg', 'rightUpLeg', 'leftLeg', 'rightLeg', 'leftFoot', 'rightFoot']
ARMS = {'leftArm': Vector((1, 0, 0)), 'leftForeArm': Vector((1, 0, 0)), 'rightArm': Vector((-1, 0, 0)), 'rightForeArm': Vector((-1, 0, 0))}
M = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
def to_bl(q): return M @ q.to_matrix() @ M.transposed()
REST = {k: arm.matrix_world @ P[v].matrix for k, v in ZB.items()}
def feet(): return (arm.matrix_world @ P['LeftFoot'].head + arm.matrix_world @ P['RightFoot'].head) / 2
REST_FEET = feet()

def pose(deltas):
    for pb in P: pb.matrix_basis = Matrix.Identity(4)
    upd(); A = {}
    for j in ORDER:
        par = PARENT[j]; A[j] = (A[par] if par else Quaternion()) @ deltas.get(j, Quaternion())
        if j not in deltas and not (par and A[par] != Quaternion()): continue
        pb = P[ZB[j]]; cur = arm.matrix_world @ pb.matrix
        if j in ('leftForeArm', 'rightForeArm'):
            tgt = (M @ (A[j] @ ARMS[j])).normalized(); ax = (cur.to_3x3() @ Vector((0, 0, 1))).normalized(); d0 = (cur.to_3x3() @ Vector((0, 1, 0))).normalized()
            a = (d0 - ax * d0.dot(ax)).normalized(); b = (tgt - ax * tgt.dot(ax)).normalized(); th = math.atan2(ax.dot(a.cross(b)), a.dot(b))
            lim = [c for c in pb.constraints if c.type == 'LIMIT_ROTATION' and not c.mute][0]; th = max(lim.min_z, min(lim.max_z, th))
            pb.rotation_mode = 'YZX'; pb.rotation_euler = (0, 0, th); upd(); continue
        if j in ARMS:
            tgt = (M @ (A[j] @ ARMS[j])).normalized(); curdir = (cur.to_3x3() @ Vector((0, 1, 0))).normalized(); R = curdir.rotation_difference(tgt).to_matrix()
        else:
            R = to_bl(A[j]) @ (REST[j].to_3x3() @ cur.to_3x3().inverted())
        new = (R @ cur.to_3x3()).to_4x4(); new.translation = cur.translation.copy(); pb.matrix = arm.matrix_world.inverted() @ new; upd()
    hips = P['Hips']; hips.matrix = Matrix.Translation(REST_FEET - feet()) @ hips.matrix; upd()

def interp(t):
    """Pose at descent fraction t. At t = 0 the arms hang at the sides, so the
    first frame (what RealityKit shows while paused) is the standing figure;
    they rise forward over the first third of the descent."""
    for (t0, a_), (t1, b_) in zip(KF, KF[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0); keys = set(a_) | set(b_)
            pose_ = {k: a_.get(k, Quaternion()).slerp(b_.get(k, Quaternion()), u) for k in keys}
            break
    else:
        pose_ = dict(KF[-1][1])
    raise_ = min(1.0, t / 0.33); raise_ = raise_ * raise_ * (3 - 2 * raise_)
    for k in fwd: pose_[k] = Quaternion().slerp(pose_[k], raise_)
    return pose_

# Down in 24 frames, back up in 24, at 24 fps: a 2 s rep. Key the visual
# (constraint-evaluated) matrix of every bone, then drop the constraints so the
# exported skeleton plays exactly what Blender evaluated.
scene = bpy.context.scene; scene.render.fps = 24; scene.frame_start = 0; scene.frame_end = 48
FRAMES = []
for f in range(49):
    t = f / 24 if f <= 24 else (48 - f) / 24
    pose(interp(t))
    FRAMES.append({pb.name: pb.matrix.copy() for pb in P})
for pb in P:
    for c in list(pb.constraints): pb.constraints.remove(c)
if arm.animation_data:
    for d in list(arm.animation_data.drivers): arm.animation_data.drivers.remove(d)
else:
    arm.animation_data_create()
arm.animation_data.action = bpy.data.actions.new('Squat')

def basis_for(pb, mats):
    """Local pose basis that reproduces an armature-space matrix."""
    rest = pb.bone.matrix_local
    if pb.parent:
        return (pb.parent.bone.matrix_local.inverted() @ rest).inverted() @ mats[pb.parent.name].inverted() @ mats[pb.name]
    return rest.inverted() @ mats[pb.name]

for f, mats in enumerate(FRAMES):
    for pb in P:
        b = basis_for(pb, mats); pb.rotation_mode = 'QUATERNION'
        loc, rot, _ = b.decompose(); pb.location = loc; pb.rotation_quaternion = rot; pb.scale = (1, 1, 1)
        pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('location', frame=f)
# Self-check: replay the keys and compare with what the constrained rig produced.
err = 0.0
for f in (0, 12, 24, 36):
    scene.frame_set(f); upd()
    for pb in P:
        err = max(err, (pb.matrix.translation - FRAMES[f][pb.name].translation).length)
print('BAKE max joint drift (m):', round(err, 5))
scene.frame_set(0)

# ---------------------------------------------------------------- export
for o in bpy.context.scene.objects: o.hide_set(False)
sizes = {}
for layer, obs in layers.items():
    if not obs: continue
    for o in bpy.context.scene.objects: o.select_set(False)
    arm.select_set(True)
    for o in obs: o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = DST + f'{layer}.usdz'
    bpy.ops.wm.usd_export(filepath=path, selected_objects_only=True, export_animation=True, export_armatures=True,
                          only_deform_bones=False, export_materials=False, export_uvmaps=False, export_normals=True,
                          triangulate_meshes=True, convert_orientation=True, export_global_forward_selection='NEGATIVE_Z',
                          export_global_up_selection='Y', root_prim_path='/Anatomy', evaluation_mode='RENDER')
    sizes[layer] = os.path.getsize(path)
json.dump({'license': 'CC BY-SA 4.0', 'detail': RATIO, 'files': sizes, 'prims': manifest},
          open(DST + 'manifest.json', 'w'), indent=1)
# Structure -> side -> layer files, for AnatomyViewerKit's LayerIndex
# (copy to AnatomyViewerKit/Sources/AnatomyViewerKit/Resources/).
table = {}
for p in manifest:
    if p['kind'] != 'catalog' or p['layer'] not in ('muscle', 'fascia'): continue
    layer = 'fascia' if p['layer'] == 'fascia' else 'muscles-' + p['chunk']
    table.setdefault(p['id'], {}).setdefault(p['side'] or '-', set()).add(layer)
json.dump({'source': 'anatomy-assets manifest.json: catalog structure -> side (l, r, - for midline) -> the layer files that contain it',
           'structures': {k: {s: sorted(v) for s, v in sides.items()} for k, sides in sorted(table.items())}},
          open(DST + 'structure-layers.json', 'w'), indent=1)
print('USDZ', json.dumps(sizes))
