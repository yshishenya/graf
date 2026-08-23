#include "../../RecApp/MeetingDetection/AutomaticRecordingPolicy.h"
#include "../../RecApp/MeetingDetection/WindowsTargetDetector.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    VerifiedTargetRegistry registry;
    VerifiedTargetIdentity target{"exe-fp", "publisher-fp", "Teams", 1};
    assert(registry.registerTarget(target));
    TargetObservation observation{target, true, false};
    assert(WindowsTargetDetector::isPromptCandidate(observation, registry));
    observation.ordinaryMediaPlayback = true;
    assert(!WindowsTargetDetector::isPromptCandidate(observation, registry));
    AutomaticRecordingPolicy policy;
    assert(policy.observeVerifiedTarget(target, true) == AutomaticPromptState::countdown);
    assert(policy.tick(7) == AutomaticPromptState::countdown);
    assert(policy.tick(1) == AutomaticPromptState::started);
    assert(policy.isAlwaysRecord(target) == false);
    (void)policy.alwaysRecordThisApplication();
    assert(policy.isAlwaysRecord(target));
    const VerifiedTargetIdentity differentPublisher{"exe-fp", "other-publisher", "Teams", 1};
    assert(!WindowsTargetDetector::isPromptCandidate({differentPublisher, true, false}, registry));
    const VerifiedTargetIdentity otherTarget{"other-exe", "other-publisher", "Meet", 1};
    assert(policy.observeVerifiedTarget(otherTarget, true) == AutomaticPromptState::countdown);
    assert(policy.disableAlwaysRecord() == AutomaticPromptState::idle);
    return 0;
}
