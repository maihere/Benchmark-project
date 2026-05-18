# LLM Coding Benchmark

A pipeline for evaluating how well large language models answer real Python programming questions sourced from Stack Overflow. Models are scored by a separate judge LLM using a structured rubric, and results are visualised in an interactive Streamlit dashboard.

---

## Overview

This project benchmarks LLM coding ability across three question types — debugging, conceptual, and implementation — using 30 Python questions collected from Stack Overflow. Each question includes an accepted Stack Overflow answer used as a reference point. Each model answer is independently scored 0–3 by a judge model. Results can be compared by model, category, and difficulty.

The benchmark is designed to reveal performance differences that academic benchmarks like MMLU or HumanEval do not show — specifically, how models differ on real developer tasks across different question types.

---

## Pipeline Architecture

The diagram below shows how data flows through the system and which components interact. Each component has a single responsibility. All prompts are kept in external files so the rubric or answer format can be changed without modifying code.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                              │
│                                                                          │
│  data/questions.csv        prompt/answer.txt      prompt/judge.txt       │
│  30 Python questions   +   Answer system      +   Scoring rubric 0-3     │
│  + accepted answers        prompt (external)       (external file)       │
└──────────────┬───────────────────────┬────────────────────┬─────────────┘
               │                       │                    │
               ▼                       │                    │
┌──────────────────────────┐           │                    │
│   pipeline/answer.py     │◄──────────┘                    │
│                          │                                │
│  Loads questions.csv     │                                │
│  Sends each question to  │                                │
│  all 3 models at once    │                                │
└─────┬──────────┬─────────┘                                │
      │          │          │                               │
      ▼          ▼          ▼                               │
┌──────────┐ ┌─────────┐ ┌──────────┐                       │
│ o4-mini  │ │ Claude  │ │ Llama 4  │                       │
│ OpenAI   │ │ Sonnet  │ │ Scout    │                       │
│ reasoning│ │ temp    │ │ Groq MoE │                       │
│ model    │ │ =0.2    │ │ temp=0.2 │                       │
└────┬─────┘ └────┬────┘ └────┬─────┘                       │ 
     └────────────┴───────────┘                             │
                  │                                         │
                  ▼                                         │
       ┌─────────────────────┐                              │
       │     prompt.csv      │                              │
       │  90 rows:           │                              │
       │  30 questions       │                              │
       │  x 3 model answers  │                              │
       └──────────┬──────────┘                              │
                  │                                         │
                  ▼                                         │
      ┌───────────────────────┐                             │
      │  pipeline/evaluate.py │◄────────────────────────────┘
      │                       │
      │  Sends each answer    │◄──── GPT-4o (judge)
      │  to judge with:       │      separate from tested
      │  - question           │      models, temp=0.0
      │  - accepted answer    │      (deterministic scoring)
      │  - model answer       │
      │  Skips empty answers  │
      └──────────┬────────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │      eval.csv       │
      │  90 rows:           │
      │  llm_score (0-3)    │
      │  + judge reasoning  │
      └──────────┬──────────┘
                 │
                 ▼
      ┌──────────────────────────┐
      │  pipeline/dashboard.py   │
      │  Streamlit:              │
      │  - Leaderboard tab       │
      │    acceptance rate,      │
      │    avg score, breakdown  │
      │  - Answer Browser tab    │
      │    inspect any answer    │
      │    + judge reasoning     │
      └──────────────────────────┘
