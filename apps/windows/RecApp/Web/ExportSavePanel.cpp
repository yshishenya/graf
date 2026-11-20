#include "ExportSavePanel.h"

#ifdef _WIN32
#include "ExportSaveCommit.h"

#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <shobjidl.h>
#include <UIAutomation.h>
#include <winrt/base.h>
#include <algorithm>
#include <filesystem>
#include <utility>

namespace graf::windows {
namespace {

constexpr wchar_t kPanelClass[] = L"GrafExportSavePanel";
constexpr UINT kOpenSelected = WM_APP + 1;
constexpr UINT kRelayout = WM_APP + 2;
constexpr UINT_PTR kSubclass = 1;
constexpr UINT_PTR kFolderTimer = 1;
constexpr wchar_t kLongFolderAddress[] = L"Путь к папке слишком длинный. Укажите более короткий путь.";
constexpr wchar_t kOpenFolderAddress[] = L"Сначала откройте папку по указанному адресу.";
enum Control : int { titleId = 100, addressLabel, addressId, goId, upId, browserId, nameLabel, nameId, statusId,
    newFolderId, folderLabel, folderNameId, createFolderId };

struct PanelFont {
    HFONT handle{};
    ~PanelFont() { if (handle) DeleteObject(handle); }
};
using PanelFontRef = std::shared_ptr<PanelFont>;

std::wstring itemPath(IShellItem* item) {
    PWSTR raw = nullptr;
    const auto result = item ? item->GetDisplayName(SIGDN_FILESYSPATH, &raw) : E_POINTER;
    const std::unique_ptr<wchar_t, decltype(&CoTaskMemFree)> path(raw, CoTaskMemFree);
    return SUCCEEDED(result) && path ? path.get() : L"";
}

std::wstring folderPath(PCIDLIST_ABSOLUTE id) {
    winrt::com_ptr<IShellItem> item;
    return id && SUCCEEDED(SHCreateItemFromIDList(id, IID_PPV_ARGS(item.put()))) ? itemPath(item.get()) : L"";
}

bool localAddress(std::wstring_view path) {
    if (path.size() < 3 || path.size() >= MAX_PATH || path[1] != L':' || path[2] != L'\\' ||
        !((path[0] >= L'A' && path[0] <= L'Z') || (path[0] >= L'a' && path[0] <= L'z')) ||
        path.find(L':', 2) != path.npos) return false;
    return GetDriveTypeW(std::wstring(path.substr(0, 3)).c_str()) == DRIVE_FIXED;
}

std::wstring textOf(HWND control) {
    std::wstring text(static_cast<std::size_t>(GetWindowTextLengthW(control)) + 1, L'\0');
    text.resize(static_cast<std::size_t>(GetWindowTextW(control, text.data(), static_cast<int>(text.size()))));
    return text;
}

struct StatusProvider : winrt::implements<StatusProvider, IRawElementProviderSimple, winrt::non_agile> {
    explicit StatusProvider(HWND control) : label(control) {}
    HWND label;

    HRESULT STDMETHODCALLTYPE get_ProviderOptions(ProviderOptions* options) noexcept override {
        *options = static_cast<ProviderOptions>(ProviderOptions_ServerSideProvider | ProviderOptions_UseComThreading);
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetPatternProvider(PATTERNID, IUnknown** pattern) noexcept override {
        *pattern = nullptr;
        return label ? S_OK : UIA_E_ELEMENTNOTAVAILABLE;
    }
    HRESULT STDMETHODCALLTYPE GetPropertyValue(PROPERTYID property, VARIANT* value) noexcept override {
        VariantInit(value);
        if (!label) return UIA_E_ELEMENTNOTAVAILABLE;
        if (property == UIA_NamePropertyId) {
            wchar_t message[256]{};
            GetWindowTextW(label, message, ARRAYSIZE(message));
            value->bstrVal = SysAllocString(message);
            if (!value->bstrVal) return E_OUTOFMEMORY;
            value->vt = VT_BSTR;
        } else if (property == UIA_ControlTypePropertyId) {
            value->vt = VT_I4;
            value->lVal = UIA_TextControlTypeId;
        }
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE get_HostRawElementProvider(IRawElementProviderSimple** provider) noexcept override {
        *provider = nullptr;
        return label ? UiaHostProviderFromHwnd(label, provider) : UIA_E_ELEMENTNOTAVAILABLE;
    }
    void detach() noexcept {
        if (const auto window = std::exchange(label, nullptr)) {
            RemoveWindowSubclass(window, subclass, kSubclass);
            UiaReturnRawElementProvider(window, 0, 0, nullptr);
        }
    }
    static LRESULT CALLBACK subclass(HWND window, UINT message, WPARAM w, LPARAM l, UINT_PTR, DWORD_PTR data) noexcept {
        winrt::com_ptr<StatusProvider> provider;
        provider.copy_from(reinterpret_cast<StatusProvider*>(data));
        if (message == WM_GETOBJECT && static_cast<LONG>(l) == UiaRootObjectId)
            return UiaReturnRawElementProvider(window, w, l, provider.get());
        if (message == WM_NCDESTROY) provider->detach();
        return DefSubclassProc(window, message, w, l);
    }
};

} // namespace

struct ExportSavePanel::State : std::enable_shared_from_this<State> {
    HWND owner{}, panel{}, viewWindow{};
    Result result;
    winrt::com_ptr<IExplorerBrowser> browser;
    winrt::com_ptr<IShellItem> pendingFolder;
    DWORD navigationCookie{};
    bool initialized = false;
    bool navigating = false;
    bool closing = false;
    bool revoked = false;
    bool layingOut = false;
    bool layoutPending = false;
    bool layoutPosted = false;
    UINT fontDpi = 0;
    int scrollOffset = 0, scrollLimit = 0, scrollStep = 0;
    enum class SavePhase { selecting, saving, conflict, location };
    SavePhase phase = SavePhase::selecting;
    std::wstring confirmedFolder;
    std::optional<std::wstring> navigationAddress;
    std::weak_ptr<ExportSaveWorker> saveWorker;
    std::shared_ptr<ExportFolderWorker> folderWorker;
    winrt::com_ptr<StatusProvider> statusProvider;
    std::uint64_t folderRevision = 0;
    std::uint64_t statusRevision = 0;

