import bpy, bmesh, sys, struct, gzip, json, mathutils
import os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
args = sys.argv[sys.argv.index('--')+1:]
mode, out, target = args[0], args[1], int(args[2])
D=OUT

def gather_world_tris(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        ev.to_mesh_clear()
    return bm

names = []
if mode == 'bp3d':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ids = [l.strip() for l in open(os.environ['BP3D_SKELETON_LIST']) if l.strip()]
    objs = []
    for i in ids:
        bpy.ops.wm.obj_import(filepath=f"{os.environ['BP3D_OBJ_DIR']}/{i}.obj", up_axis='Z', forward_axis='Y')
        objs += list(bpy.context.selected_objects)
    for o in objs:
        o.scale = (0.001,)*3
    bpy.context.view_layer.update()
    names = [o.name for o in objs]
elif mode == 'ybot':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=os.environ['YBOT_USDZ'])
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    names = [o.name for o in objs]
else:
    coll = bpy.data.collections[mode]  # "1: Skeletal system" or "Fascia"
    objs = [o for o in coll.all_objects if o.type == 'MESH' and (mode == 'Fascia' or not o.hide_render) and not any(m.type == 'WIREFRAME' for m in o.modifiers) and len(o.data.polygons) > 0]
    names = [o.name for o in objs]

src_tris = sum(len(p.vertices)-2 for o in objs for p in o.data.polygons)
bm = gather_world_tris(objs)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
me = bpy.data.meshes.new('joined'); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new('joined', me); bpy.context.scene.collection.objects.link(ob)
tri0 = len(me.polygons)
if tri0 > target:
    md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = target / tri0
    bpy.context.view_layer.objects.active = ob
    dg = bpy.context.evaluated_depsgraph_get()
    m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); ob.modifiers.clear(); ob.data = m2; me = m2
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
vs = [v.co.copy() for v in me.vertices]
tris = [tuple(p.vertices) for p in me.polygons]
# Blender Z-up (front -Y) -> three.js Y-up (front +Z): (x, z, -y)
P = [(v.x, v.z, -v.y) for v in vs]
lo = [min(p[i] for p in P) for i in range(3)]; hi = [max(p[i] for p in P) for i in range(3)]
meta = dict(mode=mode, sourceObjects=len(objs), sourceTris=src_tris, tris=len(tris), verts=len(P), lo=lo, hi=hi)
print('META', json.dumps(meta))
q = []
for p in P:
    for i in range(3):
        q.append(int(round((p[i]-lo[i])/((hi[i]-lo[i]) or 1)*65535)))
buf = struct.pack(f'<{len(q)}H', *q) + struct.pack(f'<{len(tris)*3}I', *[i for t in tris for i in t])
open(out, 'wb').write(gzip.compress(buf, 9))
json.dump(meta, open(out + '.json', 'w'))