```

---

## Design Decisions

### Why these three models?

The three models were chosen to represent three distinct deployment profiles — not picked arbitrarily:

| Model | Profile | Real question it answers |
|---|---|---|
| `o4-mini` | Commercial frontier, reasoning-optimised | Is the standard OpenAI choice worth using for real coding tasks? |
| `claude-sonnet-4-6` | Commercial alternative, different architecture | Does training approach produce different task specialisations? |
| `llama4-scout` | Open-weight, free tier via Groq | Can an organisation avoid API costs with an open-weight model? |

The 47-point acceptance rate gap between Claude (90%) and Llama (43%) directly answers the open-weight question. MMLU scores for these models would not surface this difference.

**Why GPT-4o as judge and not one of the tested models?**
Two reasons from the StackEval research (Genc et al., 2024): the judge must be more capable than the models it evaluates, and using a tested model as its own judge introduces self-scoring bias. GPT-4o is entirely separate from the three evaluation subjects.

---

### Why this answer prompt structure?

```
1. DIAGNOSIS:    Identify the core problem (1-2 sentences)
2. SOLUTION:     Provide the fix with working code where relevant
3. EXPLANATION:  Explain why this solution works
```

Each part maps to a rubric dimension:

- **DIAGNOSIS** → relevance — does the model understand the actual problem?
- **SOLUTION** → accuracy — is the code or fix correct?
- **EXPLANATION** → completeness — does the answer help the developer understand, not just copy-paste?

Without this structure a model can produce syntactically correct code with no explanation and score well on automated metrics while being less useful to a real developer. The pilot test confirmed this: unexplained-but-correct answers were scored 1 by the judge (Useful but Unacceptable). After reviewing the reasoning, this was agreed to be the right standard for a coding *assistant*.

---

### Why prompts live in external `.txt` files

`prompt/answer.txt` and `prompt/judge.txt` are kept separate from the Python code:

- **Rapid iteration** — change the judge rubric by editing one file, then re-run `evaluate.py`. No code changes needed.
- **Separation of concerns** — prompt engineering and pipeline engineering are different activities.
- **Reproducibility** — exact prompts used in any run are captured in the repository.

This paid off when the Q21 bug required a code fix in `evaluate.py`. The rubric file was completely untouched — only the code handling empty responses changed.

---

### Why temperature 0.0 for the judge and 0.2 for answer models?

| Component | Temperature | Reason |
|---|---|---|
| GPT-4o judge | `0.0` | Deterministic — same input always produces the same score. Required for a reproducible benchmark. |
| Claude Sonnet | `0.2` | Precise for technical answers; slight variation avoids identical outputs across runs. |
| Llama 4 Scout | `0.2` | Same reasoning as Claude. |
| o4-mini | Not set | o-series models do not accept a temperature parameter — setting it causes an API error. |

---

### Why `max_completion_tokens` for o4-mini?

OpenAI o-series models generate internal reasoning tokens before producing the visible answer. The API separates these into two token pools. Using `max_tokens` with an o-series model causes an empty response. The pipeline detects the model type and passes the correct parameter:

```python
# o4-mini — requires this, not max_tokens
"token_params": {"max_completion_tokens": 1500}
```

This was the root cause of the Q21 pipeline bug — documented below.

---

### Why CSV output format?

- Human-inspectable without additional tooling — any spreadsheet application opens it
- Partial results preserved — the pipeline saves after every question, so a mid-run failure loses no completed work
- Dashboard reads CSV directly — no data transformation step
- Can be uploaded directly as portfolio evidence artefacts

---

## Dataset

| Property | Value |
|---|---|
| Questions | 30 |
| Language | Python only |
| Source | Stack Overflow (accepted answers used as reference, not ground truth) |
| Categories | Debugging, Conceptual, Implementation |
| Per category | 10 questions |
| Difficulty | Beginner, Intermediate |
| Date range | Mix of established + 2024–2025 questions to reduce data leakage risk |

**Why Python only?** Highest Stack Overflow question volume, dominant in GenAI engineering, and single-language design removes noise — differences reflect model capability, not language familiarity.

**Why accepted answers as reference, not ground truth?** Many coding problems have multiple valid solutions. The judge assesses whether the model's answer is useful to a developer — not whether it matches the accepted answer word-for-word.

---

## Models Tested

| Model | Provider | Notes |
|---|---|---|
| `o4-mini` | OpenAI | Reasoning model — uses `max_completion_tokens`, no temperature |
| `claude-sonnet-4-6` | Anthropic | Temperature 0.2 |
| `llama4-scout` | Groq | Llama 4 Scout 17B MoE architecture, temperature 0.2 |

**Judge model:** `gpt-4o` (OpenAI) — temperature 0.0, chain-of-thought, accepted answer provided as reference

---

## Scoring Rubric

| Score | Label | Meaning |
|---|---|---|
| 0 | Completely Unacceptable | Incorrect, irrelevant, or severely misleading |
| 1 | Useful but Unacceptable | Partially correct but missing critical details |
| 2 | Acceptable | Correct and complete enough to solve the problem |
| 3 | Optimal | Accurate, detailed, and thorough |

**Acceptance threshold:** score ≥ 2 — the developer can proceed without additional searching.

Rubric adapted from Genc et al. (2024) StackEval paper.

---

## Project Structure

```
├── pipeline/
│   ├── config.py        # API clients — OpenAI, Anthropic, Groq
│   ├── main.py          # Shared ask() and load_questions() — imported by other scripts
│   ├── answer.py        # Step 1: send questions to all models in parallel, save answers
│   ├── evaluate.py      # Step 2: judge scores each answer, skip empty/error responses
│   └── dashboard.py     # Step 3: Streamlit — Leaderboard + Answer Browser tabs
│
├── prompt/
│   ├── answer.txt       # System prompt for answer models (external for rapid iteration)
│   └── judge.txt        # Scoring rubric for judge model (external for rapid iteration)
│
├── data/
│   └── questions.csv    # 30 Python questions with Stack Overflow accepted answers
│
├── .env                 # API keys (not tracked)
├── .gitignore
└── README.md
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/maihere/Benchmark-project.git
cd Benchmark-project
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install openai anthropic streamlit pandas python-dotenv
```

**3. Create a `.env` file with your API keys**
```
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
```

---

## Running the Pipeline

**Step 1 — Collect model answers**
```bash
python -m pipeline.answer
```
Outputs: `prompt.csv`

**Step 2 — Judge and score answers**
```bash
python -m pipeline.evaluate
```
Outputs: `eval.csv`

**Step 3 — View results in dashboard**
```bash
streamlit run pipeline/dashboard.py
```
Opens at `http://localhost:8501`

