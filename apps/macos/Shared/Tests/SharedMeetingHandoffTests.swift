import Foundation
import XCTest
@testable import TwoBrainRecAppCore

final class SharedMeetingHandoffTests: XCTestCase {
    private let workspace = "20000000-0000-0000-0000-000000000001"
    private let token = String(repeating: "a", count: 43)
    private let mediaVersion = "0123456789abcdef01234567"
    private var link: String { "grafrec-dev://shared-meeting?v=1&workspace_id=\(workspace)&share_token=\(token)&tab=recording&position_ms=14000&media_version=\(mediaVersion)" }
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
    func testTokenAndPositionBoundariesReachTheCanonicalRoute() throws {
        let configuration = DesktopCabinetConfiguration(baseURL: try XCTUnwrap(URL(string: "https://graf.example.test")))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let alphabetSample = "Aa0-_"
        for (candidate, position) in [(alphabetSample + String(repeating: "a", count: 27), 0),
                                      (alphabetSample + String(repeating: "a", count: 123), 86_400_000)] {
            let url = try intentURL(["share_token": candidate, "position_ms": String(position)])
            let handoff = try XCTUnwrap(SharedMeetingHandoff(url: url, expectedScheme: "grafrec-dev"))
            let route = try XCTUnwrap(handoff.route(configuration: configuration))
            XCTAssertEqual(route.path, "/api/v1/cabinet/public-shares/\(candidate)")
            XCTAssertEqual(route.fragment, "recording?position_ms=\(position)")
            XCTAssertEqual(policy.decision(for: route).decision, .allow)
        }
        let invalid = [
            ("share_token", String(repeating: "a", count: 31)),
            ("share_token", String(repeating: "a", count: 129)),
            ("share_token", token + "."),
            ("share_token", token + "é"),
            ("position_ms", "1.5"),
            ("position_ms", "five"),
            ("media_version", String(mediaVersion.dropLast())),
            ("media_version", mediaVersion.uppercased()),
        ]
        for (field, value) in invalid {
            let url = try intentURL([field: value])
            XCTAssertNil(SharedMeetingHandoff(url: url, expectedScheme: "grafrec-dev"), "Unexpectedly accepted \(field)")
        }
    }

    private func intentURL(_ overrides: [String: String]) throws -> URL {
        var parts = try XCTUnwrap(URLComponents(string: link))
        parts.queryItems = parts.queryItems?.map { item in
            URLQueryItem(name: item.name, value: overrides[item.name] ?? item.value)
        }
        return try XCTUnwrap(parts.url)
    }

    func testSessionRecoveryPreservesAddressedContextAndSealsPublicContext() throws {
        let configuration = DesktopCabinetConfiguration(baseURL: try XCTUnwrap(URL(string: "https://graf.example.test")))
        let intent = try XCTUnwrap(SharedMeetingHandoff(url: XCTUnwrap(URL(string: link)), expectedScheme: "grafrec-dev"))
        let publicRoute = try XCTUnwrap(intent.route(configuration: configuration))
        guard case .embedded(let publicRecovery) = DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, currentRoute: publicRoute, initialRoute: nil, configuration: configuration) else { return XCTFail("missing recovery") }
        let publicValues = try XCTUnwrap(URLComponents(url: publicRoute, resolvingAgainstBaseURL: false)?.queryItems)
        XCTAssertEqual(publicValues.count, 2)
        XCTAssertEqual(Set(publicValues), [
            URLQueryItem(name: "workspace_id", value: workspace),
            URLQueryItem(name: "media_version", value: mediaVersion),
        ])
        XCTAssertEqual(publicRecovery.host, configuration.baseURL.host)
        XCTAssertEqual(publicRecovery.path, publicRoute.path + "/continue")
        XCTAssertNil(publicRecovery.fragment)
        let continuationValues = try XCTUnwrap(URLComponents(url: publicRecovery, resolvingAgainstBaseURL: false)?.queryItems)
        XCTAssertEqual(continuationValues.count, 5)
        XCTAssertEqual(Set(continuationValues), Set(publicValues + [
            URLQueryItem(name: "action", value: "sign-in"),
            URLQueryItem(name: "tab", value: "recording"),
            URLQueryItem(name: "position_ms", value: "14000"),
        ]))
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
