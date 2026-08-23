#include "../../RecApp/MeetingDetection/WindowsTargetDetector.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    VerifiedTargetRegistry registry;
    const VerifiedTargetIdentity unknown{"unknown", "publisher", "Media", 1};
    assert(!WindowsTargetDetector::isPromptCandidate({unknown, true, false}, registry));
    assert(!WindowsTargetDetector::isPromptCandidate({unknown, true, true}, registry));
    return 0;
}
