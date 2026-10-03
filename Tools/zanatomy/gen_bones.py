"""One-off generator for bones.json, bones-zanatomy.json and landmark bone IDs.

  OUT=... python3 gen_bones.py   (needs $OUT/zb_bonemeshes.json from list_bone_meshes.py
                                  and $OUT/isa_parts_list_e.txt from BodyParts3D)
bones.json is the source of truth after this; re-running overwrites hand edits.
"""
import json, re, os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '../../Sources/AnatomyKit/Resources/')
meshes=json.load(open(OUT+'zb_bonemeshes.json'))
ORD={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,'seventh':7,'heighth':8,'eighth':8,'ninth':9,'tenth':10,'eleventh':11,'twelfth':12}
FINGER={1:'thumb',2:'index',3:'middle',4:'ring',5:'little'}; TOE={1:'hallux',2:'toe_2',3:'toe_3',4:'toe_4',5:'toe_5'}
def classify(n):
    b=re.sub(r'\.(l|r|001)$','',n); low=b.lower()
    if re.search(r'tooth|incisor|canine|molar|premolar|cartilage|sinus|sesamoid',low): return None
    m=re.match(r'(proximal|middle|distal) phalanx of (\w+) finger of (hand|foot)',low)
    if m:
        k=ORD[m.group(2)]; part=m.group(1)
        if m.group(3)=='hand': return (f'{part}_phalanx_{FINGER[k]}', f'{part.capitalize()} phalanx of {FINGER[k]}' + ('' if k==1 else ' finger'), 'hand','phalanx_hand',True)
        return (f'{part}_phalanx_{TOE[k]}', f'{part.capitalize()} phalanx of ' + ('big toe' if k==1 else f'toe {k}'), 'foot','phalanx_foot',True)
    m=re.match(r'(\w+) (metacarpal|metatarsal) bone',low)
    if m:
        k=ORD[m.group(1)]; hand=m.group(2)=='metacarpal'
        return (f'{m.group(2)}_{k}', f'{m.group(2).capitalize()} {k}', 'hand' if hand else 'foot', m.group(2), True)
    m=re.match(r'(\w+) rib$',low)
    if m: k=ORD[m.group(1)]; return (f'rib_{k}', f'Rib {k}', 'trunk','rib',True)
    m=re.match(r'vertebra ([ctl])(\d+)',low)
    if m:
        lvl=m.group(1); reg='head_neck' if lvl=='c' else 'trunk'
        return (f'vertebra_{lvl}{m.group(2)}', f'{lvl.upper()}{m.group(2)} vertebra', reg,'vertebra',False)
    fixed={'atlas (c1)':('vertebra_c1','Atlas (C1)','head_neck','vertebra',False),'axis (c2)':('vertebra_c2','Axis (C2)','head_neck','vertebra',False),
     'sacrum':('sacrum','Sacrum','trunk','vertebra',False),'coccyx':('coccyx','Coccyx','trunk','vertebra',False),
     'manubrium of sternum':('sternum','Sternum','trunk','sternum',False),'sternum':('sternum','Sternum','trunk','sternum',False),'xiphoid process':('sternum','Sternum','trunk','sternum',False),
     'frontal bone':('frontal','Frontal bone','head_neck','cranium',False),'parietal bone':('parietal','Parietal bone','head_neck','cranium',True),
     'temporal bone':('temporal','Temporal bone','head_neck','cranium',True),'occipital bone':('occipital','Occipital bone','head_neck','cranium',False),
     'sphenoid bone':('sphenoid','Sphenoid bone','head_neck','cranium',False),'ethmoid bone':('ethmoid','Ethmoid bone','head_neck','cranium',False),
     'nasal bone':('nasal','Nasal bone','head_neck','face',True),'maxilla':('maxilla','Maxilla','head_neck','face',True),'lacrimal bone':('lacrimal','Lacrimal bone','head_neck','face',True),
     'zygomatic bone':('zygomatic','Zygomatic bone','head_neck','face',True),'palatine bone':('palatine','Palatine bone','head_neck','face',True),
     'inferior nasal concha bone':('inferior_nasal_concha','Inferior nasal concha','head_neck','face',True),'vomer':('vomer','Vomer','head_neck','face',False),
     'mandible':('mandible','Mandible','head_neck','face',False),'malleus':('malleus','Malleus','head_neck','ossicle',True),'incus':('incus','Incus','head_neck','ossicle',True),
     'stapes':('stapes','Stapes','head_neck','ossicle',True),'hyoid bone':('hyoid','Hyoid','head_neck','hyoid',False),
     'clavicle':('clavicle','Clavicle','shoulder','shoulder_girdle',True),'scapula':('scapula','Scapula','shoulder','shoulder_girdle',True),
     'humerus':('humerus','Humerus','arm','arm',True),'radius':('radius','Radius','arm','arm',True),'ulna':('ulna','Ulna','arm','arm',True),
     'hip bone':('hip_bone','Hip bone','trunk','pelvis',True),'femur':('femur','Femur','leg','leg',True),'patella':('patella','Patella','leg','leg',True),
     'tibia':('tibia','Tibia','leg','leg',True),'fibula':('fibula','Fibula','leg','leg',True)}
    if low in fixed: return fixed[low]
    for c in ['scaphoid','lunate','triquetrum','pisiform','trapezium','trapezoid','capitate','hamate']:
        if low==f'{c} bone': return (c, c.capitalize(), 'hand','carpal',True)
    for c,nm in [('talus','Talus'),('calcaneus','Calcaneus'),('navicular bone','Navicular'),('cuboid bone','Cuboid'),('medial cuneiform bone','Medial cuneiform'),('intermediate cuneiform bone','Intermediate cuneiform'),('lateral cuneiform bone','Lateral cuneiform')]:
        if low==c: return (re.sub(r' bone$','',c).replace(' ','_'), nm, 'foot','tarsal',True)
    raise ValueError('unclassified '+n)
