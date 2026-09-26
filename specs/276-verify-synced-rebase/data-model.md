# Data model

Форматы не меняются. PR: immutable head/merge SHA, API base, count 1..1000.
Доказательство: ordered source/target commits, checked_base, tree SHA шагов.
Состояния: unverified → verified base или failure; частичного PASS нет.
Run/receipt/attempt/currentness остаются существующими. Новых БД/схем нет.
