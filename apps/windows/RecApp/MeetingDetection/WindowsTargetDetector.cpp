#include "WindowsTargetDetector.h"

namespace graf::windows {

bool WindowsTargetDetector::isPromptCandidate(const TargetObservation& observation,
                                              const VerifiedTargetRegistry& registry) {
    return observation.hasRenderStream && !observation.ordinaryMediaPlayback &&
           registry.contains(observation.identity.executableFingerprint, observation.identity.registryVersion);
}

} // namespace graf::windows
