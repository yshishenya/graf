#pragma once
// One sequential A/B/C extension of the existing AppMain settings stand.
// No product macros, identity setters, TLS exception, extra Core or keepalive.
#include "AppMainProblemUiFixture.h"
#include "../../RecApp/Web/WebView2Host.h"
#include <shellapi.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <shcore.h>
#include <tlhelp32.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Data.Json.h>
#include <winrt/Windows.Storage.Streams.h>
#include <winrt/Microsoft.Web.WebView2.Core.h>
#include <array>
#include <functional>
#include <fstream>
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "shcore.lib")

namespace graf::windows {
// Existing friend: observation only. Never installs callbacks or changes gates.
struct WebView2AccountStorageFixture {
    struct Observation {
        std::uint64_t requested, running;
        bool pending, inFlight, failed;
    };
    static Observation read(const WebView2Host& host) {
        const auto& s = *host.accountStorage_;
        return {s.requested, s.running, s.pending, s.inFlight, s.failed.load()};
    }
};
namespace testing {
// R2 test derivative only: synchronous registration before the original attach.
// An absent/throwing observer aborts the caller; there is no fallback attach.
using SettingsAccountAbcControl = winrt::Microsoft::UI::Xaml::Controls::WebView2;
inline std::function<void(SettingsAccountAbcControl const&)> settingsAccountAbcObserver;
inline void settingsAccountAbcBeforeAttach(SettingsAccountAbcControl const& control) {
    if (!settingsAccountAbcObserver) throw std::runtime_error("abc_observer_not_installed");
    settingsAccountAbcObserver(control);
}
struct SettingsAccountAbcState : std::enable_shared_from_this<SettingsAccountAbcState> {
    using Core = winrt::Microsoft::Web::WebView2::Core::CoreWebView2;
    using Control = winrt::Microsoft::UI::Xaml::Controls::WebView2;
    using Gate = WebView2AccountStorageFixture::Observation;
    static constexpr const char* origin = "https://rec.2brain.pro";
    static constexpr const char* document = "https://rec.2brain.pro/desktop/meetings";
    static constexpr const char* token = "generated-t088-abc-not-a-credential";
    static constexpr std::array<const char*, 3> users{
        "00000000-0000-4000-8000-000000000011", "00000000-0000-4000-8000-000000000012",
        "00000000-0000-4000-8000-000000000013"};
    static constexpr std::array<const char*, 3> spaces{
        "00000000-0000-4000-8000-000000000021", "00000000-0000-4000-8000-000000000022",
        "00000000-0000-4000-8000-000000000023"};
    std::filesystem::path stage, root, profile;
    winrt::file_handle profilePin, browser;
    BY_HANDLE_FILE_INFORMATION rootId{};
    FILETIME browserCreation{};
    DWORD browserPid = 0;
    std::wstring profilePath, profileName;
    std::atomic<unsigned> target{0}, nativeCalls{0}, unexpectedNative{0}, scripts{0}, cookieReads{0};
    std::atomic<bool> failed{false}, unknown{false};
    std::atomic<int> browserExit{0};
    std::array<bool, 3> initialized{}, navigated{}, inspected{}, settled{}, cookieStarted{}, cookieInspected{};
    std::array<ULONGLONG, 3> completedAt{};
    std::array<winrt::weak_ref<Control>, 3> controls;
    unsigned watched = 0, cores = 0, allowed = 0, denied = 0;
    bool owned = false, loaded = false, attached = false, closing = false, finished = false;
    ULONGLONG began = GetTickCount64(), closingAt = 0;

