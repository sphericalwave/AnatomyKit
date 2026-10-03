"""Prints JSON [mesh name, rig bone, mean x] for every bone-parented mesh:
  blender -b Z-Biomechanics/Startup.blend --python list_bone_meshes.py | grep ^JSON | sed s/^JSON// > zb_bonemeshes.json
"""
import bpy, json
arm=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.data.name=='Armature'][0]
out=[]
for o in bpy.data.objects:
    if o.type=='MESH' and o.parent==arm and o.parent_type=='BONE' and len(o.data.polygons)>0:
        xs=[(o.matrix_world@v.co).x for v in o.data.vertices]; cx=sum(xs)/len(xs)
        out.append([o.name,o.parent_bone,round(cx,3)])
print("JSON"+json.dumps(sorted(out)))
