#include "AutomaticRecordingTestSupport.h"

namespace {
void finalStartAcceptance() {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    using P = AutomaticRecordingPreference;
    for (int failure = 0; failure != 23; ++failure) {
        VerifiedTargetRegistry registry;
        assert(registry.registerTarget(target()));
        Preferences storage;
        AutomaticRecordingPolicy policy(registry, storage.store());
        assert(policy.setPreference(target(), P::always));
        const auto decision = observeFor(policy, 0, 5);
        assert(decision.shouldStart);
        assert(policy.canBindStart(decision.generation));
        assert(policy.bindStart(decision.generation, "session-A"));
        assert(!policy.canBindStart(decision.generation));
        assert(!policy.bindStart(decision.generation, "session-B"));
        auto observed = snapshot(at(6s));
        auto prerequisites = ready();
        auto now = at(6s);
        switch (failure) {
        case 1: policy.cancel(); break;
        case 2: assert(policy.setPreference(target(), P::never)); break;
        case 3: assert(policy.setAllPreferences(P::ask)); break;
        case 4: observed.observations.clear(); break;
        case 5: ++observed.observations.front().processId; break;
        case 6: ++observed.observations.front().processCreatedAt; break;
        case 7: now = at(8001ms); break;
        case 8: observed.observedAt = at(7s); break;
        case 9: observed.status = TargetDetectionStatus::enumerationFailed; break;
        case 10: prerequisites.oneActionStopAvailable = false; break;
        case 11: prerequisites.capture.microphonePermissionGranted = false; break;
        case 12: prerequisites.recordingAlreadyActive = true; break;
        case 13: prerequisites.suppressed = true; break;
        case 14: observed.observedAt = at(4s); break; // Older than the decision, yet within 2 s.
        case 15: observed.observations.front().signatureVerified = false; break;
        case 16: observed.observations.front().hasCaptureStream = false; break;
        case 17: observed.observations.front().hasRenderStream = false; break;
        case 18: prerequisites.visibleIndicatorAvailable = false; break;
        case 19: prerequisites.capture.storageWritable = false; break;
        case 20: prerequisites.capture.aecReady = false; break;
        case 21: prerequisites.capture.aacEncoderReady = false; break;
        case 22: assert(registry.removeTarget(target().executableFingerprint)); break;
        }
        // Polls while starting must preserve a valid intent, but invalid evidence
        // cancels it irreversibly: a later fresh snapshot cannot revive this token.
        (void)policy.update(observed, prerequisites, now);
        assert(!policy.acceptStart(decision.generation, "session-B", observed, prerequisites, now));
        assert(policy.acceptStart(decision.generation, "session-A", observed, prerequisites, now) == (failure == 0));
        assert(!policy.acceptStart(decision.generation, "session-A", snapshot(at(9s)), ready(), at(9s)));
    }

    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences storage;
    AutomaticRecordingPolicy policy(registry, storage.store());
    assert(policy.setPreference(target(), P::always));
    const auto a = observeFor(policy, 0, 5);
    assert(policy.bindStart(a.generation, "A"));
    policy.cancel();
    auto absent = snapshot(at(21s)); absent.observations.clear();
    (void)policy.update(absent, ready(), at(21s));
    const auto b = observeFor(policy, 22, 27);
    assert(b.shouldStart && b.generation != a.generation);
    assert(!policy.canBindStart(a.generation) && policy.canBindStart(b.generation));
    assert(policy.bindStart(b.generation, "B"));
    assert(!policy.acceptStart(a.generation, "A", snapshot(at(28s)), ready(), at(28s)));
    assert(!policy.acceptStart(a.generation, "B", snapshot(at(28s)), ready(), at(28s)));
    assert(!policy.acceptStart(b.generation, "A", snapshot(at(28s)), ready(), at(28s)));
    assert(policy.acceptStart(b.generation, "B", snapshot(at(28s)), ready(), at(28s)));
    assert(!policy.acceptStart(b.generation, "B", snapshot(at(28s)), ready(), at(28s)));

    // Ask still supports both the explicit button and the ordinary 8 s expiry.
    // An unrelated preference, an idempotent save or a failed save cannot revoke
    // a valid decision; a successful change away and back cannot resurrect it.
    for (int action = 0; action != 4; ++action) {
        assert(registry.registerTarget(target('c')));
        Preferences askStorage;
        AutomaticRecordingPolicy ask(registry, askStorage.store());
        assert(observeFor(ask, 0, 5).state == AutomaticPromptState::countdown);
        auto start = action == 0 ? observeFor(ask, 6, 13) :
            ask.recordNow(false, snapshot(at(6s)), ready(), at(6s));
        const auto now = action == 0 ? at(13s) : at(6s);
        assert(start.shouldStart && ask.bindStart(start.generation, "ask"));
        assert(ask.setPreference(target('c'), P::never));
        assert(ask.setPreference(target(), P::ask));
        if (action == 2) {
            askStorage.writeFails = true;
            assert(!ask.setPreference(target(), P::never));
        }
        if (action == 3) {
            assert(ask.setPreference(target(), P::never));
            assert(ask.setPreference(target(), P::ask));
        }
        assert(ask.acceptStart(start.generation, "ask", snapshot(now), ready(), now) == (action != 3));
    }
}
}

