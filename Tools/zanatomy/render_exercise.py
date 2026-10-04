"""Render an exercise in the clay-figure style, and export it for the web viewer.

  ZANATOMY_BLEND=Z-Anatomy/Startup.blend OUT=out SPEC=exercises/cable_lateral_raise.json \
    blender -b Z-Biomechanics/Startup.blend --python render_exercise.py

Writes to $OUT/<spec id>/:
  frames/####.png, <id>.mp4, <id>.gif    the Workbench render (matte grey, cavity, outlines)
  web/*.bin, web/exercise.json             skeleton, muscles, skin weights and per-frame
                                           bone motion for the three.js page

The exercise is data: poses, loop timing, equipment, camera, and which
AnatomyKit movement directions to colour. Muscles whose AnatomyKit actions
include a `prime` direction (prime role) are tinted strongly; other listed
directions' prime movers and the main direction's secondary movers are
tinted lightly.
"""
import bpy, bmesh, gzip, json, math, os, re, shutil, struct, subprocess
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '../../Sources/AnatomyKit/Resources/')
SPEC = json.load(open(os.environ['SPEC']))
OUT = os.path.join(os.environ.get('OUT', os.getcwd()), SPEC['id']) + '/'
ZA = os.environ['ZANATOMY_BLEND']
os.makedirs(OUT + 'frames', exist_ok=True); os.makedirs(OUT + 'web', exist_ok=True)

GREY = (0.80, 0.80, 0.80, 1); PRIME = (0.86, 0.30, 0.22, 1); SECONDARY = (0.94, 0.62, 0.54, 1)
FRAME = (0.70, 0.70, 0.72, 1); STACK = (0.10, 0.10, 0.10, 1); CABLE = (0.08, 0.08, 0.08, 1)

arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.name == 'Armature'][0]
P = arm.pose.bones
def upd(): bpy.context.view_layer.update()
for pb in P: pb.matrix_basis = Matrix.Identity(4)
upd()

def body(v):
    """Spec body frame (+x left, +y forward, z up) -> Blender (front is -Y)."""
    return Vector((v[0], -v[1], v[2]))

# ---------------------------------------------------------------- target colours from AnatomyKit
muscles = json.load(open(RES + 'muscles.json'))
prime_dirs = set(SPEC['targets']['prime']); second_dirs = set(SPEC['targets'].get('secondary', []))
tint = {}
for m in muscles:
    level = None
    for a in m.get('actions', []):
        if a['direction'] in prime_dirs and a['role'] == 'prime': level = 'prime'
        # Assisting: helpers of the main movement, and main movers of the
        # supporting movements (e.g. upper traps for scapular upward rotation).
        elif level != 'prime' and ((a['direction'] in prime_dirs) or (a['direction'] in second_dirs and a['role'] == 'prime')):
            level = 'secondary'
    if level: tint[m['id']] = level
meshmap = json.load(open(RES + 'meshes-zanatomy.json'))['meshes']
base_tint = {b: tint[cid] for cid, bases in meshmap.items() if cid in tint for b in bases}
print('TARGETS', tint)

# ---------------------------------------------------------------- muscles, skinned to the rig
deform = sorted({o.parent_bone for o in bpy.data.objects
                 if o.type == 'MESH' and o.parent == arm and o.parent_type == 'BONE'})
seg = np.array([[*(arm.matrix_world @ P[b].head), *(arm.matrix_world @ P[b].tail)] for b in deform])
A_ = seg[:, :3]; AB = seg[:, 3:] - A_; AB2 = np.maximum((AB * AB).sum(1), 1e-12)
ARMB = re.compile(r'Radius|Ulna|carpal|Metacarpal|of hand|Hand|Thumb|FingerBase|Offset')
LEGB = re.compile(r'UpLeg|LeftLeg$|RightLeg$|Knee|Tibia|Patella|Foot|Calcaneus|Navicular|Cuboid|Cuneiform|Metatarsal|of foot|ToeBase|Fibula|Femur|Talus')
armBone = np.array([bool(ARMB.search(b)) for b in deform]); legBone = np.array([bool(LEGB.search(b)) for b in deform])

