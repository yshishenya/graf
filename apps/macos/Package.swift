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
            name: "LeakageValidation",
            targets: ["LeakageValidation"]
        ),
        .executable(
            name: "MeetingMuteTruthRuntimeProof",
            targets: ["MeetingMuteTruthRuntimeProof"]
        )
    ],
    targets: [
        .target(
            name: "CShmHelpers",
            path: "Shared/CShmHelpers",
            publicHeadersPath: "include"
        ),
        .target(
            name: "TwoBrainRecShared",
            dependencies: ["CShmHelpers"],
            path: "Shared/Sources"
        ),
        .target(
            name: "TwoBrainRecAppCore",
            dependencies: ["TwoBrainRecShared"],
            path: "RecApp/Sources"
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
            name: "LeakageValidation",
            dependencies: ["TwoBrainRecShared", "TwoBrainRecAppCore"],
            path: "Shared/Tools/LeakageValidation"
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