bones={}; zmesh={}
for name,rigbone,cx in meshes:
    c=classify(name)
    if not c: continue
    bid,nm,reg,grp,bil=c
    bones.setdefault(bid,dict(id=bid,name=nm,region=reg,group=grp,bilateral=bil))
    side='midline' if not bil else ('left' if cx>0 else 'right')
    z=zmesh.setdefault(bid,{}); z.setdefault(side,{'meshes':[],'rigBone':rigbone})['meshes'].append(name)
total=sum(2 if b['bilateral'] else 1 for b in bones.values()); print('bone entries',len(bones),'adult count',total)
for bid,z in zmesh.items():
    b=bones[bid]
    assert (set(z)=={'left','right'}) if b['bilateral'] else (set(z)=={'midline'}), (bid,z.keys())
# FMA IDs from BodyParts3D class names where they match exactly
fma={}
for line in open(OUT+'isa_parts_list_e.txt').read().splitlines():
    p=line.split('\t')
    if len(p)>=3: fma.setdefault(p[2].strip().lower(),p[0].strip())
alias={'frontal':'frontal bone','parietal':'parietal bone','temporal':'temporal bone','occipital':'occipital bone','sphenoid':'sphenoid bone','ethmoid':'ethmoid bone','nasal':'nasal bone','lacrimal':'lacrimal bone','zygomatic':'zygomatic bone','palatine':'palatine bone','hyoid':'hyoid bone','navicular':'navicular bone of foot','cuboid':'cuboid bone','scaphoid':'scaphoid bone','lunate':'lunate bone','triquetrum':'triquetral bone','pisiform':'pisiform bone','trapezium':'trapezium bone','trapezoid':'trapezoid bone','capitate':'capitate bone','hamate':'hamate bone','vertebra_c1':'atlas','vertebra_c2':'axis','inferior_nasal_concha':'inferior nasal concha'}
nth=['','first','second','third','fourth','fifth','sixth','seventh','eighth','ninth','tenth','eleventh','twelfth']
for bid,b in bones.items():
    keys=[alias.get(bid,''), b['name'].lower(), bid.replace('_',' ')]
    m=re.match(r'rib_(\d+)',bid)
    if m: keys.append(f'{nth[int(m.group(1))]} rib')
    m=re.match(r'vertebra_([tl])(\d+)',bid)
    if m: keys.append(f"{nth[int(m.group(2))]} {'thoracic' if m.group(1)=='t' else 'lumbar'} vertebra")
    m=re.match(r'vertebra_c(\d+)',bid)
    if m: keys.append(f'{nth[int(m.group(1))]} cervical vertebra')
    for k in keys:
        if k and k in fma: b['fmaID']=fma[k]; break
    b['source']='Z-Anatomy bone meshes; FMA ID from BodyParts3D class names where they match' ; b['reviewed']=False
order={'head_neck':0,'trunk':1,'shoulder':2,'arm':3,'hand':4,'leg':5,'foot':6}
out=sorted(bones.values(),key=lambda b:(order[b['region']],b['group'],b['id']))
json.dump(out,open(R+'bones.json','w'),indent=2,ensure_ascii=False); open(R+'bones.json','a').write('\n')
json.dump({'source':'Z-Anatomy / Z-Biomechanics mesh and armature bone names, by side','bones':{b['id']:zmesh[b['id']] for b in out}},open(R+'bones-zanatomy.json','w'),indent=2,ensure_ascii=False); open(R+'bones-zanatomy.json','a').write('\n')
print('with FMA',sum('fmaID' in b for b in out),'of',len(out)); print('no FMA',[b['id'] for b in out if 'fmaID' not in b][:40])
# landmarks -> bone IDs via the placement rules
rules=json.load(open(os.path.join(HERE,'landmark_rules.json'))); name2bone={}
for name,_,_ in meshes:
    c=classify(name)
    if c: name2bone[name]=c[0]
lms=json.load(open(R+'landmarks.json'))
for l in lms:
    r=rules[l['id']]
    ids=sorted({name2bone[n] for n in name2bone if 'meshes' in r and re.search(r['meshes'],n)})
    l.pop('bone',None); l['bones']=ids
    if l['id']=='rib5.costal_cartilage': ids=['rib_5']  # cartilage isn't counted as bone
    if not ids: print('no bones for', l['id'])
json.dump(lms,open(R+'landmarks.json','w'),indent=2,ensure_ascii=False); open(R+'landmarks.json','a').write('\n')
