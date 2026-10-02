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
    public let tissues: [Tissue]
    public let landmarks: [Landmark]
    public let rigBindings: [RigBinding]
    /// Muscle or tissue ID → Z-Anatomy mesh base names (append `.l` / `.r`
    /// for a side; midline meshes have no suffix).
    public let zAnatomyMeshes: [String: [String]]
    let aliases: [LegacyNamespace: [String: String]]

    private let jointByID: [JointID: Joint]
    private let directionByID: [DirectionID: Direction]
    private let complexByID: [JointComplexID: JointComplex]
    private let muscleByID: [MuscleID: Muscle]
    private let lineByID: [TrainLineID: TrainLine]
    private let tissueByID: [TissueID: Tissue]
    private let landmarkByID: [LandmarkID: Landmark]

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
        tissues = try load("tissues")
        landmarks = try load("landmarks")
        rigBindings = [try load("rig-mixamo"), try load("rig-zanatomy")]
        struct MeshTable: Decodable { let meshes: [String: [String]] }
        zAnatomyMeshes = (try load("meshes-zanatomy") as MeshTable).meshes
        let rawAliases: [String: [String: String]] = try load("aliases")
        aliases = Dictionary(uniqueKeysWithValues: rawAliases.compactMap { key, value in
            LegacyNamespace(rawValue: key).map { ($0, value) }
        })

        jointByID = Dictionary(joints.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        directionByID = Dictionary(joints.flatMap(\.directions).map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        complexByID = Dictionary(complexes.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        muscleByID = Dictionary(muscles.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        lineByID = Dictionary(lines.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        tissueByID = Dictionary(tissues.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        landmarkByID = Dictionary(landmarks.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    }

    public var directions: [Direction] { joints.flatMap(\.directions) }

    public func joint(_ id: JointID) -> Joint? { jointByID[id] }
    public func direction(_ id: DirectionID) -> Direction? { directionByID[id] }
    public func complex(_ id: JointComplexID) -> JointComplex? { complexByID[id] }
    public func muscle(_ id: MuscleID) -> Muscle? { muscleByID[id] }
    public func line(_ id: TrainLineID) -> TrainLine? { lineByID[id] }
    public func tissue(_ id: TissueID) -> Tissue? { tissueByID[id] }
    public func landmark(_ id: LandmarkID) -> Landmark? { landmarkByID[id] }

    // MARK: - Joins (plan §2.2)

    /// Muscles on a line's tracks, in catalog order.
    public func muscles(on line: TrainLineID) -> [Muscle] {
        guard let ids = self.line(line)?.trackIDs else { return [] }
        return muscles.filter { ids.contains($0.id.rawValue) }
    }

    /// Lines whose tracks include this muscle or tissue ID.
    public func lines(through structure: String) -> [TrainLine] {
        lines.filter { $0.trackIDs.contains(structure) }
    }

    /// Muscles that produce a movement, prime movers first.
    public func muscles(producing direction: DirectionID) -> [(muscle: Muscle, role: Muscle.Action.Role)] {
        let hits = muscles.compactMap { m in
            m.actions.first { $0.direction == direction }.map { (muscle: m, role: $0.role) }
        }
        return hits.filter { $0.role == .prime } + hits.filter { $0.role == .secondary }
    }

    /// Lines loaded by a movement: every line carrying a muscle that produces it.
    /// "hip.flexion" → Deep Front (psoas, iliacus), Superficial Front (rectus femoris), …
    public func lines(trainedBy direction: DirectionID) -> [TrainLine] {
        let ids = Set(muscles(producing: direction).map(\.muscle.id.rawValue))
        return lines.filter { !$0.trackIDs.isDisjoint(with: ids) }
    }

    public func rigBinding(_ rig: String) -> RigBinding? {
        rigBindings.first { $0.rig == rig }
    }
}
