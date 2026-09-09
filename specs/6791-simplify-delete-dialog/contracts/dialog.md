# Контракт подтверждения

FR-001/003: тексты заданы в spec US1/AC1. FR-002/006: нет технического списка и ссылки; подробный отчёт не изменяется.
FR-004: тот же POST /meetings/{id}/deletion-requests или /desktop/meetings/{id}/deletion-requests; прежние hidden _csrf и confirmation_boundary=BOUNDED_DELETE_COPY. Нет удаления по открытию/отмене/ссылке.
FR-005: сохранить id, aria-labelledby, tabindex заголовка, data-meeting-delete-*; type=button у отмены, type=submit и danger-button у удаления. Существующие JS и адаптивные темы без изменений. При delete.state != available — пустой fragment.
