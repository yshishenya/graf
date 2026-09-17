# A11 — сохранение проектного PR template

Reviewer-owned requirements gate; implementation must not edit checkboxes.

- [x] CHK001 Новый template устанавливается; существующий сохраняется побайтно, а managed issue canon/labels обновляются как прежде. [FR-056]
- [x] CHK002 Общий источник нейтрален к GRAF checks, source patch/version закрепляется штатно без правки чужого bootstrap. [FR-056]
- [x] CHK003 Настоящий ensure проверен без GitHub на новой установке и двух повторах; SHA-256 и разделы сохраняются, source CI и frozen doctor обязательны. [SC-024]

Проверка требований `requirements_review`: **PASS 3/3**. Отметки внесены
2026-09-13 по прямому разрешению пользователя после уже выполненного A11 PASS.
FR-056, SC-024, A11 plan и acceptance связывают требования с T082–T083.
Это приёмка требований; результаты реализации, source CI, закреплённого
обновления и frozen doctor подтверждаются отдельно и этими отметками не закрываются.
