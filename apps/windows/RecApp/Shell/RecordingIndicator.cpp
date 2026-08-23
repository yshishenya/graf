#include "RecordingIndicator.h"

namespace graf::windows {
namespace {

std::string statusText(SessionState state) {
    switch (state) {
    case SessionState::idle: return "Запись не активна";
    case SessionState::checkingReadiness: return "Проверка готовности";
    case SessionState::ready: return "Готово к записи";
    case SessionState::starting: return "Запуск записи";
    case SessionState::recording: return "Идёт запись";
    case SessionState::paused: return "Запись на паузе";
    case SessionState::degraded: return "Запись ограничена";
    case SessionState::stopping: return "Остановка записи";
    case SessionState::finalizing: return "Сохранение записи";
    case SessionState::savedLocal: return "Сохранено локально";
    case SessionState::queued: return "Ожидает отправки";
    case SessionState::uploaded: return "Отправлено";
    case SessionState::blocked: return "Запись недоступна";
    case SessionState::failed: return "Не удалось сохранить запись";
    }
    return "Состояние записи неизвестно";
}

} // namespace

RecordingIndicator::RecordingIndicator(StopHandler stopHandler)
    : stopHandler_(std::move(stopHandler)) {}

void RecordingIndicator::publish(SessionState state, ReasonCode reason) {
    snapshot_.state = state;
    snapshot_.reason = reason;
    snapshot_.visible = isCaptureState(state);
    snapshot_.stopAvailable = snapshot_.visible;
    snapshot_.accessibleName = snapshot_.visible ? "GRAF: остановить запись" : "GRAF: запись не активна";
    snapshot_.statusText = statusText(state);
}

void RecordingIndicator::hide() noexcept {
    snapshot_.visible = false;
    snapshot_.stopAvailable = false;
}

void RecordingIndicator::clickStop() {
    if (snapshot_.stopAvailable && stopHandler_) stopHandler_();
}

} // namespace graf::windows
