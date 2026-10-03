import bpy, bmesh, os
import os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
D=OUT+'usd/'; os.makedirs(D, exist_ok=True)
def objs_of(names, include_hidden):
    out=[]
    for n in names:
        for o in bpy.data.collections[n].all_objects:
            if o.type=='MESH' and len(o.data.polygons)>0 and (include_hidden or not o.hide_render) and not any(m.type=='WIREFRAME' for m in o.modifiers):
                out.append(o)
    return list({o.name:o for o in out}.values())
sets = {
 'skeleton': (['1: Skeletal system'], False),
 'muscles': (['Superficial muscles','Muscles'], True),
 'fascia': (['Fascia'], True),
 'joints_ligaments': (['3: Joints'], True),
}
dg = bpy.context.evaluated_depsgraph_get()
for key,(names,hid) in sets.items():
    objs = objs_of(names, hid)
    bm = bmesh.new()
    for o in objs:
        ev=o.evaluated_get(dg); me=ev.to_mesh(); me.transform(o.matrix_world); bm.from_mesh(me); ev.to_mesh_clear()
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    base = bpy.data.meshes.new(key); bm.to_mesh(base); bm.free()
    tris = len(base.polygons)
    for ratio in (1.0, 0.25, 0.1):
        me = base.copy(); ob = bpy.data.objects.new(f'{key}_{ratio}', me); bpy.context.scene.collection.objects.link(ob)
        if ratio < 1:
            md = ob.modifiers.new('d','DECIMATE'); md.ratio = ratio
        for o in bpy.context.scene.objects: o.select_set(False)
        ob.select_set(True); bpy.context.view_layer.objects.active = ob
        path = f'{D}{key}_{int(ratio*100)}.usdz'
        bpy.ops.wm.usd_export(filepath=path, selected_objects_only=True, export_materials=False, export_uvmaps=False, export_normals=True, export_animation=False)
        print('USD', key, len(objs), 'objs', tris, 'tris', ratio, os.path.getsize(path))
        bpy.data.objects.remove(ob)
