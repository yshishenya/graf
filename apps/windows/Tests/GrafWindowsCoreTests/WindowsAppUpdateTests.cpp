#include "../../RecApp/Shell/WindowsAppUpdateController.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>
#include <string_view>
#ifdef _WIN32
#include <winrt/base.h>
#endif

using namespace graf::windows;

struct Probe {
    std::optional<AppUpdateResult> result;
    int starts = 0;
    int cancels = 0;
    int polls = 0;
    int destroyed = 0;
    std::function<void()> onPoll{};
    std::function<void()> onCancel{};
};
struct Operation final : AppUpdateCheckOperation {
    explicit Operation(Probe& probe) : probe(probe) { ++probe.starts; }
    ~Operation() override { ++probe.destroyed; }
    std::optional<AppUpdateResult> poll() override {
        ++probe.polls;
        if (probe.onPoll) probe.onPoll();
        return probe.result;
    }
    void cancel() noexcept override {
        ++probe.cancels;
        if (probe.onCancel) probe.onCancel();
    }
    Probe& probe;
};

void testCheckPollReentrancy() {
    const auto now = WindowsAppUpdateController::Clock::time_point{};
    for (const bool terminal : {false, true}) {
        for (const bool closeDuringPoll : {false, true}) {
            Probe probe;
            WindowsAppUpdateController controller([&] { return std::make_unique<Operation>(probe); });
            assert(controller.check(now));
            if (terminal) probe.result = AppUpdateResult{AppUpdateState::available};
            probe.onCancel = [&] {
                controller.tick(now); // Cancel may pump COM too.
                controller.close();
                assert(probe.polls == 1 && probe.destroyed == 0);
            };
            probe.onPoll = [&] {
                assert(probe.polls == 1); // No recursive poll of this check operation.
                controller.tick(now);
                if (closeDuringPoll) controller.close();
                controller.tick(now);
                assert(probe.destroyed == 0); // Outer poll still owns its object.
                assert(controller.busy());
                assert(!controller.check(now));
                assert(!controller.beginInstall(now, false, true));
            };
            controller.tick(now);
            assert(probe.polls == 1);
            assert(probe.destroyed == (terminal ? 1 : 0));
            assert(controller.busy() == !terminal);
            assert(probe.cancels == (closeDuringPoll ? 1 : 0));
            assert(controller.result().state == (closeDuringPoll ? AppUpdateState::idle
                : terminal ? AppUpdateState::available : AppUpdateState::checking));
            if (!terminal) {
                probe.onPoll = {};
                probe.result = AppUpdateResult{AppUpdateState::available};
                controller.tick(now);
                assert(probe.destroyed == 1 && !controller.busy());
                assert(controller.available() == !closeDuringPoll); // Closed check ignores late success.
            }
        }
    }
}

// Only synthetic native configuration; no test invokes a Windows installer.
AppUpdateApprovedRelease approvedRelease() {
    return {L"Synthetic.Graf_1.0.0.0_x64__synthetic", L"CN=Synthetic", L"x64",
            L"https://updates.example.invalid/approved.appinstaller"};
}

