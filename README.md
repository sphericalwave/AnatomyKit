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
```

## Data

The JSON in `Sources/AnatomyKit/Resources` is the source of truth:

| File | Holds |
|---|---|
| `regions.json` | 7 body regions |
| `joints.json` | 20 joints, each with its DOFs; every DOF names a positive and (usually) negative direction. Direction ID = `<joint>.<direction>` |
| `complexes.json` | 13 joint groups people name ("shoulder", "low back") |
| `muscles.json` | 70 entries (69 muscles + sacrotuberous ligament) with line membership |
| `lines.json` | Myers' 12 lines |
| `aliases.json` | Every string torque and suit persisted before AnatomyKit → its new ID |
| `rig-mixamo.json` | Which joints each Mixamo bone drives |

Entries carry `source` and `reviewed`. Everything is `reviewed: false` until a
person checks it against the cited source.

## Rules

- **IDs are append-only.** Hosts persist them. To rename, add a new ID plus an
  alias. `Tests/…/Resources/ids.lock.json` enforces this; append new IDs to it.
- **Old strings are never rewritten in storage.** Resolve them on read with
  `resolve(_:from:)`. An unknown string resolves to nil; keep it, don't drop it.
- `Tests/…/LegacyFixtures.swift` freezes every string the apps have shipped.
  Append when an app ships a new one.
