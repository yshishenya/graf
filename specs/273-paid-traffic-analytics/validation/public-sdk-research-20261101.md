# T106: предварительная изолированная проба официального SDK

Только исследование, не приёмка контроллера ГРАФ/всей T106. 01.11 по
Стамбулу,31.10~22:10–22:14UTC. Непостоянный headless Chrome, новая
синтетическая страница graf-sdk-test.invalid, counter99999999.

С Mac mc.yandex.ru/metrika/tag.js вернул404, также проверены .ru с учебным
ID и .com —404. С рабочего сервера оригинальный .ru URL в22:10:07UTC дал
200 application/javascript,208600байт. Файл получен через сервер без его
сохранения на нём; локальный SHA-256 совпал:
`72dadb1a319174bf611e44d0a70ed9569fb3c72fdd685223ac6091fc3ef0db9e`.
Эти наблюдения не доказывают причину различия сети или сбой у всех клиентов.

Все HTTP/WebSocket перехватывались: HTML/SDK/watch получили локальные
ответы, прочее abort/close. Реальные запросы получателю не forwarding.
Replay/clickmap/trackLinks/form_analytics false; accurateTrackBounce true,
defer true. SDK создал yaCounter99999999; до отзыва3 watch attempts
(fetch/ping). Затем disableYaCounter+штатный destruct: instance отсутствует;
клик, scroll, focus/resize/visibility и20с наблюдения дали0 новых attempts.
Watch backend отвечает минимальным учебным JSON, а не реальными settings.

Первый CLI-проход завершился без возврата результата: console.log в driver
не отобразил сводку. После закрытия контекста повторён новый с явным return;
принята только его сводка. Ошибки browser console относятся к трём
преднамеренно blocked sync_cookie/advert image запросам перед отзывом.
Browser закрыт. SDK/скрипт/полный результат в ignored output/playwright/
graf-sdk-20261101 пока нужны активной проверке; в Git только этот отчёт.

Хеш script:`ad89794e2a6641b9372d8f8bbff1a47727c0a6342d7839b3b57734490ef168f4`.
Хеш result:`d08195da22eb256329f68e9e0b8c82d9dde872478cae5d3bd07008781bb41d96`.

Проба не использует контроллер/библиотеку ГРАФ, вторую вкладку, replay
или настоящий backend. Отдельный focused профиль спланирован для первых
двух пробелов; остальные HOLD сохраняются. Конечное20с наблюдение не
доказывает любой будущий момент или готовность рабочего включения.
