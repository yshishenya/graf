# Data Model: Закреплённый верхний блок встречи

Изменений постоянной модели данных нет.

## Presentation contract

| Element | State | Rule |
|---|---|---|
| Meeting detail header | normal/sticky | one wrapper, same content order |
| Topline | inside wrapper | title, metadata and actions remain visible |
| Tabs | inside wrapper | one role=tablist, no independent sticky layer |
| Scroll target | transcript/outcome | scroll margin leaves target visible |