def nearest_bones(v, is_arm):
    """Four nearest bone segments per vertex, weights 1/(d + 1 cm)^2 (smoother than
    the ^4 used for the atlas, so the deltoid doesn't tear as the arm lifts); arm and leg
    structures can't follow each other's bones (the hands hang beside the thighs)."""
    nn_all = np.zeros((len(v), 4), int); w_all = np.zeros((len(v), 4))
    for s in range(0, len(v), 20000):
        p = v[s:s + 20000, None, :]; t = np.clip(((p - A_) * AB).sum(2) / AB2, 0, 1)
        d = np.linalg.norm(p - (A_ + t[..., None] * AB), axis=2)
        d[:, legBone if is_arm else armBone] = np.inf
        nn = np.argsort(d, 1)[:, :4]; dn = np.take_along_axis(d, nn, 1)
        w = 1 / (dn + 0.01) ** 2; w /= w.sum(1, keepdims=True)
        nn_all[s:s + 20000] = nn; w_all[s:s + 20000] = w
    return nn_all, w_all

def baked(src, ratio, name):
    md = src.modifiers.new('dec', 'DECIMATE'); md.ratio = ratio
    upd(); me = bpy.data.meshes.new_from_object(src.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    src.modifiers.remove(md); me.transform(src.matrix_world); me.name = name
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

with bpy.data.libraries.load(ZA, link=False) as (src, dst):
    dst.collections = [c for c in src.collections if c in ('Superficial muscles', 'Muscles')]
loaded = {}
# "Superficial muscles" also holds the sheets wrapped around muscles (deltoid,
# brachial, crural fascia …); they'd hide the tinted muscles and tear at the joints.
SHEET = re.compile(r'fascia|aponeurosis|retinacul|bursa|tendon sheath|septum', re.I)
for coll in dst.collections:
    for o in coll.all_objects:
        if o.type == 'MESH' and len(o.data.polygons) > 0 and not SHEET.search(o.name): loaded.setdefault(o.name, o)
for o in loaded.values():
    if o.name not in bpy.context.scene.objects: bpy.context.scene.collection.objects.link(o)
upd()
muscle_objs = []
for name, o in sorted(loaded.items()):
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    cx = sum(v.x for v in vs) / len(vs); cz = sum(v.z for v in vs) / len(vs)
    is_arm = abs(cx) > 0.19 and cz > 0.55
    ob = baked(o, SPEC['render']['detail'], 'm_' + name)
    level = base_tint.get(re.sub(r'\.(l|r)$', '', name))
    # Tint only the working side.
    side_ok = SPEC['working_side'] == ('left' if cx > 0 else 'right') or abs(cx) < 0.02
    t = (2 if level == 'prime' else 1 if level else 0) if side_ok else 0
    ob.color = (GREY, SECONDARY, PRIME)[t]; ob['tint'] = t
    nn, w = nearest_bones(np.array([tuple(v.co) for v in ob.data.vertices]), is_arm)
    groups = {}
    for i in range(len(nn)):
        for k in range(4): groups.setdefault(int(nn[i, k]), []).append((i, float(w[i, k])))
    for b, items in groups.items():
        vg = ob.vertex_groups.new(name=deform[b])
        for i, wt in items: vg.add([i], wt, 'REPLACE')
    ob.modifiers.new('Armature', 'ARMATURE').object = arm
    ob['is_arm'] = is_arm
    muscle_objs.append(ob)
for o in loaded.values(): bpy.data.objects.remove(o)
bone_objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm and o.parent_type == 'BONE']
for o in bone_objs: o.color = GREY
# Anything else in the file (labels, helper meshes) stays out of the render.
keep = set(muscle_objs) | set(bone_objs) | {arm}
for o in bpy.context.scene.objects:
    if o not in keep: o.hide_render = True

# ---------------------------------------------------------------- equipment
def box(name, lo, hi, color):
    lo, hi = body(lo), body(hi)
    c = (lo + hi) / 2; s = Vector([abs(a - b) for a, b in zip(hi, lo)])
    bpy.ops.mesh.primitive_cube_add(size=1, location=c); ob = bpy.context.object
    ob.scale = s; ob.name = name; ob.color = color
    return ob

