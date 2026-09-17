# Data model
Сохранённый MeetingDetectionSettings остаётся без изменения: automaticRecordingRules,
uploadMode, unknownIdentityUploadAllowed. Патч меняет только указанные правила.
Перенос не связывает значения с аккаунтом или workspace.

Transient snapshot: version=1, targets=[{id,name,rule}], error?.
Rule: always | ask | never. Реестр — только isVerifiedNativePromptTarget.
Пустой список валиден; массовый выбор недоступен.
Document nonce не сохраняется; обновляется при полной навигации и отзывает старые команды.
