//
//  LegacyAliasTests.swift
//  AnatomyKitTests
//
//  No saved data may stop resolving: every string in LegacyFixtures must map
//  to something that exists in the catalog.
//

import XCTest
@testable import AnatomyKit

final class LegacyAliasTests: XCTestCase {
    private let catalog = AnatomyCatalog.standard

    func testEveryTorqueMovementResolvesToADirection() {
        for raw in LegacyFixtures.torqueMovements {
            XCTAssertNotNil(catalog.direction(forTorqueMovement: raw), "torque \"\(raw)\" doesn't resolve")
        }
    }

    func testTorqueMovementsStayDistinct() {
        let resolved = LegacyFixtures.torqueMovements.compactMap { catalog.resolve($0, from: .torqueMovement) }
        XCTAssertEqual(Set(resolved).count, LegacyFixtures.torqueMovements.count,
                       "two torque movements now share one direction, so tags would merge")
    }

    func testEverySuitJointResolvesToAComplex() {
        for raw in LegacyFixtures.suitJoints {
            XCTAssertNotNil(catalog.complex(forSuitJoint: raw), "suit joint \"\(raw)\" doesn't resolve")
        }
    }

    func testEverySuitTrainLineResolves() {
        for raw in LegacyFixtures.suitTrainLines {
            let id = catalog.resolve(raw, from: .suitTrainLine)
            XCTAssertNotNil(id.flatMap { catalog.line(TrainLineID($0)) }, "suit line \"\(raw)\" doesn't resolve")
        }
    }

    func testEverySuitRegionResolves() {
        let regions = Set(catalog.regions.map(\.id.rawValue))
        for raw in LegacyFixtures.suitRegions {
            let id = catalog.resolve(raw, from: .suitRegion)
            XCTAssertTrue(id.map(regions.contains) ?? false, "suit region \"\(raw)\" doesn't resolve")
        }
    }

    func testEverySuitMuscleResolves() {
        for raw in LegacyFixtures.suitMuscles {
            let id = catalog.resolve(raw, from: .suitMuscle)
            XCTAssertNotNil(id.flatMap { catalog.muscle(MuscleID($0)) }, "suit muscle \"\(raw)\" doesn't resolve")
        }
    }

    func testUnknownStringResolvesToNil() {
        XCTAssertNil(catalog.resolve("hip.levitate", from: .torqueMovement))
    }
}
