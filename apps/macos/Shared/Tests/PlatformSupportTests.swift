import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class PlatformSupportTests: XCTestCase {
    func testAppleSiliconAndIntelAreSupportedOnMinimumMacOS() {
        let minimum = PlatformSupport.minimumSupportedMacOS

        XCTAssertTrue(PlatformSupport.isSupported(
            operatingSystemVersion: minimum,
            architecture: .appleSilicon
        ))
        XCTAssertTrue(PlatformSupport.isSupported(
            operatingSystemVersion: minimum,
            architecture: .intel
        ))
    }

    func testUnknownArchitectureIsRejected() {
        XCTAssertFalse(PlatformSupport.isSupported(
            operatingSystemVersion: PlatformSupport.minimumSupportedMacOS,
            architecture: .unknown
        ))
    }

    func testOlderMacOSIsRejectedForBothArchitectures() {
        let olderVersion = OperatingSystemVersion(majorVersion: 14, minorVersion: 4, patchVersion: 0)

        XCTAssertFalse(PlatformSupport.isSupported(
            operatingSystemVersion: olderVersion,
            architecture: .appleSilicon
        ))
        XCTAssertFalse(PlatformSupport.isSupported(
            operatingSystemVersion: olderVersion,
            architecture: .intel
        ))
    }
}
#endif