    HWND control(int id) const noexcept { return GetDlgItem(panel, id); }
    bool active() const noexcept { return panel && !closing && !revoked && GetForegroundWindow() == owner; }
    bool choosingFolder() const noexcept {
        return panel && !closing && !revoked && (phase == SavePhase::selecting || phase == SavePhase::location);
    }

    struct Site : winrt::implements<Site, IServiceProvider, ICommDlgBrowser, IExplorerBrowserEvents, winrt::non_agile> {
        explicit Site(std::weak_ptr<State> owner) : state(std::move(owner)) {}
        std::weak_ptr<State> state;

        HRESULT STDMETHODCALLTYPE QueryService(REFGUID service, REFIID iid, void** out) noexcept override {
            if (!out) return E_POINTER;
            *out = nullptr;
            return service == SID_SExplorerBrowserFrame ? QueryInterface(iid, out) : E_NOINTERFACE;
        }
        HRESULT STDMETHODCALLTYPE OnDefaultCommand(IShellView* view) noexcept override {
            try { if (const auto self = state.lock()) self->useSelection(view, true); } catch (...) {}
            return S_OK; // Never dispatch the Shell's default verb.
        }
        HRESULT STDMETHODCALLTYPE OnStateChange(IShellView* view, ULONG change) noexcept override {
            try { if (change == CDBOSC_SELCHANGE) if (const auto self = state.lock()) self->useSelection(view, false); }
            catch (...) {}
            return S_OK;
        }
        HRESULT STDMETHODCALLTYPE IncludeObject(IShellView*, PCUITEMID_CHILD) noexcept override { return S_OK; }
        HRESULT STDMETHODCALLTYPE OnNavigationPending(PCIDLIST_ABSOLUTE id) noexcept override {
            try {
                const auto self = state.lock();
                if (!self || !self->choosingFolder()) return E_ABORT;
                const auto revision = self->folderRevision;
                if (!localAddress(folderPath(id)) || !self->choosingFolder() ||
                    self->folderRevision != revision) return E_ABORT;
                self->beginNavigation();
                return S_OK;
            } catch (...) { return E_ABORT; }
        }
        HRESULT STDMETHODCALLTYPE OnViewCreated(IShellView* view) noexcept override {
            const auto self = state.lock();
            if (!self || self->closing || !view || FAILED(view->GetWindow(&self->viewWindow))) return E_FAIL;
            return self->guardView() ? S_OK : E_FAIL;
        }
        HRESULT STDMETHODCALLTYPE OnNavigationComplete(PCIDLIST_ABSOLUTE id) noexcept override {
            try { if (const auto self = state.lock()) self->navigationComplete(folderPath(id)); }
            catch (...) {}
            return S_OK;
        }
        HRESULT STDMETHODCALLTYPE OnNavigationFailed(PCIDLIST_ABSOLUTE) noexcept override {
            if (const auto self = state.lock()) self->navigationFailed();
            return S_OK;
        }
    };

    void setStatus(const wchar_t* message) noexcept {
        if (!panel || closing) return;
        const auto revision = ++statusRevision;
        const auto label = control(statusId);
        SetWindowTextW(label, message);
        if (revision == statusRevision) {
            layout();
            if (revision == statusRevision && active()) reveal(GetFocus());
        }
        if (*message && revision == statusRevision && panel && !closing && !revoked)
            NotifyWinEvent(EVENT_OBJECT_NAMECHANGE, label, OBJID_CLIENT, CHILDID_SELF);
    }

    bool error(const wchar_t* message) noexcept {
        const auto revision = statusRevision + 1;
        setStatus(message);
        const auto provider = statusProvider;
        if (revision != statusRevision || !active()) return false;
        if (provider && IsWindowVisible(provider->label) && UiaClientsAreListening()) {
            const std::unique_ptr<wchar_t, decltype(&SysFreeString)> display(SysAllocString(message), SysFreeString);
            const std::unique_ptr<wchar_t, decltype(&SysFreeString)> activity(SysAllocString(L"graf.export-save.error"), SysFreeString);
            if (display && activity) (void)UiaRaiseNotificationEvent(provider.get(), NotificationKind_ActionAborted,
                NotificationProcessing_ImportantMostRecent, display.get(), activity.get());
        }
        return revision == statusRevision && active();
    }

    void updateSave() const noexcept {
        if (!panel) return;
        const bool available = !closing && !revoked && !navigating && !confirmedFolder.empty();
        EnableWindow(control(IDOK), available && !folderWorker && phase != SavePhase::saving);
        EnableWindow(control(newFolderId), available && !folderWorker && choosingFolder());
        EnableWindow(control(createFolderId),
            available && folderWorker && folderWorker->status() == ExportFolderWorker::Status::ready);
    }
    void showFolderControls(bool show) noexcept {
        for (const auto id : {folderLabel, folderNameId, createFolderId})
            ShowWindow(control(id), show ? SW_SHOWNA : SW_HIDE);
        for (const auto id : {static_cast<int>(nameLabel), static_cast<int>(nameId), IDOK, static_cast<int>(newFolderId)})
            ShowWindow(control(id), show ? SW_HIDE : SW_SHOWNA);
        for (const auto id : {addressId, goId, upId, browserId})
            EnableWindow(control(id), !show);
        updateSave();
    }
    void endFolder(bool focus = false) noexcept {
        if (!folderWorker) return;
        folderWorker->revoke();
        folderWorker.reset();
        ++folderRevision;
        KillTimer(panel, kFolderTimer);
        showFolderControls(false);
        if (focus && active()) SetFocus(control(newFolderId));
    }
    void revoke() noexcept {
        revoked = true;
        if (folderWorker) folderWorker->revoke();
        if (const auto worker = saveWorker.lock()) worker->revoke();
    }
    void beginNavigation() {
        if (!navigating) navigationAddress = textOf(control(addressId));
        navigating = true;
        ++folderRevision;
        endFolder();
        updateSave();
    }
    void navigationFailed(const wchar_t* message = L"Не удалось открыть папку. Укажите другой путь.") noexcept {
        if (!choosingFolder()) return;
        ++folderRevision;
        navigating = false;
        navigationAddress.reset();
        confirmedFolder.clear();
        endFolder();
        if (!choosingFolder() || navigating || !confirmedFolder.empty()) return;
        updateSave();
        error(message);
    }

