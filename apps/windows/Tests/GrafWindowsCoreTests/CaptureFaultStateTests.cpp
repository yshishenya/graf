#include "../../RecApp/Capture/CaptureFaultRecovery.h"
#include "../../RecApp/Audio/ClockMapper.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    assert(!CaptureFaultRecovery::rawMicrophoneFallbackAllowed());
    const auto fault = CaptureFaultRecovery::handle(ReasonCode::clockDiscontinuity);
    assert(fault.trustedPrefixMayBeSaved && !fault.normalPackageAllowed);
    ClockMapper mapper;
    assert(mapper.observe({0, 0, 48'000}).valid);
    assert(mapper.observe({10'000'000, 48'000, 48'000}).valid);
    assert(!mapper.observe({9'000'000, 48'000, 48'000}).valid);
    return 0;
}
