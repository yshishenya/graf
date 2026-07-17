// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "TwoBrainRecMacOS",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "TwoBrainRecShared",
            targets: ["TwoBrainRecShared"]
        ),
        .library(
            name: "TwoBrainRecAppCore",
            targets: ["TwoBrainRecAppCore"]
        ),
        .executable(
            name: "TwoBrainRecApp",
            targets: ["TwoBrainRecApp"]
        ),
        .executable(
            name: "ContractValidation",
            targets: ["ContractValidation"]
        ),
        .executable(
            name: "MeetingMuteTruthRuntimeProof",
            targets: ["MeetingMuteTruthRuntimeProof"]
        ),
    ],
    dependencies: [
        .package(
            url: "https://github.com/sparkle-project/Sparkle",
            exact: "2.9.4"
        )
    ],
    targets: [
        .target(
            name: "TwoBrainRecShared",
            path: "Shared/Sources"
        ),
        .target(
            name: "TwoBrainRecAppCore",
            dependencies: [
                "TwoBrainRecShared",
                .product(name: "Sparkle", package: "Sparkle")
            ],
            path: "RecApp",
            exclude: ["App"],
            sources: ["Sources"],
            resources: [
                .copy("Resources")
            ]
        ),
        .executableTarget(
            name: "TwoBrainRecApp",
            dependencies: ["TwoBrainRecShared", "TwoBrainRecAppCore"],
            path: "RecApp/App"
        ),
        .executableTarget(
            name: "ContractValidation",
            dependencies: ["TwoBrainRecShared", "TwoBrainRecAppCore"],
            path: "Shared/Tools/ContractValidation"
        ),
        .executableTarget(
            name: "MeetingMuteTruthRuntimeProof",
            dependencies: ["TwoBrainRecShared", "TwoBrainRecAppCore"],
            path: "Shared/Tools/MeetingMuteTruthRuntimeProof"
        ),
        .testTarget(
            name: "TwoBrainRecSharedTests",
            dependencies: ["TwoBrainRecShared", "TwoBrainRecAppCore"],
            path: "Shared/Tests",
            resources: [
                .copy("Fixtures")
            ]
        )
    ]
)