    std::wstring currentFolder() const {
        const auto selectedBrowser = browser;
        winrt::com_ptr<IFolderView> view;
        winrt::com_ptr<IPersistFolder2> folder;
        if (!selectedBrowser || FAILED(selectedBrowser->GetCurrentView(IID_PPV_ARGS(view.put()))) ||
            FAILED(view->GetFolder(IID_PPV_ARGS(folder.put())))) return {};
        PIDLIST_ABSOLUTE raw = nullptr;
        const auto read = folder->GetCurFolder(&raw);
        winrt::com_ptr<IShellItem> item;
        const auto named = SUCCEEDED(read) && raw ? SHCreateItemFromIDList(raw, IID_PPV_ARGS(item.put())) : E_FAIL;
        CoTaskMemFree(raw);
        return SUCCEEDED(named) ? itemPath(item.get()) : L"";
    }

    void navigationComplete(std::wstring path) {
        if (!choosingFolder() || !navigating) return;
        const auto revision = folderRevision;
        const bool valid = localAddress(path) && currentFolder() == path && guardView();
        if (!choosingFolder() || revision != folderRevision) return;
        if (!valid) {
            navigationFailed();
            return;
        }
        const auto address = textOf(control(addressId));
        if (navigationAddress != address) {
            navigationFailed(address.size() >= MAX_PATH ? kLongFolderAddress : kOpenFolderAddress);
            return;
        }
        confirmedFolder = std::move(path);
        SetWindowTextW(control(addressId), confirmedFolder.c_str());
        navigating = false;
        navigationAddress.reset();
        setStatus(L"");
        updateSave();
    }

    void browse(IShellItem* item) {
        const auto selectedBrowser = browser;
        if (!choosingFolder() || folderWorker || !selectedBrowser) return;
        const auto revision = folderRevision;
        SFGAOF attributes{};
        const bool valid = item && localAddress(itemPath(item)) &&
            SUCCEEDED(item->GetAttributes(SFGAO_FOLDER | SFGAO_FILESYSTEM | SFGAO_LINK, &attributes)) &&
            (attributes & (SFGAO_FOLDER | SFGAO_FILESYSTEM | SFGAO_LINK)) == (SFGAO_FOLDER | SFGAO_FILESYSTEM);
        if (!choosingFolder() || folderWorker || revision != folderRevision) return;
        if (!valid) {
            navigationFailed();
            return;
        }
        beginNavigation();
        if (choosingFolder() && FAILED(selectedBrowser->BrowseToObject(item, SBSP_ABSOLUTE))) navigationFailed();
    }

    void browsePath(const std::wstring& path) {
        if (!choosingFolder()) return;
        if (navigating) {
            if (navigationAddress != path) navigationAddress.reset();
            error(path.size() >= MAX_PATH ? kLongFolderAddress : L"Дождитесь открытия папки и повторите.");
            return;
        }
        if (path.size() >= MAX_PATH) {
            navigationFailed(kLongFolderAddress);
            return;
        }
        beginNavigation();
        const auto revision = folderRevision;
        winrt::com_ptr<IShellItem> item;
        const bool valid = localAddress(path) &&
            SUCCEEDED(SHCreateItemFromParsingName(path.c_str(), nullptr, IID_PPV_ARGS(item.put())));
        if (!choosingFolder() || revision != folderRevision) return;
        if (!valid) {
            navigationFailed();
            return;
        }
        browse(item.get());
    }

    void useSelection(IShellView* view, bool open) {
        if (!active() || navigating || folderWorker || !choosingFolder() || !view) return;
        const auto revision = folderRevision;
        winrt::com_ptr<IFolderView2> folder;
        if (FAILED(view->QueryInterface(IID_PPV_ARGS(folder.put())))) return;
        winrt::com_ptr<IShellItemArray> items;
        winrt::com_ptr<IShellItem> item;
        DWORD count = 0;
        if (FAILED(folder->GetSelection(FALSE, items.put())) || !items ||
            FAILED(items->GetCount(&count)) || count != 1 || FAILED(items->GetItemAt(0, item.put()))) return;
        SFGAOF attributes{};
        if (FAILED(item->GetAttributes(SFGAO_FOLDER | SFGAO_FILESYSTEM | SFGAO_LINK, &attributes)) ||
            !(attributes & SFGAO_FILESYSTEM) || (attributes & SFGAO_LINK)) return;
        const auto path = itemPath(item.get());
        if (!active() || navigating || folderWorker || !choosingFolder() || revision != folderRevision) return;
        if (attributes & SFGAO_FOLDER) {
            if (!open || !localAddress(path)) return;
            pendingFolder = std::move(item);
            beginNavigation();
            if (!PostMessageW(panel, kOpenSelected, 0, 0)) navigationFailed();
            return;
        }
        const auto name = std::filesystem::path(path).filename().native();
        if (validExportFilename(name)) SetWindowTextW(control(nameId), name.c_str());
    }

    void submit() {
        if (phase == SavePhase::saving || !active()) return;
        const auto revision = folderRevision;
        const auto mode = phase;
        const auto folder = confirmedFolder;
        const bool validFolder = !navigating && !folder.empty() &&
            (phase == SavePhase::conflict || currentFolder() == folder);
        if (!active() || phase != mode || revision != folderRevision || confirmedFolder != folder) return;
        if (!validFolder) {
            error(L"Дождитесь открытия папки или выберите другую.");
            return;
        }
        if (choosingFolder() && textOf(control(addressId)) != folder) {
            error(kOpenFolderAddress);
            return;
        }
        const auto name = textOf(control(nameId));
        if (!validExportFilename(name)) {
            if (error(L"Введите допустимое имя файла.") && phase == mode && revision == folderRevision)
                if (const auto edit = control(nameId)) SetFocus(edit);
            return;
        }
        auto path = (std::filesystem::path(folder) / name).native();
        auto callback = result;
        phase = SavePhase::saving;
        ++folderRevision;
        updateSave();
        for (const auto id : {addressId, goId, upId, browserId, nameId})
            EnableWindow(control(id), FALSE);
        setStatus(L"Сохраняем файл…");
        if (active()) SetFocus(control(IDCANCEL));
        if (panel && !closing && !revoked && callback) callback(std::move(path), true);
    }