equipment = []
if SPEC['equipment']['type'] == 'cable_tower':
    px, py, pz = SPEC['equipment']['pulley']
    x0, x1, yf, yb, top = px + 0.06, px + 0.78, py - 0.04, py - 0.5, 2.15
    t = 0.045
    for x in (x0, x1):
        for y in (yf, yb):
            equipment.append(box('upright', (x - t / 2, y - t / 2, 0.02), (x + t / 2, y + t / 2, top), FRAME))
        equipment.append(box('top rail', (x - t / 2, yb, top - t), (x + t / 2, yf, top), FRAME))
        equipment.append(box('base rail', (x - t, yb - 0.1, 0), (x + t, yf + 0.12, 0.04), FRAME))
    equipment.append(box('cross', (x0, yb - t / 2, top - t), (x1, yb + t / 2, top), FRAME))
    equipment.append(box('cross low', (x0, yb - t / 2, 0.1), (x1, yb + t / 2, 0.14), FRAME))
    mx = (x0 + x1) / 2; my = (yf + yb) / 2
    for dx in (-0.06, 0.06):
        equipment.append(box('guide rod', (mx + dx - 0.008, my - 0.008, 0.1), (mx + dx + 0.008, my + 0.008, top - 0.05), FRAME))
    equipment.append(box('weight stack', (mx - 0.14, my - 0.07, 0.12), (mx + 0.14, my + 0.07, 0.58), STACK))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=0.03, location=body((px, py, pz)), rotation=(0, math.pi / 2, 0))
    pulley = bpy.context.object; pulley.color = FRAME; equipment.append(pulley)
    equipment.append(box('pulley arm', (px - 0.02, py - 0.02, 0.02), (px + 0.08, py + 0.02, pz), FRAME))

cable_curve = bpy.data.curves.new('cable', 'CURVE'); cable_curve.dimensions = '3D'; cable_curve.bevel_depth = 0.006
spl = cable_curve.splines.new('POLY'); spl.points.add(1)
cable = bpy.data.objects.new('cable', cable_curve); cable.color = CABLE; bpy.context.scene.collection.objects.link(cable)
pulley_pt = body(SPEC['equipment']['pulley'])

# ---------------------------------------------------------------- posing
SIDE = {'right': ('RightShoulder', 'RightArm', 'RightForeArm', -1.0), 'left': ('LeftShoulder', 'LeftArm', 'LeftForeArm', 1.0)}

def arm_dirs(p, sign):
    a, f, e = math.radians(p['abduct']), math.radians(p['forward']), math.radians(p['elbowFlex'])
    out, fwd, down = Vector((sign, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, -1))
    d = (out * math.sin(a) * math.cos(f) + fwd * math.sin(a) * math.sin(f) + down * math.cos(a)).normalized()
    perp = (fwd - d * fwd.dot(d)).normalized()
    return d, (d * math.cos(e) + perp * math.sin(e)).normalized()

def aim(pb, target):
    cur = arm.matrix_world @ pb.matrix
    dirv = (cur.to_3x3() @ Vector((0, 1, 0))).normalized()
    new = (dirv.rotation_difference(target).to_matrix() @ cur.to_3x3()).to_4x4(); new.translation = cur.translation
    pb.matrix = arm.matrix_world.inverted() @ new; upd()

def hinge(pb, target):
    """Elbow: rotate about the bone's local Z only, inside the rig's limit."""
    cur = arm.matrix_world @ pb.matrix
    ax = (cur.to_3x3() @ Vector((0, 0, 1))).normalized(); d0 = (cur.to_3x3() @ Vector((0, 1, 0))).normalized()
    a = (d0 - ax * d0.dot(ax)).normalized(); b = (target - ax * target.dot(ax)).normalized()
    th = math.atan2(ax.dot(a.cross(b)), a.dot(b))
    lim = [c for c in pb.constraints if c.type == 'LIMIT_ROTATION' and not c.mute][0]
    pb.rotation_mode = 'YZX'; pb.rotation_euler = (0, 0, max(lim.min_z, min(lim.max_z, th))); upd()

def lerp_pose(a, b, u):
    return {s: {k: a[s][k] + (b[s][k] - a[s][k]) * u for k in a[s]} for s in a}

