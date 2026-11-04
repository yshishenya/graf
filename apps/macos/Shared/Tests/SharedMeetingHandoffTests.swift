import Foundation
import XCTest
@testable import TwoBrainRecAppCore

final class SharedMeetingHandoffTests: XCTestCase {
    private let workspace = "20000000-0000-0000-0000-000000000001"
    private let token = String(repeating: "a", count: 43)
    private var link: String { "grafrec-dev://shared-meeting?v=1&workspace_id=\(workspace)&share_token=\(token)&tab=recording&position_ms=14000&media_version=0123456789abcdef01234567" }
    func testStrictIntentAndConfiguredOrigin() throws {
        let handoff = try XCTUnwrap(SharedMeetingHandoff(url: XCTUnwrap(URL(string: link)), expectedScheme: "grafrec-dev"))
        let configuration = DesktopCabinetConfiguration(baseURL: try XCTUnwrap(URL(string: "https://graf.example.test")))
        let route = try XCTUnwrap(handoff.route(configuration: configuration))
        XCTAssertEqual(route.host, "graf.example.test")
        XCTAssertEqual(route.path, "/api/v1/cabinet/public-shares/\(token)")
        XCTAssertEqual(route.fragment, "recording?position_ms=14000")
        XCTAssertEqual(DesktopCabinetRoutePolicy(baseURL: configuration.baseURL).decision(for: route).decision, .allow)
        for invalid in [link + "&tab=outcomes", link + "&origin=https://evil.test", link + "&meeting_id=\(workspace)",
            link.replacingOccurrences(of: "position_ms=14000", with: "position_ms=-1"),
            link.replacingOccurrences(of: "position_ms=14000", with: "position_ms=86400001"),
            link.replacingOccurrences(of: "tab=recording", with: "tab=outcomes"),
            link.replacingOccurrences(of: "//shared-meeting", with: "//user@shared-meeting"),
            link.replacingOccurrences(of: "//shared-meeting", with: "//shared-meeting:42"),
            link.replacingOccurrences(of: "grafrec-dev:", with: "grafrec:"), link + "#recording"] {
            XCTAssertNil(SharedMeetingHandoff(url: try XCTUnwrap(URL(string: invalid)), expectedScheme: "grafrec-dev"), invalid)
        }
        XCTAssertNil(SharedMeetingHandoff(url: try XCTUnwrap(URL(string: link)), expectedScheme: "grafrec"))
    }
    func testSessionRecoveryPreservesAddressedContextAndSealsPublicContext() throws {
        let configuration = DesktopCabinetConfiguration(baseURL: try XCTUnwrap(URL(string: "https://graf.example.test")))
        let intent = try XCTUnwrap(SharedMeetingHandoff(url: XCTUnwrap(URL(string: link)), expectedScheme: "grafrec-dev"))
        let publicRoute = try XCTUnwrap(intent.route(configuration: configuration))
        guard case .embedded(let publicRecovery) = DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, currentRoute: publicRoute, initialRoute: nil, configuration: configuration) else { return XCTFail("missing recovery") }
        XCTAssertEqual(publicRecovery.path, publicRoute.path + "/continue")
        XCTAssertFalse(publicRecovery.absoluteString.contains("next="))
        let addressed = try XCTUnwrap(URL(string: "https://graf.example.test/shared-meetings/20000000-0000-0000-0000-000000000002?workspace_id=\(workspace)#recording?position_ms=14000"))
        guard case .embedded(let recovery) = DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, currentRoute: addressed, initialRoute: nil, configuration: configuration) else { return XCTFail("missing recovery") }
        let values = URLComponents(url: recovery, resolvingAgainstBaseURL: false)?.queryItems
        XCTAssertEqual(values?.first(where: { $0.name == "next" })?.value, addressed.path + "?workspace_id=\(workspace)#recording?position_ms=14000")
    }

    @MainActor
    func testColdAndWarmIntentIsConsumedOnceAndLatestWins() throws {
        let inbox = SharedMeetingHandoffInbox()
        var state = DesktopCabinetState.ready
        let configuration = DesktopCabinetConfiguration(baseURL: try XCTUnwrap(URL(string: "https://graf.example.test")))
        XCTAssertTrue(inbox.receive(try XCTUnwrap(URL(string: link)), expectedScheme: "grafrec-dev"))
        XCTAssertTrue(inbox.receive(try XCTUnwrap(URL(string: link.replacingOccurrences(of: "14000", with: "24000"))), expectedScheme: "grafrec-dev"))
        XCTAssertEqual(inbox.take(configuration: configuration, state: &state)?.fragment, "recording?position_ms=24000")
        XCTAssertNil(inbox.take(configuration: configuration, state: &state))
        XCTAssertTrue(inbox.receive(try XCTUnwrap(URL(string: link)), expectedScheme: "grafrec-dev"))
        XCTAssertNotNil(inbox.take(configuration: configuration, state: &state))
    }

    @MainActor
    func testNewIntentLoadsFromRecoveryWithoutChangingAnEmptyInboxState() throws {
        let configuration = DesktopCabinetConfiguration(baseURL: try XCTUnwrap(URL(string: "https://graf.example.test")))
        for original in DesktopCabinetState.allCases {
            let inbox = SharedMeetingHandoffInbox()
            var state = original
            XCTAssertNil(inbox.take(configuration: configuration, state: &state))
            XCTAssertEqual(state, original)
            XCTAssertFalse(inbox.receive(try XCTUnwrap(URL(string: link + "&tab=outcomes")), expectedScheme: "grafrec-dev"))
            XCTAssertNil(inbox.take(configuration: configuration, state: &state))
            XCTAssertEqual(state, original)
            XCTAssertTrue(inbox.receive(try XCTUnwrap(URL(string: link)), expectedScheme: "grafrec-dev"))
            let route = try XCTUnwrap(inbox.take(configuration: configuration, state: &state))
            XCTAssertEqual(state, .loading)
            XCTAssertEqual(route.fragment, "recording?position_ms=14000")
            XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(for: state, currentRoute: route, initialRoute: nil, configuration: configuration))
            state = .notFound
            XCTAssertNil(inbox.take(configuration: configuration, state: &state))
            XCTAssertEqual(state, .notFound, "An already consumed intent must not override the server refusal")
        }
    }
}
