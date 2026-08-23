import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MacOSAudioOwnershipParserTests: XCTestCase {
    func testParsesPrimaryAudioHALAssertionBundleOwnership() throws {
        let event = try XCTUnwrap(MacOSAudioOwnershipParser().parse(
            line: #"<RBAssertion| identifier:412-81445-989880 target:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] explanation:"AudioHAL" active originator:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] transientState:<RBAssertionTransientState| policies:["#,
            observedAt: Date(timeIntervalSince1970: 90)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.displayName, "telemost")
        XCTAssertEqual(event.processID, 81445)
        XCTAssertEqual(event.source, .audioHAL)
        XCTAssertEqual(event.state, .active)
    }

    func testParsesAudioHALAssertionInvalidationAsInactive() throws {
        let event = try XCTUnwrap(MacOSAudioOwnershipParser().parse(
            line: #"Invalidating <RBAssertion| identifier:412-81445-989880 target:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] explanation:"AudioHAL" inactive originator:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] transientState:<RBAssertionTransientState| policies:["#,
            observedAt: Date(timeIntervalSince1970: 91)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.processID, 81445)
        XCTAssertEqual(event.source, .audioHAL)
        XCTAssertEqual(event.state, .inactive)
    }

    func testParsesAudioHALAssertionDidInvalidateAsInactive() throws {
        let event = try XCTUnwrap(MacOSAudioOwnershipParser().parse(
            line: #"<RBAssertion| identifier:412-81445-989880 target:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] explanation:"AudioHAL" did invalidate originator:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] transientState:<RBAssertionTransientState| policies:["#,
            observedAt: Date(timeIntervalSince1970: 92)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.processID, 81445)
        XCTAssertEqual(event.state, .inactive)
    }

    func testParsesAudioHALAssertionInvalidatedAsInactive() throws {
        let event = try XCTUnwrap(MacOSAudioOwnershipParser().parse(
            line: #"<RBAssertion| identifier:412-81445-989880 target:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] explanation:"AudioHAL" invalidated originator:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] transientState:<RBAssertionTransientState| policies:["#,
            observedAt: Date(timeIntervalSince1970: 93)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.processID, 81445)
        XCTAssertEqual(event.state, .inactive)
    }

    func testParsesAudioHALAssertionInactiveAsInactive() throws {
        let event = try XCTUnwrap(MacOSAudioOwnershipParser().parse(
            line: #"<RBAssertion| identifier:412-81445-989880 target:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] explanation:"AudioHAL" inactive originator:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] transientState:<RBAssertionTransientState| policies:["#,
            observedAt: Date(timeIntervalSince1970: 94)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.processID, 81445)
        XCTAssertEqual(event.state, .inactive)
    }

    func testParsesControlCenterSensorIndicatorMicrophoneAttributions() {
        let parser = MacOSAudioOwnershipParser()

        let bundles = parser.parseSensorIndicatorMicrophoneBundleIDs(
            line: #"2026-07-09 ControlCenter[939] [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["aud:ai.krisp.krispMac", "mic:ru.yandex.desktop.telemost", "cam:ru.yandex.desktop.telemost", "mic:ai.krisp.krispMac"]"#
        )

        XCTAssertEqual(bundles, ["ru.yandex.desktop.telemost", "ai.krisp.krispMac"])
        XCTAssertNil(parser.parse(line: #"Active activity attributions changed to ["mic:ru.yandex.desktop.telemost"]"#))
    }

    func testParsesControlCenterSensorIndicatorNDJSONLine() {
        let parser = MacOSAudioOwnershipParser()

        let bundles = parser.parseSensorIndicatorMicrophoneBundleIDs(
            line: #"{"subsystem":"com.apple.controlcenter","category":"sensor-indicators","eventMessage":"Active activity attributions changed to [\"aud:ai.krisp.krispMac\", \"mic:ru.yandex.desktop.telemost\", \"cam:ru.yandex.desktop.telemost\"]"}"#
        )

        XCTAssertEqual(bundles, ["ru.yandex.desktop.telemost"])
    }

    func testSensorIndicatorMicrophoneParserReturnsEmptySetWhenNoMicrophoneAttributions() {
        let parser = MacOSAudioOwnershipParser()

        XCTAssertEqual(
            parser.parseSensorIndicatorMicrophoneBundleIDs(
                line: #"ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to ["aud:ai.krisp.krispMac", "cam:ru.yandex.desktop.telemost"]"#
            ),
            []
        )
        XCTAssertNil(parser.parseSensorIndicatorMicrophoneBundleIDs(line: "regular app log line mic:us.zoom.xos"))
    }

    func testSensorIndicatorParserIgnoresRedactedOrTruncatedSnapshots() {
        let parser = MacOSAudioOwnershipParser()
        let redacted = "ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to <private>"
        let truncated = #"ControlCenter [com.apple.controlcenter:sensor-indicators] Active activity attributions changed to [\"mic:us.zoom.xos\""#

        XCTAssertTrue(parser.isSensorIndicatorAttributionLine(redacted))
        XCTAssertTrue(parser.isSensorIndicatorAttributionLine(truncated))
        XCTAssertNil(parser.parseSensorIndicatorMicrophoneBundleIDs(line: redacted))
        XCTAssertNil(parser.parseSensorIndicatorMicrophoneBundleIDs(line: truncated))
    }

    func testMalformedOrNonAudioHALLinesAreIgnored() {
        let parser = MacOSAudioOwnershipParser()

        XCTAssertNil(parser.parse(line: #"<RBAssertion| target:[app<application.ru.yandex.desktop.telemost.1.2(501)>:81445] explanation:"AppDrawing" active"#))
        XCTAssertNil(parser.parse(line: #"<RBAssertion| explanation:"AudioHAL" active without target"#))
        XCTAssertNil(parser.parse(line: "regular app log line bundleID=us.zoom.xos"))
    }
}
#endif
