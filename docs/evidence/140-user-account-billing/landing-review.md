# Отдельная проверка лендинга и публичных страниц

Статус: **автоматизированный browser pass выполнен 2026-08-12; moderated и
clean-room human review не выполнены**. Лендинг не считается закрытым только
по серверным тестам или одному браузерному проходу.

Отдельное moderated participant evidence **не выполнено**; T079 остаётся
открытой до такого прогона.

## Production browser pass

- Chromium desktop `1200 px`, mobile `390×844`, reduced-motion и no-JavaScript
  contexts загрузили `https://rec.2brain.pro/` без console errors;
- один `h1`, один `main`, skip-link, named primary navigation, download/login
  CTA и legal/footer routes присутствуют в accessibility snapshot;
- horizontal overflow не обнаружен на desktop/mobile/reduced-motion;
- no-JavaScript mobile snapshot сохранил download/login, privacy, cookies,
  terms, offer/refund и analytics-consent links;
- public snapshot не содержит billing amount, promo/referral token, email,
  phone или provider identifier.

Перед публичным запуском отдельным проходом проверить:

- визуальную иерархию блока тарифов на desktop/mobile;
- цены `790 ₽/месяц` и `7 900 ₽/год`, формулировку «2 месяца бесплатно» и
  соответствие server-owned catalog;
- корректность CTA, `/offer`, `/privacy`, `/terms`, cookies и login/download;
- keyboard navigation, visible focus, screen reader labels и 200% reflow;
- отсутствие горизонтального overflow на узком экране;
- отсутствие в публичной аналитике сумм, promo/referral tokens, email, телефона,
  платёжных и provider identifiers;
- clean-room review: не копируются макеты, тексты или визуальные элементы
  Krisp и других референсов;
- production smoke после публикации лендинга и юридического утверждения.

Screenshots/video и participant result добавляются только после отдельного
moderated прогона. Реальные платежные реквизиты и данные пользователей в
evidence не сохраняются.
