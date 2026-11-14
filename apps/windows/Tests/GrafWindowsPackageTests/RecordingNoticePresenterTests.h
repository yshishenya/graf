#pragma once
#include "../../RecApp/Shell/RecordingNoticePresenter.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>

// Runs in the existing ShortRecordingThresholdTests target. Portable state and
// source-wiring checks are not Windows accessibility / visual acceptance.
inline void testF277RecordingNoticePresenter() {
    using namespace graf::windows;
    using namespace std::chrono;
    const auto now = RecordingNoticePresenter::Clock::now();
    const auto shortCard = [](std::string id) { return NoticeContent{NoticeKind::shortRecording, std::move(id), L"", L"", {}}; };
    const auto promptCard = [](std::string id) { return NoticeContent{NoticeKind::recordingPrompt, std::move(id), L"", L"", {}}; };
#ifdef _WIN32
    {
        RecordingNoticePresenter unbound;
        assert(!unbound.present(promptCard("unbound-native"), now, now + seconds(8)));
        assert(!unbound.visible()); // native default is deny, not the portable model seam
    }
#endif
    for (int mode = 0; mode != 6; ++mode) {
        RecordingNoticePresenter card;
        InteractionPermit permit{true, 1};
        card.interactionPermitProvider = [&] { return permit; };
        auto queuedAt = now;
        if (mode == 3) {
            assert(card.present(promptCard("queue-blocker"), now, now + seconds(8)));
            queuedAt = card.deadline() - seconds(8);
        }
        card.setQuiet(mode == 1);
        if (mode == 2) permit.allowed = false;
        const auto generation = card.generation();
        int presented = 0;
        card.queueShortRecordingDiscarded(queuedAt, [&] {
            assert(card.visible() && card.kind() == NoticeKind::shortRecording);
            ++presented;
        });
        assert(card.history().size() == 1 && card.history().front().kind == NoticeKind::shortRecording);
        assert(presented == 0 && card.generation() == generation);
        assert(card.visible() == (mode == 3)); // enqueue never shows a new surface
        if (mode == 3) {
            assert(!card.presentPendingShort(queuedAt + seconds(1)) && presented == 0);
            card.dismiss();
        }
        if (mode == 4) ++permit.epoch; // lock/unlock before actual show invalidates pending
        if (mode == 5) card.tick(queuedAt + seconds(20));
        card.setQuiet(false);
        permit.allowed = true;
        const auto delivery = queuedAt + seconds(mode == 5 ? 20 : 2);
        const bool shouldShow = mode == 0 || mode == 3;
        assert(card.presentPendingShort(delivery) == shouldShow);
        assert(presented == (shouldShow ? 1 : 0));
        assert(!card.presentPendingShort(delivery + seconds(1)));
        card.dismiss();
        card.tick(queuedAt + seconds(40));
        assert(card.history().size() == 1); // expiry/quiet/denial never erase the receipt
        assert(presented == (shouldShow ? 1 : 0));
    }
    for (int suppressLatest = 0; suppressLatest != 3; ++suppressLatest) {
        RecordingNoticePresenter card;
        InteractionPermit permit{true, 1};
        card.interactionPermitProvider = [&] { return permit; };
        int first = 0, latest = 0;
        card.queueShortRecordingDiscarded(now, [&] { ++first; });
        card.setQuiet(suppressLatest == 1);
        if (suppressLatest == 2) permit.allowed = false;
        card.queueShortRecordingDiscarded(now + seconds(1), [&] { ++latest; });
        assert(!card.visible() && first == 0 && latest == 0 && card.history().size() == 2);
        card.setQuiet(false);
        permit.allowed = true;
        assert(card.presentPendingShort(now + seconds(2)) == (suppressLatest == 0));
        assert(first == 0 && latest == (suppressLatest == 0 ? 1 : 0));
        card.dismiss();
        assert(!card.presentPendingShort(now + seconds(3)) && card.history().size() == 2);
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        int presented = 0;
        card.showShortRecordingDiscarded(now, [&] {
            assert(card.visible() && card.kind() == NoticeKind::shortRecording);
            ++presented;
        });
        assert(presented == 1 && card.visible());
        const auto deadline = card.deadline();
        assert(card.present(card.content(), now + seconds(1), now + seconds(21)));
        card.tick(now + seconds(1));
        assert(presented == 1 && card.deadline() == deadline);
        card.close();
        assert(presented == 1 && !card.presentPendingShort(now + seconds(2)));
        card.showShortRecordingDiscarded(now + seconds(2)); // legacy call, no callback
        assert(card.visible() && presented == 1);
    }
    for (int suppressed = 0; suppressed != 3; ++suppressed) {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [&] {
            // Failure seam: deny initially or revoke after show before acknowledgement.
            return InteractionPermit{suppressed != 1 && (suppressed != 2 || !card.visible()), 1};
        };
        card.setQuiet(suppressed == 0);
        int presented = 0;
        card.showShortRecordingDiscarded(now, [&] { ++presented; });
        assert(!card.visible() && presented == 0);
        card.tick(now + seconds(1));
        assert(!card.presentPendingShort(now + seconds(1)) && presented == 0);
    }
    for (const bool expiresPending : {false, true}) {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        assert(card.present(promptCard("short-sound-blocker"), now, now + seconds(8)));
        const auto shownAt = card.deadline() - seconds(8);
        int presented = 0;
        card.showShortRecordingDiscarded(shownAt, [&] {
            assert(card.visible() && card.kind() == NoticeKind::shortRecording);
            ++presented;
        });
        assert(presented == 0 && card.automaticPromptActive());
        assert(!card.presentPendingShort(shownAt + seconds(1)) && presented == 0);
        card.dismiss();
        assert(presented == 0); // releasing the blocker alone is not a show
        const auto delivery = shownAt + seconds(expiresPending ? 20 : 2);
        assert(card.presentPendingShort(delivery) == !expiresPending);
        assert(presented == (expiresPending ? 0 : 1));
        assert(!card.presentPendingShort(delivery + seconds(1)));
        card.dismiss();
        assert(presented == (expiresPending ? 0 : 1));
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        InteractionPermit permit{false, 1};
        card.interactionPermitProvider = [&] { return permit; };
        int claims = 0, presented = 0, invalidated = 0;
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [&] { ++claims; return true; };
        hooks.onPresented = [&] { ++presented; };
        hooks.onInvalidated = [&] { ++invalidated; };
        assert(!card.present(promptCard("denied-before-claim"), now, now + seconds(8), {}, {}, hooks));
        assert(claims == 0 && presented == 0 && !card.visible());
        permit = {true, 2};
        hooks.beforeFirstShow = [&] { ++claims; ++permit.epoch; return true; };
        assert(!card.present(promptCard("revoked-during-claim"), now, now + seconds(8), {}, {}, hooks));
        assert(claims == 1 && presented == 0 && invalidated == 1 && !card.visible());
        hooks.beforeFirstShow = [&] { ++claims; return true; };
        card.interactionPermitProvider = [&] {
            // Model seam for revocation after show but before acknowledgement.
            return InteractionPermit{!card.visible(), permit.epoch};
        };
        assert(!card.present(promptCard("revoked-before-ack"), now, now + seconds(8), {}, {}, hooks));
        assert(presented == 0 && invalidated == 2 && !card.visible());
        card.interactionPermitProvider = []() -> InteractionPermit { throw std::runtime_error("probe unavailable"); };
        assert(!card.present(promptCard("query-failed"), now, now + seconds(8), {}, {}, hooks));
        assert(!card.visible() && presented == 0);
    }
    for (int operation = 0; operation != 6; ++operation) {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        InteractionPermit permit{true, 10};
        card.interactionPermitProvider = [&] { return permit; };
        card.recordProblemHistory("preserve-history", now + seconds(300));
        int acted = 0, expired = 0, remembered = 0, invalidated = 0, closed = 0;
        NoticePresentationHooks hooks;
        hooks.onExpired = [&] { ++expired; };
        hooks.onRememberChanged = [&](bool) { ++remembered; };
        hooks.onInvalidated = [&] { ++invalidated; };
        auto prompt = promptCard("guard-every-terminal");
        prompt.buttons = {{L"Записать", NoticeAction::record}};
        assert(card.present(prompt, now, now + seconds(8), [&](auto) { ++acted; }, [&] { ++closed; }, hooks));
        const auto shownAt = card.deadline() - seconds(8);
        card.showShortRecordingDiscarded(shownAt);
        // Even a now-unlocked desktop cannot revive the pre-lock generation.
        ++permit.epoch;
        switch (operation) {
        case 0: card.tick(card.deadline()); break;
        case 1: card.invoke(NoticeAction::record, card.generation(), shownAt + seconds(1)); break;
        case 2: card.setRememberChoice(true); break;
        case 3: card.focus(); break;
        case 4: card.close(); break;
        case 5: card.invalidatePresentation(); break;
        }
        assert(!card.visible() && !card.content().rememberChoice);
        assert(acted == 0 && expired == 0 && remembered == 0 && closed == 0 && invalidated == 1);
        assert(card.history().size() == 2);
        assert(!card.presentPendingShort(shownAt + seconds(1))); // lifecycle discards the old pending surface
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        card.setQuiet(true);
        card.recordProblemHistory("claimed-not-shown", now + seconds(300));
        card.recordProblemHistory("claimed-not-shown", now + seconds(300));
        assert(card.history().size() == 1 && !card.visible());
        card.setQuiet(false);
        card.tick(now + seconds(21));
        assert(card.present({NoticeKind::problem, "claimed-not-shown", L"", L"", {}},
            now + seconds(299), now + seconds(319)));
        assert(card.history().size() == 1 && card.deadline() == now + seconds(319));
        card.dismiss();
        card.tick(now + seconds(320));
        assert(!card.present({NoticeKind::problem, "claimed-not-shown", L"", L"", {}},
            now + seconds(320), now + seconds(340)));
        card.resolveProblem("claimed-not-shown");
        card.recordProblemHistory("claimed-not-shown", now + seconds(300));
        assert(card.history().size() == 2);
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        assert(card.present(promptCard("history-blocker"), now, now + seconds(8)));
        const auto shownAt = card.deadline() - seconds(8);
        const NoticeContent problem{NoticeKind::problem, "unshown-problem", L"", L"", {}};
        assert(!card.present(problem, shownAt, shownAt + seconds(300)));
        assert(card.history().size() == 1);
        card.dismiss();
        card.tick(shownAt + seconds(21));
        // A history receipt is not proof of presentation. The domain still owns
        // this pending candidate, whose first visible budget has not begun.
        assert(card.present(problem, shownAt + seconds(21), shownAt + seconds(41)));
        assert(card.history().size() == 1);
        card.dismiss();
        card.tick(shownAt + seconds(42));
        assert(!card.present(problem, shownAt + seconds(42), shownAt + seconds(62)));
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        int presented = 0, invalidated = 0;
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [&] {
            assert(!card.visible() && !card.automaticPromptActive() && !card.occupied());
            return false;
        };
        hooks.onPresented = [&] {
            ++presented;
            assert(card.visible() && card.automaticPromptActive() && card.occupied());
        };
        hooks.onInvalidated = [&] {
            ++invalidated;
            assert(!card.visible() && !card.automaticPromptActive() && !card.occupied());
        };
        assert(!card.present(promptCard("failed-prompt"), now, now + seconds(8), {}, {}, hooks));
        assert(!card.automaticPromptActive() && !card.occupied() && presented == 0);
        hooks.beforeFirstShow = [&] {
            assert(!card.automaticPromptActive() && !card.occupied());
            return true;
        };
        assert(card.present(promptCard("shown-prompt"), now, now + seconds(8), {}, {}, hooks));
        const auto deadline = card.deadline();
        assert(card.present(promptCard("shown-prompt"), now + seconds(1), now + seconds(9), {}, {}, hooks));
        assert(card.deadline() == deadline && presented == 1 && card.automaticPromptActive());
        card.invalidate();
        assert(invalidated == 1 && !card.automaticPromptActive());
        assert(card.present(shortCard("ordinary-card"), now, now + seconds(20)));
        assert(card.occupied() && !card.automaticPromptActive());
        card.dismiss();
        assert(!card.occupied() && !card.automaticPromptActive());
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        int claims = 0, presented = 0, closed = 0;
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [&] { ++claims; assert(!card.visible()); return false; };
        hooks.onPresented = [&] { ++presented; assert(card.visible()); };
        assert(!card.present(shortCard("claim"), now, now + seconds(20), {}, {}, hooks));
        assert(!card.visible() && claims == 1 && presented == 0);
        hooks.beforeFirstShow = [&] { ++claims; assert(!card.visible()); return true; };
        assert(card.present(shortCard("claim"), now, now + seconds(20), {}, [&] { ++closed; }, hooks));
        const auto token = card.generation();
        assert(card.present(shortCard("claim"), now + seconds(1), now + seconds(21), {}, [&] { ++closed; }, hooks));
        assert(card.generation() == token && claims == 2 && presented == 1);
        assert(card.deadline() == now + seconds(20));
        card.close(token); card.close(token);
        assert(closed == 1 && !card.visible());
        assert(!card.present(shortCard("claim"), now + seconds(2), now + seconds(22)));
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        auto eventTime = now;
        int displaced = 0;
        NoticePresentationHooks hooks; hooks.onInvalidated = [&] { ++displaced; };
        assert(card.present(promptCard("priority-prompt"), now, now + seconds(8), {}, {}, hooks));
        eventTime = card.deadline() - seconds(8); // use the visible instant, not pre-show time
        const auto token = card.generation();
        assert(!card.present({NoticeKind::problem, "problem", L"", L"", {}}, eventTime, eventTime + seconds(20)));
        card.showShortRecordingDiscarded(eventTime);
        card.showShortRecordingDiscarded(eventTime + seconds(1));
        assert(card.history().size() == 3 && displaced == 0 && card.automaticPromptActive());
        card.close(token - 1); assert(card.automaticPromptActive());
        card.close(token);
        assert(!card.automaticPromptActive());
        card.tick(eventTime + seconds(2));
        assert(!card.visible()); // timer does not bypass fresh domain candidates
        assert(card.presentPendingShort(eventTime + seconds(2)));
        assert(card.visible() && card.kind() == NoticeKind::shortRecording);
        assert(card.deadline() == eventTime + seconds(22)); // pending budget vs visible budget
        assert(card.present(promptCard("next-prompt"), eventTime + seconds(3), eventTime + seconds(11)));
        assert(card.automaticPromptActive());
        card.dismiss();
        card.tick(eventTime + seconds(4));
        assert(!card.visible()); // already shown short does not resurrect
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        int invalidated = 0;
        NoticePresentationHooks hooks; hooks.onInvalidated = [&] { ++invalidated; };
        assert(card.present(promptCard("reset-prompt"), now, now + seconds(8), {}, {}, hooks));
        card.resetContext();
        assert(!card.automaticPromptActive() && !card.occupied() && invalidated == 1);
        card.resetContext(); assert(invalidated == 1);
        assert(card.present({NoticeKind::preview, "preview", L"", L"", {}}, now, now + seconds(6)));
        assert(!card.automaticPromptActive());
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        assert(card.present(shortCard("hold"), now, now + seconds(20)));
        card.setInteraction(true, false, now + seconds(5));
        card.tick(now + seconds(30)); assert(card.visible());
        card.setInteraction(false, true, now + seconds(30));
        card.setInteraction(false, false, now + seconds(40));
        assert(card.deadline() == now + seconds(55));
        card.tick(now + seconds(55)); assert(!card.visible());
        assert(card.present({NoticeKind::meeting, "hard", L"", L"", {}}, now, now + seconds(10)));
        card.setInteraction(true, true, now + seconds(5));
        card.tick(now + seconds(10)); assert(!card.visible());
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        card.setQuiet(true);
        for (int i = 0; i < 75; ++i) {
            assert(!card.present(shortCard("private-session-" + std::to_string(i)), now, now + seconds(20)));
        }
        assert(card.history().size() == 50 && card.history().front().sequence == 75);
        for (const auto& item : card.history()) assert(RecordingNoticePresenter::historyMessage(item.kind) == RecordingNoticePresenter::message());
        // F277's explicitly requested preview is allowed in quiet, not automatic delivery.
        assert(card.present({NoticeKind::preview, "preview", L"secret", L"secret", {}}, now, now + seconds(6)));
        assert(!card.present({NoticeKind::preview, "preview", L"secret", L"secret", {}}, now, now + seconds(6)));
        assert(card.history().size() == 50);
        NoticeContent prompt{NoticeKind::recordingPrompt, "prompt", L"Встреча", L"8 секунд", {{L"Записать", NoticeAction::record}, {L"Не записывать", NoticeAction::skip}}, L"Запомнить выбор", false};
        int acted = 0, expired = 0, invalidated = 0;
        NoticePresentationHooks hooks; hooks.onExpired = [&] { ++expired; }; hooks.onInvalidated = [&] { ++invalidated; };
        assert(card.present(prompt, now, now + seconds(8), [&](auto) { ++acted; }, {}, hooks));
        assert(card.content().buttons.front().action == NoticeAction::skip);
        card.setRememberChoice(true); assert(card.content().rememberChoice);
        auto token = card.generation();
        card.invoke(NoticeAction::record, token, now + seconds(1));
        card.invoke(NoticeAction::record, token, now + seconds(1));
        assert(acted == 1 && expired == 0 && !card.automaticPromptActive() && !card.occupied());
        prompt.id = "new-prompt";
        assert(card.present(prompt, now, now + seconds(8), {}, {}, hooks));
        card.close(token); assert(card.visible());
        card.tick(now + seconds(10)); // a sleep-sized tick gap invalidates, never starts
        assert(!card.visible() && !card.automaticPromptActive() && expired == 0 && invalidated == 1);
        prompt.id = "reset-prompt";
        assert(card.present(prompt, now, now + seconds(8), {}, {}, hooks));
        card.resetContext(); assert(card.history().empty() && !card.occupied());
        assert(expired == 0 && invalidated == 2);
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        card.setQuiet(true);
        const NoticeContent incident{NoticeKind::problem, "session-incident", L"private title", L"private detail", {}};
        assert(!card.present(incident, now, now + seconds(20)));
        assert(!card.present(incident, now + seconds(21), now + seconds(41)));
        assert(card.history().size() == 1); // expiry is not resolution of an incident
        card.resolveProblem(incident.id);
        assert(!card.present(incident, now + seconds(22), now + seconds(42)));
        assert(card.history().size() == 2); // genuinely new occurrence after resolution
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [&] { card.resetContext(); return true; };
        assert(!card.present(shortCard("stale-claim"), now, now + seconds(20), {}, {}, hooks));
        assert(!card.visible() && card.history().empty());
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [&] {
            assert(!card.present(shortCard("nested-during-hidden-preparation"), now, now + seconds(20)));
            return true;
        };
        assert(card.present(shortCard("outer-claim"), now, now + seconds(20), {}, {}, hooks));
        assert(card.visible() && card.id() == "outer-claim");
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        int shown = 0;
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = []() -> bool { throw std::runtime_error("synthetic claim failure"); };
        hooks.onPresented = [&] { ++shown; };
        assert(!card.present(shortCard("exception"), now, now + seconds(20), {}, {}, hooks));
        assert(shown == 0 && !card.visible());
        hooks = {};
        hooks.onInvalidated = [&] {
            assert(card.present({NoticeKind::recordingPrompt, "reentrant", L"", L"", {}}, now, now + seconds(8)));
        };
        assert(card.present({NoticeKind::meeting, "replace", L"", L"", {}}, now, now + seconds(60), {}, {}, hooks));
        assert(!card.present(shortCard("cannot-replace-callback"), now, now + seconds(20)));
        assert(card.visible() && card.id() == "reentrant");
        card.resetContext();
        assert(card.present(promptCard("pending-budget"), now, now + seconds(8)));
        const auto shownAt = card.deadline() - seconds(8);
        card.showShortRecordingDiscarded(shownAt);
        assert(card.automaticPromptActive());
        card.dismiss();
        assert(!card.presentPendingShort(shownAt + seconds(20))); // unseen budget cannot restart
        assert(card.history().size() == 1);
    }
    {
        RecordingNoticePresenter card;
        card.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        int expired = 0;
        NoticePresentationHooks hooks; hooks.onExpired = [&] { ++expired; };
        assert(card.present({NoticeKind::recordingPrompt, "countdown", L"", L"", {}}, now, now + seconds(8), {}, {}, hooks));
        card.setInteraction(true, true, now + seconds(1));
        for (int second = 1; second <= 9; ++second) card.tick(now + seconds(second));
        assert(expired == 1 && !card.visible() && !card.automaticPromptActive() && !card.occupied());
        assert(card.present({NoticeKind::meeting, "shortened", L"", L"", {}}, now, now + seconds(100)));
        assert(card.present({NoticeKind::meeting, "shortened", L"", L"", {}}, now + seconds(1), now + seconds(5)));
        card.tick(now + seconds(5)); assert(!card.visible());
    }
    {
        const NoticeRect work{0, 0, 1920, 1080};
        auto layout = RecordingNoticePresenter::place(work, 44, 44, {});
        assert(layout && layout->cardWidth == 380 && layout->cardHeight == 44);
        assert(layout->frame.y == 8 && layout->frame.width == 408);
        auto below = RecordingNoticePresenter::place(work, 44, 44, {layout->frame});
        assert(below && below->frame.y == layout->frame.y + layout->frame.height + 8);
        assert(!RecordingNoticePresenter::place(work, 44, 44, {work}));
        auto narrow = RecordingNoticePresenter::place({0, 0, 280, 300}, 200, 80, {});
        assert(narrow && narrow->cardWidth == 236);
        assert(!RecordingNoticePresenter::place({0, 0, 250, 300}, 200, 80, {}));
        auto scaled = RecordingNoticePresenter::place({0, 0, 1920, 1080}, 88, 88, {}, 192);
        assert(scaled && scaled->cardWidth == 760 && scaled->frame.y == 16);
    }
    {
        // Win32 source wiring only; no HWND/focus/Narrator runtime claim.
        const auto sourcePath = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
            "RecApp/Shell/RecordingNoticePresenter.cpp";
        std::ifstream input(sourcePath);
        const std::string source{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
        assert(!source.empty());
        const auto nativeCreate = source.find("bool RecordingNoticePresenter::createWindow()");
        const auto nativeUpdate = source.find("bool RecordingNoticePresenter::updateWindow()");
        const auto nativeShow = source.find("bool RecordingNoticePresenter::showWindow()");
        assert(nativeCreate < nativeUpdate && nativeUpdate < nativeShow);
        const auto create = source.substr(nativeCreate, nativeUpdate - nativeCreate);
        const auto update = source.substr(nativeUpdate, nativeShow - nativeUpdate);
        assert(create.find("SW_SHOWNOACTIVATE") == std::string::npos);
        assert(create.find("!ok || !updateWindow()") != std::string::npos);
        assert(update.find("CreateWindowExW") == std::string::npos);
        assert(update.find("GetCursorPos") == std::string::npos); // pinned monitor
        assert(update.find("selectedMonitor_") != std::string::npos);
        assert(update.find("protectedFramesProvider") != std::string::npos);
        assert(source.find("MA_NOACTIVATE") != std::string::npos);
        assert(source.find("IsWindowVisible(window) || IsIconic(window)") != std::string::npos);
        assert(source.find("ES_READONLY | ES_MULTILINE | ES_AUTOVSCROLL") != std::string::npos);
        assert(source.find("VK_TAB") != std::string::npos && source.find("VK_ESCAPE") != std::string::npos);
        assert(source.find("VK_RETURN || wparam == VK_SPACE") != std::string::npos);
        assert(source.find("SetWindowsHookEx") == std::string::npos);
        assert(source.find("KillTimer(window, kTick)") != std::string::npos);
        assert(source.find("EVENT_SYSTEM_ALERT") == source.rfind("EVENT_SYSTEM_ALERT"));
        assert(source.find("if (!createWindow())") < source.find("auto claim = hooks_.beforeFirstShow"));
        assert(source.find("visible_ = showWindow()") < source.find("auto presented = hooks_.onPresented"));
        const auto claim = source.find("auto claim = hooks_.beforeFirstShow");
        assert(source.rfind("if (!requireInteraction()) return false;", claim) > source.find("if (!createWindow())"));
        const auto show = source.substr(nativeShow);
        assert(show.find("if (!requireInteraction()) return false;") < show.find("ShowWindow(window, SW_SHOWNOACTIVATE)"));
        const auto lifecycle = source.substr(source.find("void RecordingNoticePresenter::invalidatePresentation()"),
            source.find("void RecordingNoticePresenter::setQuiet(") - source.find("void RecordingNoticePresenter::invalidatePresentation()"));
        assert(lifecycle.find("pendingShort_.reset()") != std::string::npos);
        assert(lifecycle.find("explicitFocus_ = false") < lifecycle.find("invalidate()"));
        assert(lifecycle.find("history_.clear()") == std::string::npos);
    }
}
