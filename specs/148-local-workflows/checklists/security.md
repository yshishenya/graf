# Security Requirements Checklist: Локальные workflows

**Purpose**: Проверить полноту и непротиворечивость требований к signer custody
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md)

## Secret Custody

- [x] CHK001 Требования запрещают экспорт private signer во все новые каналы. [Spec §FR-005]
- [x] CHK002 Единственный разрешённый signer и его public identity однозначно определены. [Spec §FR-005, §FR-006]
- [x] CHK003 Требования к metadata-only evidence исключают private material и live paths. [Spec §FR-006]

## Provenance And Publication

- [x] CHK004 Exact tag, commit, default branch и clean checkout определены как обязательные gates. [Spec §FR-007]
- [x] CHK005 Archive traversal и unsafe extraction описаны как fail-closed scenarios. [Spec §FR-008]
- [x] CHK006 Draft-only upload и отдельная production-feed mutation заданы без двусмысленности. [Spec §FR-010]
- [x] CHK007 Partial failure и retry boundary отражены в требованиях и data model. [Spec §Edge Cases]

## Compatibility

- [x] CHK008 Сохранение trust generation, key ID и public key явно обязательно. [Spec §FR-014]
- [x] CHK009 Ротация ключа и production deploy явно исключены. [Spec §FR-014]
