# PR Draft: 050 MVP Launch Proof

## Что изменилось

- Зафиксирован честный MVP launch proof для `050-mvp-launch-proof`.
- Обновлена readiness-матрица: `049` закрывает blocker по сохраненным итогам,
  а `050` оставляет текущий продукт в статусе `pilot_blocked`, пока не будет
  живого production-доказательства пользовательского пути.
- Добавлены тесты и runtime verifier для playback, таймкодов, нижней шкалы
  спикеров, stored outcomes, web/embedded parity, mobile-width layout и
  честного macOS cabinet state.
- Обновлены `docs/current-product-status.md`,
  `docs/evidence/050-mvp-launch-proof/*`,
  `docs/evidence/036-owner-review-live-polish/readiness-report.md`,
  `CHANGELOG.md` и Spec Kit evidence.

## Что это дает продукту

Теперь видно, что уже можно считать принятым, а что еще блокирует MVP-пилот:

- прослушивание, seek по таймкодам и speaker timeline проверены;
- веб и встроенное macOS-окно дают одинаковую review truth;
- macOS-приложение не показывает зеленый кабинет, если нужен вход или сервер
  недоступен;
- production metadata показывает обработанный кандидат с transcript и
  diarization, но stored outcomes на этом кандидате отсутствуют;
- часовой production timing proof еще не закрыт.

Итоговый claim: `pilot_blocked`. Это лучше, чем размытое “почти готово”: у нас
есть конкретный список оставшихся gates.

## Проверка

- `SPECIFY_FEATURE_DIRECTORY=specs/050-mvp-launch-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_mvp_loop_readiness_matrix.py tests/integration/test_mvp_loop_readiness_report.py tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_outcomes.py tests/integration/test_cabinet_playback_route.py tests/integration/test_cabinet_meeting_detail.py` -> `58 passed, 1 warning`
- `specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs` -> `failures=[]`
- `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|CaptureControl|DesktopUploadQueue|EmbeddedCabinet'` -> `110 tests, 0 failures`
- `infra/scripts/ci-local.sh` -> `ci_local_result=pass`
- `infra/scripts/cd-remote.sh --dry-run` -> `deploy_result=dry_run`
- forbidden-content scan -> pass; broad matches are policy terms only.

## Known limitations

- Не закрыт свежий installed-app путь record/stop/upload-to-review на production.
- Не закрыты stored outcomes на текущем production-кандидате.
- Не закрыт representative one-hour production timing proof.
- `production_ready`, `user_rollout_ready` и `internal_pilot_candidate` не
  заявляются.

## Issues

Refs #1707
Refs #1708
Refs #1709
Refs #1710
Refs #1711
Refs #1712
Refs #1713
Refs #1714
Refs #1715
Refs #1716
Refs #1717
Refs #1718
Refs #1719
Refs #1720
Refs #1721
Refs #1722
Refs #1723
Refs #1724
Refs #1725
Refs #1726
Refs #1727
Refs #1728
Refs #1729
Refs #1730
Refs #1731
Refs #1732
Refs #1733
Refs #1734
Refs #1735
Refs #1736
Refs #1737
Refs #1738
Refs #1739
Refs #1740
Refs #1741
Refs #1742
Refs #1743
Refs #1744
Refs #1745
Refs #1746
Refs #1747
Refs #1748
Refs #1749
Refs #1750
Refs #1751
Refs #1752
