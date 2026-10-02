//
//  AnatomyID.swift
//  AnatomyKit
//
//  String IDs, typed by what they name so a joint ID can't be passed where a
//  muscle ID is expected. The raw string is what hosts persist: IDs are
//  append-only (see `ids.lock.json` in the tests). Renaming one means adding a
//  new ID and an alias from the old string, never editing it in place.
//

import Foundation

public struct AnatomyID<Kind>: RawRepresentable, Hashable, Sendable, Codable,
    ExpressibleByStringLiteral, CustomStringConvertible {
    public let rawValue: String

    public init(rawValue: String) { self.rawValue = rawValue }
    public init(_ rawValue: String) { self.rawValue = rawValue }
    public init(stringLiteral value: String) { self.rawValue = value }

    public init(from decoder: Decoder) throws {
        rawValue = try decoder.singleValueContainer().decode(String.self)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        try c.encode(rawValue)
    }

    public var description: String { rawValue }
}

public enum RegionKind {}
public enum JointKind {}
public enum DirectionKind {}
public enum JointComplexKind {}
public enum MuscleKind {}
public enum TrainLineKind {}

public typealias RegionID = AnatomyID<RegionKind>
public typealias JointID = AnatomyID<JointKind>
/// `"<joint>.<direction>"`, e.g. `"glenohumeral.external_rotation"`.
public typealias DirectionID = AnatomyID<DirectionKind>
public typealias JointComplexID = AnatomyID<JointComplexKind>
public typealias MuscleID = AnatomyID<MuscleKind>
public typealias TrainLineID = AnatomyID<TrainLineKind>