void testCheckPollException() {
    using namespace std::chrono_literals;
    const auto now = WindowsAppUpdateController::Clock::time_point{};
    for (const auto lateState : {AppUpdateState::available, AppUpdateState::required}) {
        // Open, previously closed, timed out, close in poll, close in Cancel.
        for (const int scenario : {0, 1, 2, 3, 4}) {
            Probe probe;
            WindowsAppUpdateController controller([&] { return std::make_unique<Operation>(probe); },
                approvedRelease());
            assert(controller.check(now));
            probe.onCancel = [&] {
                assert(probe.cancels == 1 && probe.destroyed == 0);
                const auto polls = probe.polls;
                controller.tick(now);
                if (scenario == 4) controller.close();
                assert(probe.polls == polls && probe.destroyed == 0);
                assert(controller.busy() && !controller.blocksNewWork());
                assert(!controller.check(now) && !controller.beginInstall(now, false, true));
            };
            probe.onPoll = [&] {
                const auto polls = probe.polls;
                controller.tick(now);
                if (scenario == 3) controller.close();
                assert(probe.polls == polls && probe.destroyed == 0);
                assert(controller.busy() && !controller.blocksNewWork());
                assert(!controller.check(now) && !controller.beginInstall(now, false, true));
                throw std::runtime_error("synthetic unknown check status");
            };
            if (scenario == 1) controller.close();
            controller.tick(scenario == 2 ? now + 30s : now);
            const auto expected = controller.result();
            assert(expected.state == (scenario == 0 || scenario == 2
                ? AppUpdateState::error : AppUpdateState::idle));
            assert(expected.reason == (scenario == 2 ? AppUpdateReason::timeout : AppUpdateReason::none));
            if (scenario == 0)
                assert(appUpdateDetail(expected, true).find(L"Ожидаем завершения") != std::wstring::npos);
            controller.tick(now + 31s); // Repeated exception cannot replace close/timeout/error.
            assert(probe.polls == 2 && probe.cancels == 1 && probe.destroyed == 0);
            probe.onPoll = {};
            controller.tick(now + 32s); // Cancellation may remain pending after the exception.
            assert(controller.busy() && !controller.blocksNewWork());
            assert(!controller.check(now) && !controller.beginInstall(now, false, true));
            probe.result = AppUpdateResult{lateState};
            controller.tick(now + 33s);
            assert(!controller.busy() && probe.destroyed == 1 && probe.cancels == 1);
            assert(controller.result().state == expected.state && controller.result().reason == expected.reason);
            assert(!controller.available() && !controller.canInstall());
            assert(controller.check(now + 34s));
            assert(probe.starts == 2);
            probe.result = AppUpdateResult{AppUpdateState::current};
            controller.tick(now + 34s);
            assert(!controller.busy() && probe.destroyed == 2);
            assert(controller.result().state == AppUpdateState::current);
        }
    }
}

struct InstallProbe {
    AppUpdateReason preparation = AppUpdateReason::none;
    std::optional<AppUpdateResult> result;
    std::function<void()> onPrepare;
    std::function<void()> onStart;
    std::function<void()> onPoll;
    bool throwOnPoll = false;
    int factories = 0, prepares = 0, starts = 0, cancels = 0;
};

struct InstallOperation final : AppUpdateInstallOperation {
    explicit InstallOperation(InstallProbe& value) : probe(value) {}
    AppUpdateReason prepare(const AppUpdateApprovedRelease&) override {
        ++probe.prepares;
        if (probe.onPrepare) probe.onPrepare();
        return probe.preparation;
    }
    void start() override {
        ++probe.starts;
        if (probe.onStart) probe.onStart();
    }
    std::optional<AppUpdateResult> poll() override {
        if (probe.onPoll) probe.onPoll();
        if (probe.throwOnPoll) throw std::runtime_error("synthetic poll failure");
        return probe.result;
    }
    void cancel() noexcept override { ++probe.cancels; }
    InstallProbe& probe;
};

struct InstallFixture {
    using Clock = WindowsAppUpdateController::Clock;
    Clock::time_point now{};
    Probe checkProbe{AppUpdateResult{AppUpdateState::available}};
    InstallProbe install;
    WindowsAppUpdateController controller;
    explicit InstallFixture(std::optional<AppUpdateApprovedRelease> approved = approvedRelease())
        : controller([this] { return std::make_unique<Operation>(checkProbe); }, std::move(approved),
                     [this] {
                         ++install.factories;
                         return std::make_unique<InstallOperation>(install);
                     }, [this] { return now; }) {
        assert(controller.check(now));
        controller.tick(now);
    }
    void tick(bool drained = true, const std::function<bool()>& ready = [] { return true; }) {
        controller.tick(now, drained, ready);
    }
};

