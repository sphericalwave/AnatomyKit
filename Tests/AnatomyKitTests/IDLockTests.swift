//
//  IDLockTests.swift
//  AnatomyKitTests
//
//  IDs are persisted by hosts, so the catalog is append-only. ids.lock.json
//  lists every ID that has existed; removing or renaming one fails here.
//  After adding IDs, append them to the lock file.
//

import XCTest
@testable import AnatomyKit

final class IDLockTests: XCTestCase {
    private struct Lock: Decodable {
        let regions, joints, directions, complexes, lines, muscles, tissues, landmarks, bones, articulations, sorenessAreas: [String]
    }

    func testNoLockedIDWasRemoved() throws {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "ids.lock", withExtension: "json"))
        let lock = try JSONDecoder().decode(Lock.self, from: Data(contentsOf: url))
        let c = AnatomyCatalog.standard
        assertKept(lock.regions, Set(c.regions.map(\.id.rawValue)), "region")
        assertKept(lock.joints, Set(c.joints.map(\.id.rawValue)), "joint")
        assertKept(lock.directions, Set(c.directions.map(\.id.rawValue)), "direction")
        assertKept(lock.complexes, Set(c.complexes.map(\.id.rawValue)), "complex")
        assertKept(lock.lines, Set(c.lines.map(\.id.rawValue)), "line")
        assertKept(lock.muscles, Set(c.muscles.map(\.id.rawValue)), "muscle")
        assertKept(lock.tissues, Set(c.tissues.map(\.id.rawValue)), "tissue")
        assertKept(lock.landmarks, Set(c.landmarks.map(\.id.rawValue)), "landmark")
        assertKept(lock.bones, Set(c.bones.map(\.id.rawValue)), "bone")
        assertKept(lock.articulations, Set(c.articulations.map(\.id.rawValue)), "articulation")
        assertKept(lock.sorenessAreas, Set(c.sorenessAreas.map(\.id.rawValue)), "soreness area")
    }

    private func assertKept(_ locked: [String], _ current: Set<String>, _ what: String) {
        let missing = locked.filter { !current.contains($0) }
        XCTAssertTrue(missing.isEmpty, "\(what) IDs removed or renamed: \(missing). Add a new ID plus an alias instead.")
    }
}
