#include "../../RecApp/Shell/AutomaticRecordingPrompt.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    AutomaticRecordingPolicy policy;
    (void)policy.observeVerifiedTarget({"exe", "publisher", "Meeting", 1}, true);
    const auto prompt = AutomaticRecordingPrompt::view(policy);
    assert(prompt.primaryAction == "Записать сейчас");
    assert(prompt.secondaryAction == "Пропустить");
    assert(prompt.tertiaryAction == "Всегда писать это приложение");
    assert(prompt.accessibleDescription.find("клавиатур") != std::string::npos);
    return 0;
}
