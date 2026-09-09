# Research

- Decision: править общий _render_delete_confirmation. Rationale: единственный caller render_meeting_detail_page обслуживает web/embedded; JS только открывает/закрывает native dialog, POST идёт прежним form. Alternatives: новый компонент/JS/CSS не нужен.
- Decision: убрать ссылку на отчёт. Rationale: deletion_report_response возвращает deletion_report_not_found до первого request_meeting_deletion. Alternatives: новый экран подробностей усложнил бы задачу.
- Decision: коротко назвать границу GRAF и необратимость. По уточнению пользователя исключение скачанных/отправленных копий в окне не перечисляется. Rationale: PRD и product-gates; технические сведения нужны в существующем отчёте, а не подтверждении.
- Независимое исследование: агент deletion_review подтвердил границы и отсутствие отчёта до удаления. Технических неизвестных не осталось.
