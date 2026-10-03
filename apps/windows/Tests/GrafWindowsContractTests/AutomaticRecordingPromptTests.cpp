#include "../GrafWindowsCoreTests/AutomaticRecordingTestSupport.h"
#include "../../RecApp/Shell/AutomaticRecordingPrompt.h"

int main() {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    using P = AutomaticRecordingPreference;
    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences storage;
    AutomaticRecordingPolicy policy(registry, storage.store());
    assert(!AutomaticRecordingPrompt::view(policy, at()).visible);
    assert(observeFor(policy, 0, 4).state == AutomaticPromptState::detecting);
    assert(observeFor(policy, 5, 5).state == AutomaticPromptState::countdown);
    const auto view = AutomaticRecordingPrompt::view(policy, at(5s));
    assert(view.visible && view.secondsRemaining == 8 && view.applicationName == "Meeting app");
    assert(view.primaryAction == "Записать сейчас");
    assert(view.secondaryAction == "Не записывать");
    assert(view.rememberChoiceLabel == "Запомнить выбор");
    assert(!view.accessibleDescription.empty());
    assert(AutomaticRecordingPrompt::view(policy, at(5500ms)).secondsRemaining == 8);
    assert(AutomaticRecordingPrompt::view(policy, at(6s)).secondsRemaining == 7);
    assert(!observeFor(policy, 6, 12).shouldStart);
    assert(policy.secondsRemaining(at(12s)) == 1);
    const auto expired = observeFor(policy, 13, 13);
    assert(expired.shouldStart && expired.startReason == AutomaticStartReason::promptExpired);
    assert(!expired.preferenceSaved && storage.writes == 0 && policy.preference(target()) == P::ask);
    assert(!AutomaticRecordingPrompt::view(policy, at(13s)).visible);
    assert(!policy.recordNow(true, snapshot(at(13s)), ready(), at(13s)).shouldStart);
    assert(!policy.refuse(true, at(13s)).preferenceSaved);
    assert(!observeFor(policy, 14, 20).shouldStart && storage.writes == 0);

    for (const bool remember : {false, true}) {
        Preferences local;
        AutomaticRecordingPolicy explicitStart(registry, local.store());
        (void)observeFor(explicitStart, 0, 5);
        const auto started = explicitStart.recordNow(remember, snapshot(at(6s)), ready(), at(6s));
        assert(started.shouldStart && started.startReason == AutomaticStartReason::promptButton);
        assert(started.preferenceSaved == remember);
        assert(explicitStart.preference(target()) == (remember ? P::always : P::ask));
        assert(!explicitStart.recordNow(true, snapshot(at(6s)), ready(), at(6s)).shouldStart);
        assert(local.writes == (remember ? 1U : 0U));

        Preferences refusalStorage;
        AutomaticRecordingPolicy refusal(registry, refusalStorage.store());
        (void)observeFor(refusal, 0, 5);
        const auto declined = refusal.refuse(remember, at(6s));
        assert(declined.state == AutomaticPromptState::refused && !declined.shouldStart);
        assert(declined.preferenceSaved == remember);
        assert(refusal.preference(target()) == (remember ? P::never : P::ask));
        assert(!refusal.refuse(true, at(6s)).preferenceSaved);
        assert(!observeFor(refusal, 6, 30).shouldStart);
        assert(refusalStorage.writes == (remember ? 1U : 0U));
    }

    // A queued explicit callback which arrives at/after expiry cannot remember.
    Preferences delayedStorage;
    AutomaticRecordingPolicy delayed(registry, delayedStorage.store());
    (void)observeFor(delayed, 0, 12);
    assert(!delayed.refuse(true, at(13s)).preferenceSaved);
    const auto delayedStart = delayed.recordNow(true, snapshot(at(13s)), ready(), at(13s));
    assert(delayedStart.shouldStart && delayedStart.startReason == AutomaticStartReason::promptExpired);
    assert(delayedStorage.writes == 0);

    // Failed persistence is visible; explicit refusal still suppresses this meeting.
    Preferences failedStorage;
    failedStorage.writeFails = true;
    AutomaticRecordingPolicy failed(registry, failedStorage.store());
    (void)observeFor(failed, 0, 5);
    const auto refused = failed.refuse(true, at(6s));
    assert(refused.state == AutomaticPromptState::refused && !refused.preferenceSaved);
    assert(failed.settings().preferenceWriteFailed);
    assert(failed.preference(target()) == P::ask);
    assert(!observeFor(failed, 6, 20).shouldStart);
    return 0;
}
