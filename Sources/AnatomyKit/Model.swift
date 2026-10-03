//
//  Model.swift
//  AnatomyKit
//
//  The catalog's value types. Everything here is decoded from the JSON in
//  Resources; the JSON is the source of truth (ANATOMY_MODEL_PLAN.md §5).
//
//  `source` and `reviewed` travel with each drafted entry: a row is only
//  `reviewed` once a person has checked it against the cited source.
//

import Foundation

/// A body area, for grouping lists and choosing what to load.
public struct Region: Identifiable, Hashable, Sendable, Codable {
    public let id: RegionID
    public let name: String
}

/// An articulation (or a group of near-identical ones, like the MCP joints of
/// fingers 2–5) and the directions it moves in.
public struct Joint: Identifiable, Hashable, Sendable, Codable {
    public let id: JointID
    public let name: String
    public let region: RegionID
    /// False for midline joints, where left or right is meaningless.
    public let bilateral: Bool
    public let dofs: [DOF]
    public let source: String
    public let reviewed: Bool

    /// Every direction this joint moves in, positive before negative per DOF.
    public var directions: [Direction] {
        dofs.flatMap { dof in
            [dof.positive, dof.negative].compactMap { $0 }.map {
                Direction(id: DirectionID("\(id.rawValue).\($0)"), joint: id, dofAxis: dof.axis, name: $0)
            }
        }
    }
}

/// One degree of freedom. A DOF moves two ways (flexion / extension) unless
/// the two ways are mirror images that a side already distinguishes — lateral
/// flexion and spinal rotation have one direction, used for both sides.
public struct DOF: Hashable, Sendable, Codable {
    public enum Plane: String, Hashable, Sendable, Codable {
        case sagittal, frontal, transverse
    }

    /// Typical range from neutral (0), per direction. Nil where a single
    /// number doesn't describe the motion (a translation not yet measured, or
    /// thumb opposition).
    public struct ROM: Hashable, Sendable, Codable {
        public enum Unit: String, Hashable, Sendable, Codable {
            case deg, mm
        }

        public let positive: Double?
        public let negative: Double?
        public let unit: Unit
        public let source: String
    }

    /// e.g. `"flexion_extension"`. Unique within its joint.
    public let axis: String
    public let positive: String
    public let negative: String?
    /// The plane the motion happens in, from anatomical position.
    public let plane: Plane
    public let rom: ROM
    /// For spinal DOFs: typical range at each motion segment, so a whole-region
    /// motion can be spread across vertebrae. Nil for other joints.
    public let segments: Segments?

    public struct Segments: Hashable, Sendable, Codable {
        public let source: String
        /// How to read `degrees` (combined both-direction range, or one side).
        public let note: String
        /// Articulation ID → degrees at that segment.
        public let degrees: [String: Double]

        /// Each segment's fraction of the region's motion, summing to 1.
        public var shares: [ArticulationID: Double] {
            let total = degrees.values.reduce(0, +)
            guard total > 0 else { return [:] }
            return Dictionary(uniqueKeysWithValues: degrees.map { (ArticulationID($0.key), $0.value / total) })
        }
    }
}

/// One way a joint moves: what torque tags an exercise with.
public struct Direction: Identifiable, Hashable, Sendable {
    public let id: DirectionID
    public let joint: JointID
    public let dofAxis: String
    /// Snake-case direction name, e.g. `"external_rotation"`.
    public let name: String

    /// "External rotation".
    public var label: String {
        let words = name.replacingOccurrences(of: "_", with: " ")
        return words.prefix(1).uppercased() + words.dropFirst()
    }
}

/// The joint a person names: "shoulder" covers the shoulder blade and the
/// glenohumeral joint. Coarse notes and logs attach here.
public struct JointComplex: Identifiable, Hashable, Sendable, Codable {
    public let id: JointComplexID
    public let name: String
    public let region: RegionID
    public let joints: [JointID]
}

public struct Muscle: Identifiable, Hashable, Sendable, Codable {
    public enum Kind: String, Hashable, Sendable, Codable {
        case muscle, ligament
    }

    /// One movement the muscle produces. `prime` movers are the main source of
    /// the motion; `secondary` ones assist.
    public struct Action: Hashable, Sendable, Codable {
        public enum Role: String, Hashable, Sendable, Codable {
            case prime, secondary
        }

        public let direction: DirectionID
        public let role: Role
    }

    /// Snake-case Latin slug; also the planned join key to mesh names.
    public let id: MuscleID
    public let name: String
    public let kind: Kind
    /// Where the bulk lies, not where it inserts.
    public let region: RegionID
    public let actions: [Action]
    public let actionSource: String?
    public let source: String
    public let reviewed: Bool
}

/// Connective tissue that isn't a muscle: fascia, aponeuroses, ligaments,
/// tendons, septa and retinacula. Myers' lines run through these between
/// muscles.
public struct Tissue: Identifiable, Hashable, Sendable, Codable {
    public enum Kind: String, Hashable, Sendable, Codable {
        case fascia, aponeurosis, ligament, tendon, septum, retinaculum
    }

    public let id: TissueID
    public let name: String
    public let kind: Kind
    public let region: RegionID
    public let source: String
    public let reviewed: Bool
}

