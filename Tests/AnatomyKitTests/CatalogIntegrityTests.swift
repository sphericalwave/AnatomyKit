//
//  CatalogIntegrityTests.swift
//  AnatomyKitTests
//
//  The JSON is hand-edited, so these are the checks a schema would give us:
//  unique IDs, and every reference pointing at something that exists.
//

import XCTest
@testable import AnatomyKit

final class CatalogIntegrityTests: XCTestCase {
    private var catalog: AnatomyCatalog!

    override func setUpWithError() throws {
        catalog = try AnatomyCatalog(bundle: AnatomyCatalog.resourceBundle)
    }

    func testStandardCatalogLoads() {
        XCTAssertFalse(AnatomyCatalog.standard.joints.isEmpty)
    }

    func testIDsAreUnique() {
        assertUnique(catalog.regions.map(\.id.rawValue), "region")
        assertUnique(catalog.joints.map(\.id.rawValue), "joint")
        assertUnique(catalog.directions.map(\.id.rawValue), "direction")
        assertUnique(catalog.complexes.map(\.id.rawValue), "complex")
        assertUnique(catalog.muscles.map(\.id.rawValue), "muscle")
        assertUnique(catalog.lines.map(\.id.rawValue), "line")
    }

    func testDOFAxesAreUniqueWithinEachJoint() {
        for joint in catalog.joints {
            assertUnique(joint.dofs.map(\.axis), "DOF axis in \(joint.id)")
        }
    }

    func testIDsAreSnakeCase() throws {
        let slug = try Regex("^[a-z][a-z0-9_]*$")
        let directionID = try Regex("^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$")
        let all = catalog.regions.map(\.id.rawValue) + catalog.joints.map(\.id.rawValue)
            + catalog.complexes.map(\.id.rawValue) + catalog.muscles.map(\.id.rawValue)
            + catalog.lines.map(\.id.rawValue)
        for id in all { XCTAssertNotNil(id.wholeMatch(of: slug), "\(id) is not snake_case") }
        for d in catalog.directions {
            XCTAssertNotNil(d.id.rawValue.wholeMatch(of: directionID),
                            "\(d.id) is not <joint>.<direction>")
        }
    }

    func testEveryJointMovesAndHasASource() {
        for joint in catalog.joints {
            XCTAssertFalse(joint.dofs.isEmpty, "\(joint.id) has no DOF")
            XCTAssertFalse(joint.source.isEmpty, "\(joint.id) has no source")
        }
    }

    func testReferencesResolve() {
        let regions = Set(catalog.regions.map(\.id))
        for joint in catalog.joints {
            XCTAssertTrue(regions.contains(joint.region), "\(joint.id) → unknown region \(joint.region)")
        }
        for complex in catalog.complexes {
            XCTAssertTrue(regions.contains(complex.region), "\(complex.id) → unknown region")
            XCTAssertFalse(complex.joints.isEmpty, "\(complex.id) has no joints")
            for j in complex.joints { XCTAssertNotNil(catalog.joint(j), "\(complex.id) → unknown joint \(j)") }
        }
        for muscle in catalog.muscles {
            XCTAssertTrue(regions.contains(muscle.region), "\(muscle.id) → unknown region")
            XCTAssertFalse(muscle.source.isEmpty, "\(muscle.id) has no source")
        }
        for tissue in catalog.tissues {
            XCTAssertTrue(regions.contains(tissue.region), "\(tissue.id) → unknown region")
        }
        for binding in catalog.rigBindings {
            for bone in binding.bones {
                for j in bone.joints { XCTAssertNotNil(catalog.joint(j), "\(bone.bone) → unknown joint \(j)") }
            }
        }
    }

    func testEveryJointBelongsToAComplex() {
        let covered = Set(catalog.complexes.flatMap(\.joints))
        for joint in catalog.joints {
            XCTAssertTrue(covered.contains(joint.id), "\(joint.id) is in no complex")
        }
    }

    func testEveryLineHasMembers() {
        for line in catalog.lines {
            XCTAssertFalse(catalog.muscles(on: line.id).isEmpty, "\(line.id) has no muscles")
        }
    }

    func testDirectionLabel() {
        XCTAssertEqual(catalog.direction("glenohumeral.external_rotation")?.label, "External rotation")
    }

    private func assertUnique(_ ids: [String], _ what: String, file: StaticString = #filePath, line: UInt = #line) {
        let dupes = Dictionary(grouping: ids, by: { $0 }).filter { $1.count > 1 }.keys
        XCTAssertTrue(dupes.isEmpty, "duplicate \(what) IDs: \(dupes.sorted())", file: file, line: line)
    }
}
