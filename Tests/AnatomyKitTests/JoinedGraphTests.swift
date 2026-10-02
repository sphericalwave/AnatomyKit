//
//  JoinedGraphTests.swift
//  AnatomyKitTests
//
//  P1: ranges, muscle actions and ordered line paths, and the queries that
//  join them (movement → muscles → lines).
//

import XCTest
@testable import AnatomyKit

final class JoinedGraphTests: XCTestCase {
    private let catalog = AnatomyCatalog.standard

    // MARK: Ranges

    func testEveryDOFHasASourcedRangeForEachDirection() {
        for joint in catalog.joints {
            for dof in joint.dofs {
                XCTAssertFalse(dof.rom.source.isEmpty, "\(joint.id).\(dof.axis) has no ROM source")
                if dof.negative == nil {
                    XCTAssertNil(dof.rom.negative, "\(joint.id).\(dof.axis) has a negative range but one direction")
                }
                for value in [dof.rom.positive, dof.rom.negative].compactMap({ $0 }) {
                    XCTAssertTrue((0...180).contains(value), "\(joint.id).\(dof.axis) range \(value) out of bounds")
                }
            }
        }
    }

    func testKneeRange() {
        let dof = catalog.joint("knee")?.dofs.first { $0.axis == "flexion_extension" }
        XCTAssertEqual(dof?.rom.positive, 135)
        XCTAssertEqual(dof?.plane, .sagittal)
    }

    // MARK: Actions

    func testEveryActionNamesARealDirectionOnce() {
        for muscle in catalog.muscles {
            for action in muscle.actions {
                XCTAssertNotNil(catalog.direction(action.direction), "\(muscle.id) → unknown direction \(action.direction)")
            }
            let dirs = muscle.actions.map(\.direction)
            XCTAssertEqual(Set(dirs).count, dirs.count, "\(muscle.id) lists a direction twice")
            if !muscle.actions.isEmpty { XCTAssertNotNil(muscle.actionSource, "\(muscle.id) actions have no source") }
        }
    }

    func testPrimeMoversComeFirst() {
        let movers = catalog.muscles(producing: "hip.flexion")
        XCTAssertEqual(movers.first?.role, .prime)
        XCTAssertTrue(movers.contains { $0.muscle.id == "psoas_major" && $0.role == .prime })
        XCTAssertTrue(movers.contains { $0.muscle.id == "rectus_femoris" && $0.role == .secondary })
    }

    // MARK: Line paths

    func testPathsAlternateStationsAndTracksAndResolve() {
        for line in catalog.lines {
            XCTAssertFalse(line.paths.isEmpty, "\(line.id) has no path")
            for path in line.paths {
                let where_ = "\(line.id)/\(path.name)"
                XCTAssertGreaterThanOrEqual(path.steps.count, 3, "\(where_) is too short")
                for (i, step) in path.steps.enumerated() {
                    switch step {
                    case let .station(id, _):
                        XCTAssertTrue(i.isMultiple(of: 2), "\(where_): station at odd step \(i)")
                        XCTAssertNotNil(catalog.landmark(id), "\(where_): unknown landmark \(id)")
                    case let .track(ids):
                        XCTAssertFalse(i.isMultiple(of: 2), "\(where_): track at even step \(i)")
                        XCTAssertFalse(ids.isEmpty, "\(where_): empty track at step \(i)")
                        for id in ids {
                            let known = catalog.muscle(MuscleID(id)) != nil || catalog.tissue(TissueID(id)) != nil
                            XCTAssertTrue(known, "\(where_): unknown muscle or tissue \(id)")
                        }
                    }
                }
                XCTAssertTrue(path.steps.count % 2 == 1, "\(where_) doesn't end on a station")
            }
        }
    }

