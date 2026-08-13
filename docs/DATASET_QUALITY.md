# Dataset quality notes

The materialized MERA snapshot is preserved unchanged from the local cache.

Validation note:

- The file must be split on physical LF bytes (`b"\\n"`) when validating JSONL. Python `str.splitlines()` also treats Unicode line separators such as U+2028 as line boundaries.
- `rummlu/train.jsonl` contains a U+2028 character inside a JSON string at the physical record corresponding to dataset id 3379. That is valid JSON and is present identically in the source blob and the archive.
- The source bytes are retained; no repair, deletion, normalization, or silent replacement was performed.