---

## Re-running After Changes

| What changed | What to re-run |
|---|---|
| Answer prompt (`prompt/answer.txt`) | answer → evaluate → dashboard |
| Judge rubric (`prompt/judge.txt`) | evaluate only → dashboard |
| Questions dataset | answer → evaluate → dashboard |
| Dashboard code only | dashboard only |

The dashboard auto-refreshes when CSV files change on disk.

---

## Output Files

| File | Description |
|---|---|
| `prompt.csv` | One row per question × model — full model answer |
| `eval.csv` | One row per question × model — LLM score (0–3) and judge reasoning |

Both excluded from git since they are generated outputs.

---

## Known Issues and Fixes

### Q21 — empty response scored as optimal by judge

**What happened:** `o4-mini` returned an empty response on Q21. The judge then scored this empty response as 3 (Optimal).

**Root cause — empty response:** Incorrect token parameter for o-series model on this specific call caused the API to return an empty completion.

**Root cause — judge bias:** The judge received an empty `model_answer` field and was not validated against this edge case. This is the "Unaligned LLM Judges" failure mode — the judge should return score 0 or refuse to score when no answer is present.

**Fixes applied:**
- `answer.py` — empty response guard: if a model returns empty, saves `ERROR: empty response returned` instead of blank.
- `evaluate.py` — skip check: rows where `model_answer` is empty, nan, or starts with `ERROR:` are marked `SKIP` and not sent to the judge.

**Impact:** Q21 o4-mini score excluded. Corrected o4-mini acceptance rate: **80%** (25/29 valid responses).

---

## Key Findings

| Model | Acceptance rate | Conceptual | Implementation | Debugging |
|---|---|---|---|---|
| `claude-sonnet-4-6` | **90%** | 100% | 77.8% | 92.3% |
| `o4-mini` | **80%** | — | 88.9% | — |
| `llama4-scout` | **43%** | — | — | — |

The 47-point gap between Claude and Llama is invisible in MMLU or HumanEval scores. Claude leads on conceptual explanation (100%); o4-mini leads on implementation. These task-level differences are the type of actionable finding that justifies domain-specific benchmarking over generic academic scores.

---

## Notes

- `pipeline/main.py` is not run directly — shared library imported by `answer.py` and `evaluate.py`
- `extrasaction='raise'` on DictWriter crashes immediately on unexpected column keys — prevents silent data corruption
- `human_score` column in `eval.csv` is intentionally blank — fill manually to validate judge reliability

---

## References

- Genc, Z., et al. (2024). *StackEval: Benchmarking LLMs in Coding Assistance.* arXiv:2412.05288
- ProLLM.ai — live leaderboard for real-world coding benchmarks
