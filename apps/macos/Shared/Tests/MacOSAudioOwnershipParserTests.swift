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
        XCTAssertEqual(event.state, .active)
    }

    func testParsesAudioHALAssertionInvalidationAsInactive() throws {
        let event = try XCTUnwrap(MacOSAudioOwnershipParser().parse(
            line: #"Invalidating <RBAssertion| identifier:412-81445-989880 target:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] explanation:"AudioHAL" inactive originator:[app<application.ru.yandex.desktop.telemost.216958610.216958636(501)>:81445] transientState:<RBAssertionTransientState| policies:["#,
            observedAt: Date(timeIntervalSince1970: 91)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.processID, 81445)
        XCTAssertEqual(event.state, .inactive)
    }

    func testSensorIndicatorLinesAreIgnored() {
        let parser = MacOSAudioOwnershipParser()

        XCTAssertNil(parser.parse(line: "sensor-indicators microphone state=active bundleID=us.zoom.xos"))
        XCTAssertNil(parser.parse(line: "ControlCenter SensorIndicators active attribution set: mic:ru.yandex.desktop.telemost"))
    }

    func testMalformedOrNonAudioHALLinesAreIgnored() {
        let parser = MacOSAudioOwnershipParser()

        XCTAssertNil(parser.parse(line: #"<RBAssertion| target:[app<application.ru.yandex.desktop.telemost.1.2(501)>:81445] explanation:"AppDrawing" active"#))
        XCTAssertNil(parser.parse(line: #"<RBAssertion| explanation:"AudioHAL" active without target"#))
        XCTAssertNil(parser.parse(line: "regular app log line bundleID=us.zoom.xos"))
    }
}
#endif
