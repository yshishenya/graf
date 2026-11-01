#include "MicrophoneConsentKey.h"

namespace graf::windows {

std::vector<std::wstring> microphoneConsentKeySuffixes(std::wstring_view packageFamilyName) {
    std::vector<std::wstring> suffixes;
    if (!packageFamilyName.empty()) {
        std::wstring packaged(L"\\");
        packaged.append(packageFamilyName);
        suffixes.push_back(std::move(packaged));
    }
    suffixes.emplace_back(L"\\NonPackaged");
    suffixes.emplace_back();
    return suffixes;
}

} // namespace graf::windows