def pose(p):
    for pb in P: pb.matrix_basis = Matrix.Identity(4)
    upd()
    for side, (girdle, upper, fore, sign) in SIDE.items():
        e = math.radians(p[side].get('shoulderElevate', 0))
        if e:
            # Lift the lateral end of the clavicle: the scapula follows it.
            cur = arm.matrix_world @ P[girdle].matrix
            d = (cur.to_3x3() @ Vector((0, 1, 0))).normalized()
            aim(P[girdle], (d * math.cos(e) + Vector((0, 0, 1)) * math.sin(e)).normalized())
        d_upper, d_fore = arm_dirs(p[side], sign)
        aim(P[upper], d_upper); hinge(P[fore], d_fore)

def grip(side):
    return arm.matrix_world @ P['RightFingerBase' if side == 'right' else 'LeftFingerBase'].head

L = SPEC['loop']; N = L['frames']; hb, ht = L['hold_bottom'], L['hold_top']; move = (N - hb - ht) // 2
def u_at(f):
    """Eased 0 -> 1 -> 0 over the loop, with holds at the bottom and top."""
    if f < hb: return 0.0
    if f < hb + move: x = (f - hb) / move; return 0.5 - 0.5 * math.cos(math.pi * x)
    if f < hb + move + ht: return 1.0
    x = (f - hb - move - ht) / max(1, N - hb - move - ht); return 0.5 + 0.5 * math.cos(math.pi * min(1, x))

# ---------------------------------------------------------------- render setup
s = bpy.context.scene
s.render.engine = 'BLENDER_WORKBENCH'
s.render.resolution_x, s.render.resolution_y = SPEC['render']['size']
s.display.render_aa = '16'
sh = s.display.shading
sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_specular_highlight = False
sh.show_cavity = True; sh.cavity_type = 'BOTH'
sh.cavity_ridge_factor = 1.2; sh.cavity_valley_factor = 1.4; sh.curvature_ridge_factor = 1.0; sh.curvature_valley_factor = 1.2
sh.show_object_outline = True; sh.object_outline_color = (0.05, 0.05, 0.05)
s.world = s.world or bpy.data.worlds.new('World'); s.world.color = (1, 1, 1)
s.view_settings.view_transform = 'Standard'
cam_spec = SPEC['camera']
cam = bpy.data.objects.new('camera', bpy.data.cameras.new('camera')); s.collection.objects.link(cam); s.camera = cam
cam.data.lens = cam_spec['lens']
az, el = math.radians(cam_spec['azimuth']), math.radians(cam_spec['elevation'])
target = body(cam_spec['target'])
cam.location = target + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * cam_spec['distance']
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- frames (render + web motion)
C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))  # Blender -> three.js
# Rest = the pose all skin weights were computed in (identity basis).
for pb in P: pb.matrix_basis = Matrix.Identity(4)
upd(); rest = {b: arm.matrix_world @ P[b].matrix for b in deform}
frames_out = []; grips = []
# PREVIEW=1 renders three frames (bottom, middle, top) to check the look quickly.
render_frames = {0, hb + move // 2, hb + move} if os.environ.get('PREVIEW') else set(range(N))
for f in range(N):
    pose(lerp_pose(SPEC['poses']['bottom'], SPEC['poses']['top'], u_at(f)))
    g = grip(SPEC['working_side'])
    spl.points[0].co = (*pulley_pt, 1); spl.points[1].co = (*g, 1)
    upd()
    if f in render_frames:
        s.render.filepath = OUT + f'frames/{f:04d}.png'; bpy.ops.render.render(write_still=True)
    row = []
    for b in deform:
        l, q, _ = (C @ ((arm.matrix_world @ P[b].matrix) @ rest[b].inverted()) @ C.inverted()).decompose()
        row += [l.x, l.y, l.z, q.x, q.y, q.z, q.w]
    frames_out.append(row); grips.append(list(C @ g))
print('RENDERED', len(render_frames))
if os.environ.get('PREVIEW'): raise SystemExit(0)

fps = L['fps']
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', OUT + 'frames/%04d.png',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', OUT + SPEC['id'] + '.mp4'], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', OUT + 'frames/%04d.png', '-vf',
                'scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer:bayer_scale=4',
                '-loop', '0', OUT + SPEC['id'] + '.gif'], check=True)

