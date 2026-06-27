# Checklist: Auth and Secret Safety for 065

- [x] CHK001 Are active Yandex browser login requirements explicit about server-side callback verification rather than client-side token handling? [Completeness, Spec §FR-003, FR-010]
- [x] CHK002 Are unsafe return paths defined and bounded before redirecting after auth? [Coverage, Spec §FR-005]
- [x] CHK003 Are raw Yandex codes, tokens, client secrets, profile payloads, emails, phones, and secret paths prohibited in rendered output and evidence? [Safety, Spec §FR-010]
- [x] CHK004 Are disabled-provider and provider-unavailable failure modes specified as fail-closed? [Coverage, Spec §FR-007]
- [x] CHK005 Is the public callback URL source defined for reverse-proxy deployments? [Clarity, Spec §FR-008]
- [x] CHK006 Is scope bounded to avoid new migrations, provider families, or desktop token custody? [Clarity, Spec §FR-011]
