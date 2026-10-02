//
//  LegacyID.swift
//  AnatomyKit
//
//  Strings torque and suit already persisted before AnatomyKit existed. They
//  are never rewritten in storage: hosts resolve them on read. A string with no
//  alias resolves to nil, and the host keeps it as-is rather than dropping it.
//

import Foundation

public enum LegacyNamespace: String, CaseIterable, Sendable, Codable {
    /// torque `Movement.rawValue`, e.g. `"gh.flex"` → `"glenohumeral.flexion"`.
    case torqueMovement
    /// SuitKit `Joint.rawValue`, e.g. `"thoracicSpine"` → complex `"upper_back"`.
    case suitJoint
    /// SuitKit `AnatomyTrainLine.rawValue`, e.g. `"superficialBack"`.
    case suitTrainLine
    /// SuitKit `AnatomyRegion.rawValue`, e.g. `"torso"` → `"trunk"`.
    case suitRegion
    /// SuitKit `AnatomyNode.nodeName`; unchanged in the new scheme.
    case suitMuscle
}

extension AnatomyCatalog {
    /// The current ID for a legacy string, or nil if this build doesn't know it.
    public func resolve(_ legacy: String, from namespace: LegacyNamespace) -> String? {
        aliases[namespace]?[legacy]
    }

    public func direction(forTorqueMovement raw: String) -> Direction? {
        resolve(raw, from: .torqueMovement).flatMap { direction(DirectionID($0)) }
    }

    public func complex(forSuitJoint raw: String) -> JointComplex? {
        resolve(raw, from: .suitJoint).flatMap { complex(JointComplexID($0)) }
    }
}