# ---------------------------------------------------------------- web export (rest geometry + motion)
for pb in P: pb.matrix_basis = Matrix.Identity(4)
upd()
def pack(objs, ratio, per_vertex):
    pos, idx, ranges, extra = [], [], [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        mods = [m for m in o.modifiers if m.type == 'ARMATURE']
        for m in mods: m.show_viewport = False
        md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = ratio
        upd(); dg = bpy.context.evaluated_depsgraph_get()
        me = o.evaluated_get(dg).to_mesh()
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
        W = C @ o.matrix_world; base = len(pos) // 3; i0 = len(idx)
        world = [o.matrix_world @ v.co for v in me.vertices]
        for v in world: p = C @ v; pos += [p.x, p.y, p.z]
        for fc in me.polygons: idx += [base + i for i in fc.vertices]
        extra.append(per_vertex(o, world))
        ranges.append([o.name, i0, len(idx) - i0, int(o.get('tint', 0))])
        o.evaluated_get(dg).to_mesh_clear(); o.modifiers.remove(md)
        for m in mods: m.show_viewport = True
    return pos, idx, ranges, extra

def write_geo(path, pos, idx):
    lo = [min(pos[i::3]) for i in range(3)]; hi = [max(pos[i::3]) for i in range(3)]
    q = [int(round((pos[i] - lo[i % 3]) / (hi[i % 3] - lo[i % 3]) * 65535)) for i in range(len(pos))]
    open(path, 'wb').write(gzip.compress(struct.pack(f'<{len(q)}H', *q) + struct.pack(f'<{len(idx)}I', *idx), 9))
    return lo, hi

bidx = {b: i for i, b in enumerate(deform)}
spos, sidx, sranges, sbones = pack(bone_objs, 0.25, lambda o, w: [bidx[o.parent_bone]] * len(w))
slo, shi = write_geo(OUT + 'web/skeleton.bin', spos, sidx)
open(OUT + 'web/skeleton_bones.bin', 'wb').write(gzip.compress(bytes([b for chunk in sbones for b in chunk]), 9))
mpos, midx, mranges, mweights = pack(muscle_objs, 0.4, lambda o, w: nearest_bones(np.array([tuple(v) for v in w]), bool(o.get('is_arm'))))
mlo, mhi = write_geo(OUT + 'web/muscles.bin', mpos, midx)
nn = np.concatenate([a for a, _ in mweights]).astype(np.uint8)
wq = np.concatenate([w for _, w in mweights]); wq = np.round(wq * 255).astype(int); wq[:, 0] += 255 - wq.sum(1)
open(OUT + 'web/weights.bin', 'wb').write(gzip.compress(nn.tobytes() + np.clip(wq, 0, 255).astype(np.uint8).tobytes(), 9))
open(OUT + 'web/frames.bin', 'wb').write(gzip.compress(struct.pack(f'<{len(frames_out) * len(deform) * 7}f', *[x for r in frames_out for x in r]), 9))
boxes = []
for o in equipment:
    bb = [C @ (o.matrix_world @ Vector(c)) for c in o.bound_box]
    lo = [min(v[i] for v in bb) for i in range(3)]; hi = [max(v[i] for v in bb) for i in range(3)]
    boxes.append({'lo': lo, 'hi': hi, 'dark': o.color[0] < 0.3, 'round': o.name.startswith('Cylinder')})
json.dump({'name': SPEC['name'], 'fps': fps, 'frames': N, 'bones': len(deform),
           'skeleton': {'verts': len(spos) // 3, 'tris': len(sidx) // 3, 'lo': slo, 'hi': shi},
           'muscles': {'verts': len(mpos) // 3, 'tris': len(midx) // 3, 'lo': mlo, 'hi': mhi, 'ranges': mranges},
           'pulley': list(C @ pulley_pt), 'grips': grips, 'equipment': boxes,
           'camera': {'position': list(C @ cam.location), 'target': list(C @ target), 'lens': cam_spec['lens']},
           'targets': tint}, open(OUT + 'web/exercise.json', 'w'))
print('DONE', OUT)
