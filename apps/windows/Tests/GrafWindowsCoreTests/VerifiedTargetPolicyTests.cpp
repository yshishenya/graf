#include "AutomaticRecordingTestSupport.h"

int main() {
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
    assert(bundled.targets().size() == 1);
    const auto& teams = bundled.targets().front();
    assert(teams.targetKey == "microsoft_teams_new");
    assert(teams.displayName == "Microsoft Teams");
    assert(VerifiedTargetRegistry::validIdentity(teams));
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
