#include "../../RecApp/Core/WindowsDesktopSession.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    WindowsDesktopSession session("one");
    assert(session.beginReadinessCheck().accepted());
    assert(session.markReady().accepted());
    assert(session.beginStart().accepted());
    assert(session.startRecording().accepted());
    assert(session.pause().accepted());
    assert(session.resume().accepted());
    assert(session.stop().accepted());
    assert(session.stop().status == TransitionStatus::idempotent);
    assert(session.beginFinalizing().accepted());
    assert(session.saveLocal().accepted());
    assert(session.queue().accepted());
    assert(session.upload().accepted());
    WindowsDesktopSession second("two");
    assert(second.beginReadinessCheck().accepted());
    assert(second.block(ReasonCode::recordingPolicyBlocked).accepted());
    return 0;
}
