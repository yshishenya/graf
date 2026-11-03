# Research F291 — 2026-10-23

Decision: certifi >=2026.10.19 и Node 22 >=22.23.4 по https://render.com/docs/advisory-emudhra . Пакеты сверяются через официальный индекс перед обновлением, hashes не угадываются. Выбран только targeted certifi upgrade, чтобы не менять транзитивный граф без необходимости. `uv tree --outdated` фиксирует остальные старые версии как отдельную работу.

Decision: системные CA обновляются штатным Debian package manager в Docker build; ручное редактирование CA и TLS-настроек запрещено. Изменение Dockerfile обеспечивает новый install layer; сборка и runtime проверяются отдельно.

Decision: текущий master 4ab1fd497; последний опубликованный stable v2026.10.22.1. v2026.10.22.2 — draft, владелец исходного release pointer growth-f273. Чужие изменения и черновик не изменяются; новый оператор security-f291 координирует следующий серверный выпуск после сверки всего диапазона.

Decision: неизвестную backup authority нельзя считать выданной. До доказательства применимости разрешения execute блокируется, gates не обходятся. Исходное исправление и проверки независимы от backup. Последний remote checkout 8e37e0e3 не доказывает SHA образов; inspect/readback обязательны.

Decision: новый клиент macOS не нужен; live appcast/assets сохраняются. Required native PR/Full CI gates всё равно обязательны.

Validation: certifi latest official PyPI 2026.10.23. Semantic lock comparison: only certifi version/object changed, plus direct root floor. uv0.11.28 lock-check and repeated export PASS. Governance83 PASS after using prepared venv PATH (initial sandbox cache failure preserved separately). Bootstrap/process preflight PASS. System TLS baseline accepts both advisory certificates; HTTPX/Requests accept the first; ordinary HTTPS succeeds.
