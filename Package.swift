// swift-tools-version: 5.9
import PackageDescription

// Data and types only: no RealityKit, SwiftUI or UIKit, so torque, suit, RigKit
// and any command-line tool can depend on it without pulling in a renderer.
let package = Package(
    name: "AnatomyKit",
    platforms: [.iOS(.v17), .macOS(.v14), .watchOS(.v10)],
    products: [
        .library(name: "AnatomyKit", targets: ["AnatomyKit"]),
    ],
    targets: [
        .target(name: "AnatomyKit", resources: [.process("Resources")]),
        .testTarget(name: "AnatomyKitTests", dependencies: ["AnatomyKit"],
                    resources: [.process("Resources")]),
    ]
)
