import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

final class CalendarMeetingOpenerTests: XCTestCase {
    func testRejectsUnsafeURLsAndPreservesPassword() throws {
        for raw in ["http://zoom.us/j/123456789", "https://a:b@zoom.us/j/123456789", "file:///tmp/test", "https://zoom.us:444/j/123456789", "https://zoom.us/\n"] {
            XCTAssertNil(CalendarMeetingOpener.validatedHTTPS(raw))
        }
        let original=try XCTUnwrap(URL(string:"https://us02web.zoom.us/j/12345678901?pwd=synthetic%2Bpass#fragment"))
        let native=try XCTUnwrap(CalendarMeetingOpener.nativeCandidate(for:original))
        XCTAssertEqual(native.scheme,"zoommtg")
        XCTAssertEqual(URLComponents(url:native,resolvingAgainstBaseURL:false)?.queryItems?.first(where:{$0.name=="pwd"})?.value,"synthetic+pass")
        XCTAssertEqual(native.fragment,"fragment")
        XCTAssertNil(CalendarMeetingOpener.nativeCandidate(for:URL(string:"https://zoom.us.evil.test/j/12345678901")!))
        XCTAssertNil(CalendarMeetingOpener.nativeCandidate(for:URL(string:"https://zoom.us/my/personal")!))
        XCTAssertNil(CalendarMeetingOpener.nativeCandidate(for:URL(string:"https://meet.google.com/abc-defg-hij")!))
        XCTAssertEqual(CalendarMeetingOpener.nativeCandidate(for:URL(string:"https://teams.microsoft.com/l/meetup-join/synthetic?context=x")!)?.scheme,"msteams")
    }
}

@MainActor
final class EmbeddedCabinetCalendarJoinBridgeTests: XCTestCase {
    func testPayloadRejectsURLAndExtraFields() {
        let payload=["action":"joinCalendarEvent","eventId":UUID().uuidString,"requestId":UUID().uuidString]
        XCTAssertNotNil(EmbeddedCabinetCalendarJoinBridge.Request.parse(payload))
        XCTAssertNil(EmbeddedCabinetCalendarJoinBridge.Request.parse(payload.merging(["url":"https://evil.test"]){$1}))
        XCTAssertNil(EmbeddedCabinetCalendarJoinBridge.Request.parse(payload.merging(["eventId":"bad"]){$1}))
    }

    func testSessionBoundarySuppressesResponseAndDoubleClick() async {
        let bridge=EmbeddedCabinetCalendarJoinBridge()
        let pending=JoinPendingResolver()
        var current=true
        var opened=0
        let request=EmbeddedCabinetCalendarJoinBridge.Request(eventID:UUID(),requestID:UUID())
        bridge.join(request,resolve:{ _ in try await pending.resolve() },isCurrent:{current},open:{_ in opened += 1;return true},reply:{_ in})
        while !(await pending.started) { await Task.yield() }
        bridge.join(.init(eventID:UUID(),requestID:UUID()),resolve:{_ in XCTFail("duplicate resolver");return URL(string:"https://example.test")!},isCurrent:{current},open:{_ in opened += 1;return true},reply:{_ in})
        current=false
        await pending.finish()
        for _ in 0..<20 { await Task.yield() }
        XCTAssertEqual(opened,0)
        bridge.invalidate()
    }

    func testActiveAuthBarrierPreventsJoin() {
        let barrier=DesktopCabinetSessionBridge.beginNavigation()
        defer { DesktopCabinetSessionBridge.endNavigation(barrier) }
        XCTAssertFalse(DesktopCabinetSessionBridge.isCurrentSession(DesktopCabinetSessionBridge.generation))
    }
}

private actor JoinPendingResolver {
    var started=false
    var continuation: CheckedContinuation<URL,Error>?
    func resolve() async throws -> URL { try await withCheckedThrowingContinuation { continuation=$0;started=true } }
    func finish() { continuation?.resume(returning:URL(string:"https://meet.google.com/abc-defg-hij")!);continuation=nil }
}

