# Data Model: Процесс от разработки до релиза

Изменение не добавляет runtime-данные или миграции.

Для release evidence используются только metadata-поля:

- exact commit SHA;
- validation mode (`focused`, `fast`, `full`);
- command/result/timestamp;
- deploy, smoke и rollback status.

Raw audio, transcripts, credentials, signed URLs и private meeting content в
evidence не входят.