void testInstall() {
    using namespace std::chrono_literals;
    const auto approved = approvedRelease();
    assert(approved.matchesPackage(approved.packageFullName, approved.publisher,
                                   approved.architecture, approved.appInstallerUri));
    assert(!approved.matchesPackage(L"different-version", approved.publisher,
                                    approved.architecture, approved.appInstallerUri));
    assert(!approved.matchesPackage(approved.packageFullName, L"CN=Other",
                                    approved.architecture, approved.appInstallerUri));
    assert(!approved.matchesPackage(approved.packageFullName, approved.publisher,
                                    L"arm64", approved.appInstallerUri));
    assert(!approved.matchesPackage(approved.packageFullName, approved.publisher,
                                    approved.architecture, approved.appInstallerUri + L"/other"));
    {
        InstallFixture f(std::nullopt);
        assert(!f.controller.canInstall());
        assert(!f.controller.beginInstall(f.now, false, true));
        assert(f.controller.result().reason == AppUpdateReason::noApprovedRelease);
        assert(!f.controller.blocksNewWork() && f.install.factories == 0);
    }
    for (const bool activeCapture : {false, true}) {
        InstallFixture f;
        assert(!f.controller.beginInstall(f.now, activeCapture, activeCapture));
        assert(!f.controller.blocksNewWork() && f.install.factories == 0);
        assert(f.controller.result().reason == (activeCapture ? AppUpdateReason::captureActive
                                                            : AppUpdateReason::custodyUnhealthy));
    }
    {
        InstallFixture f;
        assert(f.controller.canInstall());
        assert(f.controller.beginInstall(f.now, false, true));
        assert(f.controller.result().state == AppUpdateState::preparing);
        assert(f.controller.blocksNewWork() && f.controller.busy());
        assert(!f.controller.check(f.now) && !f.controller.beginInstall(f.now, false, true));
        f.tick(false);
        assert(f.install.factories == 0); // Drain is not cancellation of work.
        f.controller.close();
        assert(!f.controller.blocksNewWork());
        f.tick();
        assert(f.install.starts == 0);
    }
    for (const bool duringPrepare : {false, true}) {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        if (duringPrepare) f.install.onPrepare = [&] { f.now += 30s; };
        else f.now += 30s;
        f.tick();
        assert(f.controller.result().reason == AppUpdateReason::timeout);
        assert(!f.controller.blocksNewWork() && f.install.starts == 0);
    }
    for (const auto reason : {AppUpdateReason::invalidSource, AppUpdateReason::restartFailed}) {
        InstallFixture f;
        f.install.preparation = reason;
        assert(f.controller.beginInstall(f.now, false, true));
        f.tick();
        assert(f.controller.result().reason == reason);
        assert(!f.controller.blocksNewWork() && f.install.starts == 0);
    }
    {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        int readyCalls = 0;
        f.tick(true, [&] {
            ++readyCalls;
            assert(f.install.prepares == 1 && f.install.starts == 0);
            return false;
        });
        assert(readyCalls == 1 && f.install.starts == 0);
        assert(!f.controller.blocksNewWork());
    }
    for (const int action : {0, 1, 2, 3}) {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        f.tick(true, [&] {
            if (action == 0) f.now += 30s;
            if (action == 1) f.controller.close();
            if (action == 2) throw std::runtime_error("synthetic readiness failure");
            if (action == 3) {
                f.controller.close();
                assert(!f.controller.blocksNewWork());
                assert(f.controller.busy());
                assert(!f.controller.check(f.now));
                assert(!f.controller.beginInstall(f.now, false, true));
            }
            return true;
        });
        assert(f.install.starts == 0); // Expiry/close/old readiness cannot admit another attempt.
        assert(!f.controller.blocksNewWork());
        if (action == 3) {
            assert(f.controller.check(f.now)); f.controller.tick(f.now);
            assert(f.controller.beginInstall(f.now, false, true));
            f.tick(); assert(f.install.starts == 1);
        }
    }
    {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        f.controller.tick(f.now); // Check-only caller cannot silently authorize installation.
        assert(f.install.starts == 0);
        f.tick(true, {});
        assert(f.install.starts == 0 && !f.controller.blocksNewWork());
    }
    for (const bool cancel : {false, true}) {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        f.tick();
        assert(f.install.starts == 1 && f.controller.result().state == AppUpdateState::installing);
        f.now += 90s; // Thirty seconds is a preparation deadline, NOT an install timeout.
        if (cancel) { f.controller.close(); f.controller.close(); }
        f.tick();
        assert(f.controller.blocksNewWork() && !f.controller.check(f.now));
        assert(f.install.cancels == (cancel ? 1 : 0));
        f.install.throwOnPoll = true;
        f.tick();
        assert(f.controller.blocksNewWork()); // A failed status read is not OS completion.
        f.install.throwOnPoll = false;
        f.install.result = AppUpdateResult{AppUpdateState::installed};
        f.tick();
        assert(!f.controller.blocksNewWork() && !f.controller.busy());
        // Cancellation is a request, not proof of rollback: OS success remains
        // success if it won the race. No callback reopens the closed UI.
        assert(f.controller.result().state == AppUpdateState::installed);
    }
    {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        f.tick();
        f.install.result = AppUpdateResult{AppUpdateState::error};
        f.tick();
        assert(!f.controller.blocksNewWork() && f.controller.result().state == AppUpdateState::error);
    }
    {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true));
        f.now += 29999ms;
        f.install.onStart = [&] {
            assert(f.controller.blocksNewWork());
            f.controller.close(); // Even a reentrant Close cannot lose cancellation.
        };
        f.tick();
        assert(f.install.starts == 1 && f.install.cancels == 1);
        assert(f.controller.blocksNewWork());
        f.install.result = AppUpdateResult{AppUpdateState::cancelled};
        f.tick();
        assert(!f.controller.blocksNewWork() && f.controller.result().state == AppUpdateState::cancelled);
    }
    {
        InstallFixture f;
        f.checkProbe.result = AppUpdateResult{AppUpdateState::unknown};
        assert(f.controller.check(f.now)); f.controller.tick(f.now);
        assert(!f.controller.beginInstall(f.now, false, true));
        assert(!f.controller.blocksNewWork() && f.install.factories == 0);
    }
    {
        InstallFixture f;
        f.install.onPrepare = [] { throw std::runtime_error("synthetic package API failure"); };
        assert(f.controller.beginInstall(f.now, false, true));
        f.tick();
        assert(!f.controller.blocksNewWork() && f.install.starts == 0);
        assert(f.controller.result().state == AppUpdateState::error);
    }
    for (const bool terminal : {false, true}) {
        InstallFixture f;
        assert(f.controller.beginInstall(f.now, false, true)); f.tick();
        int polls = 0;
        f.install.onPoll = [&] {
            ++polls;
            assert(polls == 1); // Nested COM dispatch must not poll/destroy this object.
            f.controller.close();
            f.tick();
            assert(f.controller.blocksNewWork() && f.controller.busy());
            assert(!f.controller.check(f.now));
            assert(!f.controller.beginInstall(f.now, false, true));
        };
        if (terminal) f.install.result = AppUpdateResult{AppUpdateState::installed};
        f.tick();
        assert(polls == 1 && f.controller.blocksNewWork() == !terminal);
        if (!terminal) {
            assert(f.install.cancels == 1);
            f.install.onPoll = {};
            f.install.result = AppUpdateResult{AppUpdateState::cancelled};
            f.tick();
            assert(!f.controller.blocksNewWork());
        }
    }
    for (const bool nullFactory : {false, true}) {
        Probe check{AppUpdateResult{AppUpdateState::available}};
        const auto now = InstallFixture::Clock::time_point{};
        WindowsAppUpdateController c([&] { return std::make_unique<Operation>(check); }, approved,
            [=]() -> std::unique_ptr<AppUpdateInstallOperation> {
                if (nullFactory) return {};
                throw std::runtime_error("synthetic factory failure");
            }, [=] { return now; });
        assert(c.check(now)); c.tick(now);
        assert(c.beginInstall(now, false, true));
        c.tick(now, true, [] { return true; });
        assert(!c.blocksNewWork() && c.result().state == AppUpdateState::error);
    }
    {
        InstallFixture f;
        f.install.onStart = [] { throw std::runtime_error("OS call rejected before operation creation"); };
        assert(f.controller.beginInstall(f.now, false, true));
        f.tick();
        assert(!f.controller.blocksNewWork() && f.controller.result().state == AppUpdateState::error);
    }
}