    bool retryAfter(ExportSaveResult failure) noexcept {
        if (!panel || closing || revoked || !retryableExportSave(failure)) return false;
        const bool otherFolder = failure == ExportSaveResult::unavailableLocation;
        const auto next = otherFolder ? SavePhase::location : SavePhase::conflict;
        if (phase == next) return true;
        if (phase != SavePhase::saving) return false;
        phase = next;
        const auto revision = ++folderRevision;
        EnableWindow(control(nameId), TRUE);
        for (const auto id : {addressId, goId, upId, browserId})
            EnableWindow(control(id), otherFolder);
        updateSave();
        if (error(otherFolder ? L"Не удалось сохранить в эту папку. Выберите другую." :
                L"Это имя уже занято. Введите другое имя файла.") && phase == next && revision == folderRevision) {
            if (const auto edit = control(otherFolder ? addressId : nameId)) {
                SetFocus(edit);
                if (active() && revision == folderRevision && GetFocus() == edit)
                    SendMessageW(edit, EM_SETSEL, 0, -1);
            }
        }
        return true;
    }

    void startFolder() {
        if (folderWorker || !choosingFolder() || navigating || confirmedFolder.empty()) return;
        const auto folder = confirmedFolder;
        const auto revision = folderRevision;
        if (currentFolder() != folder || !active() || folderRevision != revision || folderWorker ||
            navigating || confirmedFolder != folder) return;
        if (textOf(control(addressId)) != folder) {
            error(kOpenFolderAddress);
            return;
        }
        folderWorker = ExportFolderWorker::start(folder);
        if (!folderWorker || !SetTimer(panel, kFolderTimer, 50, nullptr)) {
            folderWorker.reset();
            error(L"Не удалось подготовить создание папки.");
            return;
        }
        ++folderRevision;
        SetWindowTextW(control(folderNameId), L"");
        showFolderControls(true);
        setStatus(IsWindowEnabled(control(createFolderId)) ? L"" : L"Проверяем выбранную папку…");
        if (active()) SetFocus(control(folderNameId));
    }

    void createFolder() {
        const auto worker = folderWorker;
        if (!worker || navigating || currentFolder() != confirmedFolder || !active() || folderWorker != worker) return;
        auto name = textOf(control(folderNameId));
        if (!validExportFilename(name) || confirmedFolder.size() + 1 + name.size() >= 260) {
            if (error(L"Введите допустимое имя папки.") && folderWorker == worker && !navigating)
                if (const auto edit = control(folderNameId)) SetFocus(edit);
            return;
        }
        if (worker->create(std::move(name))) {
            setStatus(L"Создаём папку…");
            updateSave();
        }
    }

    void pollFolder() {
        const auto worker = folderWorker;
        if (!worker || !active()) return;
        using Status = ExportFolderWorker::Status;
        const auto state = worker->status();
        if (state == Status::preparing || state == Status::creating) return;
        if (state == Status::ready) {
            if (!IsWindowEnabled(control(createFolderId))) {
                setStatus(L"");
                updateSave();
            }
            return;
        }
        const auto folder = confirmedFolder;
        const auto matches = currentFolder() == folder;
        if (folderWorker != worker || !active()) return;
        if (!matches || navigating || confirmedFolder != folder) { endFolder(); return; }
        const auto revision = folderRevision + 1;
        endFolder();
        if (!active() || navigating || folderRevision != revision || confirmedFolder != folder) return;
        if (state == Status::created) {
            const auto selectedBrowser = browser;
            winrt::com_ptr<IShellView> view;
            if (selectedBrowser && SUCCEEDED(selectedBrowser->GetCurrentView(IID_PPV_ARGS(view.put()))) &&
                active() && folderRevision == revision && confirmedFolder == folder)
                (void)view->Refresh();
        }
        if (!active() || navigating || folderRevision != revision || confirmedFolder != folder) return;
        if (state == Status::created) setStatus(L"Папка создана. Откройте её в списке.");
        else if (!error(state == Status::conflict ? L"Это имя уже занято. Выберите другое." :
            L"Не удалось создать папку. Выберите другое место.")) return;
        if (active() && !navigating && revision == folderRevision) SetFocus(control(newFolderId));
    }

    void complete(std::optional<std::wstring> path) {
        auto callback = std::move(result);
        close();
        if (callback) callback(std::move(path), true);
    }

    static LRESULT CALLBACK keyProc(HWND window, UINT message, WPARAM key, LPARAM parameter,
        UINT_PTR, DWORD_PTR data) noexcept {
        const auto owner = reinterpret_cast<State*>(data)->weak_from_this().lock();
        if (!owner) return DefSubclassProc(window, message, key, parameter);
        auto& self = *owner;
        if (message == WM_SETFOCUS && self.active()) {
            self.reveal(window);
            if (!self.panel || !IsChild(self.panel, window)) return 0;
        }
        const bool shell = self.viewWindow && (window == self.viewWindow || IsChild(self.viewWindow, window));
        if (shell && (message == WM_CONTEXTMENU || message == WM_RBUTTONDOWN || message == WM_RBUTTONUP ||
            message == WM_RBUTTONDBLCLK || message == WM_MBUTTONDOWN || message == WM_MBUTTONUP || message == WM_DROPFILES))
            return 0;
        if (self.active() && GetFocus() == window && (message == WM_KEYDOWN || message == WM_SYSKEYDOWN)) {
            if (key == VK_TAB) { self.moveFocus(window); return 0; }
            if (key == VK_ESCAPE) { PostMessageW(self.panel, WM_CLOSE, 0, 0); return 0; }
            if (key == VK_RETURN && !shell) {
                const auto id = GetDlgCtrlID(window);
                const auto command = id == addressId ? goId : id == nameId ? IDOK :
                    id == folderNameId ? createFolderId : id;
                PostMessageW(self.panel, WM_COMMAND, MAKEWPARAM(command, BN_CLICKED),
                    reinterpret_cast<LPARAM>(self.control(command)));
                return 0;
            }
            if (shell && (key == VK_DELETE || key == VK_APPS || key == VK_F2 || key == VK_F10 ||
                GetKeyState(VK_CONTROL) < 0 || GetKeyState(VK_MENU) < 0)) return 0;
        }
        if (message == WM_CHAR && (key == L'\t' || key == VK_ESCAPE || (key == L'\r' && !shell))) return 0;
        return DefSubclassProc(window, message, key, parameter);
    }

