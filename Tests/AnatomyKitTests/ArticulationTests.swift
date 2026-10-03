//
//  ArticulationTests.swift
//  AnatomyKitTests
//
//  P2: where bones meet, which catalog joint each articulation moves as, and
//  how spinal motion spreads across segments.
//

import XCTest
@testable import AnatomyKit

final class ArticulationTests: XCTestCase {
    private let catalog = AnatomyCatalog.standard

    func testArticulationsJoinRealBonesAndJoints() {
        XCTAssertEqual(Set(catalog.articulations.map(\.id)).count, catalog.articulations.count, "duplicate articulation IDs")
        for a in catalog.articulations {
            for b in a.bones { XCTAssertNotNil(catalog.bone(b), "\(a.id) → unknown bone \(b)") }
            // The pubic symphysis joins the left and right hip bones: one bone ID.
            XCTAssertGreaterThanOrEqual(a.bones.count, a.id == "pubic_symphysis" ? 1 : 2, "\(a.id) joins too few bones")
            if let j = a.joint { XCTAssertNotNil(catalog.joint(j), "\(a.id) → unknown joint \(j)") }
        }
    }

    func testEveryJointIsMadeOfArticulations() {
        for joint in catalog.joints {
            XCTAssertFalse(catalog.articulations(of: joint.id).isEmpty, "\(joint.id) has no articulations")
        }
        XCTAssertEqual(Set(catalog.articulations(of: "knee").map(\.id)), ["tibiofemoral", "patellofemoral"])
    }

    func testSpineHasAMotionSegmentAtEveryLevel() {
        let segments = catalog.articulations.filter { $0.kind == .intervertebral }
        XCTAssertEqual(segments.count, 23, "C2–C3 through L5–S1")
    }

    func testSpinalDOFsSpreadAcrossTheirOwnSegments() throws {
        for id: JointID in ["cervical_spine", "thoracic_spine", "lumbar_spine"] {
            let joint = try XCTUnwrap(catalog.joint(id))
            let own = Set(catalog.articulations(of: id).map(\.id))
            for dof in joint.dofs where dof.axis != "protraction_retraction" {
                let segments = try XCTUnwrap(dof.segments, "\(id).\(dof.axis) has no segments")
                XCTAssertEqual(Set(segments.shares.keys), own, "\(id).\(dof.axis) segments don't match its articulations")
                XCTAssertEqual(segments.shares.values.reduce(0, +), 1, accuracy: 1e-9)
            }
        }
    }

    /// Half of neck rotation happens at C1–C2.
    func testAtlantoAxialCarriesMostNeckRotation() throws {
        let rotation = try XCTUnwrap(catalog.joint("cervical_spine")?.dofs.first { $0.axis == "axial_rotation" })
        let share = try XCTUnwrap(rotation.segments?.shares["atlanto_axial"])
        XCTAssertGreaterThan(share, 0.4)
    }
}
