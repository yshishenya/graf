# F263: данные проверки

Продуктовые сущности не меняются. Существующий JSON плана сохраняет changed_paths,
groups, tests, covered_tests, environment, scope, coverage, next_gate и сведения
Git. tests/covered_tests не пересекаются; объединение равно mapped целям.
Временный JUnit должен содержать каждый выбранный модуль без skipped. Ошибка
runner сохраняет ненулевой код. Секреты/данные встреч в материалы не записываются.