    void moveFocus(HWND focused) noexcept {
        HWND order[]{control(addressId), control(goId), control(upId),
            folderWorker || !choosingFolder() ? nullptr : viewWindow,
            control(nameId), control(IDOK), control(folderNameId), control(createFolderId), control(IDCANCEL), control(newFolderId)};
        constexpr auto count = static_cast<int>(std::size(order));
        int at = 0;
        for (; at < count; ++at)
            if (order[at] && (focused == order[at] || IsChild(order[at], focused))) break;
        const int direction = GetKeyState(VK_SHIFT) < 0 ? -1 : 1;
        for (int i = 0; i < count; ++i) {
            at = (at + direction + count) % count;
            const auto next = order[at];
            if (!next || !IsWindowEnabled(next) || !IsWindowVisible(next)) continue;
            reveal(next);
            if (!active() || !IsChild(panel, next) || !IsWindowEnabled(next) || !IsWindowVisible(next)) return;
            if (next == viewWindow) {
                winrt::com_ptr<IShellView> view;
                if (browser && SUCCEEDED(browser->GetCurrentView(IID_PPV_ARGS(view.put()))))
                    (void)view->UIActivate(SVUIA_ACTIVATE_FOCUS);
            } else SetFocus(next);
            return;
        }
    }

    bool guardChild(HWND child) noexcept {
        DragAcceptFiles(child, FALSE);
        (void)RevokeDragDrop(child);
        return SetWindowSubclass(child, keyProc, kSubclass, reinterpret_cast<DWORD_PTR>(this)) != FALSE;
    }

    bool guardView() noexcept {
        if (!viewWindow || !guardChild(viewWindow)) return false;
        struct Guard { State* state; bool success; } guard{this, true};
        EnumChildWindows(viewWindow, [](HWND child, LPARAM value) -> BOOL {
            auto& guard = *reinterpret_cast<Guard*>(value);
            return guard.success = guard.state->guardChild(child);
        }, reinterpret_cast<LPARAM>(&guard));
        return guard.success;
    }

    static LRESULT CALLBACK ownerProc(HWND window, UINT message, WPARAM w, LPARAM l,
        UINT_PTR id, DWORD_PTR data) noexcept {
        const auto self = reinterpret_cast<State*>(data)->weak_from_this().lock();
        if (self && message == WM_DESTROY) self->revoke();
        const auto result = DefSubclassProc(window, message, w, l);
        if (self && self->panel && (message == WM_SIZE || message == WM_DPICHANGED)) {
            self->layout();
            if (self->active()) self->reveal(GetFocus());
        }
        if (message == WM_NCDESTROY) RemoveWindowSubclass(window, ownerProc, id);
        return result;
    }

    static LRESULT CALLBACK panelProc(HWND window, UINT message, WPARAM w, LPARAM l) noexcept {
        if (message == WM_NCCREATE) {
            const auto create = reinterpret_cast<CREATESTRUCTW*>(l);
            SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(create->lpCreateParams));
        }
        const auto raw = reinterpret_cast<State*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        const auto self = raw ? raw->weak_from_this().lock() : nullptr;
        if (message == WM_NCDESTROY) {
            // Child controls are gone, including when close() detached State.
            delete reinterpret_cast<PanelFontRef*>(SetWindowLongPtrW(window, 0, 0));
        }
        if (self) {
            try {
                if (message == WM_DESTROY) {
                    self->revoke();
                } else if (message == WM_NCDESTROY) {
                    self->revoke();
                    self->folderWorker.reset();
                    SetWindowLongPtrW(window, GWLP_USERDATA, 0);
                    self->panel = nullptr;
                    self->closing = true;
                    auto callback = std::move(self->result);
                    self->releaseBrowser();
                    if (callback) callback(std::nullopt, false);
                } else if (message == WM_CLOSE) {
                    if (self->active()) {
                        if (self->folderWorker) { self->endFolder(true); self->setStatus(L""); }
                        else self->complete(std::nullopt);
                    }
                    return 0;
                } else if (message == WM_VSCROLL && self->active() && !l) {
                    self->scroll(LOWORD(w));
                    return 0;
                } else if (message == WM_TIMER && w == kFolderTimer) {
                    self->pollFolder();
                    return 0;
                } else if (message == kRelayout) {
                    self->layoutPosted = false;
                    self->layout();
                    return 0;
                } else if (message == kOpenSelected && self->active() && self->choosingFolder()) {
                    const auto item = std::exchange(self->pendingFolder, {});
                    self->browse(item.get());
                    return 0;
                } else if (message == WM_COMMAND && self->active() && HIWORD(w) == BN_CLICKED &&
                    l && reinterpret_cast<HWND>(l) == self->control(LOWORD(w)) &&
                    IsWindowVisible(reinterpret_cast<HWND>(l)) && IsWindowEnabled(reinterpret_cast<HWND>(l))) {
                    switch (LOWORD(w)) {
                    case goId: self->browsePath(textOf(self->control(addressId))); break;
                    case upId:
                        if (!self->navigating) self->browsePath(std::filesystem::path(self->confirmedFolder).parent_path().native());
                        break;
                    case IDOK: self->submit(); break;
                    case newFolderId: self->startFolder(); break;
                    case createFolderId: self->createFolder(); break;
                    case IDCANCEL:
                        if (self->folderWorker) { self->endFolder(true); self->setStatus(L""); }
                        else self->complete(std::nullopt);
                        break;
                    default: break;
                    }
                    return 0;
                }
            } catch (...) { self->error(L"Не удалось выполнить действие. Попробуйте ещё раз."); }
        }
        return DefWindowProcW(window, message, w, l);
    }