final class CalendarJoinClientTests: XCTestCase {
    func testResolverUsesCurrentSessionAndDoesNotExposeItToMeetingURL() async throws {
        let id=UUID()
        let client=DesktopUploadClient(baseURL:URL(string:"https://graf.test")!,headers:["Cookie":"not-forwarded"],partSizeBytes:1,
            authSessionTokenProvider:{_ in "synthetic-session"}, requestExecutor:{request in
                XCTAssertEqual(request.url?.path,"/api/v1/calendar/events/\(id.uuidString.lowercased())/join-target")
                XCTAssertEqual(request.value(forHTTPHeaderField:"X-Auth-Session"),"synthetic-session")
                XCTAssertNil(request.value(forHTTPHeaderField:"Cookie"))
                return (Data("{\"event_id\":\"\(id.uuidString)\",\"https_url\":\"https://meet.google.com/abc-defg-hij?pwd=synthetic\"}".utf8),HTTPURLResponse(url:request.url!,statusCode:200,httpVersion:nil,headerFields:nil)!)
            },sessionRenewalHandler:{_,_,_ in})
        let url=try await client.calendarJoinTarget(eventID:id)
        XCTAssertEqual(url.absoluteString,"https://meet.google.com/abc-defg-hij?pwd=synthetic")
        XCTAssertFalse(url.absoluteString.contains("session"))
    }
}

#if canImport(WebKit)
import WebKit

@MainActor
final class CalendarJoinIsolationTests: XCTestCase {
    private static var retainedViews: [WKWebView] = []
    private func readIsolated(_ web: WKWebView, _ world: WKContentWorld) async throws -> String? {
        try await withCheckedThrowingContinuation { continuation in
            web.evaluateJavaScript("typeof window.GRAFCalendarJoin", in: nil, in: world) { result in
                switch result {
                case .success(let value): continuation.resume(returning: value as? String)
                case .failure(let error): continuation.resume(throwing: error)
                }
            }
        }
    }
    func testPageCannotMessageBridgeOrSynthesizeJoin() async throws {
        let configuration=WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let handler=CalendarJoinMessageSpy()
        let world=EmbeddedCabinetCalendarJoinBridge.contentWorld
        configuration.userContentController.add(handler,contentWorld:world,name:EmbeddedCabinetCalendarJoinBridge.handlerName)
        configuration.userContentController.addUserScript(WKUserScript(source:EmbeddedCabinetCalendarJoinBridge.documentScript,injectionTime:.atDocumentEnd,forMainFrameOnly:true,in:world))
        let web=WKWebView(frame:.zero,configuration:configuration)
        Self.retainedViews.append(web)
        defer {configuration.userContentController.removeScriptMessageHandler(forName:EmbeddedCabinetCalendarJoinBridge.handlerName,contentWorld:world)}
        web.loadHTMLString("<a href='#' data-calendar-join='00000000-0000-0000-0000-000000000001'>Join</a><span data-calendar-join-status></span>",baseURL:URL(string:"https://graf.test/desktop/meetings"))
        for _ in 0..<100 {
            let ready=try? await readIsolated(web, world)
            if ready == "object" {break}
            try await Task.sleep(nanoseconds:20_000_000)
        }
        let isolated=try await readIsolated(web, world)
        XCTAssertEqual(isolated,"object")
        let pageHandler=try await web.evaluateJavaScript("typeof window.webkit?.messageHandlers?.grafCalendarJoin") as? String
        XCTAssertEqual(pageHandler,"undefined")
        let pageReply=try await web.evaluateJavaScript("typeof window.GRAFCalendarJoin") as? String
        XCTAssertEqual(pageReply,"undefined")
        _ = try await web.evaluateJavaScript("document.querySelector('a').click(); document.querySelector('a').dispatchEvent(new MouseEvent('click',{bubbles:true})); true")
        try await Task.sleep(nanoseconds:50_000_000)
        XCTAssertEqual(handler.count,0)
    }
}

