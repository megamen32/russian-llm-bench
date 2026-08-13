# Failure log

| date | mode | symptom | impact | preserved evidence |
|---|---|---|---|---|
| 2026-08-13 | Sol/Codex CLI | `Read-only file system` while creating PATH aliases | both lanes stopped after 500/525 | raw Sol lane JSONL; session transcript; `manifests/runs.json` |
| 2026-08-13 | MiniMax batch 25 | response ended at effective 256 completion tokens / incomplete JSON | batch not appended | transcript canary summary; retry code; run manifest |
| 2026-08-13 | MiniMax parallel lanes | malformed JSON and timeout under concurrent load | lanes stopped/restarted, prior rows retained | raw lane JSONL; transcript; failure log |
| 2026-08-13 | MiniMax `reasoning_split=true` | early route showed reasoning behavior despite disabled thinking on long batches | configuration changed | prompt/config history and live receipt summary |
| 2026-08-13 | MiniMax no-reasoning batch 10 | live receipt showed `reasoning_tokens: 0`, 10/10 parsed | accepted canary only; no full completion | `manifests/runs.json` |

No Docker benchmark run exists. Docker is recorded as a future reproducibility mode, not retroactively claimed as execution evidence.