    void updateFont(HWND window, UINT dpi) noexcept try {
        if (fontDpi == dpi) return;
        NONCLIENTMETRICSW metrics{};
        metrics.cbSize = sizeof(metrics);
        if (!SystemParametersInfoForDpi(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0, dpi)) return;
        const auto font = std::make_shared<PanelFont>();
        font->handle = CreateFontIndirectW(&metrics.lfMessageFont);
        if (!font->handle) return;
        auto windowFont = std::make_unique<PanelFontRef>(font);
        SetLastError(ERROR_SUCCESS);
        const auto oldSlot = SetWindowLongPtrW(window, 0, reinterpret_cast<LONG_PTR>(windowFont.get()));
        if (!oldSlot && GetLastError() != ERROR_SUCCESS) return;
        windowFont.release();
        const std::unique_ptr<PanelFontRef> previous(reinterpret_cast<PanelFontRef*>(oldSlot));
        fontDpi = dpi;
        for (const int id : {int(titleId), int(addressLabel), int(addressId), int(goId), int(upId),
                int(nameLabel), int(nameId), int(statusId), int(newFolderId), int(folderLabel),
                int(folderNameId), int(createFolderId), IDOK, IDCANCEL}) {
            if (panel != window) break;
            SendMessageW(GetDlgItem(window, id), WM_SETFONT, reinterpret_cast<WPARAM>(font->handle), FALSE);
        }
    } catch (const std::bad_alloc&) {} // Keep the previous font if allocation fails.

    void scrollTo(int position) noexcept {
        const auto next = std::clamp(position, 0, scrollLimit);
        if (next == scrollOffset) return;
        scrollOffset = next;
        layout();
    }

    void scroll(unsigned command) noexcept {
        SCROLLINFO info{sizeof(info), SIF_PAGE | SIF_TRACKPOS};
        if (!GetScrollInfo(panel, SB_VERT, &info)) return;
        switch (command) {
        case SB_TOP: scrollTo(0); break;
        case SB_BOTTOM: scrollTo(scrollLimit); break;
        case SB_LINEUP: scrollTo(scrollOffset - scrollStep); break;
        case SB_LINEDOWN: scrollTo(scrollOffset + scrollStep); break;
        case SB_PAGEUP: scrollTo(scrollOffset - static_cast<int>(info.nPage)); break;
        case SB_PAGEDOWN: scrollTo(scrollOffset + static_cast<int>(info.nPage)); break;
        case SB_THUMBTRACK: scrollTo(info.nTrackPos); break;
        }
    }

    void reveal(HWND child) noexcept {
        if (!scrollLimit || !panel || !child || !IsChild(panel, child)) return;
        auto parent = GetParent(child);
        while (parent && parent != panel) {
            child = parent;
            parent = GetParent(child);
        }
        RECT rect{}, bounds{};
        if (parent != panel || !GetWindowRect(child, &rect) || !GetClientRect(panel, &bounds)) return;
        MapWindowPoints(nullptr, panel, reinterpret_cast<POINT*>(&rect), 2);
        if (rect.top < 0 || rect.bottom - rect.top >= bounds.bottom)
            scrollTo(scrollOffset + rect.top);
        else if (rect.bottom > bounds.bottom)
            scrollTo(scrollOffset + rect.bottom - bounds.bottom);
    }

    int statusHeight(int width, int row) const noexcept {
        const auto label = control(statusId);
        wchar_t message[256]{};
        if (!GetWindowTextW(label, message, static_cast<int>(std::size(message)))) return row;
        const auto dc = GetDC(label);
        if (!dc) return row;
        const auto font = reinterpret_cast<HFONT>(SendMessageW(label, WM_GETFONT, 0, 0));
        const auto previous = font ? SelectObject(dc, font) : nullptr;
        RECT rect{0, 0, width, 0};
        DrawTextW(dc, message, -1, &rect, DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX);
        if (previous && previous != HGDI_ERROR) SelectObject(dc, previous);
        ReleaseDC(label, dc);
        return std::max(row, static_cast<int>(rect.bottom));
    }

    void layout() noexcept {
        const auto window = panel;
        if (!window || closing || revoked) return;
        if (layingOut) {
            layoutPending = true;
            return;
        }
        layoutPending = false;
        layingOut = true;
        layoutControls(window);
        layingOut = false;
        if (layoutPending && !layoutPosted && panel == window && !closing && !revoked)
            layoutPosted = PostMessageW(window, kRelayout, 0, 0) != FALSE;
    }

