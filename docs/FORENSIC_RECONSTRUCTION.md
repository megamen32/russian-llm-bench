# RuBench forensic reconstruction

Дата архива: 2026-08-13. Цель — сохранить воспроизводимый слепок локального эксперимента, а не объявить законченный benchmark.

## Источники реконструкции

- текущий checkout и `git log`;
- локальные JSONL-результаты в `results/full/`;
- Codex rollout/session JSONL и session-events index текущей задачи;
- локальные Hugging Face snapshot-кэши SLAVA и MERA;
- official MERA checkout, использованный для проверки ruTiE-протокола.

## Что реально запускалось

| run | model | route | status |
|---|---|---|---|
| Sol canaries/partial | `gpt-5.6-sol` | Codex CLI, OpenAI/Codex runtime | partial |
| MiniMax partial | `minimax/MiniMax-M3` | local OmniRoute `http://127.0.0.1:20128/v1/chat/completions`, auth field `omniroute` redacted | partial |

Два lane одного имени модели — это ускорение одного прогона, не две модели. `ruTiE` должен идти последовательно, поскольку prompt следующего вопроса зависит от предыдущего ответа.

## Reasoning / thinking

- Sol: `reasoning_effort`, `thinking`, `reasoning_split`, service tier — `unknown / not recoverable`; Codex CLI receipt с этими полями не был сохранён.
- Ранний MiniMax route: `thinking: {"type":"disabled"}`, `reasoning_split: true`; длинные batch-запросы иногда всё равно возвращали обрезанный JSON.
- Финальный проверенный MiniMax canary: `thinking: {"type":"disabled"}`, `reasoning_split` убран, `reasoning_tokens: 0`, `max_completion_tokens: 256`; batch 10 вернул 10/10 записей.
- Service tier (`fast`/`default`) и reasoning effort: `unknown / not recoverable`.

## История режимов и отказов

1. Sol: batch 3 canary 3/3; batch 10 preflight 10/10; full lanes стартовали с batch 25.
2. Sol: два lane остановились на 500 и 525 строках из-за Codex CLI ошибки записи PATH aliases в read-only sandbox. Результаты до остановки сохранены.
3. Для Sol добавлен retry/backoff; локальный commit `5f00635`, push в тот момент был заблокирован временным DNS.
4. MiniMax: OmniRoute HTTP 200 canary; ранний batch 25 мог упереться в фактический completion limit 256 и дать неполный JSON.
5. MiniMax: batch 5 был устойчивее, но слишком медленным; batch 10 прошёл live-canary 10/10.
6. MiniMax: `reasoning_split: true` использовался в раннем режиме и затем удалён; после удаления receipt показал `reasoning_tokens: 0`.
7. Два параллельных MiniMax lane дали нестабильные неполные JSON/таймауты; partial JSONL не переписывались.
8. Docker: `planned_not_used`. Ни один benchmark-запрос фактически не выполнялся из Docker; Docker image, digest, container ID и compose manifest: `unknown / not recoverable`.

## Prompt provenance

Точные восстановленные варианты wrapper/canary prompt находятся в `prompts/prompt-variants.json`. Полные expanded per-task prompt payloads для каждого исторического HTTP-запроса не были сохранены отдельным receipt и отмечены как `unknown / not recoverable`; dataset prompts сохранены в `datasets/`.

## Данные и результаты

- `datasets/SLAVA/open_questions_dataset.jsonl` — локальная копия snapshot, 2,840 записей.
- `datasets/MERA/data/` — materialized copy локального snapshot, 43 файла с train/dev/test и reference fields.
- `results/full/` — исходные raw JSONL, не переписанные.
- `results/normalized/` — производное представление с `source_raw_file` и `source_line`.
- `manifests/datasets.json`, `manifests/models.json`, `manifests/runs.json` — hashes, route/config provenance, статусы и неизвестные поля.

В архивах нет API keys, bearer tokens, cookies или auth-файлов. Auth mechanism и имя credential field сохранены как redacted metadata.

## Что пока невозможно доказать

- точный provider-side service tier;
- Sol reasoning level и Sol usage receipt;
- точные timestamp начала каждого batch;
- dirty/clean состояние checkout в момент каждого запуска;
- upstream commit/tag snapshot-ов Hugging Face;
- полный HTTP receipt каждого запроса MiniMax;
- Docker image/container provenance, так как Docker не использовался.

Эти поля намеренно записаны как `unknown / not recoverable`, а не реконструированы догадкой.
