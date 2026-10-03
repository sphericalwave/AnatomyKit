//
//  LineSideTests.swift
//  AnatomyKitTests
//

import XCTest
@testable import AnatomyKit

final class LineSideTests: XCTestCase {
    private let catalog = AnatomyCatalog.standard

    func testLeftSpiralCrossesToTheRightAndBack() throws {
        let spiral = try XCTUnwrap(catalog.line("spiral"))
        let tracks = try XCTUnwrap(spiral.tracks(startingOn: .left).first)
        func side(of id: String) -> BodySide? { tracks.first { $0.structures.contains(id) }?.side }
        XCTAssertEqual(side(of: "splenius_capitis"), .left)
        XCTAssertEqual(side(of: "rhomboid_major"), .right)
        XCTAssertEqual(side(of: "external_oblique"), .right)
        XCTAssertEqual(side(of: "internal_oblique"), .left)
        XCTAssertEqual(side(of: "tibialis_anterior"), .left)
    }

    func testLinesWithoutCrossingsStayOnOneSide() throws {
        let sbl = try XCTUnwrap(catalog.line("superficial_back"))
        XCTAssertTrue(sbl.tracks(startingOn: .right).joined().allSatisfy { $0.side == .right })
    }
}