    static bool absent(const std::filesystem::path& path) {
        SetLastError(ERROR_SUCCESS);
        if (GetFileAttributesW(path.c_str()) != INVALID_FILE_ATTRIBUTES) return false;
        const auto error = GetLastError();
        return error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND;
    }
    static void noOverrides() {
        for (const auto name : {L"WEBVIEW2_USER_DATA_FOLDER", L"WEBVIEW2_BROWSER_EXECUTABLE_FOLDER",
            L"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", L"WEBVIEW2_PIPE_FOR_SCRIPT_DEBUGGER",
            L"WEBVIEW2_WAIT_FOR_SCRIPT_DEBUGGER", L"WEBVIEW2_CHANNEL_SEARCH_KIND",
            L"WEBVIEW2_RELEASE_CHANNEL_PREFERENCE", L"WEBVIEW2_RELEASE_CHANNELS"}) {
            SetLastError(ERROR_SUCCESS);
            requireProblemUi(GetEnvironmentVariableW(name, nullptr, 0) == 0 &&
                GetLastError() == ERROR_ENVVAR_NOT_FOUND, "abc_environment_override");
        }
        for (HKEY hive : {HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE})
            for (REGSAM view : {KEY_WOW64_32KEY, KEY_WOW64_64KEY})
                for (auto suffix : {L"UserDataFolder", L"BrowserExecutableFolder", L"AdditionalBrowserArguments",
                    L"ChannelSearchKind", L"ReleaseChannels"}) {
                    HKEY key = nullptr;
                    const auto path = std::wstring(L"Software\\Policies\\Microsoft\\Edge\\WebView2\\") + suffix;
                    const auto status = RegOpenKeyExW(hive, path.c_str(), 0, KEY_READ | view, &key);
                    if (key) RegCloseKey(key);
                    requireProblemUi(status == ERROR_FILE_NOT_FOUND || status == ERROR_PATH_NOT_FOUND,
                        "abc_creation_policy_present_or_unreadable");
                }
    }
    SettingsAccountAbcState() {
        int argc = 0; auto argv = CommandLineToArgvW(GetCommandLineW(), &argc);
        if (!argv) throw std::runtime_error("abc_arguments");
        const bool valid = argc == 2;
        if (valid) stage = argv[1];
        LocalFree(argv); requireProblemUi(valid, "abc_stage_argument");
        std::ifstream input(stage / "main-udf-preflight.json");
        const std::string text((std::istreambuf_iterator<char>(input)), {});
        const auto receipt = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(text));
        requireProblemUi(receipt.GetNamedBoolean(L"read_only") &&
            !receipt.GetNamedBoolean(L"product_udf_exists") &&
            receipt.GetNamedArray(L"graf_processes").Size() == 0 &&
            receipt.GetNamedString(L"qa_profile") == L"yshis", "abc_main_preflight");
        wchar_t user[256]{}; DWORD userSize = 256;
        requireProblemUi(GetUserNameW(user, &userSize) && _wcsicmp(user, L"yshis") == 0, "abc_qa_user");
        noOverrides();
        winrt::handle processes(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0));
        requireProblemUi(processes && processes.get() != INVALID_HANDLE_VALUE, "abc_process_inventory");
        PROCESSENTRY32W entry{}; entry.dwSize = sizeof(entry);
        requireProblemUi(Process32FirstW(processes.get(), &entry) != FALSE, "abc_process_first");
        do {
            requireProblemUi(entry.th32ProcessID == GetCurrentProcessId() ||
                _wcsicmp(entry.szExeFile, L"GrafWindowsApp.exe") != 0, "abc_other_product_process");
        } while (Process32NextW(processes.get(), &entry));
        requireProblemUi(GetLastError() == ERROR_NO_MORE_FILES, "abc_process_inventory_complete");
        PWSTR raw = nullptr;
        winrt::check_hresult(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT, nullptr, &raw));
        const std::filesystem::path local(raw); CoTaskMemFree(raw);
        const auto parent = local / L"GRAF";
        if (absent(parent)) requireProblemUi(CreateDirectoryW(parent.c_str(), nullptr) != FALSE, "abc_parent_birth");
        const auto attributes = GetFileAttributesW(parent.c_str());
        requireProblemUi(attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_DIRECTORY) &&
            !(attributes & FILE_ATTRIBUTE_REPARSE_POINT), "abc_parent_not_reparse");
        profile = parent / L"WebView2";
        requireProblemUi(absent(profile), "abc_existing_udf_refused");
        // Exclusive birth is the authority to clean ONLY this run's new UDF.
        requireProblemUi(CreateDirectoryW(profile.c_str(), nullptr) != FALSE, "abc_exclusive_udf_birth");
        owned = true;
        std::fputs("T088_ABC exclusive_birth=1 cleanup_pending=1 setup_failure_means_retained=1\n", stderr);
        std::fflush(stderr);
        profilePin.attach(CreateFileW(profile.c_str(), FILE_READ_ATTRIBUTES | DELETE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        requireProblemUi(profilePin && GetFileInformationByHandle(profilePin.get(), &rootId) &&
            !(rootId.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT), "abc_owned_root_pin");
        root = stage / L"recordings-never-created";
        requireProblemUi(absent(root), "abc_capture_root_absent");
        std::fputs("T088_ABC preflight=1 runtime_absent=1 exclusive_birth=1 no_override=1\n", stderr);
    }
    DesktopHttpTransport::UploadResponse account(const DesktopHttpConfig& config,
        const DesktopHttpTransport::UploadRequest& request) {
        const auto slot = target.load();
        if (slot >= 3 || config.baseOrigin != origin || config.sessionToken != token || request.method != "GET" ||
            (request.path != "/api/v1/auth/me" && request.path != "/desktop/settings/spaces")) {
            ++unexpectedNative; failed.store(true); return {403, "{}"};
        }
        ++nativeCalls;
        if (request.path == "/desktop/settings/spaces")
            return {200, "{\"spaces\":[{\"id\":\"" + std::string(spaces[slot]) + "\",\"active\":true}]}"};
        return {200, "{\"user_id\":\"" + std::string(users[slot]) + "\",\"workspace_id\":\"" +
            spaces[slot] + "\",\"active_session_id\":\"00000000-0000-4000-8000-000000000031\"}"};
    }
    bool matches(const std::optional<DesktopAccountIdentity>& account) const {
        const auto slot = target.load();
        return slot < 3 && account && account->userId == users[slot] && account->workspaceId == spaces[slot];
    }
    void identity(Core const& core, unsigned slot) {
        const auto environment = core.Environment(); const auto actualProfile = core.Profile();
        const std::wstring udf(environment.UserDataFolder().c_str()), path(actualProfile.ProfilePath().c_str()), name(actualProfile.ProfileName().c_str());
        requireProblemUi(_wcsicmp(udf.c_str(), profile.c_str()) == 0 &&
            path.size() > udf.size() + 1 && _wcsnicmp(path.c_str(), (udf + L"\\").c_str(), udf.size() + 1) == 0 &&
            !actualProfile.IsInPrivateModeEnabled(), "abc_actual_owned_profile");
        const DWORD pid = core.BrowserProcessId(); requireProblemUi(pid != 0, "abc_browser_pid");
        winrt::handle process(OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
        FILETIME created{}, ended{}, kernel{}, user{};
        requireProblemUi(process && GetProcessTimes(process.get(), &created, &ended, &kernel, &user) &&
            WaitForSingleObject(process.get(), 0) == WAIT_TIMEOUT, "abc_live_process_handle");
        if (slot == 0) {
            browserPid = pid; browserCreation = created; browser.attach(process.detach());
            profilePath = path; profileName = name;
            const auto self = shared_from_this();
            environment.BrowserProcessExited([self](auto const&, auto const& event) {
                self->browserExit.store(event.BrowserProcessExitKind() ==
                    winrt::Microsoft::Web::WebView2::Core::CoreWebView2BrowserProcessExitKind::Normal ? 1 : 2);
            });
        } else requireProblemUi(pid == browserPid && CompareFileTime(&created, &browserCreation) == 0 &&
            path == profilePath && name == profileName && browserExit.load() == 0, "abc_same_profile_process");
        std::fprintf(stderr, "T088_ABC core=%u udf_equal=1 path_equal=1 name_equal=1 name_len=%zu private=0 pid=%lu creation_equal=1\n",
            slot, name.size(), static_cast<unsigned long>(pid));
    }
    static winrt::Windows::Storage::Streams::IRandomAccessStream htmlStream() {
        constexpr char html[] = "<!doctype html><meta charset=utf-8><title>T088 generated</title><p>Synthetic fixture</p>";
        winrt::com_ptr<IStream> stream;
        stream.attach(SHCreateMemStream(reinterpret_cast<const BYTE*>(html), static_cast<UINT>(sizeof(html) - 1)));
        requireProblemUi(bool(stream), "abc_html_stream");
        winrt::Windows::Storage::Streams::IRandomAccessStream result{nullptr};
        winrt::check_hresult(CreateRandomAccessStreamOverStream(stream.get(), BSOS_DEFAULT,
            winrt::guid_of<decltype(result)>(), winrt::put_abi(result)));
        return result;
    }
    static std::string scriptText(unsigned slot, bool seed) {
        std::string js;
        if (seed) js = "(()=>{const ok=" + std::string(slot ?
            "localStorage.getItem('t088-local')===null&&sessionStorage.getItem('t088-session')===null" : "true") +
            ";localStorage.setItem('t088-local','" + std::to_string(slot) +
            "');sessionStorage.setItem('t088-session','" + std::to_string(slot) +
            "');window.t088Ticks=0;setInterval(()=>{localStorage.setItem('t088-local','" + std::to_string(slot) +
            "');++window.t088Ticks},20);return ok})()";
        else js = "window.t088Ticks>=2&&localStorage.getItem('t088-local')==='" + std::to_string(slot) +
            "'&&sessionStorage.getItem('t088-session')==='" + std::to_string(slot) + "'";
        return js;
    }
    void script(Core const& core, unsigned slot, bool seed) {
        const auto self = shared_from_this(); const auto dispatcher = controls[slot].get().DispatcherQueue();
        ++scripts;
        try {
            core.ExecuteScriptAsync(winrt::to_hstring(scriptText(slot, seed))).Completed([self, dispatcher, slot, seed](auto const& operation, auto const&) {
                try {
                    if (dispatcher.TryEnqueue([self, operation, slot, seed] {
                        try {
                            requireProblemUi(operation.GetResults() == L"true", "abc_storage_readback");
                            if (!self->closing) {
                                if (seed) { self->inspected[slot] = true; self->completedAt[slot] = GetTickCount64(); }
                                else self->settled[slot] = true;
                                std::fprintf(stderr, "T088_ABC readback=%u seed=%u pass=1\n", slot, unsigned(seed));
                            }
                        } catch (...) { self->failed.store(true); }
                        --self->scripts;
                    })) return;
                } catch (...) {}
                self->unknown.store(true); self->failed.store(true); --self->scripts;
            });
        } catch (...) { --scripts; throw; }
    }
    void readCookie(Core const& core, unsigned slot) {
        requireProblemUi(slot > 0 && slot < 3 && !cookieStarted[slot], "abc_cookie_once_on_b_c");
        cookieStarted[slot] = true;
        const auto self = shared_from_this(); const auto dispatcher = controls[slot].get().DispatcherQueue();
        ++cookieReads;
        try {
            core.CookieManager().GetCookiesAsync(winrt::to_hstring(document)).Completed(
                [self, dispatcher, slot](auto const& operation, auto status) {
                    try {
                        if (dispatcher.TryEnqueue([self, operation, status, slot] {
                            try {
                                requireProblemUi(status == winrt::Windows::Foundation::AsyncStatus::Completed,
                                    "abc_cookie_completion");
                                const auto cookies = operation.GetResults();
                                unsigned matches = 0;
                                for (const auto& cookie : cookies) {
                                    if (cookie.Name() == L"__Host-twobrain_rec_owner_session") {
                                        requireProblemUi(cookie.Value() == winrt::to_hstring(token), "abc_cookie_value");
                                        ++matches;
                                    }
                                }
                                requireProblemUi(matches == 1 && !self->closing && self->target.load() == slot,
                                    "abc_cookie_current_exact_readback");
                                self->cookieInspected[slot] = true;
                                std::fprintf(stderr, "T088_ABC cookie_readback=%u exact_name_value=1 completion=1 pass=1\n", slot);
                            } catch (...) { self->failed.store(true); }
                            --self->cookieReads;
                        })) return;
                    } catch (...) {}
                    self->unknown.store(true); self->failed.store(true); --self->cookieReads;
                });
        } catch (...) { --cookieReads; failed.store(true); throw; }
    }
    void observe(Control const& control, std::function<Gate()> gate) {
        using namespace winrt::Microsoft::Web::WebView2::Core;
        const auto slot = watched++;
        requireProblemUi(slot < 3 && !control.CoreWebView2(), "abc_only_three_fresh_controls");
        controls[slot] = winrt::make_weak(control);
        const auto self = shared_from_this();
        control.CoreWebView2Initialized([self, slot, gate](auto const& sender, auto const& event) {
            try {
                std::fprintf(stderr, "T088_ABC initialized=%u hr=%08X\n", slot, static_cast<unsigned>(event.Exception()));
                requireProblemUi(!self->closing && SUCCEEDED(event.Exception()) && sender.CoreWebView2(), "abc_core_initialized");
                const auto core = sender.CoreWebView2();
                core.AddWebResourceRequestedFilter(L"*", CoreWebView2WebResourceContext::All,
                    CoreWebView2WebResourceRequestSourceKinds::All);
                core.WebResourceRequested([self, slot](auto const& view, auto const& event) {
                    try {
                        const bool allow = !self->closing && self->initialized[slot] &&
                            event.Request().Uri() == winrt::to_hstring(document) && event.Request().Method() == L"GET" &&
                            event.ResourceContext() == CoreWebView2WebResourceContext::Document;
                        auto response = view.Environment().CreateWebResourceResponse(allow ? htmlStream() : nullptr,
                            allow ? 200 : 403, allow ? L"OK" : L"Fixture denied",
                            allow ? L"Content-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nContent-Security-Policy: default-src 'none'" : L"Content-Length: 0");
                        event.Response(response); // Every request is answered locally, including denied requests.
                        if (allow) ++self->allowed; else ++self->denied;
                    } catch (...) {
                        self->failed.store(true); self->unknown.store(true);
                        try { event.Response(view.Environment().CreateWebResourceResponse(nullptr, 403, L"Denied", L"Content-Length: 0")); }
                        catch (...) {
                            try { view.Stop(); } catch (...) {}
                            try { if (auto control = self->controls[slot].get()) control.Close(); } catch (...) {}
                        }
                    }
                });
                requireProblemUi(self->cores++ == slot && !self->initialized[slot] &&
                    (core.Source().empty() || core.Source() == L"about:blank"), "abc_blank_before_first_navigation");
                self->identity(core, slot); self->initialized[slot] = true;
                core.PermissionRequested([](auto const&, auto const& event) { event.State(CoreWebView2PermissionState::Deny); });
                core.NewWindowRequested([self](auto const&, auto const& event) { event.Handled(true); self->failed.store(true); });
                core.DownloadStarting([self](auto const&, auto const& event) { event.Cancel(true); self->failed.store(true); });
                core.NavigationStarting([self, slot, gate](auto const&, auto const& event) {
                    try {
                        const auto s = gate();
                        requireProblemUi(!self->closing && !self->navigated[slot] && self->target.load() == slot &&
                            event.Uri() == winrt::to_hstring(document) && !event.IsRedirected() &&
                            !s.pending && !s.inFlight && !s.failed && s.requested == slot && s.running == slot,
                            "abc_first_navigation_after_clear");
                        self->navigated[slot] = true;
                        std::fprintf(stderr, "T088_ABC navigate=%u requested=%llu running=%llu pending=0 inflight=0\n",
                            slot, static_cast<unsigned long long>(s.requested), static_cast<unsigned long long>(s.running));
                    } catch (...) { event.Cancel(true); self->failed.store(true); }
                });
                core.NavigationCompleted([self, slot](auto const& view, auto const& event) {
                    if (self->closing || self->failed.load()) return;
                    try {
                        requireProblemUi(event.IsSuccess() && self->navigated[slot] &&
                            view.Source() == winrt::to_hstring(document), "abc_navigation_complete");
                        self->script(view, slot, true);
                    } catch (...) { self->failed.store(true); }
                });
                // Seed once. Never repair/recreate the cookie on B or C; product must preserve it.
                if (slot == 0) {
                    const auto manager = core.CookieManager();
                    auto cookie = manager.CreateCookie(L"__Host-twobrain_rec_owner_session", winrt::to_hstring(token), L"rec.2brain.pro", L"/");
                    cookie.IsSecure(true); cookie.IsHttpOnly(true); manager.AddOrUpdateCookie(cookie);
                }
            } catch (...) {
                self->failed.store(true); self->unknown.store(true);
                // Do not let the next (product) Initialized delegate navigate an unguarded Core.
                try { sender.Close(); } catch (...) {}
            }
        });
    }
    bool processStopped() const {
        return browser && WaitForSingleObject(browser.get(), 0) == WAIT_OBJECT_0 && browserExit.load() == 1;
    }
    bool cleanupOwnedProfile() {
        if (!owned || !profilePin || unknown.load() || scripts.load() || cookieReads.load() || !processStopped()) return false;
        BY_HANDLE_FILE_INFORMATION current{};
        if (!GetFileInformationByHandle(profilePin.get(), &current) || current.dwVolumeSerialNumber != rootId.dwVolumeSerialNumber ||
            current.nFileIndexHigh != rootId.nFileIndexHigh || current.nFileIndexLow != rootId.nFileIndexLow ||
            (current.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) return false;
        // No traversal through reparse points; unknown/new namespace stays retained.
        std::vector<std::filesystem::path> entries;
        for (const auto& item : std::filesystem::recursive_directory_iterator(profile)) {
            const auto attributes = GetFileAttributesW(item.path().c_str());
            if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_REPARSE_POINT) ||
                entries.size() >= 20000 || GetTickCount64() - began >= 295000) return false;
            entries.push_back(item.path());
        }
        std::reverse(entries.begin(), entries.end());
        for (const auto& item : entries) if (!std::filesystem::remove(item)) return false;
        FILE_DISPOSITION_INFO disposition{TRUE};
        if (!SetFileInformationByHandle(profilePin.get(), FileDispositionInfo, &disposition, sizeof(disposition))) return false;
        profilePin.close(); owned = false;
        return absent(profile);
    }
};
} // namespace testing
} // namespace graf::windows
