# T023: согласованная матовая композиция

2026-09-07. Active Spec Kit slice; high-risk UX/reference fidelity. Сохраняется принятая владельцем структура HTML-навигации и профиля.

## Изменения

Один контейнер вокруг WebView и native inspector: отступ8 pt, непрерывный радиус12 pt. Удалены две лишние обёртки HStack/VStack. Titlebar записи находится снаружи маски. Правая панель использует системный непрозрачный controlBackground. В CSS мягкий разделитель sidebar, матовая upcoming, спокойные карточки обзора настроек и подписи области действия. Последнее правило list-card больше не возвращает яркий контур и тень. Поля, действия, фокус и повышенный контраст сохраняются.

## Проверено до установки

- Свежий установленный Dev: экран настроек подтвердил яркий стык sidebar, контуры карточек/подписей и несогласованную правую поверхность. Локальный снимок `/tmp/graf-f255/design-pass/01-graf-settings.png`.
- Реальный Krisp Shared with me: общая внутренняя рамка и тонкие стыки; наблюдения предыдущего прохода в `krisp-review.md`. Чужие ресурсы не извлекались.
- Swift: `swift test --package-path apps/macos --parallel --num-workers 1 --filter 'DesktopMeetingShellWebViewBoundary|AppControlAccessibility|CabinetSidebarRuntime|DesktopCabinetWorkspace'`: 91 PASS; включая реальный WKWebView переход через отступ подменю.
- Server: existing shell/template/settings contracts: 116 PASS.
- Существующая synthetic fixture дополнена только маршрутом overview. Production CSS/HTML: тёмная/светлая темы настроек, шрифт служебной подписи, ширина640 без горизонтального переполнения. Снимки `03-settings-dark.png`, `04-settings-light.png` остаются локально. Browser preview не доказывает native clip.

## Открыто

Фактическая установка и whole-window проверка общего clip/правой панели фиксируются отдельно после штатного build/promote/status/smoke на совместимом SHA. Минимальное native окно, 200%, VoiceOver, активный Stop и обе поддерживаемые macOS требуют полной матрицы T016. Этот этап непрозрачный; Liquid Glass не реализован и не объявляется принятым. Ручной web theme и системная native appearance сохраняют существующую раздельность; их полная синхронизация относится к незавершённой T008, нового bridge здесь нет.
