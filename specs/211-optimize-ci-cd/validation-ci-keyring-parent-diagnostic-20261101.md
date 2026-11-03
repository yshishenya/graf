# F211 T114: диагностика отказа каталога ключей

Предыдущий source e118223edac681a0fa90ea502ba11feba8596665,
run41256850185/job124701772801,01.11.2026 00:28:23UTC отказал
`unsafe keyring directory` до actual pin. Метаданные каталога неизвестны;
нет разрешения изменять каталог или принимать неизвестное содержимое.

Независимое before-code CLI requirements review PASS, existing checklist5/0,
scoped analyze4/4 C/H/M0 и sync #7859/canon250issuesPASS. Reviewer читал
только файлы, не запускал тесты, не менял состояние. Новый срез меняет только
сообщение прежнего guard из уже прочитанного key_parent: fixed literal
keyring-directory и numeric type/uid/gid/mode/size. Никаких новых runtime
reads/writes, paths/content/env или изменения guard/control flow.

RED9fail/3PASS на прежнем сообщении, GREEN12PASS. Восемь static/process
PASS. Независимое read-only code review: no actionable defects, без
самостоятельного запуска тестов. Его вывод не означает native success,
merge или release acceptance. Scoped converge4/4: дополнительной задачи
для этого диагностического среза не найдено, native facts и последующая
функциональная адаптация остаются внутри открытой T114. Tasks не менялись.

## Контрольные суммы независимых журналов

- .dev/ci-official-sources/key-parent-requirements-review.log: `bac3cdeefeae0db7bec4894da3ec9ab70661fe960d1e8b4fe0a7bade5f975fbe`.
- .dev/ci-official-sources/key-parent-code-review.log: `8e83f629d9e21a379b26c41b0285b43e47071cfa2031a107185683821b31c153`.
- .dev/ci-official-sources/key-parent-red.log: `ec0f0982f4746e80efe13ab5245794222e98cdd3dd46de3bddc0baa3a8346b1f`.
- .dev/ci-official-sources/key-parent-green.log: `ec9e2f92cf0c127e97f389f252a67b03a917481d646e64ef9f4361ac98c3fa86`.
- .dev/ci-official-sources/key-parent-static.log: `c35b8b3e9f9a9acfe6c79b9be835e575ba52f6a6311ef30f7bbdc8c2ac5add1d`.

Полный профиль исполнителя: **453PASS,0skips,162,81с**; source hashes до/после
совпали. Module log SHA256`b38eff286cf57948e368e14f4f0537fda47cdd77f44d139716d4ca028d09739e`.
