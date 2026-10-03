//
//  BoneCatalogTests.swift
//  AnatomyKitTests
//
//  P2: the 206 adult bones, the landmarks on them, and where both sit on the
//  Z-Anatomy model.
//

import XCTest
@testable import AnatomyKit

final class BoneCatalogTests: XCTestCase {
    private let catalog = AnatomyCatalog.standard

    func testAdultSkeletonHas206Bones() {
        XCTAssertEqual(catalog.boneCount, 206)
    }

    func testGroupCounts() {
        func count(_ group: Bone.Group) -> Int {
            catalog.bones.filter { $0.group == group }.reduce(0) { $0 + ($1.bilateral ? 2 : 1) }
        }
        XCTAssertEqual(count(.cranium) + count(.face), 22, "skull")
        XCTAssertEqual(count(.ossicle), 6)
        XCTAssertEqual(count(.vertebra), 26)
        XCTAssertEqual(count(.rib), 24)
        XCTAssertEqual(count(.carpal) + count(.metacarpal) + count(.phalanxHand), 54, "two hands")
        XCTAssertEqual(count(.tarsal) + count(.metatarsal) + count(.phalanxFoot), 52, "two feet")
    }

    func testBonesAreUniqueAndInRealRegions() throws {
        let fmaPattern = try Regex("FMA[0-9]+")
        let ids = catalog.bones.map(\.id)
        XCTAssertEqual(Set(ids).count, ids.count)
        let regions = Set(catalog.regions.map(\.id))
        for bone in catalog.bones {
            XCTAssertTrue(regions.contains(bone.region), "\(bone.id) → unknown region")
            if let fma = bone.fmaID { XCTAssertNotNil(fma.wholeMatch(of: fmaPattern), "\(bone.id) bad FMA ID \(fma)") }
        }
    }

    func testEveryBoneHasZAnatomyMeshesOnItsSides() {
        for bone in catalog.bones {
            let parts = catalog.zAnatomyBones[bone.id]
            if bone.bilateral {
                XCTAssertFalse(parts?.left?.meshes.isEmpty ?? true, "\(bone.id) has no left mesh")
                XCTAssertFalse(parts?.right?.meshes.isEmpty ?? true, "\(bone.id) has no right mesh")
            } else {
                XCTAssertFalse(parts?.midline?.meshes.isEmpty ?? true, "\(bone.id) has no midline mesh")
            }
        }
    }

    func testLandmarksSitOnRealBonesAndHavePositions() {
        for landmark in catalog.landmarks {
            for id in landmark.bones { XCTAssertNotNil(catalog.bone(id), "\(landmark.id) → unknown bone \(id)") }
            let pos = catalog.zAnatomyLandmarks[landmark.id]
            if landmark.midline == true {
                XCTAssertEqual(pos?.midline?.count, 3, "\(landmark.id) has no midline position")
            } else {
                XCTAssertEqual(pos?.left?.count, 3, "\(landmark.id) has no left position")
                XCTAssertEqual(pos?.right?.count, 3, "\(landmark.id) has no right position")
            }
        }
        XCTAssertEqual(catalog.landmark("linea_alba")?.bones, [], "the linea alba is soft tissue")
    }

    /// Left positions are on the body's left (+X) and mirror the right ones.
    func testLandmarkSidesMirror() throws {
        let asis = try XCTUnwrap(catalog.zAnatomyLandmarks["ilium.asis"])
        let l = try XCTUnwrap(asis.left), r = try XCTUnwrap(asis.right)
        XCTAssertGreaterThan(l[0], 0)
        XCTAssertLessThan(r[0], 0)
        XCTAssertEqual(l[0], -r[0], accuracy: 0.02)
        XCTAssertEqual(l[1], r[1], accuracy: 0.02)
    }
}
