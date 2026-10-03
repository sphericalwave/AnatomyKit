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
    public let bones: [Bone]
    public let articulations: [Articulation]
    public let rigBindings: [RigBinding]
    /// Muscle or tissue ID → Z-Anatomy mesh base names (append `.l` / `.r`
    /// for a side; midline meshes have no suffix).
    public let zAnatomyMeshes: [String: [String]]
    /// Bone → its Z-Anatomy meshes and rig bone, per side.
    public let zAnatomyBones: [BoneID: Sided<ZAnatomyBonePart>]
    /// Landmark → rest-pose position `[x, y, z]` on the Z-Anatomy model, in
    /// metres: +Y up, +Z anterior, +X the body's left.
    public let zAnatomyLandmarks: [LandmarkID: Sided<[Double]>]
    let aliases: [LegacyNamespace: [String: String]]

    private let jointByID: [JointID: Joint]
    private let directionByID: [DirectionID: Direction]
    private let complexByID: [JointComplexID: JointComplex]
    private let muscleByID: [MuscleID: Muscle]
    private let lineByID: [TrainLineID: TrainLine]
    private let tissueByID: [TissueID: Tissue]
    private let landmarkByID: [LandmarkID: Landmark]
    private let boneByID: [BoneID: Bone]
    private let articulationByID: [ArticulationID: Articulation]

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
        bones = try load("bones")
        articulations = try load("articulations")
        rigBindings = [try load("rig-mixamo"), try load("rig-zanatomy")]
        struct MeshTable: Decodable { let meshes: [String: [String]] }
        zAnatomyMeshes = (try load("meshes-zanatomy") as MeshTable).meshes
        struct BoneTable: Decodable { let bones: [String: Sided<ZAnatomyBonePart>] }
        zAnatomyBones = Dictionary(uniqueKeysWithValues: (try load("bones-zanatomy") as BoneTable).bones.map { (BoneID($0.key), $0.value) })
        struct LandmarkTable: Decodable { let landmarks: [String: Sided<[Double]>] }
        zAnatomyLandmarks = Dictionary(uniqueKeysWithValues: (try load("landmarks-zanatomy") as LandmarkTable).landmarks.map { (LandmarkID($0.key), $0.value) })
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
        boneByID = Dictionary(bones.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        articulationByID = Dictionary(articulations.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    }

    public var directions: [Direction] { joints.flatMap(\.directions) }

    public func joint(_ id: JointID) -> Joint? { jointByID[id] }
    public func direction(_ id: DirectionID) -> Direction? { directionByID[id] }
    public func complex(_ id: JointComplexID) -> JointComplex? { complexByID[id] }
    public func muscle(_ id: MuscleID) -> Muscle? { muscleByID[id] }
    public func line(_ id: TrainLineID) -> TrainLine? { lineByID[id] }
    public func tissue(_ id: TissueID) -> Tissue? { tissueByID[id] }
    public func landmark(_ id: LandmarkID) -> Landmark? { landmarkByID[id] }
    public func bone(_ id: BoneID) -> Bone? { boneByID[id] }
    public func articulation(_ id: ArticulationID) -> Articulation? { articulationByID[id] }

    /// The articulations whose motion a joint's DOFs describe.
    public func articulations(of joint: JointID) -> [Articulation] {
        articulations.filter { $0.joint == joint }
    }

    /// Adult bone count: bilateral bones count twice. 206 for a complete catalog.
    public var boneCount: Int { bones.reduce(0) { $0 + ($1.bilateral ? 2 : 1) } }

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
