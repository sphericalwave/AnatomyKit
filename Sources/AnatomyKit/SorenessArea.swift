//
//  SorenessArea.swift
//  AnatomyKit
//
//  The words people use for where they're sore ("glutes", "low back") as
//  weighted sets of catalog muscles, so a soreness note can be matched against
//  the muscles a set loaded. Weights say how much of the area each muscle makes
//  up, not how likely it is to be sore.
//

import Foundation

public enum SorenessAreaKind {}
public typealias SorenessAreaID = AnatomyID<SorenessAreaKind>

public struct SorenessArea: Identifiable, Hashable, Sendable, Codable {
    public struct Member: Hashable, Sendable, Codable {
        public let muscle: MuscleID
        public let weight: Double
    }

    public let id: SorenessAreaID
    public let name: String
    public let muscles: [Member]
    /// SuitKit `Joint` raw values that mean this area in a note ("lumbarSpine").
    public let suitJoints: [String]?
}

extension AnatomyCatalog {
    public var sorenessAreas: [SorenessArea] { Self.areaTable }

    public func sorenessArea(_ id: SorenessAreaID) -> SorenessArea? {
        Self.areaTable.first { $0.id == id }
    }

    /// The area a suit note's joint stands for, if any ("lumbarSpine" → low back).
    public func sorenessArea(forSuitJoint raw: String) -> SorenessArea? {
        Self.areaTable.first { $0.suitJoints?.contains(raw) == true }
    }

    private struct AreaFile: Decodable { let areas: [SorenessArea] }

    private static let areaTable: [SorenessArea] = {
        guard let url = resourceBundle.url(forResource: "soreness-areas", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let file = try? JSONDecoder().decode(AreaFile.self, from: data) else { return [] }
        return file.areas
    }()
}
