# Russian LLM Bench

Small, reproducible **blind** diagnostic slices for two Russian benchmarks:

- [SLAVA](https://huggingface.co/datasets/RANEPA-ai/SLAVA-OpenData-2800-v1)
- [MERA](https://huggingface.co/datasets/ai-forever/MERA)

The goal is not to publish a leaderboard from 20 questions. It is to make a
cheap comparison that can be rerun without leaking answer keys into prompts.

## Current diagnostic result

All models received the same fully rendered 20-item input: 10 SLAVA tasks and
10 MERA tasks. The answer key is stored separately and is never passed to a
model. Scores below are strict normalized exact matches.

| Model | SLAVA | MERA scalar tasks |
| --- | ---: | ---: |
| GPT-5.6 Luna | 6/10 | 4/8 |
| GPT-5.4 mini | 6/10 | **5/8** |
| MiniMax M3 | 7/10 | 4/8 |
| GPT-5.6 Sol | **9/10** | 4/8 |

Two MERA records (`multiq`, `ruethics`) are intentionally not shown in the
MERA scalar column. They need their task-specific official metrics rather than
string equality.

### The slightly cursed MERA observation

On eight heterogeneous, mostly scalar MERA examples, the smaller GPT-5.4 mini
beats the larger models by one exact match. This is funny, but it is **not**
evidence that making a model worse makes it better at MERA. With `n = 8`, one
answer moves the percentage by 12.5 points; MERA also mixes different task
types and scoring rules. The responsible conclusion is: this slice is too
small to rank models on MERA.

SLAVA does separate the models on this slice: Sol scored 9/10, versus 7/10 for
M3 and 6/10 for Luna and 5.4 mini. It is still a diagnostic signal, not a
published benchmark claim.

## What a task-specific scorer is

A scorer is code, not a person and not another LLM. It implements the official
metric for an individual MERA task.

- **MultiQ** expects a structured answer, including an extracted text segment
  and its location. A semantically correct string cannot be graded fairly with
  `prediction == gold`.
- **RuEthics** has several labels per example, one for each ethical framework.
  It needs a multi-label metric instead of comparison with one string.

The next meaningful step is to integrate MERA's official scorers and run a
larger fixed sample per task. Until then this repository reports the 8 scalar
MERA examples separately and does not turn them into a fake aggregate score.

## Reproduce the slice

The public manifest fixes the 20 examples by benchmark, task and ID. Fetch the
two source datasets at the revisions recorded in `data/slice-manifest-v3.json`,
then build a prompt-only input with `build_blind_v3.py`. The builder deliberately
does not write the reference answers.

```bash
python3 build_blind_v3.py \
  --slava /path/to/open_questions_dataset.jsonl \
  --mera /path/to/MERA/data \
  --output data/blind-input-v3.json
```

Create the local key in a separate, non-public path:

```bash
python3 build_blind_v3.py \
  --slava /path/to/open_questions_dataset.jsonl \
  --mera /path/to/MERA/data \
  --output /tmp/blind-input-v3.json \
  --reference-key /tmp/reference-key-v3.json
```

Run only `/tmp/blind-input-v3.json` through a model. Save `benchmark`, `task`,
`id`, optional `split`, and the model `answer` in the same shape as files in
`results/`, then score it locally:

```bash
python3 evaluate_blind_v3.py --key /tmp/reference-key-v3.json results/model.json
```

Do not send the key to a model and do not commit it to a public repository.

## Route evidence and pending models

The requested OpenCode-only route for GLM-5.2 is visible as
`omniroute/opencode/glm-5.2`, but its canary returned HTTP 402 because that
OpenCode connection has no provider API key. It was not silently substituted
with Auto or another Z.ai route.

GLM-5 Turbo appears in non-OpenCode Z.ai/Cline catalog routes, but was not
listed in the active `opencode` / `opencode-go` catalog. It remains pending an
actual OpenCode route and credential.

## Repository contents

- `build_blind_v3.py` — deterministic, prompt-only slice builder.
- `data/` — the blind prompts and the separate key for this diagnostic slice.
- `results/` — model answers used for the table.

No full benchmark datasets, API keys, provider credentials, or raw service logs
are included.
