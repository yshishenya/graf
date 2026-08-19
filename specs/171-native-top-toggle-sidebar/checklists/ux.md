# UX Checklist: Единый верхний toggle и аккуратный rail

**Purpose**: Проверить визуальную и accessibility полноту native/web среза
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

- [x] Toggle имеет один стабильный slot и понятное действие в обоих состояниях
- [x] Длинное native-содержимое не сдвигает toggle и не перекрывается им
- [x] Wide/narrow default states проверяются отдельно на web и embedded
- [x] Compact rail не оставляет пустой логотипный слот
- [x] Compact navigation сохраняет accessible names, focus и tooltip
- [x] Проверяются keyboard, reduced motion, contrast и overflow
- [x] В evidence не попадают private meeting content, audio или credentials

## Notes

Результаты визуального audit и проверки accessibility будут добавлены в
`quickstart.md` и `analysis.md` после реализации.
