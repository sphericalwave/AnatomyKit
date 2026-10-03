import bpy, math, json
import os
OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Sources/AnatomyKit/Resources/')
arm=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.data.name=='Armature'][0]
bones={"Hips":[],"LowerBack":["lumbar_spine"],"Spine":["thoracic_spine"],"Spine1":["thoracic_spine"],"Neck1":["cervical_spine"],"Head":["cervical_spine"],"Mandible":["temporomandibular"]}
for S,s in (("Left","left"),("Right","right")):
    bones.update({f"{S}Shoulder":["scapulothoracic"],f"{S}Arm":["glenohumeral"],f"{S}ForeArm":["elbow","radioulnar"],f"{S}Hand":["wrist"],f"{S}UpLeg":["hip"],f"{S}Leg":["knee"],f"{S}Foot":["talocrural","subtalar"],f"{S}ToeBase":["toes_mtp"]})
out=[]
for b,js in bones.items():
    pb=arm.pose.bones[b]; e={"bone":b,"joints":js}
    if b.startswith("Left"): e["side"]="left"
    if b.startswith("Right"): e["side"]="right"
    lim={}
    for c in pb.constraints:
        if c.type=='LIMIT_ROTATION' and not c.mute:
            for ax in "xyz":
                if getattr(c,f"use_limit_{ax}"): lim[ax]=[round(math.degrees(getattr(c,f"min_{ax}")),1),round(math.degrees(getattr(c,f"max_{ax}")),1)]
    if lim: e["limitsDegrees"]=lim
    out.append(e)
print("JSON"+json.dumps(out))