    func testOnlyMidlineStationsCross() {
        for line in catalog.lines {
            for case let .station(id, true) in line.paths.flatMap(\.steps) {
                XCTAssertEqual(catalog.landmark(id)?.midline, true, "\(line.id) crosses at off-midline \(id)")
            }
        }
    }

    /// The Spiral Line wraps the body: it crosses at the upper back and again
    /// at the belly, so it ends on the side it started.
    func testSpiralLineCrossesTwiceAndReturns() throws {
        let spiral = try XCTUnwrap(catalog.line("spiral"))
        let crossings = spiral.paths.flatMap(\.steps).filter {
            if case .station(_, true) = $0 { return true }
            return false
        }
        XCTAssertEqual(crossings.count, 2)
        let steps = try XCTUnwrap(spiral.paths.first?.steps)
        guard case let .station(first, _) = steps.first, case let .station(last, _) = steps.last else {
            return XCTFail("spiral doesn't start and end on stations")
        }
        XCTAssertEqual(first, last, "spiral should close its loop at the occiput")
    }

    func testFunctionalLinesCrossOnce() {
        for id: TrainLineID in ["back_functional", "front_functional"] {
            let n = catalog.line(id)?.paths.flatMap(\.steps).filter {
                if case .station(_, true) = $0 { return true }
                return false
            }.count
            XCTAssertEqual(n, 1, "\(id) should cross the midline once")
        }
        XCTAssertEqual(catalog.line("ipsilateral_functional")?.paths.flatMap(\.steps).contains {
            if case .station(_, true) = $0 { return true }
            return false
        }, false)
    }

    // MARK: Joins

    func testHipFlexionLoadsDeepAndSuperficialFrontLines() {
        let lines = Set(catalog.lines(trainedBy: "hip.flexion").map(\.id))
        XCTAssertTrue(lines.isSuperset(of: ["deep_front", "superficial_front"]), "got \(lines)")
    }

    func testTorqueTagReachesLinesThroughAliases() throws {
        let dir = try XCTUnwrap(catalog.direction(forTorqueMovement: "ankle.plantarflex"))
        XCTAssertTrue(catalog.lines(trainedBy: dir.id).contains { $0.id == "superficial_back" })
    }

    func testSpiralMembers() {
        let ids = Set(catalog.muscles(on: "spiral").map(\.id.rawValue))
        XCTAssertTrue(ids.isSuperset(of: ["splenius_capitis", "rhomboid_major", "serratus_anterior", "external_oblique",
                                          "internal_oblique", "tensor_fasciae_latae", "tibialis_anterior",
                                          "fibularis_longus", "biceps_femoris", "erector_spinae"]))
        XCTAssertTrue(catalog.lines(through: "iliotibial_tract").contains { $0.id == "spiral" })
    }

    func testRigBindingsResolve() {
        XCTAssertNotNil(catalog.rigBinding("mixamo"))
        let knee = catalog.rigBinding("zanatomy")?.bones.first { $0.bone == "LeftLeg" }
        XCTAssertEqual(knee?.joints, ["knee"])
        XCTAssertEqual(knee?.limitsDegrees?["x"], [-165, 0])
    }

    // MARK: Meshes

    /// Every structure a line runs through has a Z-Anatomy mesh to light,
    /// except the two Z-Anatomy doesn't model.
    func testLineTracksHaveZAnatomyMeshes() {
        let noMesh: Set<String> = ["sternochondral_fascia", "patellar_ligament"]
        for id in catalog.lines.reduce(into: Set<String>(), { $0.formUnion($1.trackIDs) }) where !noMesh.contains(id) {
            XCTAssertFalse(catalog.zAnatomyMeshes[id, default: []].isEmpty, "\(id) has no Z-Anatomy mesh")
        }
        for id in catalog.zAnatomyMeshes.keys {
            let known = catalog.muscle(MuscleID(id)) != nil || catalog.tissue(TissueID(id)) != nil
            XCTAssertTrue(known, "mesh table names unknown structure \(id)")
        }
    }
}