    void layoutControls(HWND window) noexcept {
        RECT bounds{};
        if (!GetClientRect(owner, &bounds)) return;
        const auto dpi = GetDpiForWindow(owner);
        const auto effectiveDpi = dpi ? dpi : 96u;
        const auto px = [effectiveDpi](int unit) { return MulDiv(unit, static_cast<int>(effectiveDpi), 96); };
        const int w = bounds.right, h = bounds.bottom;
        if (w <= 0 || h <= 0) return;
        updateFont(window, effectiveDpi);
        const auto current = [&] { return panel == window && !closing && !revoked; };
        if (!current()) return;
        SetWindowPos(window, HWND_TOP, 0, 0, w, h, SWP_NOACTIVATE);
        int row{}, button{}, gap{}, folderButton{}, margin{};
        const auto setDensity = [&](bool compact) {
            row = px(compact ? 26 : 30);
            button = px(compact ? 88 : 98);
            gap = px(compact ? 6 : 8);
            folderButton = px(compact ? 108 : 112);
            margin = px(compact ? 10 : 16);
        };
        const bool shortWindow = h < px(300);
        setDensity(shortWindow);
        struct Geometry {
            int usable, status, listTop, listHeight, footer, actions, total;
            bool addressWrap, nameWrap, stackActions, wrapFolder;
        };
        const auto geometry = [&](int width) {
            Geometry g{};
            g.usable = std::max(1, std::min(width - 2 * margin, px(700)));
            g.addressWrap = g.usable < 2 * (button + gap) + px(80);
            g.nameWrap = g.usable < px(170);
            g.stackActions = g.usable < 2 * button + gap;
            g.wrapFolder = g.usable < 2 * (button + gap) + folderButton;
            g.status = statusHeight(g.usable, row);
            g.listTop = margin + (g.addressWrap ? 4 : 3) * row + (g.stackActions ? row : 0);
            const int footerHeight = 2 * gap + 2 * row + g.status + (g.nameWrap ? row : 0)
                + (g.stackActions ? row + gap : 0) + (g.wrapFolder ? row + gap : 0);
            g.listHeight = std::max(2 * row, h - g.listTop - footerHeight - margin);
            g.footer = g.listTop + g.listHeight;
            g.actions = g.footer + 2 * gap + row + (g.nameWrap ? row : 0) + g.status;
            g.total = g.footer + footerHeight + margin;
            return g;
        };
        auto g = geometry(w);
        if (!shortWindow && g.total > h && current()) {
            setDensity(true);
            g = geometry(w);
        }
        if (!current()) return;
        const bool needScroll = g.total > h;
        ShowScrollBar(window, SB_VERT, needScroll ? TRUE : FALSE);
        if (!current() || !GetClientRect(window, &bounds)) return;
        const int available = bounds.right;
        if (available <= 0) return;
        if (available != w) g = geometry(available);
        if (!current()) return;
        scrollLimit = std::max(0, g.total - h);
        scrollOffset = std::clamp(scrollOffset, 0, scrollLimit);
        scrollStep = row;
        if (needScroll) {
            SCROLLINFO info{sizeof(info), SIF_RANGE | SIF_PAGE | SIF_POS, 0, g.total - 1,
                static_cast<UINT>(h), scrollOffset};
            SetScrollInfo(window, SB_VERT, &info, TRUE);
        }
        const int x = std::max(0, (available - g.usable) / 2);
        const auto place = [&](int id, int left, int top, int width, int height) {
            if (current()) MoveWindow(GetDlgItem(window, id), left, top - scrollOffset, width, height, TRUE);
        };
        place(titleId, x, margin, g.usable, row);
        place(addressLabel, x, margin + row, g.usable, row);
        const int address = g.addressWrap ? g.usable : g.usable - 2 * (button + gap);
        const int addressY = margin + 2 * row;
        const int browseX = g.addressWrap ? x : x + address + gap;
        const int browseY = addressY + (g.addressWrap ? row : 0);
        const int browseWidth = g.stackActions ? g.usable : button;
        place(addressId, x, addressY, address, row - gap / 2);
        place(goId, browseX, browseY, browseWidth, row - gap / 2);
        place(upId, g.stackActions ? browseX : browseX + browseWidth + gap,
            browseY + (g.stackActions ? row : 0), browseWidth, row - gap / 2);
        RECT previousView{};
        GetClientRect(control(browserId), &previousView);
        place(browserId, x, g.listTop, g.usable, g.listHeight);
        if (current() && browser && initialized &&
            (previousView.right != g.usable || previousView.bottom != g.listHeight)) {
            const auto selectedBrowser = browser;
            RECT view{0, 0, g.usable, g.listHeight};
            (void)selectedBrowser->SetRect(nullptr, view);
        }
        const int nameY = g.footer + gap;
        const int labelWidth = g.nameWrap ? g.usable : px(90);
        const int nameX = g.nameWrap ? x : x + labelWidth;
        const int nameWidth = g.nameWrap ? g.usable : g.usable - labelWidth;
        place(nameLabel, x, nameY, labelWidth, row);
        place(nameId, nameX, nameY + (g.nameWrap ? row : 0), nameWidth, row);
        place(folderLabel, x, nameY, labelWidth, row);
        place(folderNameId, nameX, nameY + (g.nameWrap ? row : 0), nameWidth, row);
        place(statusId, x, nameY + row + (g.nameWrap ? row : 0), g.usable, g.status);
        const int actionWidth = g.stackActions ? g.usable : button;
        place(IDOK, x, g.actions, actionWidth, row);
        place(createFolderId, x, g.actions, actionWidth, row);
        place(IDCANCEL, g.stackActions ? x : x + button + gap,
            g.actions + (g.stackActions ? row + gap : 0), actionWidth, row);
        place(newFolderId, g.wrapFolder ? x : x + 2 * (button + gap),
            g.actions + (g.stackActions ? row + gap : 0) + (g.wrapFolder ? row + gap : 0),
            std::min(folderButton, g.usable), row);
    }

    bool initialize(const std::wstring& filename) {
        WNDCLASSW wc{};
        wc.lpfnWndProc = panelProc;
        wc.cbWndExtra = sizeof(LONG_PTR);
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
        wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_BTNFACE + 1);
        wc.lpszClassName = kPanelClass;
        if (!RegisterClassW(&wc) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) return false;
        panel = CreateWindowExW(WS_EX_CONTROLPARENT, kPanelClass, L"Сохранение экспорта",
            WS_CHILD | WS_CLIPSIBLINGS | WS_CLIPCHILDREN | WS_VSCROLL, 0, 0, 0, 0, owner, nullptr, wc.hInstance, this);
        if (!panel) return false;
        const auto add = [&](int id, const wchar_t* type, const wchar_t* label, DWORD styles = 0, DWORD extra = 0) {
            const auto child = CreateWindowExW(extra, type, label, WS_CHILD | WS_VISIBLE | styles,
                0, 0, 0, 0, panel, reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), wc.hInstance, nullptr);
            if (!child) return false;
            SendMessageW(child, WM_SETFONT, reinterpret_cast<WPARAM>(GetStockObject(DEFAULT_GUI_FONT)), FALSE);
            return !(styles & WS_TABSTOP) || SetWindowSubclass(child, keyProc, kSubclass, reinterpret_cast<DWORD_PTR>(this));
        };
        if (!add(titleId, L"STATIC", L"Сохранить экспорт") ||
            !add(addressLabel, L"STATIC", L"Папка") ||
            !add(addressId, L"EDIT", L"", WS_TABSTOP | ES_AUTOHSCROLL, WS_EX_CLIENTEDGE) ||
            !add(goId, L"BUTTON", L"Открыть", WS_TABSTOP) ||
            !add(upId, L"BUTTON", L"Выше", WS_TABSTOP) ||
            !add(browserId, L"STATIC", L"", WS_CLIPCHILDREN) ||
            !add(nameLabel, L"STATIC", L"Имя файла") ||
            !add(nameId, L"EDIT", filename.c_str(), WS_TABSTOP | ES_AUTOHSCROLL, WS_EX_CLIENTEDGE) ||
            !add(newFolderId, L"BUTTON", L"Новая папка", WS_TABSTOP) ||
            !add(folderLabel, L"STATIC", L"Имя папки") ||
            !add(folderNameId, L"EDIT", L"", WS_TABSTOP | ES_AUTOHSCROLL, WS_EX_CLIENTEDGE) ||
            !add(createFolderId, L"BUTTON", L"Создать", WS_TABSTOP | BS_DEFPUSHBUTTON) ||
            !add(statusId, L"STATIC", L"") || !add(IDOK, L"BUTTON", L"Сохранить", WS_TABSTOP | BS_DEFPUSHBUTTON) ||
            !add(IDCANCEL, L"BUTTON", L"Отмена", WS_TABSTOP)) return false;
        const auto status = control(statusId);
        statusProvider = winrt::make_self<StatusProvider>(status);
        if (!SetWindowSubclass(status, StatusProvider::subclass, kSubclass,
            reinterpret_cast<DWORD_PTR>(statusProvider.get()))) statusProvider = nullptr;
        SendMessageW(control(nameId), EM_SETLIMITTEXT, 255, 0);
        SendMessageW(control(folderNameId), EM_SETLIMITTEXT, 255, 0);
        showFolderControls(false);
        // Keep an unsupported address intact so it cannot become a different valid folder.
        SendMessageW(control(addressId), EM_SETLIMITTEXT, 32767, 0);
        if (!SetWindowSubclass(owner, ownerProc, reinterpret_cast<UINT_PTR>(this), reinterpret_cast<DWORD_PTR>(this))) return false;

