#include "../GrafWindowsCoreTests/AutomaticRecordingTestSupport.h"

#include <charconv>
#include <iostream>

int main(int argc, char** argv) {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    // Optional Windows-host proof against a known installation. Prints only
    // cryptographic identities, never paths, command lines, app content or audio.
    if (argc == 3 && std::string_view(argv[1]) == "--inspect-process") {
        std::uint32_t pid = 0;
        const std::string_view input(argv[2]);
        const auto parsed = std::from_chars(input.data(), input.data() + input.size(), pid);
        if (parsed.ec != std::errc{} || parsed.ptr != input.data() + input.size()) return 2;
        const auto proof = WindowsTargetDetector::inspectProcess(pid);
        if (!proof) { std::cout << "signed_identity_unavailable\n"; return 1; }
        std::cout << "executable_sha256=" << proof->identity.executableFingerprint
                  << "\nsigner_certificate_sha256=" << proof->identity.publisherFingerprint << '\n';
        return 0;
    }
    if (argc == 4 && std::string_view(argv[1]) == "--observe-target") {
        VerifiedTargetRegistry approved;
        if (!approved.registerTarget({argv[2], argv[3], "Approved test installation", 1, "approved_test"})) return 2;
        const auto observed = WindowsTargetDetector::snapshot(approved);
        std::cout << "native_snapshot_status=" << static_cast<unsigned>(observed.status)
                  << "; verified_active_targets=" << observed.observations.size() << '\n';
        return observed.status == TargetDetectionStatus::ready ? 0 : 1;
    }
    if (argc != 1) return 2;
    using P = AutomaticRecordingPreference;
    // Preferences follow a product update; a countdown/recording still follows
    // the exact approved image. Neither can substitute another approved version.
    for (bool active : {false, true}) {
        VerifiedTargetRegistry versions;
        auto newer = target('c', 'd', 2);
        newer.targetKey = target().targetKey;
        assert(versions.registerTarget(target()));
        assert(versions.registerTarget(newer));
        Preferences local;
        AutomaticRecordingPolicy policy(versions, local.store());
        assert(observeFor(policy, 0, 5).state == AutomaticPromptState::countdown);
        if (!active) {
            assert(!policy.recordNow(true, snapshot(at(6s), newer), ready(), at(6s)).shouldStart);
            assert(local.writes == 0);
            continue;
        }
        assert(policy.recordNow(false, snapshot(at(6s)), ready(), at(6s)).shouldStart);
        policy.captureAccepted();
        for (int second = 7; second <= 22; ++second) {
            const auto now = at(std::chrono::seconds(second));
            assert(policy.shouldStopCapture(snapshot(now, newer), true, now) == (second == 22));
        }
        assert(local.writes == 0);
    }
    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences storage;
    AutomaticRecordingPolicy always(registry, storage.store());
    assert(always.setPreference(target(), P::always));
    assert(!observeFor(always, 0, 4).shouldStart);
    assert(observeFor(always, 5, 5).shouldStart);
    assert(always.state() == AutomaticPromptState::started);
    always.cancel(); // Manual Stop must not restart the same continuous meeting.
    assert(!observeFor(always, 6, 30).shouldStart);
    auto absent = snapshot(at(45s));
    absent.observations.clear();
    assert(!always.update(absent, ready(), at(45s)).shouldStart);
    assert(observeFor(always, 46, 51).shouldStart); // Confirmed absence, new meeting.

    Preferences neverStorage;
    AutomaticRecordingPolicy never(registry, neverStorage.store());
    assert(never.setPreference(target(), P::never));
    assert(observeFor(never, 0, 30).state == AutomaticPromptState::suppressed);
    assert(never.secondsRemaining(at(30s)) == 0);

    // Every required gate is rechecked at expiry and on the immediate action.
    for (unsigned gate = 0; gate < 12; ++gate) {
        Preferences local;
        AutomaticRecordingPolicy policy(registry, local.store());
        (void)observeFor(policy, 0, 12);
        auto denied = ready();
        switch (gate) {
            case 0: denied.capture.microphonePermissionGranted = false; break;
            case 1: denied.capture.microphoneEndpointReady = false; break;
            case 2: denied.capture.renderEndpointReady = false; break;
            case 3: denied.capture.formatNormalizationReady = false; break;
            case 4: denied.capture.aecReady = false; break;
            case 5: denied.capture.storageWritable = false; break;
            case 6: denied.capture.aacEncoderReady = false; break;
            case 7: denied.visibleIndicatorAvailable = false; break;
            case 8: denied.oneActionStopAvailable = false; break;
            case 9: denied.recordingAlreadyActive = true; break;
            case 10: denied.suppressed = true; break;
            case 11: break; // WebView/network are deliberately NOT capture gates.
        }
        const auto result = policy.update(snapshot(at(13s)), denied, at(13s));
        assert(result.shouldStart == (gate == 11));
        assert(!policy.recordNow(true, snapshot(at(13s)), denied, at(13s)).shouldStart);
        assert(local.writes == 0);

        // Independent countdown: a previously blocked/started policy cannot
        // prove that the immediate button rechecks readiness before expiry.
        AutomaticRecordingPolicy immediate(registry, local.store());
        assert(observeFor(immediate, 0, 5).state == AutomaticPromptState::countdown);
        assert(immediate.recordNow(false, snapshot(at(6s)), denied, at(6s)).shouldStart == (gate == 11));
        assert(local.writes == 0);
    }
    for (unsigned fault = 0; fault < 8; ++fault) {
        Preferences local;
        AutomaticRecordingPolicy policy(registry, local.store());
        (void)observeFor(policy, 0, 12);
        auto evidence = snapshot(at(13s));
        switch (fault) {
            case 0: evidence.observations.clear(); break;
            case 1: evidence.observations.front().hasCaptureStream = false; break;
            case 2: evidence.observations.front().signatureVerified = false; break;
            case 3: evidence.observations.front().identity = target('c'); break;
            case 4: evidence.observations.front().processCreatedAt++; break;
            case 5: evidence.status = TargetDetectionStatus::enumerationFailed; break;
            case 6: evidence.observedAt = at(9s); break; // Stale cached snapshot.
            case 7: evidence.observedAt = at(14s); break; // Future/reordered snapshot.
        }
        assert(!policy.recordNow(true, evidence, ready(), at(13s)).shouldStart);
        assert(local.writes == 0);
    }

    // No stale snapshot can itself accumulate five seconds of stable evidence.
    Preferences staleStorage;
    AutomaticRecordingPolicy stale(registry, staleStorage.store());
    for (int second = 0; second < 20; ++second)
        assert(!stale.update(snapshot(at()), ready(), at(std::chrono::seconds(second))).shouldStart);

    // Lifetime starts when native capture accepts Starting, not after Recording.
    assert(registry.registerTarget(target('c')));
    for (unsigned scenario = 0; scenario < 10; ++scenario) {
        Preferences local;
        AutomaticRecordingPolicy policy(registry, local.store());
        assert(policy.setPreference(target(), P::always));
        assert(observeFor(policy, 0, 5).shouldStart);
        policy.captureAccepted();
        for (int second = 6; second <= 21; ++second) {
            auto evidence = snapshot(at(std::chrono::seconds(second)));
            switch (scenario) {
                case 0: evidence.observations.clear(); break;
                case 1: // A new PID of the same verified application continues it.
                    evidence.observations.front().processId++;
                    evidence.observations.front().processCreatedAt++;
                    break;
                case 2: evidence.observations.front().identity = target('c'); break;
                case 3: evidence.observations.front().signatureVerified = false; break;
                case 4: evidence.observations.front().hasCaptureStream = false; break;
                case 5: evidence.observations.front().hasRenderStream = false; break;
                case 6: evidence.observations.front().processId = 0; break;
                case 7: evidence.observations.front().processCreatedAt = 0; break;
                case 8: evidence.observations.front().identity.registryVersion++; break;
                case 9: evidence.observations.front().identity.publisherFingerprint = std::string(64, 'd'); break;
            }
            const bool stops = scenario != 1 && second == 21;
            assert(policy.shouldStopCapture(evidence, true, evidence.observedAt) == stops);
            // UI polling the same snapshot cannot advance time or repeat Stop.
            assert(!policy.shouldStopCapture(evidence, true, evidence.observedAt));
        }
        assert(local.writes == 1); // Lifetime never changes a user's rule.
    }
    for (unsigned fault = 0; fault < 5; ++fault) {
        Preferences local;
        AutomaticRecordingPolicy policy(registry, local.store());
        assert(policy.setPreference(target(), P::always));
        assert(observeFor(policy, 0, 5).shouldStart);
        policy.captureAccepted();
        for (int second = 6; second <= 605; ++second) {
            auto evidence = snapshot(at(std::chrono::seconds(second)));
            switch (fault) {
                case 0: evidence.status = TargetDetectionStatus::enumerationFailed; break;
                case 1: evidence.observedAt = at(5s); break; // Repeated then stale positive.
                case 2: evidence.observedAt += 1s; break; // Future positive.
                case 3: evidence.observedAt = at(4s); break; // Reordered positive.
                case 4: // Snapshot gaps cannot prove continuous absence.
                    evidence.observations.clear();
                    if (second % 3) evidence.status = TargetDetectionStatus::enumerationFailed;
                    break;
            }
            assert(policy.shouldStopCapture(evidence, true, at(std::chrono::seconds(second))) == (second == 605));
        }
        assert(!policy.shouldStopCapture(snapshot(at(606s)), true, at(606s)));
    }
    // A new positive observation renews the 600-second deadline; old/duplicate
    // observations in between reset absence but never renew positive evidence.
    Preferences lifetimeStorage;
    AutomaticRecordingPolicy lifetime(registry, lifetimeStorage.store());
    assert(lifetime.setPreference(target(), P::always));
    assert(observeFor(lifetime, 0, 5).shouldStart);
    lifetime.captureAccepted();
    assert(!lifetime.shouldStopCapture(snapshot(at(600s)), true, at(600s)));
    assert(!lifetime.shouldStopCapture(snapshot(at(600s)), true, at(1199s)));
    assert(lifetime.shouldStopCapture(snapshot(at(600s)), true, at(1200s)));

    for (unsigned interruption = 0; interruption < 4; ++interruption) {
        Preferences local;
        AutomaticRecordingPolicy policy(registry, local.store());
        assert(policy.setPreference(target(), P::always));
        assert(observeFor(policy, 0, 5).shouldStart);
        policy.captureAccepted();
        for (int second = 6; second <= 31; ++second) {
            auto evidence = snapshot(at(std::chrono::seconds(second)));
            evidence.observations.clear();
            if (second == 15) {
                switch (interruption) {
                    case 0: evidence.status = TargetDetectionStatus::enumerationFailed; break;
                    case 1: evidence.observedAt = at(12s); break;
                    case 2: evidence.observedAt = at(16s); break;
                    case 3: evidence.observedAt = at(13s); break;
                }
            }
            assert(policy.shouldStopCapture(evidence, true, at(std::chrono::seconds(second))) == (second == 31));
        }
    }
    // Manual capture, rejected native starts, terminal states and manual Stop
    // cannot be controlled by an old automatic lifetime.
    for (unsigned manual = 0; manual < 4; ++manual) {
        Preferences local;
        AutomaticRecordingPolicy policy(registry, local.store());
        if (manual != 0) {
            assert(policy.setPreference(target(), P::always));
            assert(observeFor(policy, 0, 5).shouldStart);
            if (manual != 1) policy.captureAccepted();
            if (manual == 2) policy.cancel();
            if (manual == 3) assert(!policy.shouldStopCapture(snapshot(at(6s)), false, at(6s)));
        } else policy.captureAccepted(); // No accepted automatic start intent.
        assert(!policy.shouldStopCapture(snapshot(at(5s)), true, at(1000s)));
        if (manual == 2) assert(!observeFor(policy, 6, 30).shouldStart);
    }
#ifndef _WIN32
    assert(WindowsTargetDetector::snapshot(registry).status == TargetDetectionStatus::platformUnavailable);
    assert(!WindowsTargetDetector::inspectProcess(42));
#else
    const auto native = WindowsTargetDetector::snapshot(registry);
    assert(native.status == TargetDetectionStatus::ready || native.status == TargetDetectionStatus::enumerationFailed);
    assert(native.observations.empty()); // Real OS enumeration cannot authorize synthetic pins.
    std::cout << "native_negative_snapshot_status=" << static_cast<unsigned>(native.status) << '\n';
#endif
    std::cout << "automatic_recording_contracts_passed; native_meeting_acceptance_not_claimed\n";
    return 0;
}
