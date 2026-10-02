import bpy, bmesh, json, struct, gzip
import os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
D=OUT
R=RES
mm=json.load(open(R+'meshes-zanatomy.json'))['meshes']
lines=json.load(open(R+'lines.json'))
used=set(x for l in lines for p in l['paths'] for s in p['steps'] for x in s.get('via',[]))
want=[]
for cid in sorted(used):
    for b in mm.get(cid,[]):
        for n in (b+'.l',b+'.r',b):
            if n in bpy.data.objects: want.append(n)
C=__import__('mathutils').Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
for n in want:
    o=bpy.data.objects[n]
    if not any(m.type=='DECIMATE' for m in o.modifiers):
        md=o.modifiers.new('dec','DECIMATE'); md.ratio=0.25
bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
pos=[]; idx=[]; ranges=[]; src=0
for n in want:
    o=bpy.data.objects[n]; src+=sum(len(p.vertices)-2 for p in o.data.polygons)
    ev=o.evaluated_get(dg); me=ev.to_mesh()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm,faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    W=C@o.matrix_world; base=len(pos)//3; i0=len(idx)
    for v in me.vertices: p=W@v.co; pos+=[p.x,p.y,p.z]
    for f in me.polygons: idx+=[base+i for i in f.vertices]
    ranges.append([n,i0,len(idx)-i0]); ev.to_mesh_clear()
lo=[min(pos[i::3]) for i in range(3)]; hi=[max(pos[i::3]) for i in range(3)]
q=[int(round((pos[i]-lo[i%3])/(hi[i%3]-lo[i%3])*65535)) for i in range(len(pos))]
open(D+'out_lines.bin','wb').write(gzip.compress(struct.pack(f'<{len(q)}H',*q)+struct.pack(f'<{len(idx)}I',*idx),9))
json.dump(dict(verts=len(pos)//3,tris=len(idx)//3,sourceTris=src,lo=lo,hi=hi,ranges=ranges),open(D+'out_lines.json','w'))
print('LINES',len(want),'objects',len(idx)//3,'tris from',src)
