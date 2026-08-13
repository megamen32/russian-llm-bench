# Dataset quality notes

The materialized MERA snapshot is preserved unchanged from the local cache.

Known parse issue:

- `datasets/MERA/data/rummlu/train.jsonl:3380-3381` is not valid JSONL: line 3380 has an unterminated string and line 3381 begins with a continuation that is not a JSON value.
- This does not affect the MERA `test.jsonl` rows used by the prompt-only run, but it prevents claiming that every archived train file is valid JSONL.
- The source bytes are retained; no repair, deletion, normalization, or silent replacement was performed.