        if (FAILED(CoCreateInstance(__uuidof(ExplorerBrowser), nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(browser.put()))))
            return false;
        const auto site = winrt::make_self<Site>(weak_from_this());
        const auto withSite = browser.try_as<IObjectWithSite>();
        if (!withSite || FAILED(withSite->SetSite(static_cast<IServiceProvider*>(site.get())))) return false;
        RECT viewport{};
        FOLDERSETTINGS settings{FVM_LIST, FWF_AUTOARRANGE | FWF_SINGLESEL | FWF_NOWEBVIEW};
        if (FAILED(browser->Initialize(control(browserId), &viewport, &settings))) return false;
        initialized = true;
        if (FAILED(browser->Advise(site.get(), &navigationCookie)) ||
            FAILED(browser->SetOptions(static_cast<EXPLORER_BROWSER_OPTIONS>(EBO_NOTRAVELLOG | EBO_NOPERSISTVIEWSTATE))))
            return false;
        layout();
        updateSave();
        PWSTR raw = nullptr;
        const auto downloads = SHGetKnownFolderPath(FOLDERID_Downloads, KF_FLAG_DONT_VERIFY, nullptr, &raw);
        const std::unique_ptr<wchar_t, decltype(&CoTaskMemFree)> folder(raw, CoTaskMemFree);
        if (SUCCEEDED(downloads) && folder) browsePath(folder.get());
        else navigationFailed();
        const auto window = panel;
        if (!active() || !SetWindowPos(window, HWND_TOP, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE) ||
            panel != window || closing || revoked) return false;
        if (const auto edit = active() ? control(nameId) : nullptr) {
            SetFocus(edit);
            if (active() && control(nameId) == edit) SendMessageW(edit, EM_SETSEL, 0, -1);
        }
        return panel == window && !closing && !revoked;
    }

    void releaseBrowser() noexcept {
        pendingFolder = nullptr;
        viewWindow = nullptr;
        if (!browser) return;
        if (navigationCookie) (void)browser->Unadvise(std::exchange(navigationCookie, 0));
        if (const auto site = browser.try_as<IObjectWithSite>()) (void)site->SetSite(nullptr);
        if (std::exchange(initialized, false)) (void)browser->Destroy();
        browser = nullptr;
    }

    void close() noexcept {
        revoke();
        closing = true;
        if (panel && folderWorker) KillTimer(panel, kFolderTimer);
        folderWorker.reset();
        result = {};
        RemoveWindowSubclass(owner, ownerProc, reinterpret_cast<UINT_PTR>(this));
        if (panel) SetWindowPos(panel, nullptr, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_HIDEWINDOW | SWP_NOACTIVATE);
        if (panel) EnumChildWindows(panel, [](HWND child, LPARAM) -> BOOL {
            RemoveWindowSubclass(child, keyProc, kSubclass);
            return TRUE;
        }, 0);
        if (const auto provider = std::exchange(statusProvider, {})) provider->detach();
        releaseBrowser();
        if (const auto closingPanel = std::exchange(panel, nullptr)) {
            // Detach the window procedure even if destruction is rejected.
            SetWindowLongPtrW(closingPanel, GWLP_USERDATA, 0);
            DestroyWindow(closingPanel);
        }
    }
};

ExportSavePanel::ExportSavePanel(std::shared_ptr<State> state) : state_(std::move(state)) {}
ExportSavePanel::~ExportSavePanel() { close(); }

std::unique_ptr<ExportSavePanel> ExportSavePanel::open(HWND owner, const std::wstring& suggestedName, Result result) {
    if (!owner || GetForegroundWindow() != owner || GetWindowThreadProcessId(owner, nullptr) != GetCurrentThreadId())
        return {};
    auto state = std::make_shared<State>();
    state->owner = owner;
    state->result = std::move(result);
    auto panel = std::unique_ptr<ExportSavePanel>(new ExportSavePanel(state));
    return state->initialize(suggestedName) ? std::move(panel) : nullptr;
}

void ExportSavePanel::revoke() noexcept { state_->revoke(); }
void ExportSavePanel::close() noexcept { state_->close(); }
void ExportSavePanel::watch(const std::shared_ptr<ExportSaveWorker>& worker) noexcept {
    if (state_->revoked || state_->closing) worker->revoke();
    else state_->saveWorker = worker;
}
bool ExportSavePanel::retryAfter(ExportSaveResult result) noexcept {
    const auto state = state_;
    return state->retryAfter(result);
}
bool ExportSavePanel::acceptsResult() const noexcept {
    return state_->panel && !state_->closing && !state_->revoked;
}

} // namespace graf::windows
#endif
