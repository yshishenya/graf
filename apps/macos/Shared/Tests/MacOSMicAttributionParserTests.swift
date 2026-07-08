import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MacOSMicAttributionParserTests: XCTestCase {
    func testParsesActiveSensorIndicatorBundleAttribution() throws {
        let event = try XCTUnwrap(MacOSMicAttributionParser().parse(
            line: #"sensor-indicators microphone state=active bundleID=us.zoom.xos displayName="Zoom" pid=42"#,
            observedAt: Date(timeIntervalSince1970: 100)
        ))

        XCTAssertEqual(event.bundleID, "us.zoom.xos")
        XCTAssertEqual(event.displayName, "Zoom")
        XCTAssertEqual(event.processID, 42)
        XCTAssertEqual(event.state, .active)
    }

    func testParsesInactiveSensorIndicatorBundleAttribution() throws {
        let event = try XCTUnwrap(MacOSMicAttributionParser().parse(
            line: "ControlCenter sensor indicators microphone stopped bundle=ru.yandex.desktop.telemost",
            observedAt: Date(timeIntervalSince1970: 200)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.state, .inactive)
    }

    func testParsesRealMicAttributionToken() throws {
        let event = try XCTUnwrap(MacOSMicAttributionParser().parse(
            line: "ControlCenter SensorIndicators active attribution set: mic:ru.yandex.desktop.telemost cam:ru.yandex.desktop.telemost",
            observedAt: Date(timeIntervalSince1970: 300)
        ))

        XCTAssertEqual(event.bundleID, "ru.yandex.desktop.telemost")
        XCTAssertEqual(event.state, .active)
    }

    func testParsesRemovedMicAttributionTokenAsInactive() throws {
        let event = try XCTUnwrap(MacOSMicAttributionParser().parse(
            line: "ControlCenter SensorIndicators removing attribution mic:us.zoom.xos",
            observedAt: Date(timeIntervalSince1970: 301)
        ))

        XCTAssertEqual(event.bundleID, "us.zoom.xos")
        XCTAssertEqual(event.state, .inactive)
    }

    func testMalformedOrNonMicLinesAreIgnored() {
        let parser = MacOSMicAttributionParser()

        XCTAssertNil(parser.parse(line: "sensor-indicators camera state=active bundleID=us.zoom.xos"))
        XCTAssertNil(parser.parse(line: "sensor-indicators microphone active without bundle"))
        XCTAssertNil(parser.parse(line: "regular app log line bundleID=us.zoom.xos"))
    }
}
#endif
