// swift-tools-version:5.7
// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

import PackageDescription

let package = Package(
    name: "RRA",
    platforms: [
        .iOS(.v14),
        .macOS(.v12)
    ],
    products: [
        .library(
            name: "RRA",
            targets: ["RRA"]
        ),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "RRA",
            dependencies: [],
            path: "Sources/RRA"
        ),
        .testTarget(
            name: "RRATests",
            dependencies: ["RRA"],
            path: "Tests/RRATests"
        ),
    ]
)
