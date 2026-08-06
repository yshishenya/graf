# Security and privacy requirements checklist

- [x] [CHK001] Все четыре transient email form endpoints перечислены явно.
- [x] [CHK002] Transient WebKit responses отделены от SwiftUI-owned GET routes.
- [x] [CHK003] Same-origin allowlist и Yandex OAuth явно сохранены в scope.
- [x] [CHK004] Запрещено записывать email, коды, cookies, tokens, audio и meeting content.
- [x] [CHK005] Production deploy и credentials явно исключены из реализации.
