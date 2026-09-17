# Research

Дата: 2026-09-12. Base: ad71f2ce4db68d846d7c333213961c5f5f7d5e89.

- Decision: общий фиксированный порог 30 секунд, без диалога. Rationale: прямое уточнение владельца после исследования 2026-09-11. Alternatives: 10 секунд слабее отсеивает случайные запуски; 2 минуты слишком агрессивны; ручной диалог явно отклонён.
- Krisp overview указывает 30 секунд, FAQ — 2 минуты; это не доказательство фактического удаления аудио. https://help.krisp.ai/hc/en-us/articles/8214720684956-AI-Meeting-Assistant-overview и https://help.krisp.ai/hc/en-us/articles/8326933081116-AI-Meeting-Assistant-FAQ
- Исследование ICASSP 2025 https://www.alphaxiv.org/abs/2501.11378 касается ложных расшифровок неречевого звука, не обосновывает полезность по длительности. VAD/ИИ не добавляем.
- Decision: решение writer до публикации manifest. Rationale: enqueueSaving предшествует остановке; scanner работает асинхронно. Alternatives: удаление только из UI оставляет race/restart upload.
- Decision: frameCount/sampleRate канонического WAV. Rationale: ceil seconds очереди и AAC duration искажают границу. Тишину и выключение микрофона не вычитаем.
- Decision: optional признак + blocked result. Rationale: старые записи не затрагиваются; старый клиент не принимает такой пакет в upload. Перед откатом завершить cleanup.
- Decision: reuse проверки root и сериализации DesktopUploadQueueService; удалить manifest последним. Rationale: сбой физического удаления должен оставлять durable запрет. Полный новый механизм tombstone/reconciliation не нужен.
- Decision: самостоятельное нейтральное сообщение, не recordingBlocker. Rationale: blocker запускает диагностику и системное уведомление ошибки.