/// One of the 206 adult bones. Bilateral bones have one entry for both sides.
public struct Bone: Identifiable, Hashable, Sendable, Codable {
    public enum Group: String, Hashable, Sendable, Codable, CaseIterable {
        case cranium, face, ossicle, hyoid, vertebra, rib, sternum
        case shoulderGirdle = "shoulder_girdle"
        case arm, carpal, metacarpal
        case phalanxHand = "phalanx_hand"
        case pelvis, leg, tarsal, metatarsal
        case phalanxFoot = "phalanx_foot"
    }

    public let id: BoneID
    public let name: String
    public let region: RegionID
    public let group: Group
    public let bilateral: Bool
    /// Foundational Model of Anatomy class, e.g. `"FMA9611"` for the femur.
    public let fmaID: String?
    public let source: String
    public let reviewed: Bool
}

/// Where bones meet. Each articulation lists the bones it joins and, if it
/// moves meaningfully, the catalog joint whose DOFs describe that motion
/// (the knee joint is the tibiofemoral and patellofemoral articulations).
public struct Articulation: Identifiable, Hashable, Sendable, Codable {
    public enum Kind: String, Hashable, Sendable, Codable {
        case hinge, pivot, condyloid, saddle, plane, bicondylar
        case ballAndSocket = "ball_and_socket"
        /// A vertebral motion segment: disc plus facet joints.
        case intervertebral
        case symphysis, suture, syndesmosis
        /// Not a true joint, but moves like one (scapulothoracic).
        case functional
    }

    public let id: ArticulationID
    public let name: String
    public let bones: [BoneID]
    public let kind: Kind
    public let joint: JointID?
    public let bilateral: Bool
    public let source: String
    public let reviewed: Bool
}

/// A named spot, e.g. `"ischium.ischial_tuberosity"`, on one or more bones
/// (`"thoracic_vertebrae.upper_spinous_processes"` spans C7–T5). Soft-tissue
/// stations like the linea alba have no bones.
public struct Landmark: Identifiable, Hashable, Sendable, Codable {
    public let id: LandmarkID
    public let name: String
    public let bones: [BoneID]
    /// True on the body's midline, where left and right meet.
    public let midline: Bool?
}

/// One of Myers' twelve myofascial lines, as ordered paths from bone landmark
/// to bone landmark. Most lines are one path; a few (Deep Front, the arm
/// lines) branch or have gaps Myers bridges through bone, so they have several.
public struct TrainLine: Identifiable, Hashable, Sendable, Codable {
    public struct Path: Hashable, Sendable, Codable {
        public let name: String
        /// Alternates landmark, tissue, landmark … starting and ending on a landmark.
        public let steps: [Step]
    }

    public enum Step: Hashable, Sendable, Codable {
        /// A bony station. `crosses` marks where the line passes the midline
        /// to the other side of the body (Spiral and Functional lines).
        case station(LandmarkID, crosses: Bool)
        /// The muscles and connective tissue spanning to the next station,
        /// as muscle or tissue IDs.
        case track([String])

        private enum CodingKeys: String, CodingKey { case at, crosses, via }

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            if let at = try c.decodeIfPresent(LandmarkID.self, forKey: .at) {
                self = .station(at, crosses: try c.decodeIfPresent(Bool.self, forKey: .crosses) ?? false)
            } else {
                self = .track(try c.decode([String].self, forKey: .via))
            }
        }

        public func encode(to encoder: Encoder) throws {
            var c = encoder.container(keyedBy: CodingKeys.self)
            switch self {
            case let .station(id, crosses):
                try c.encode(id, forKey: .at)
                if crosses { try c.encode(true, forKey: .crosses) }
            case let .track(ids):
                try c.encode(ids, forKey: .via)
            }
        }
    }

    public let id: TrainLineID
    public let name: String
    /// "SBL".
    public let shortName: String
    public let paths: [Path]
    public let source: String
    public let reviewed: Bool

    /// Every muscle or tissue ID on any path.
    public var trackIDs: Set<String> {
        Set(paths.flatMap(\.steps).flatMap { step -> [String] in
            if case let .track(ids) = step { return ids }
            return []
        })
    }
}

/// Which catalog joints a rig's bones drive, e.g. Mixamo's `LeftForeArm`
/// drives the elbow and the forearm's pronation.
public struct RigBinding: Hashable, Sendable, Codable {
    public struct Bone: Hashable, Sendable, Codable {
        public let bone: String
        /// `"left"` or `"right"`; nil for midline bones.
        public let side: String?
        public let joints: [JointID]
        /// The rig's own rotation limits per bone-local axis, in degrees.
        /// Animation constraints, not clinical range of motion.
        public let limitsDegrees: [String: [Double]]?
    }

    public let rig: String
    public let source: String
    public let bones: [Bone]
}

/// Where something sits on one specific 3D model, per side. Midline things
/// have only `midline`; bilateral ones have `left` and `right`.
public struct Sided<Value: Hashable & Sendable & Codable>: Hashable, Sendable, Codable {
    public let left: Value?
    public let right: Value?
    public let midline: Value?
}

/// A bone's meshes and driving rig bone in the Z-Anatomy model, on one side.
public struct ZAnatomyBonePart: Hashable, Sendable, Codable {
    public let meshes: [String]
    public let rigBone: String
}
