# Native Full failure — read-only diagnosis

Frozen source: `95be4e117dc2403e5388abe04a9aab9a475f4ca2`. Lane: read-only investigation; scoped releaseT025 gate repair proposal, no product change. Source/git/GitHub/deployment not modified; no tests/app launches performed. `docs/agent-guidance/local-development.md` read before diagnosis.

## Proven failure

Full36934946364 native1191 has one assertion failure, `/tmp/graf-f280-provider-full-corrected-macos.log:5492`: DesktopNotificationAccessibilityTests.swift:199, final policy0(.regular) differs from baseline2(.prohibited). In the same test all checks of initial visible inactive host, automatic nonactivating show, focus() acceptance, actual application activation/key-window and keyboard responder passed. This is not evidence that explicit focus failed.

## Causal source proof

1. `DesktopNotificationAccessibilityTests.swift:174–202` prepares the command-line host with `requireScreen`, `requireFocusHost`, `requireInactiveHost`; samples `policy` at182; shows the panel; yields30ms at186; subsequently `awaitAppKitState` may start another bounded NSApp event-loop run; only inside its timer perform closure at194 invokes presenter.focus(). The baseline covers a separate asynchronous host lifecycle interval rather than the product command alone.
2. `DesktopNotificationCardPresenter.swift:294` is the first guard in focus(): policy must NOT equal `.prohibited` before the method performs any activation/key-window work. The test's XCTAssertTrue(presenter.focus()) did not fail. Therefore the sampled policy2 had already changed BEFORE product focus accepted the command. This is a direct causal deduction from the successful guard, not an assumption based on a previous green run.
3. Presenter never sets activation policy. Every executable setter under apps/macos is: `DesktopNotificationCompactTests.swift:24`, test requireScreen requests `.regular` for an unbundled command-line XCTest host; `TwoBrainRecApp.swift:3266`, app delegate applicationWillFinishLaunching requests `.regular` at real app startup. `Package.swift` excludes RecApp/App from TwoBrainRecAppCore, and TwoBrainRecSharedTests depends only on Shared/AppCore/AEC3; the real app delegate is not this XCTest host's launch path. `AppLifecycleWindowRegressionTests.swift:89` is an inert class named NSApplication in a script string compiled in a separate child, not another AppKit instance or setter.
4. `DesktopNotificationCompactTests.swift:18–30` sets permitted policy synchronously once/when prohibited and tracks launch via preparedApplication. `requireInactiveHost:90–108` waits only !active/hidden then !active/!hidden, with hide/unhide and bounded NSApp.run/stop. `awaitAppKitState:41–70` runs NSApp.run when stopped, with timer+stop+wake event, or pumps events and sleeps otherwise. None of these readiness conditions constrain a stable activationPolicy at the eventual product call. The OS-owned policy transition during this interval is outside the presenter's setter-free focus implementation.
5. `run-swift-tests.sh` uses one sequential XCTest process with `swift test --skip-build`; no parallel test execution. MainActor prevents concurrent application code but not AppKit lifecycle/WindowServer transitions between awaits and loop restarts. Previous focus tests dismiss their own panels and may restore a previous application; every test still uses the same NSApp/WindowServer host. The suite resets its local panel, but cannot assert a global policy remains constant across unrelated host pumping.
6. `present():208–259` constructs a `.nonactivatingPanel`, orders it without requesting activation, and the test's isActive/keyWindow assertions after automatic display passed. `focus():294–340` checks policy then requests NSApp.activate()/makeKeyAndOrderFront with generation-protected continuations; no setActivationPolicy call exists in this path or its callbacks. `clear():405–432` restores previous key window/application but likewise has no activation-policy setter.

**Classification:** timing-sensitive test baseline in the shared unbundled AppKit host; no demonstrated product regression. The exact internal OS event that changes policy2 to0 cannot be named from this log because policy/state are not traced around each helper. Claiming a particular NSApp.run/hide/unhide callback would exceed the evidence. The decisive fact is that the change happened before the guard accepted product focus, making line199's old baseline unsuitable for attributing the transition to focus.

## Smallest root-cause correction

Move activationPolicy baseline sampling into the existing awaitAppKitState `perform` closure, directly before calling presenter.focus(). Capture it in an optional typed variable; explicitly assert it is not `.prohibited` at that command boundary. Keep the final equality against the unwrapped sampled baseline after the real active/key-window condition, plus all current visible-inactive/automatic-show/firstResponder/key-loop assertions. Do not change product focus, set policy inside the command, add skips, retries, fixed longer sleeps or another host abstraction. This checks the intended invariant over the actual product operation after the test's event-loop setup, without weakening automatic-display or actual-focus behavior.

Suggested validation after authorized test-only edit: failing test independently, full DesktopNotificationAccessibilityTests together with Compact/ProtectedRegion suite, then complete sequential native1191; retain existing exact-SHA CI/Full governance. A diagnostic same-frozen-SHA run is evidence for diagnosis, not deployment authorization or replacing failed Full.

## Source identity

`git diff --stat 91b59 --` three files returned empty; previous commit resolves to `91b59ac8ee89aad47104ab0f0ff3747a0f70cafa`. These sources are unchanged from the prior passing native run36931385550 (run outcome supplied by root):

- Accessibility tests: `a1b4d6e76151f8aa3736ce2cee1ebfe75e12ff4e2eb36c656b41625032ef2e4b`.
- Compact helper/tests: `a6184827336d655a1d1b6d95370fa001400e909714343d81a2a8b6c816ea3e73`.
- Presenter: `fdbe7b422d59b2467a1bdc544b166786ed0d369de30d6a31520f5a0f8f2d57c3`.

No live manual UX/GRAF Dev evidence claimed. No source edits or test executions performed by this diagnostic agent.
