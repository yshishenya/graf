# Contract: termination and relaunch

1. A macOS quit/reopen request enters the existing `.terminateLater` flow.
2. The app immediately clears SwiftUI permission onboarding and meeting prompts.
3. The lifecycle delegate ends attached and detached sheets, aborts an active
   AppKit modal session, and closes visible modal helper windows.
4. Existing capture cleanup remains in force; the app does not use force-kill.
5. Cleanup replies with `NSApp.reply(toApplicationShouldTerminate: true)` when
   complete, or at the existing ten-second timeout.
6. A repeated request while a reply is pending does not create another cleanup
   continuation or reset the deadline.
7. The new process reads TCC state from macOS on launch and does not reuse a
   stale “ready” value from the old process.
8. GRAF's explicit restart marks a relaunch request before termination and opens
   a fresh application instance from `applicationWillTerminate` after cleanup;
   it does not force-kill or leave the user at a permanently closed process.
