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
            name: "ContractValidation",
            targets: ["ContractValidation"]
        )
    ],
    targets: [
        .target(
            name: "TwoBrainRecShared",
            path: "Shared/Sources"
        ),
        .target(
            name: "TwoBrainRecAppCore",
            dependencies: ["TwoBrainRecShared"],
            path: "RecApp/Sources"
        ),
        .executableTarget(
            name: "ContractValidation",
            dependencies: ["TwoBrainRecShared", "TwoBrainRecAppCore"],
            path: "Shared/Tools/ContractValidation"
        )
    ]
)
