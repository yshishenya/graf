# F283 research and design decisions

Research date: 2026-10-02. Only public primary documentation and observable UI. No private meeting titles/screenshots retained.

| Source | Observed / documented behavior | Decision for GRAF |
|---|---|---|
| [Krisp recurring meeting announcement](https://whatsnew.krisp.ai/announcements/february-updates-for-free-and-pro-users) | Published grouping of recurring instances in meeting view. Current local app observation: quiet Upcoming area distinct from My Notes; recurring detail itself was not observed. | Preserve series grouping, separate upcoming calendar from past results. No claim of access to source or closed algorithm. |
| [Otter recurring meetings](https://help.otter.ai/hc/en-us/articles/25947061277975-Manage-recurring-meetings) | Compact recurrence icon; series settings open on selection; calendar owns recurrence. | Small recurrence marker, no editor or invented cadence. |
| [Fireflies home](https://guide.fireflies.ai/articles/8020055559-fireflies-welcome-screen-a-guide-to-your-new-home-screen) and [Upcoming FAQ](https://guide.fireflies.ai/articles/2596333792-upcoming-meetings-module-faqs?lang=en) | Upcoming and recent recorded results are distinct; upcoming is calendar-derived. | Two contextual views, date actions differ from recording actions. No bot/recording switches borrowed. |
| [Zoom recurring meetings](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0082196) | Upcoming/previous views and bounded date visibility. | Loaded window is clear; no promise of complete history. |

Our inference: separate immediate action, schedule and historical outcome. These are interaction references, not a pixel copy. GRAF uses current inline home placement, its own tokens and independently authored icons/code. Fonts and third-party assets unchanged; no borrowed assets.

Review refinement: normalized instances do not provide a reliable canonical master title or exception flag. The representative date must not be treated as that master. Date rows therefore show their own permitted title at the start of a title run and when that title changes; adjacent equal titles are not repeated, including across pages. These are descriptive date labels, not inferred exception classification. A renamed representative stays explicit without turning ordinary dates into repeated exceptions. Refresh/view changes reset title context. Clock text is exposed once per date; independent action names include the full permitted date/time so multiple occurrences on one day remain distinguishable.

## Scenario decisions

Collapsed: next date, one title, recurrence marker, main Join. Expanded: segmented native buttons, upcoming first, 30-day context; history latest-first. Rows: date/time + contextual action; show a permitted title once at the start and when it changes, omitting adjacent repeated names. Exact timezone in tooltip, compact shared timezone context. Keep per-date Join so a distinct changed link is never replaced by the representative link. Main quick action and per-date action serve collapsed and expanded context.

History has no Join. Multiple recordings have distinct numbered link names, no guessed title/success state. If search is partial, a neutral dash carries accessible description instead of falsely asserting no recording. Help explains this once and offers explicitly general meeting list. Empty states name period, not absolute calendar history. Cancellation never blocks results or other dates. No automatic recording, RRULE guessing or cross-series grouping.

## Technical resolution

Client filtering old all/ascending pages is rejected: old history fills first page before upcoming dates, and a partial page can falsely look empty. Add optional server view on existing query. Signed cursor binds fixed anchor and view, retaining owner/session/workspace/range checks. Current ends_at decides completed vs current; old all remains compatible. Cursor preserves comparison direction and ID tie-breaker. No new table/index/helper class.

При скрытом времени полная дата не может различать действия. Использовать нейтральный порядковый номер «Встреча N» в текущем отображаемом списке и доступном имени действия. Это номер строки, не идентификатор экземпляра и не раскрытие времени; он продолжается между страницами, заново начинается при смене периода/обновлении. Проверить несколько подключений и разные записи при скрытых датах/названиях.