int main(int argc, char** argv) {
#ifdef _WIN32
    if (argc == 2 && std::string_view(argv[1]) == "--native-no-package") {
        winrt::init_apartment();
        WindowsAppUpdateController native;
        assert(native.check(WindowsAppUpdateController::Clock::now()));
        native.tick(WindowsAppUpdateController::Clock::now());
        assert(native.result().state == AppUpdateState::unavailable);
        assert(native.result().reason == AppUpdateReason::noPackage);
        return 0;
    }
#else
    (void)argc;
    (void)argv;
#endif
    using Clock = WindowsAppUpdateController::Clock;
    const auto now = Clock::time_point{};
    Probe probe;
    WindowsAppUpdateController controller([&] { return std::make_unique<Operation>(probe); });
    assert(controller.check(now));
    assert(!controller.check(now));
    assert(probe.starts == 1);
    controller.tick(now + std::chrono::seconds(29));
    assert(controller.result().state == AppUpdateState::checking);
    controller.tick(now + std::chrono::seconds(30));
    assert(controller.result().reason == AppUpdateReason::timeout);
    assert(probe.cancels == 1);
    assert(!controller.check(now)); // Cancel is not completion; no duplicate native operation.
    probe.result = AppUpdateResult{AppUpdateState::available};
    controller.tick(now + std::chrono::seconds(31));
    assert(!controller.available()); // Timed-out completion cannot paint a badge.
    assert(controller.result().reason == AppUpdateReason::timeout);
    for (const auto state : {AppUpdateState::current, AppUpdateState::available,
                            AppUpdateState::required, AppUpdateState::unknown,
                            AppUpdateState::unavailable, AppUpdateState::error}) {
        assert(controller.check(now));
        probe.result = AppUpdateResult{state};
        controller.tick(now);
        assert(controller.result().state == state);
        assert(controller.available() == (state == AppUpdateState::available || state == AppUpdateState::required));
        assert(!appUpdateDetail(controller.result()).empty());
    }
    probe.result.reset();
    assert(controller.check(now));
    controller.close();
    assert(controller.result().state == AppUpdateState::idle);
    assert(!controller.check(now));
    controller.tick(now);
    assert(controller.busy());
    assert(appUpdateDetail(controller.result(), controller.busy()).find(L"Завершаем предыдущую") != std::wstring::npos);
    probe.result = AppUpdateResult{AppUpdateState::required};
    controller.tick(now);
    assert(controller.result().state == AppUpdateState::idle);
    assert(!controller.available());
    assert(!controller.busy());
    assert(appUpdateDetail(controller.result(), controller.busy()).find(L"Завершаем предыдущую") == std::wstring::npos);
    assert(controller.check(now));
    probe.result = AppUpdateResult{AppUpdateState::current};
    controller.tick(now);
    assert(controller.result().state == AppUpdateState::current);
    controller.close();
    assert(controller.result().state == AppUpdateState::current);
    WindowsAppUpdateController throwing([]() -> std::unique_ptr<AppUpdateCheckOperation> {
        throw std::runtime_error("synthetic");
    });
    assert(throwing.check(now));
    assert(throwing.result().state == AppUpdateState::error);
    assert(!throwing.busy());
    WindowsAppUpdateController empty([]() -> std::unique_ptr<AppUpdateCheckOperation> { return {}; });
    assert(empty.check(now));
    assert(empty.result().state == AppUpdateState::error);
    Probe reentrantProbe;
    WindowsAppUpdateController* checking = nullptr;
    WindowsAppUpdateController reentrant([&] {
        assert(checking->busy());
        checking->tick(now);
        checking->close();
        checking->tick(now);
        assert(!checking->check(now));
        assert(!checking->beginInstall(now, false, true));
        return std::make_unique<Operation>(reentrantProbe);
    });
    checking = &reentrant;
    assert(reentrant.check(now));
    assert(reentrantProbe.starts == 1 && reentrantProbe.cancels == 1);
    assert(reentrant.busy() && reentrant.result().state == AppUpdateState::idle);
    reentrantProbe.result = AppUpdateResult{AppUpdateState::available};
    reentrant.tick(now);
    assert(!reentrant.busy() && !reentrant.available());
    testCheckPollReentrancy();
    testCheckPollException();
    testInstall();
    return 0;
}
