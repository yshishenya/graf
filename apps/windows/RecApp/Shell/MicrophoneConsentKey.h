#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace graf::windows {

// Ключи реестра, в которых Windows хранит согласие на доступ к микрофону, в
// порядке проверки. У упакованного приложения согласие лежит под именем
// семейства пакетов, а общий ключ NonPackaged относится к обычным программам и
// остаётся «Allow» даже после отказа в системном запросе. Если проверять общий
// ключ первым, приложение считает, что доступ есть, и начинает запись, которая
// обречена на ошибку.
[[nodiscard]] std::vector<std::wstring> microphoneConsentKeySuffixes(std::wstring_view packageFamilyName);

} // namespace graf::windows
