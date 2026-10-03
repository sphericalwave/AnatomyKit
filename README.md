# AnatomyKit

The fitness suite's shared anatomy model, as data: regions, joints and the
directions they move in, joint groups people name ("shoulder"), muscles, Myers'
twelve myofascial lines, and rig bindings. No RealityKit or UI, so torque, suit,
RigKit and tools can all depend on it.

Design and roadmap: `suitKit/ANATOMY_MODEL_PLAN.md`.

## Requirements

- iOS 17+ / macOS 14+ / watchOS 10+
- Swift 5.9+

## Use

```swift
import AnatomyKit

let catalog = AnatomyCatalog.standard
let gh = catalog.joint("glenohumeral")
let dir = catalog.direction(forTorqueMovement: "gh.flex")   // glenohumeral.flexion
let shoulder = catalog.complex(forSuitJoint: "shoulder")    // scapulothoracic + glenohumeral
let spiral = catalog.muscles(on: "spiral")
let movers = catalog.muscles(producing: "hip.flexion")        // psoas, iliacus (prime) …
let loaded = catalog.lines(trainedBy: "hip.flexion")          // deep_front, superficial_front …
```

## Data

The JSON in `Sources/AnatomyKit/Resources` is the source of truth:

| File | Holds |
|---|---|
| `regions.json` | 7 body regions |
| `joints.json` | 20 joints, each with its DOFs; every DOF names a positive and (usually) negative direction, its plane and a typical range. Direction ID = `<joint>.<direction>` |
| `complexes.json` | 13 joint groups people name ("shoulder", "low back") |
| `muscles.json` | 75 entries (74 muscles + sacrotuberous ligament), each with the movements it produces (prime or secondary) |
| `tissues.json` | 17 connective tissues the lines run through (fascia, aponeuroses, ligaments …) |
| `bones.json` | The 206 adult bones (120 entries; bilateral bones count twice), with region, group and FMA ID where BodyParts3D's names match |
| `landmarks.json` | 64 landmarks (`<bone>.<feature>`) the lines attach to, each listing the bone IDs it sits on |
| `lines.json` | Myers' 12 lines as ordered paths: landmark → muscles/tissue → landmark …, with midline crossings marked. Line membership is derived from these paths |
| `aliases.json` | Every string torque and suit persisted before AnatomyKit → its new ID |
| `rig-mixamo.json` | Which joints each Mixamo bone drives |
| `meshes-zanatomy.json` | Muscle/tissue ID → Z-Anatomy mesh names, for lighting structures in a 3D viewer |
| `bones-zanatomy.json` | Bone → its Z-Anatomy meshes and rig bone, per side |
| `landmarks-zanatomy.json` | Landmark → rest-pose position on the Z-Anatomy model, per side (metres, +Y up, +Z anterior, +X the body's left) |
| `rig-zanatomy.json` | Same for the Z-Anatomy (Z-Biomechanics) rig's control bones, with that rig's own rotation limits |

Entries carry `source` and `reviewed`. Everything is `reviewed: false` until a
person checks it against the cited source.

## Rules

- **IDs are append-only.** Hosts persist them. To rename, add a new ID plus an
  alias. `Tests/…/Resources/ids.lock.json` enforces this; append new IDs to it.
- **Old strings are never rewritten in storage.** Resolve them on read with
  `resolve(_:from:)`. An unknown string resolves to nil; keep it, don't drop it.
- `Tests/…/LegacyFixtures.swift` freezes every string the apps have shipped.
  Append when an app ships a new one.
