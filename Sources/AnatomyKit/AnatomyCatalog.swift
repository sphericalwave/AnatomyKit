//
//  AnatomyCatalog.swift
//  AnatomyKit
//
//  The whole model, loaded once from the bundled JSON. `standard` is the
//  shared suite vocabulary; `init(bundle:)` exists so tests can load the same
//  files and fail with a message instead of a crash.
//

import Foundation

public struct AnatomyCatalog: Sendable {
    public let regions: [Region]
    public let joints: [Joint]
    public let complexes: [JointComplex]
    public let muscles: [Muscle]
    public let lines: [TrainLine]
    public let rigBindings: [RigBinding]
    let aliases: [LegacyNamespace: [String: String]]

    private let jointByID: [JointID: Joint]
    private let directionByID: [DirectionID: Direction]
    private let complexByID: [JointComplexID: JointComplex]
    private let muscleByID: [MuscleID: Muscle]
    private let lineByID: [TrainLineID: TrainLine]

    /// Tests validate every file, so a load failure here is a packaging bug.
    public static let standard: AnatomyCatalog = {
        do { return try AnatomyCatalog(bundle: .module) } catch {
            fatalError("AnatomyKit catalog failed to load: \(error)")
        }
    }()

    /// The bundle holding the catalog JSON, for loading with `init(bundle:)`.
    static let resourceBundle = Bundle.module

    public init(bundle: Bundle) throws {
        func load<T: Decodable>(_ name: String) throws -> T {
            guard let url = bundle.url(forResource: name, withExtension: "json") else {
                throw CocoaError(.fileNoSuchFile, userInfo: [NSFilePathErrorKey: "\(name).json"])
            }
            return try JSONDecoder().decode(T.self, from: Data(contentsOf: url))
        }
        regions = try load("regions")
        joints = try load("joints")
        complexes = try load("complexes")
        muscles = try load("muscles")
        lines = try load("lines")
        rigBindings = [try load("rig-mixamo")]
        let rawAliases: [String: [String: String]] = try load("aliases")
        aliases = Dictionary(uniqueKeysWithValues: rawAliases.compactMap { key, value in
            LegacyNamespace(rawValue: key).map { ($0, value) }
        })

        jointByID = Dictionary(joints.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        directionByID = Dictionary(joints.flatMap(\.directions).map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        complexByID = Dictionary(complexes.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        muscleByID = Dictionary(muscles.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        lineByID = Dictionary(lines.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    }

    public var directions: [Direction] { joints.flatMap(\.directions) }

    public func joint(_ id: JointID) -> Joint? { jointByID[id] }
    public func direction(_ id: DirectionID) -> Direction? { directionByID[id] }
    public func complex(_ id: JointComplexID) -> JointComplex? { complexByID[id] }
    public func muscle(_ id: MuscleID) -> Muscle? { muscleByID[id] }
    public func line(_ id: TrainLineID) -> TrainLine? { lineByID[id] }

    public func muscles(on line: TrainLineID) -> [Muscle] {
        muscles.filter { $0.lines.contains(line) }
    }

    public func rigBinding(_ rig: String) -> RigBinding? {
        rigBindings.first { $0.rig == rig }
    }
}
