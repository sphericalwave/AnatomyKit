# Z-Anatomy pipeline

Blender scripts that turn Z-Anatomy into what the anatomy model needs: decimated
meshes, the Z-Anatomy rig's limits, line muscles skinned to the rig, a baked
squat, and two web prototypes (the line atlas and the source comparison).

Run headless with Blender 4.2 LTS. Every script reads `$OUT` (default: the
current directory) for inputs and writes its outputs there. The catalog JSON
comes from `../../Sources/AnatomyKit/Resources`.

## Inputs

- `Z-Anatomy/Startup.blend` and `Z-Biomechanics/Startup.blend` from
  github.com/Z-Anatomy/Models-of-human-anatomy (`Z-Anatomy.zip`,
  `Z-Biomechanics.7z`). CC BY-SA 4.0: anything derived from them is too.
- For the comparison page only: BodyParts3D 4.0 (`isa_BP3D_4.0_obj_99.zip` and
  `isa_element_parts.txt` from dbarchive.biosciencedbc.jp, CC BY 4.0) and
  Mixamo's `YBot.usdz`.

## Steps

```sh
B=/Applications/Blender.app/Contents/MacOS/Blender
ZA=Z-Anatomy/Startup.blend; ZB=Z-Biomechanics/Startup.blend

$B -b $ZA --python export_lines.py         # line muscles/tissues at 25% → out_lines.*
$B -b $ZB --python rig_lines.py            # skeleton, skin weights, squat bone frames → rig_*
$B -b $ZB --python ribbons.py              # ribbon points: stations on bone (landmark_rules.json) → ribbons.json
$B -b $ZB --python limits.py | grep '^JSON' | sed 's/^JSON//' > zb_limits.json   # rig limits

# Comparison page:
awk -F'\t' '$1=="FMA5018"||$1=="FMA55107"||$1=="FMA7591"{print $3}' isa_element_parts.txt | sort -u > bp3d_skel.txt
BP3D_OBJ_DIR=bp3d/isa_BP3D_4.0_obj_99 BP3D_SKELETON_LIST=bp3d_skel.txt \
  $B -b --python export_skeleton.py -- bp3d out_bp3d.bin 160000
$B -b $ZA --python export_skeleton.py -- "1: Skeletal system" out_za.bin 160000
$B -b $ZA --python export_skeleton.py -- Fascia out_zfascia.bin 50000
YBOT_USDZ=YBot.usdz $B -b --python export_skeleton.py -- ybot out_ybot.bin 60000
$B -b $ZB --python squat_bake.py           # rigid-bone squat for the comparison page

python3 build_pages.py                     # → myofascial-lines.html, skeleton-compare.html

# Rigged USDZ layers for the apps (published at github.com/sphericalwave/anatomy-assets):
ZANATOMY_BLEND=$ZA $B -b $ZB --python export_usdz.py   # → usdz/*.usdz + manifest.json
$B -b $ZA --python usdsize.py              # optional: USDZ size per layer at 100/25/10%
```

## Exercise animations

One JSON spec per exercise in `exercises/`. The spec holds the poses, loop timing,
equipment, camera, and the AnatomyKit movement directions to colour.

```sh
SPEC=exercises/cable_lateral_raise.json ZANATOMY_BLEND=$ZA \
  $B -b $ZB --python render_exercise.py          # → $OUT/<id>/<id>.mp4, .gif, web/
EXERCISE=<id> python3 build_pages.py             # → $OUT/<id>.html (render vs live)
PREVIEW=1 …                                      # three frames only, to check the look
```

- **Render:** Blender Workbench with matte object colours, cavity shading for muscle
  definition, and object outlines on white.
- **Colours:** prime movers of the `prime` directions are red. Prime movers of the
  `secondary` directions, and helpers of the prime ones, are light red. Working side only.
- **Muscles:** Z-Anatomy's sheets (fascia, aponeuroses, retinacula) are left out. They
  hide the tinted muscles and tear at the joints.
- **Live look:** each vertex gets a baked crease value (how far its neighbours rise above
  its tangent plane). The page darkens grooves and lightens ridges with it, standing in
  for cavity shading. A screen-space pass draws outlines where depth jumps (the
  silhouette) or surface direction jumps (borders between muscles). `WEB_ONLY=1` skips
  the render and re-exports just the web data.
- **Shoulder:** `shoulderElevate` lifts the shoulder girdle with the arm (scapulohumeral
  rhythm), which keeps the deltoid from tearing at the top of a raise.

## Notes

- **Squat:** RigKit's sample back squat, retargeted to the Z-Biomechanics
  control bones (`Hips`, `LowerBack`, `LeftUpLeg` …). The rig's constraints move
  everything else. Elbows are driven as hinges about the bone's local Z,
  because a free-aim rotation gets cancelled by the rig's rotation limits.
- **Skinning:** each muscle vertex follows its four nearest bone segments,
  weighted by 1/(d + 1 cm)⁴. Leg and trunk structures can't follow forearm or
  hand bones, and arm structures can't follow leg bones. The hands hang beside
  the thighs at rest, so without this the thigh muscles stretch toward the hands.
- **Ribbons:** each station is placed on its bone by a rule in
  `landmark_rules.json`: the bone mesh, the direction to its extreme point, and
  an optional height band (e.g. the ASIS is the front-most point of the upper
  hip bone). Points between stations are the centre of the track's muscles,
  sliced along the station-to-station direction. Muscle-contact heuristics
  failed here, because Z-Anatomy has no separate tendon meshes.
- **Geometry format** in the `.bin` files: gzip of uint16 positions quantised
  to the bbox in the matching `.json`, then uint32 triangle indices.
