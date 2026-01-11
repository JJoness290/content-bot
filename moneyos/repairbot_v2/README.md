# RepairBot v2

RepairBot v2 is an autonomous repair loop for MoneyOS.

## Run

```bash
python -m moneyos.repairbot_v2.run --mode once
python -m moneyos.repairbot_v2.run --mode watch
```

## UI

Visit `/repairbot` for status, preflight, plan, preview, and an iteration trigger.

## Outputs

All artifacts are written to `outputs/repairbot_v2/`:

- `preflight_latest.json` / `.md`
- `plan_latest.json` / `.md`
- `preview_latest.md`
- `last_status.json`
- `snapshots/` and `diffs/`

## Rollback

Baseline snapshots are stored in `outputs/repairbot_v2/baseline_commit.txt`.
The agent rolls back using `git reset --hard <baseline>`.

## LLM Selection

Order of preference:

1. Ollama (`OLLAMA_HOST` / local)
2. Transformers (`TRANSFORMERS_MODEL`)
3. OpenAI (`OPENAI_API_KEY`)
4. Heuristics-only
