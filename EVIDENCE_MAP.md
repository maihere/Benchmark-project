# Evidence Map — LLM Benchmark Project

Traceability index: every claim made in the decision logs and the portfolio
entry should resolve to one of the rows below. Use this when writing or
reviewing the portfolio so each statement can be checked against a real file.

| Claim / Finding | Backing artifact | Decision Log |
|---|---|---|
| Academic benchmarks (MMLU) don't reflect real coding usefulness | `documents/Benchmark LLM - domain understand.docx` | DL1 |
| StackEval-style, real-world evaluation is the right direction | `documents/Decision_Log_1.docx` | DL1 |
| BLEU/ROUGE/HumanEval are unsuitable for this benchmark; LLM-as-judge chosen | `documents/Benchmarking LLM approach research.docx`, `documents/Decision_Log_2.docx` | DL2 |
| **Pilot validation (expanded 2026-06-07):** human vs AI-judge scores — 17/21 exact matches (81.0%), 21/21 within 1 point (100%), across all 3 categories and both difficulty levels | `eval_outputs.csv` (Q01–Q03 original 9 rows + Q04/Q06/Q14/Q18 added via `documents/LO2_Pilot_Expansion_Worksheet.docx`, a worksheet the author hand-scored independently before seeing the judge's reasoning) | DL2, DL3 |
| Benchmark design: 30 Python questions × 3 task types × 3 models, judge = GPT-4o, 0–3 rubric | `documents/Decision_Log_3.docx`, `data/questions.csv`, `prompt/answer.txt`, `prompt/judge.txt` | DL3 |
| Full pipeline implementation (ask models, judge, dashboard) | `pipeline/main.py`, `pipeline/answer.py`, `pipeline/evaluate.py`, `pipeline/dashboard.py`, `pipeline/config.py` | DL3, DL4 |
| Q21/o4-mini empty-response bug + judge scored it 3 (Unaligned LLM Judge mistake) | `documents/Decision_Log_4.docx` (narrative); reproduced pattern confirmed in `eval.csv` row Q21/o4-mini | DL4 |
| Fixes: empty-response guard in `answer.py`, skip check + `print_summary()` in `evaluate.py` | `pipeline/answer.py` (`_ask_one` empty guard), `pipeline/evaluate.py` (`run_evaluation` skip block, `print_summary`) | DL4 |
| Streamlit chosen over HTML dashboard ("Remove All Friction" principle) | `documents/Decision_Log_4.docx`, `pipeline/dashboard.py` | DL4 |
| **Final audited leaderboard** — Claude 90.0% (27/30, avg 2.67), o4-mini 56.7% (17/30, avg 1.70), Llama 43.3% (13/30, avg 1.47); 46.7-point spread | `eval.csv` (canonical, 90/90 scored, 0 skips), reproducible via `pipeline/summary_report.py` | DL5 |
| **Per-category breakdown** — Claude 100% conceptual / 92.3% debugging / 77.8% implementation; o4-mini 62.5/61.5/44.4%; Llama 37.5/61.5/22.2% | `eval.csv` → `pipeline/summary_report.py` output | DL5 |
| **prompt.csv vs eval.csv mismatch** — 29/90 rows (Q21–Q30, all 3 models) inconsistent; eval.csv scored against an earlier, complete run, current prompt.csv reflects a later run with Connection-error failures | `pipeline/check_evidence.py` output; raw evidence in `prompt.csv` rows Q21–Q30 vs `eval.csv` rows Q21–Q30 | DL5 |
| eval.csv adopted as canonical evidence source; prompt.csv flagged stale | `documents/Decision_Log_5.docx`, `documents/checklist task.xlsx` (row 17, "Manage & Validate (DL5)") | DL5 |
| Closing the loop: a 46.7-point real-world gap that MMLU-style aggregate scores would not predict or explain | `documents/Decision_Log_1.docx` (original research question) ↔ `documents/Decision_Log_5.docx` (answer) | DL1 ↔ DL5 |
| Recommended pipeline improvement: stamp every CSV row with a run ID so paired output files can be auto-verified | `documents/Decision_Log_5.docx` §7 "What this unlocks" | DL5 |

## Image evidence embedded in the decision logs

Every decision log now carries visual, primary-source evidence for its core
claims — DL1 and DL5 were the two gaps (0 images each) and both now have a
dedicated "Evidence Screenshots" section appended at the end, matching the
screenshot convention already established in DL2 (1), DL3 (5), and DL4 (8).

**Decision Log 1** (`documents/Decision_Log_1.docx`) — 3 figures:

| Figure | Shows | Backs |
|---|---|---|
| DL1-1 | A live academic leaderboard (MMLU-Pro), models ranked by a single aggregate accuracy score | §5 "What I found/observed" — that academic benchmarks reduce a model to one number with no view of real-task usefulness |
| DL1-2 | A comparison table of widely-cited benchmarks showing which are saturated (GSM8K, MMLU, HellaSwag — all "Yes") vs. still meaningful (SWE-bench Verified, HLE — task-grounded, "No") | §5 "What this means" — the direct evidence for why a StackEval-style, task-based benchmark was the right call instead of an academic one |
| DL1-3 | An overview table of what benchmarks like MMLU and HumanEval actually measure (broad academic knowledge / isolated function generation) | §5 "What surprised me" — explains mechanically why models with similar academic scores can "behave very differently in real-world tasks" |

**Decision Log 5** (`documents/Decision_Log_5.docx`) — 3 figures:

| Figure | Shows | Backs |
|---|---|---|
| DL5-1 | Terminal output of `pipeline/summary_report.py` — full leaderboard + per-category table | The audited final numbers (Claude 90.0%/27/30/avg 2.67, o4-mini 56.7%/17/30/avg 1.70, Llama 43.3%/13/30/avg 1.47, 46.7-pt spread) quoted in DL5 §4 |
| DL5-2 | Terminal output of `pipeline/check_evidence.py` — mismatch counts per model + script's own conclusion | The "prompt.csv vs eval.csv are different runs" finding (29 mismatched rows: o4-mini 15, claude-sonnet-4-6 8, llama4-scout 6) quoted in DL5 §4 |
| DL5-3 | The Streamlit dashboard (Answer Browser tab, Q01) | The working visualisation tool from DL4 that this audit was protecting from silently displaying a mismatched row as trustworthy |

Source screenshots for both logs live in `image/` (`dl1_*.png`, `leaderboard_terminal.png`, `check mismatch.png`, `dashboard.png`).

## How to reproduce the headline numbers

```bash
# from the project root, with the venv active
python -m pipeline.summary_report     # → final leaderboard + per-category rates from eval.csv
python -m pipeline.check_evidence      # → prompt.csv vs eval.csv consistency audit
```

## File status at time of writing (2026-06-07)

| File | Status | Use |
|---|---|---|
| `eval.csv` | ✅ Canonical — 90/90 rows scored, 0 SKIP/ERROR | Source for all final leaderboard figures |
| `prompt.csv` | ⚠️ Stale — 29 rows show Connection-error failures from a later re-run | Kept for transparency; not used for final numbers |
| `eval_outputs.csv` | ✅ Pilot validation evidence (human vs judge agreement) | Supports DL2/DL3 judge-reliability claim |
| `data/questions.csv` | ✅ Source dataset, 30 questions | Input to the whole pipeline |
| `documents/checklist task.xlsx` | ✅ Updated — all phases through DL5 marked Done | Project-tracking evidence |
