# Built-in format contracts

All formats inherit: untrusted transcript boundary, exact source refs, atomic/deduplicated items, no invented owner/date/decision, latest explicit correction, honest empty states and strict closed JSON schema.

| Key | Name | Prioritize | Exclude |
|---|---|---|---|
| `graf-auto-v1` | Авто | concise result, key themes, explicit decisions/actions, risks/questions | guessed meeting type, filler chronology |
| `graf-outline-v1` | По темам | topic outline in conversation order, transitions, supported conclusion per topic | greetings/setup/repetition as key points |
| `graf-meeting-minutes-v1` | Протокол встречи | purpose, final decisions, commitments, follow-ups | proposal/option as final decision |
| `graf-project-sync-v1` | Синхронизация проекта | health evidence, progress, milestones, blockers, dependencies, decisions/asks | invented health label or completion |
| `graf-weekly-team-meeting-v1` | Еженедельная встреча команды | weekly changes, wins, priorities, blockers, team actions/questions | personal evaluation not discussed as team result |
| `graf-one-to-one-v1` | Один на один | person-led themes, wins, workload, support, feedback, mutual commitments | diagnosis, sentiment score, performance verdict |
| `graf-client-status-update-v1` | Статус для клиента | reporting period, delivered value/progress, evidence, risks, decisions/asks, next review | internal speculation or unspoken renewal/upsell |
| `graf-interview-v1` | Интервью с кандидатом | questions, observable answers/evidence, candidate questions, follow-ups | protected traits, invented score/recommendation/hiring decision |
| `graf-sales-discovery-v1` | Выявление потребностей | current state, pains/impact, goals, constraints, stakeholders/process, objections, agreed next step | guessed budget/authority/timeline/fit |

Personal formats select supported sections and language/detail only; personal text remains data and cannot weaken inherited trust rules.
