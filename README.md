# FixIt LLMOps

Local-first customer-support routing system for FixIt. The application classifies queries, selects a model tier and prompt from external configuration, tracks cost, applies budget controls, and supports both mock and real Gemini execution.

## Implemented Capabilities

- Configuration-driven routing and prompt selection from `configs/config.yaml`
- Hot reload with last-known-good fallback for invalid config changes
- Query classification with three modes:
  - `rule_based`
  - `gemini`
  - `hybrid`
- Gemini-backed generation via REST API and mock-safe local execution
- Prompt fallback chain:
  - selected prompt
  - configured base prompt
  - built-in fallback prompt
- Estimated and actual cost tracking with warning, critical, and degraded modes
- Model fallback to cheaper tiers when generation fails
- Evaluation workflow that writes JSON and CSV reports under `reports/`
- CLI entry points for single-query and interactive testing

## Project Layout

- `configs/`: active app and pricing configuration
- `prompts/`: versioned prompt files
- `src/`: application modules
- `scripts/`: local run and evaluation entry points
- `sample_data/`: evaluation dataset
- `data/`: prompt runtime metrics
- `reports/`: evaluation artifacts
- `tests/`: unit and integration coverage
- `docs/`: design and implementation documentation

## Key Configuration

`configs/config.yaml` controls routing, prompt defaults, budgets, and classifier behavior. The classifier section is:

```yaml
classifier:
  mode: rule_based
  provider: gemini
  model_id: gemini-2.5-flash-lite
  low_confidence_threshold: 0.65
  fallback_to_rule_based_on_error: true
```

Classifier modes:

- `rule_based`: deterministic keyword and substring matching
- `gemini`: classify every query with Gemini
- `hybrid`: use Gemini only for ambiguous or low-confidence rule-based results

## Environment

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Runtime variables:

- `PROVIDER_MODE=mock|gemini`
- `GEMINI_API_KEY=<your key>` when using Gemini
- `GEMINI_API_BASE_URL` optional override
- `GEMINI_TIMEOUT_SECONDS` optional timeout override

Default local execution can stay on `PROVIDER_MODE=mock`. Switch to `gemini` only when a valid key and quota are available.

## Run

Single query:

```powershell
python scripts/query_app.py "What are your working hours?"
```

Interactive CLI:

```powershell
python scripts/query_app.py
```

Evaluation workflow:

```powershell
python scripts/run_evaluation.py
```

## Test

Run the full suite:

```powershell
python -m pytest
```

The current implementation passes the full test suite locally.

## Evidence and Reports

- Prompt metrics file: [data/prompt_metrics.json](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/data/prompt_metrics.json)
- Evaluation report: [reports/evaluation_report.json](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/reports/evaluation_report.json)
- Evaluation results: [reports/evaluation_results.csv](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/reports/evaluation_results.csv)

## Documentation

- [LLD.md](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/docs/LLD.md)
- [IMPLEMENTATION_CONTEXT.md](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/docs/IMPLEMENTATION_CONTEXT.md)
- [IMPLEMENTATION_ARTIFACTS.md](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/docs/IMPLEMENTATION_ARTIFACTS.md)
- [TECHNICAL_DECISIONS.md](C:/Users/Dell/Desktop/Phase3-AI/KDU-2026-AI/docs/TECHNICAL_DECISIONS.md)
