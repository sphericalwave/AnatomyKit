//
//  SorenessAreaTests.swift
//  AnatomyKitTests
//

import XCTest
@testable import AnatomyKit

final class SorenessAreaTests: XCTestCase {
    private let catalog = AnatomyCatalog.standard

    func testAreasNameRealMuscles() {
        XCTAssertFalse(catalog.sorenessAreas.isEmpty)
        for area in catalog.sorenessAreas {
            XCTAssertFalse(area.muscles.isEmpty, "\(area.id) has no muscles")
            for m in area.muscles {
                XCTAssertNotNil(catalog.muscle(m.muscle), "\(area.id) → unknown muscle \(m.muscle)")
                XCTAssertTrue((0...1).contains(m.weight), "\(area.id) weight out of range")
            }
        }
    }

    func testSuitJointsMapToAreas() {
        XCTAssertEqual(catalog.sorenessArea(forSuitJoint: "lumbarSpine")?.id, "low_back")
        XCTAssertEqual(catalog.sorenessArea(forSuitJoint: "hip")?.id, "glutes")
        for raw in LegacyFixtures.suitJoints where raw != "jaw" {
            XCTAssertNotNil(catalog.sorenessArea(forSuitJoint: raw), "suit joint \(raw) has no soreness area")
        }
    }

    func testLowBackIsBackMusclesNotAbs() throws {
        let ids = Set(try XCTUnwrap(catalog.sorenessArea("low_back")).muscles.map(\.muscle))
        XCTAssertTrue(ids.isSuperset(of: ["erector_spinae", "quadratus_lumborum", "multifidus"]))
        XCTAssertFalse(ids.contains("rectus_abdominis"))
    }
}
