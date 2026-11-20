#pragma once
// Test-only derivative startup; the product handler and bridge stay unchanged.
#include "AppMainProblemUiFixture.h"
#include <shellapi.h>
#include <winrt/Microsoft.Web.WebView2.Core.h>
#include <fstream>

namespace graf::windows::testing {
struct SettingsUiState {
    std::filesystem::path stage, parent, root, profile;
    winrt::file_handle profilePin;
    std::map<std::wstring, std::filesystem::path> resources;
    std::string owner, preferenceKey, observed, origin;
    bool loaded = false, initializing = false, attached = false, closing = false, finished = false, failed = false;
    bool sawQuiet = false, sawRestore = false, sawPreview = false;
    bool meetingsAfterQuiet = false, returnedWhileQuiet = false;
    std::atomic_bool browserExited{false};
    unsigned starts = 0, settingsLoads = 0, meetingsLoads = 0;
    ULONGLONG began = GetTickCount64(), closingAt = 0, completedAt = 0;
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2Environment environment{nullptr};

    SettingsUiState() {
        int argc = 0;
        auto argv = CommandLineToArgvW(GetCommandLineW(), &argc);
        requireProblemUi(argv && argc == 2, "settings_stage_argument");
        stage = argv[1]; LocalFree(argv);
        std::ifstream originInput(stage / "fixture-origin.txt"); std::getline(originInput, origin);
        constexpr std::string_view prefix = "https://localhost:";
        requireProblemUi(origin.rfind(prefix, 0) == 0 && origin.size() > prefix.size() &&
            origin.substr(prefix.size()).find_first_not_of("0123456789") == std::string::npos &&
            std::stoul(origin.substr(prefix.size())) >= 1024 && std::stoul(origin.substr(prefix.size())) <= 65535,
            "settings_loopback_origin");
        std::ifstream input(stage / "fixture-owner.txt"); std::getline(input, owner);
        requireProblemUi(owner.size() == 36 && owner.find_first_not_of("0123456789abcdef-") == std::string::npos,
            "generated_canonical_owner");
        preferenceKey = sha256(owner);
        const std::wstring value(preferenceKey.begin(), preferenceKey.end());
        DWORD size = 0;
        const auto absent = RegGetValueW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Notifications",
            value.c_str(), RRF_RT_ANY, nullptr, nullptr, &size);
        requireProblemUi(absent == ERROR_FILE_NOT_FOUND || absent == ERROR_PATH_NOT_FOUND, "generated_value_absent");
        GUID id{}; wchar_t name[40]{};
        requireProblemUi(CoCreateGuid(&id) == S_OK && StringFromGUID2(id, name, 40) == 39, "settings_profile_guid");
        const auto temporary = std::filesystem::temp_directory_path();
        wchar_t actual[32768]{};
        const auto length = GetLongPathNameW(temporary.c_str(), actual, 32768);
        requireProblemUi(length && length < 32768, "settings_temp_namespace");
        parent = std::filesystem::path(actual) / (std::wstring(L"graf-settings-ui-") + name);
        requireProblemUi(CreateDirectoryW(parent.c_str(), nullptr) != FALSE, "exclusive_settings_parent");
        root = parent / L"recordings"; profile = parent / L"webview";
        requireProblemUi(CreateDirectoryW(profile.c_str(), nullptr) != FALSE, "exclusive_settings_profile");
        profilePin.attach(CreateFileW(profile.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        requireProblemUi(bool(profilePin), "settings_profile_pin");
        const auto directory = stage / L"resources";
        for (const auto& file : std::filesystem::recursive_directory_iterator(directory)) if (file.is_regular_file()) {
            requireProblemUi(!file.is_symlink(), "regular_settings_resource");
            resources.emplace(L"/" + file.path().lexically_relative(directory).generic_wstring(), file.path());
        }
        requireProblemUi(resources.count(L"/desktop/settings/notifications") && resources.count(L"/desktop/settings/account") &&
            resources.count(L"/desktop/meetings"), "real_shared_pages");
    }
    const char* pageName(std::wstring_view url) const {
        for (const auto& [path, name] : {std::pair{"/desktop/settings/notifications", "notifications"},
                {"/desktop/settings/account", "account"}, {"/desktop/settings", "settings_root"}, {"/desktop/meetings", "meetings"}}) {
            const auto expected = winrt::to_hstring(origin + path);
            if (url == std::wstring_view(expected.c_str(), expected.size())) return name;
        }
        return "other";
    }
    bool profileMatches(const std::wstring& actual) const {
        if (CompareStringOrdinal(actual.c_str(), -1, profile.c_str(), -1, TRUE) != CSTR_EQUAL) return false;
        winrt::file_handle handle(CreateFileW(actual.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        BY_HANDLE_FILE_INFORMATION a{}, b{};
        return handle && GetFileInformationByHandle(profilePin.get(), &a) && GetFileInformationByHandle(handle.get(), &b) &&
            !(b.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) && a.dwVolumeSerialNumber == b.dwVolumeSerialNumber &&
            a.nFileIndexHigh == b.nFileIndexHigh && a.nFileIndexLow == b.nFileIndexLow;
    }
    DesktopHttpTransport::UploadResponse account(const DesktopHttpConfig& config, const DesktopHttpTransport::UploadRequest& request) const {
        requireProblemUi(config.sessionToken == "generated-settings-ui" && request.method == "GET", "settings_fake_wire");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        requireProblemUi(request.path == "/api/v1/auth/me", "settings_identity_only");
        return {200, "{\"user_id\":\"" + owner + R"(","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    }
    bool clearPreference() const {
        const std::wstring name(preferenceKey.begin(), preferenceKey.end());
        HKEY key = nullptr;
        const auto opened = RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Notifications", 0, KEY_SET_VALUE, &key);
        LONG removed = ERROR_FILE_NOT_FOUND;
        if (opened == ERROR_SUCCESS) { removed = RegDeleteValueW(key, name.c_str()); RegCloseKey(key); }
        DWORD size = 0;
        const auto after = RegGetValueW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Notifications", name.c_str(), RRF_RT_ANY,
            nullptr, nullptr, &size);
        return (opened == ERROR_SUCCESS || opened == ERROR_FILE_NOT_FOUND || opened == ERROR_PATH_NOT_FOUND) &&
            (removed == ERROR_SUCCESS || removed == ERROR_FILE_NOT_FOUND) && (after == ERROR_FILE_NOT_FOUND || after == ERROR_PATH_NOT_FOUND);
    }
};

} // namespace graf::windows::testing
