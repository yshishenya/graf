#include "AutomaticRecordingTestSupport.h"

int main() {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    using P = AutomaticRecordingPreference;
    VerifiedTargetRegistry registry;
    const auto first = target(), second = target('c');
    assert(!registry.registerTarget({"Teams.exe", "Microsoft", "Teams", 1}));
    assert(!registry.registerTarget(target('g')));
    assert(!registry.registerTarget(target('a', 'b', 0)));
    auto invalid = first;
    invalid.displayName = "Meeting\nuntrusted";
    assert(!registry.registerTarget(invalid));
    assert(registry.registerTarget(first));
    assert(registry.registerTarget(second));
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
    assert(registry.registerTarget(target('a', 'f')));
    assert(policy.preference(target('a', 'f')) == P::ask); // Exact signer, no inherited grant.
    assert(registry.registerTarget(target('a', 'b', 2)));
    assert(policy.preference(target('a', 'b', 2)) == P::ask); // Registry approval version also matters.
    assert(registry.removeTarget(first.executableFingerprint));
    assert(policy.preference(first) == P::ask);
    assert(registry.registerTarget(first));

    const auto key = VerifiedTargetRegistry::preferenceKey(first);
    for (const auto& malformed : std::vector<std::string>{
        std::string("assisted_auto_start=1\nprompt_before_recording=0\n"),
        "graf.automatic-recording.v1\n" + key + "=always", // Partial write.
        "graf.automatic-recording.v1\n" + key + "=unknown\n",
        "graf.automatic-recording.v1\n" + key + "=always\n" + key + "=never\n",
        "graf.automatic-recording.v1\n../untrusted=always\n",
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