@MainActor
private final class CalendarJoinMessageSpy: NSObject, @preconcurrency WKScriptMessageHandler {
    var count=0
    func userContentController(_ controller: WKUserContentController,didReceive message: WKScriptMessage) {count += 1}
}
#endif

@MainActor
final class NativeCalendarJoinTests: XCTestCase {
    func testProductionPromptJoinKeepsSyntheticRecordingContinuous() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("f279-join-\(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        let source = BufferedLocalRecordingSampleSource(channelCount: 1)
        let silence = BufferedLocalRecordingSampleSource(channelCount: 1)
        let writer = LocalRecordingWriter(store: LocalRecordingStore(rootURL: root),
            microphoneSampleSourceFactory: { silence }, incomingSampleSourceFactory: { source },
            recordMicrophone: true)
        defer { if writer.isRecording { _ = try? writer.stop() } }
        let controller = CaptureSessionController(idFactory: { "f279-active-recording" })
        let started = Date(timeIntervalSince1970: 100)
        let scope = CaptureScopeApproval(scopeApprovalId: "synthetic-scope", scopeKind: .display,
            sourceDisplayName: "Synthetic samples only", approvedAt: started,
            approvalMode: .userConfirmedSuggestedScope, eligibleReason: .manualMeetingScope)
        let permissions = SystemAudioPermissionSnapshot(microphone: .granted, systemAudio: .granted, evaluatedAt: started)
        var starts = 0
        var opens = 0
        var scenario = 0
        var joinTask: Task<Bool, Never>?
        var context: DesktopCalendarResolveCommand?
        let eventID = UUID()
        let safeURL = URL(string: "https://meet.google.com/abc-defg-hij")!
        let actions = DesktopCalendarPromptActions(openURL: { _ in
            let selectedScenario = scenario
            joinTask = Task {
                var current = true
                return await CalendarMeetingOpener.resolveAndOpen(eventID: eventID, resolve: { _ in
                    if selectedScenario == 1 { throw URLError(.resourceUnavailable) }
                    if selectedScenario == 2 { current = false }
                    return safeURL
                }, isCurrent: { current }, open: { _ in opens += 1; return true })
            }
        }, startRecording: { intent, selectedID in
            starts += 1
            do {
                _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
                _ = try controller.markReady()
                _ = try controller.start()
                let session = try controller.markCapturing()
                _ = try writer.start(sessionId: session.id, startedAt: started, scopeApproval: scope, permissions: permissions)
                context = DesktopCalendarResolvePolicy.commandAfterCaptureStarted(localRecordingActive: writer.isRecording,
                    localRecordingId: session.id, recordingStartedAt: started, decisionIntent: intent, eventId: selectedID)
            } catch { XCTFail("Synthetic record action failed: \(error)") }
        }, dismiss: { _ in })
        var prompt = DesktopCalendarPrompt(id: "f279-prompt", kind: .record, eventId: eventID.uuidString,
            title: "Synthetic", message: "", primaryActionTitle: "Record", accessibilityLabel: "Synthetic", openMeetingURL: safeURL)
        // Positive control: the same production dispatcher really owns this recorder's start callback.
        actions.performPrimaryAction(for: prompt)
        let sessionBeforeJoin = try XCTUnwrap(controller.session)
        let contextBeforeJoin = try XCTUnwrap(context)
        let directoryBeforeJoin = try XCTUnwrap(writer.currentDirectoryURL())
        XCTAssertEqual(sessionBeforeJoin.state, .active)
        func append(_ index: Int) {
            silence.append(RecordingAudioBatch(samples: Array(repeating: 0, count: 4_800),
                format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
                presentationTime: RecordingAudioPresentationTimestamp(seconds: 100 + Double(index) / 10, clockDomain: .hostTime),
                discontinuity: .none, routeGeneration: 0))
            source.append(RecordingAudioBatch(samples: Array(repeating: 0.2, count: 4_800),
                format: RecordingAudioFormat(sampleRate: 48_000, channelCount: 1),
                presentationTime: RecordingAudioPresentationTimestamp(seconds: 100 + Double(index) / 10, clockDomain: .hostTime),
                discontinuity: .none, routeGeneration: 0))
        }
        append(0)
        prompt.kind = .join
        for selectedScenario in 0...2 {
            scenario = selectedScenario
            actions.performPrimaryAction(for: prompt)
            let result = await joinTask!.value
            XCTAssertEqual(result, selectedScenario == 0)
            XCTAssertEqual(starts, 1)
            XCTAssertEqual(opens, 1)
            XCTAssertEqual(controller.session, sessionBeforeJoin)
            XCTAssertEqual(context, contextBeforeJoin)
            XCTAssertTrue(writer.isRecording)
            XCTAssertEqual(writer.currentDirectoryURL(), directoryBeforeJoin)
            XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: try XCTUnwrap(controller.session), stopDisabled: false))
            append(selectedScenario + 1)
        }
        let manifest = try await writer.stopAsync()
        XCTAssertNil(manifest.captureFailureCode)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertEqual(manifest.tracks.first { $0.role == .mixedMeetingAudio }?.frameCount, 6_400)
        XCTAssertFalse(writer.isRecording)
    }

    func testNativeEntryRechecksSessionAndSuppressesDuplicate() async {
        let pending = JoinPendingResolver()
        var current = true
        var opens = 0
        let first = Task {
            await CalendarMeetingOpener.resolveAndOpen(eventID: UUID(),
                resolve: { _ in try await pending.resolve() }, isCurrent: { current },
                open: { _ in opens += 1; return true })
        }
        while !(await pending.started) { await Task.yield() }
        let duplicate = await CalendarMeetingOpener.resolveAndOpen(eventID: UUID(),
            resolve: { _ in XCTFail("duplicate resolver"); return URL(string: "https://example.test")! },
            isCurrent: { true }, open: { _ in opens += 1; return true })
        XCTAssertFalse(duplicate)
        current = false
        await pending.finish()
        let result = await first.value
        XCTAssertFalse(result)
        XCTAssertEqual(opens, 0)
        let retry = await CalendarMeetingOpener.resolveAndOpen(eventID: UUID(),
            resolve: { _ in URL(string: "https://meet.google.com/abc-defg-hij")! },
            isCurrent: { true }, open: { _ in opens += 1; return true })
        XCTAssertTrue(retry)
        XCTAssertEqual(opens, 1)
    }

    func testNativeLaunchSelectsKnownMacAppInsteadOfArbitrarySchemeHandler() {
        XCTAssertEqual(CalendarMeetingOpener.nativeApplicationIdentifiers(for: URL(string: "https://teams.microsoft.com/l/meetup-join/synthetic")!), ["com.microsoft.teams2", "com.microsoft.teams"])
        XCTAssertEqual(CalendarMeetingOpener.nativeApplicationIdentifiers(for: URL(string: "https://zoom.us/j/12345678901")!), ["us.zoom.xos"])
        XCTAssertEqual(CalendarMeetingOpener.nativeApplicationIdentifiers(for: URL(string: "https://teams.microsoft.com.evil.test/l/meetup-join/synthetic")!), [])
        XCTAssertEqual(CalendarMeetingOpener.nativeApplicationIdentifiers(for: URL(string: "https://zoom.us/my/personal")!), [])
    }

    func testUnavailableNativeEventDoesNotOpenCachedLink() async {
        let result = await CalendarMeetingOpener.resolveAndOpen(eventID: UUID(),
            resolve: { _ in throw URLError(.resourceUnavailable) }, isCurrent: { true },
            open: { _ in XCTFail("unavailable event must not open"); return true })
        XCTAssertFalse(result)
    }
}
