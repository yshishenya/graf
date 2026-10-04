# Требования восстановления предложения T016

Reviewer-owned. Риск high-risk-product. Только независимый reviewer отмечает пункты на основании доказательств.

- [x] CHK001 FR014/SC010 различают временное принудительное закрытие и ручной Skip/Stop/accepted; изменяется только ожидающий prompt.
- [x] CHK002 План использует общий dismiss и существующий retryable, сохраняет2s/8s, nil registry и не сбрасывает весь detector.
- [x] CHK003 Приёмка задаёт исполняемый red/green восстановления/подавления повторов/accepted/terminal и отдельную production wiring обоих callers.
- [x] CHK004 Независимое ревью, текущие Dev/CI и аппаратные границы отражены; прежняя45min проверка не объявляется проверкой нового helper.

Независимые ворота требований: PASS, 5 отмечено / 0 не отмечено;
CRITICAL 0 · HIGH 0 · MEDIUM 0. Доказательства:
[prompt-recovery-review.md](prompt-recovery-review.md).
Отметки относятся к требованиям до реализации, не подтверждают Dev/CI/выпуск.

- [x] CHK005 Требования задают оба порядка auth observers через существующий authEpoch и настоящий presenter.invalidate; обычная invalidation остаётся terminal.