int main() {
    finalStartAcceptance();
    using namespace graf::windows;
    using namespace graf::windows::testing;
    using P = AutomaticRecordingPreference;
    VerifiedTargetRegistry registry;
    const auto first = target(), second = target('c');
    assert(!registry.registerTarget({"Teams.exe", "Microsoft", "Teams", 1, "microsoft_teams_new"}));
    assert(!registry.registerTarget(target('g')));
    assert(!registry.registerTarget(target('a', 'b', 0)));
    auto invalid = first;
    invalid.displayName = "Meeting\nuntrusted";
    assert(!registry.registerTarget(invalid));
    for (const auto& key : {"", "Teams", "1teams", "../teams", "teams:beta", "teams=always", "teams\n"}) {
        invalid = first;
        invalid.targetKey = key;
        assert(!registry.registerTarget(invalid));
    }
    invalid = first;
    invalid.targetKey = std::string(65, 'a');
    assert(!registry.registerTarget(invalid));
    assert(registry.registerTarget(first));
    assert(registry.registerTarget(second));
    invalid = first;
    invalid.targetKey = second.targetKey;
    assert(!registry.registerTarget(invalid)); // Same EXE cannot represent another product.
    invalid = first;
    invalid.executableFingerprint = std::string(64, 'e');
    invalid.displayName = "Different name";
    assert(!registry.registerTarget(invalid)); // One product has one display name.
    Preferences storage;
    AutomaticRecordingPolicy policy(registry, storage.store());
    assert(policy.preference(first) == P::ask);
    assert(policy.settings().applications.size() == 2);
    assert(policy.settings().bulkPreference == P::ask);
    assert(policy.setPreference(first, P::always));
    assert(!policy.settings().bulkPreference);
    assert(policy.setPreference(second, P::never));
    assert(policy.preference(first) == P::always);
    assert(policy.preference(second) == P::never);
    invalid = first;
    invalid.targetKey = second.targetKey;
    assert(policy.preference(invalid) == P::ask);
    assert(!policy.setPreference(invalid, P::always));
    assert(!WindowsTargetDetector::isPromptCandidate(snapshot(at(), invalid).observations.front(), registry));
    AutomaticRecordingPolicy relaunched(registry, storage.store());
    assert(relaunched.preference(first) == P::always);
    assert(relaunched.preference(second) == P::never);
    const auto writesBeforeBulk = storage.writes;
    assert(policy.setAllPreferences(P::never));
    assert(storage.writes == writesBeforeBulk + 1); // One atomic write, not partially applied rows.
    assert(policy.settings().bulkPreference == P::never);
    assert(registry.registerTarget(target('d')));
    assert(policy.preference(target('d')) == P::ask); // Bulk is not a future-app/global permission.
    assert(!policy.settings().bulkPreference);
    storage.writeFails = true;
    assert(!policy.setAllPreferences(P::always));
    assert(policy.settings().preferenceWriteFailed);
    assert(policy.preference(first) == P::never);
    assert(policy.preference(target('d')) == P::ask);
    storage.writeFails = false;
    assert(policy.setAllPreferences(P::ask));
    assert(!policy.settings().preferenceWriteFailed);
    assert(!policy.setPreference(target('e'), P::always));
    assert(!policy.setPreference(first, static_cast<P>(99)));
    assert(!policy.setAllPreferences(static_cast<P>(99)));
    assert(policy.setPreference(first, P::always));
    assert(policy.preference(target('a', 'f')) == P::ask); // Unapproved signer, no inherited grant.
    assert(policy.preference(target('a', 'b', 2)) == P::ask);
    assert(!policy.setPreference(target('a', 'f'), P::always));
    assert(!policy.setPreference(target('a', 'b', 2), P::always));
    auto updated = target('e', 'f', 2);
    updated.targetKey = first.targetKey;
    assert(registry.registerTarget(updated));
    assert(VerifiedTargetRegistry::identityKey(first) != VerifiedTargetRegistry::identityKey(updated));
    for (const auto choice : {P::always, P::ask, P::never}) {
        assert(policy.setPreference(first, choice));
        assert(policy.preference(updated) == choice);
        AutomaticRecordingPolicy restart(registry, storage.store());
        assert(restart.preference(updated) == choice);
        assert(restart.settings().applications.size() == 3); // Four identities, three products.
    }
    const auto saved = storage.bytes;
    assert(registry.removeTarget(first.executableFingerprint));
    assert(registry.removeTarget(updated.executableFingerprint));
    assert(policy.preference(first) == P::ask);
    AutomaticRecordingPolicy withoutApp(registry, storage.store());
    assert(withoutApp.setPreference(second, P::ask)); // Retain rules for absent products.
    assert(registry.registerTarget(first));
    AutomaticRecordingPolicy restored(registry, storage.store());
    assert(restored.preference(first) == P::never);
    assert(saved.find("graf.automatic-recording.v2\n") == 0);
    assert(saved.find(first.targetKey + "=never\n") != std::string::npos);

    const auto key = first.targetKey;
    for (const auto& malformed : std::vector<std::string>{
        std::string("assisted_auto_start=1\nprompt_before_recording=0\n"),
        "graf.automatic-recording.v1\n" + VerifiedTargetRegistry::identityKey(first) + "=always\n",
        "graf.automatic-recording.v1\n" + key + "=always\n",
        "graf.automatic-recording.v2\n" + key + "=always", // Partial write.
        "graf.automatic-recording.v2\n" + key + "=unknown\n",
        "graf.automatic-recording.v2\n" + key + "=always\n" + key + "=never\n",
        "graf.automatic-recording.v2\n" + key + "=always\n../untrusted=always\n",
        "graf.automatic-recording.v2\n" + key + "=always\nTeams=always\n",
        std::string(65537, 'x')
    }) {
        storage.bytes = malformed;
        AutomaticRecordingPolicy loaded(registry, storage.store());
        assert(loaded.preference(first) == P::ask);
    }

    // Authorizing evidence needs active input AND output of the same signed process.
    auto observed = snapshot(at()).observations.front();
    assert(WindowsTargetDetector::isPromptCandidate(observed, registry));
    observed.hasCaptureStream = false;
    assert(!WindowsTargetDetector::isPromptCandidate(observed, registry)); // Music/video.
    observed.hasCaptureStream = true;
    observed.hasRenderStream = false;
    assert(!WindowsTargetDetector::isPromptCandidate(observed, registry));

    const auto bundled = VerifiedTargetRegistry::bundled();
    assert(bundled.targets().size() == 2);
    const auto& teams = bundled.targets().front();
    assert(teams.targetKey == "microsoft_teams_new");
    assert(teams.displayName == "Microsoft Teams");
    assert(VerifiedTargetRegistry::validIdentity(teams));
    // The shared product catalog already lists Telemost; the Windows pin adds
    // the exact approved binary and signer for this platform.
    const auto& telemost = bundled.targets().back();
    assert(telemost.targetKey == "yandex_telemost");
    assert(telemost.displayName == "Yandex Telemost");
    assert(VerifiedTargetRegistry::validIdentity(telemost));
    observed.hasRenderStream = true;
    observed.signatureVerified = false;
    assert(!WindowsTargetDetector::isPromptCandidate(observed, registry));
    observed.signatureVerified = true;
    observed.processCreatedAt = 0;
    assert(!WindowsTargetDetector::isPromptCandidate(observed, registry));
    observed.processCreatedAt = 1234;
    observed.processId = 0;
    assert(!WindowsTargetDetector::isPromptCandidate(observed, registry));
    observed.processId = 42;
    observed.identity = target('e');
    assert(!WindowsTargetDetector::isPromptCandidate(observed, registry));

    VerifiedTargetRegistry empty;
    AutomaticRecordingPolicy emptyPolicy(empty, storage.store());
    assert(emptyPolicy.settings().applications.empty());
    assert(!emptyPolicy.settings().bulkPreference);
    assert(!emptyPolicy.setAllPreferences(P::always));
    assert(WindowsTargetDetector::snapshot(empty).status == TargetDetectionStatus::noVerifiedTargets);
    assert(automaticRecordingPreferenceLabel(P::always) == "Всегда");
    assert(automaticRecordingPreferenceLabel(P::ask) == "Спрашивать");
    assert(automaticRecordingPreferenceLabel(P::never) == "Никогда");
    return 0;
}
