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
    /// e.g. `"flexion_extension"`. Unique within its joint.
    public let axis: String
    public let positive: String
    public let negative: String?
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

    /// Snake-case Latin slug; also the planned join key to mesh names.
    public let id: MuscleID
    public let name: String
    public let kind: Kind
    /// Where the bulk lies, not where it inserts.
    public let region: RegionID
    /// Myers line membership. Many-to-many, and interpretive.
    public let lines: [TrainLineID]
    public let source: String
    public let reviewed: Bool
}

/// One of Myers' twelve myofascial lines.
public struct TrainLine: Identifiable, Hashable, Sendable, Codable {
    public let id: TrainLineID
    public let name: String
    /// "SBL".
    public let shortName: String
}

/// Which catalog joints a rig's bones drive, e.g. Mixamo's `LeftForeArm`
/// drives the elbow and the forearm's pronation.
public struct RigBinding: Hashable, Sendable, Codable {
    public struct Bone: Hashable, Sendable, Codable {
        public let bone: String
        /// `"left"` or `"right"`; nil for midline bones.
        public let side: String?
        public let joints: [JointID]
    }

    public let rig: String
    public let source: String
    public let bones: [Bone]
}
