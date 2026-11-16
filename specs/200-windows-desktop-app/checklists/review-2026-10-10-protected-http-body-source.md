# T116 — независимый source-review protected HTTP body, frozen312

SCOPED SOURCE GO — C0/H0/M0/L0 только для пятифайлового body/transport-среза.
Это не compilation/native/full/installed/release GO и не закрытие T116/#7444.
Принятая HTTP-конструкция из nine-hash requirements GO остаётся обязательной.

## Точные входы

Canonical HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty bytes.
Проверялся frozen `/Users/yshishenya/Documents/graf-f200-http312-native.YHZXTp`.
`source312.json` SHA-256:
`5e7b08688a1c12656848074a58ef3d6d3791c2fa73f011536304cf936f975edb`.
База: `/Users/yshishenya/Documents/graf-f200-http310-red.LFfgRh/source310.json`,
SHA-256 `c021ff32d3d7aba3bb643c14d7b4529a34cfd45920600c7ceebf3172f1169998`.
У обоих снимков проверены209/209 physical file hashes; diff содержит ровно
следующие пять production-файлов. Test inputs неизменны относительно310.
При source-review все пять canonical файлов также совпали с frozen312.

| Файл от корня репозитория | Frozen312 SHA-256 |
| --- | --- |
| apps/windows/RecApp/Recording/LocalRecordingPackage.cpp | 3d9de267321760047253f29dab49fde01d52f6cbd5632f0b4233cd6132f7dafd |
| apps/windows/RecApp/Recording/LocalRecordingPackage.h | eb99a90b6027a2941d462ca460a3e4789c1e66113f1d6cfbe339781ddde446de |
| apps/windows/RecApp/Recording/NativeCapture.h | aa532e1d4ce802087b82bce3240361733b1cf30c2bdbdf498e8611a49cbd0257 |
| apps/windows/RecApp/Upload/DesktopHttpTransport.cpp | 50d8655a94484b35acd867c436c4df5993bd409ae7a1b0630076feb9cd7ad3dc |
| apps/windows/RecApp/Upload/DesktopHttpTransport.h | 049f366bd8f81907ebf508ad1dd81667fc705239d498947ddce1aa882861da11 |

## Проверенная причинная цепочка

- LocalRecordingPackage.cpp:437–440,567: genuine semantic inspection сохраняет
  уже charged owning session через move после её validation, не string_view
  или повторный parser. Pair/readers остаются внутри retained proof.
- DesktopHttpTransport.cpp:1201–1247: protected overload принимает strong proof
  по значению; loader удерживает его до выхода uploadPrepared. Проверяются
  valid/sealedNormal, точные pair directory и validated session. Три selected-slot
  refs sealed, имеют length/SHA; bounded whole-stream hash сверяется с ref.
  Borrowed IStream живёт не дольше удержанного proof. Proof не account/queue grant.
- DesktopHttpTransport.cpp:1023–1197: один общий production upload flow для
  legacy/protected source. Owner/unclaimed/session и прежний wire protocol
  сохраняются. Protected loader failure не вызывает packageTracks/plaintext
  fallback; успешные protected tracks несут stream, а не plaintext path.
- DesktopHttpTransport.cpp:638–702: range bounds, explicit Seek, exact reads
  не более256KiB; cancel/short read/failure не отправляет недозаполненную часть.
  HTTP partSize не меняется. allocate_shared с CustodyAllocator учитывает body
  object/control block; внутренний CustodyBytes storage также charged. Mutable
  owner перемещается в shared<const CustodyBytes> перед send, ordinary body пуст.
  Part digest/offset/index/ack sequence сохраняются; bad_alloc даёт retryable
  failure с передачей уже известного server truth общим flow.
- DesktopHttpTransport.h:128–134, cpp:452–460: mixed bodies invalid до WinHttpOpen.
  Native wrapper удерживает strong body owner до возврата вложенного request;
  request handles закрываются там же раньше owner release, включая exception
  unwinding. Cancel не стирает активный native body. Default native wire как
  legacy upload, так и protected overload вызывает именно этот wrapper.
- NativeCapture.h:227,1117–1129: injected wire захвачен по значению в account
  task. Default остаётся native account getter; fake GET использует прежний
  resolver и authGeneration adoption. Нет private account setter/auth policy
  change. Будущий protected scheduler executor пока этим wire не подключён.

## Обязательные незавершённые границы

ALL-control-buffer quota остаётся PENDING: request/response/hash/serialization
capacity, control blocks, Debug allocations и retained flight/results должны
войти в общий бюджет до allocation. Charged payload не принимает весь бюджет.
64MiB owned/cache2MiB/pins32/jobs4 не повышаются.

Scheduler/result остаются PENDING: непустой prepare всегда full commit/adoption;
storage-worker proof preparation/launch, отдельный network executor, fresh current
queue single result commit/adoption, stale-before/after-publish fences, lost poll,
effects after ACK и actual last release/drain. Body overload не принимает этот
сквозной путь. T120 и остальные consumers/global admission остаются закрытыми;
FULL T116, T117/T118, installed/hardware/parity/release не приняты.

## Статус проверок и сохранность

Reviewer применил code-reviewer, прочитал frozen diff/связанный код и проверил
hashes; builds/tests/native jobs/VM/CUA не запускал. Root bugs в этом scope
не обнаружены. RED311 terminal4/4 expected missing APIs и ложный harness310
сообщены main; reviewer независимо их здесь не принимал.

Последнее сообщение main: portable312 build exit0,47PASS/29.97s; native312
запускается последовательно для Calendar unit и Capture --protected-upload,
Release/Debug, после terminal311 bound RED. Это не результаты, лично прочитанные
reviewer, и не full-suite claim. Native312 outcome на момент отчёта PENDING;
последующий отказ требует отдельной проверки exact frozen source.

Единственная запись reviewer — этот новый файл. Production/tests/spec/plan,
tasks, нормативные checklist markers и прежние отчёты не изменялись.
