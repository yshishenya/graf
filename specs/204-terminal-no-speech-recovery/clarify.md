# Clarification Record: Feature 204

Критические вопросы не остаются открытыми. Контракт уже определён Feature 195
и подтверждён production-диагностикой: `no_recognizable_speech` является
terminal business outcome, повторная попытка только явная, а Temporal dispatch
и quota/deletion fences переиспользуются.

Решения:

- Разрешается новая попытка только для result текущей revision и текущего
  terminal workflow.
- Старый result не удаляется и не переписывается.
- Состояние нового workflow имеет приоритет в projection, пока он active.
- API recovery routes не зависят от предварительно заполненного process state:
  Temporal client подключается лениво и переиспользуется после успешного
  подключения; при реальной недоступности сохраняется компенсационный путь.
