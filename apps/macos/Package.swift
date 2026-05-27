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
        .executableTarget(
            name: "ContractValidation",
            dependencies: ["TwoBrainRecShared"],
            path: "Shared/Tools/ContractValidation"
        )
    ]
)
