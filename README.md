# LLM Coding Benchmark

A pipeline for evaluating how well large language models answer real Python programming questions sourced from Stack Overflow. Models are scored by a judge LLM using a structured rubric, and results are visualised in an interactive dashboard.

---

## Overview

This project benchmarks LLM coding ability across three question types — debugging, conceptual, and implementation — using 30 Python questions collected from Stack Overflow accepted answers as reference. Each model answer is independently scored 0–3 by a judge model. Results can be compared by model, category, and difficulty.

---

## Dataset

| Property | Value |
|---|---|
| Questions | 30 |
| Language | Python |
| Source | Stack Overflow (accepted answers) |
| Categories | Debugging, Conceptual, Implementation |
| Difficulty | Beginner, Intermediate |

---

## Models Tested

| Model | Provider | Notes |
|---|---|---|
| `o4-mini` | OpenAI | Reasoning model — uses `max_completion_tokens` |
| `claude-sonnet-4-6` | Anthropic | Temperature 0.2 |
| `llama4-scout` | Groq | Llama 4 Scout 17B, temperature 0.2 |

**Judge model:** `gpt-4o` (OpenAI)

---

## Scoring Rubric

Scores are assigned by the judge model on a 0–3 scale:

| Score | Label | Meaning |
|---|---|---|
| 0 | Completely Unacceptable | Incorrect, irrelevant, or severely misleading |
| 1 | Useful but Unacceptable | Partially correct but missing critical details |
| 2 | Acceptable | Correct and complete enough to solve the problem |
| 3 | Optimal | Accurate, detailed, and thorough |

**Acceptance threshold:** score ≥ 2

---

## Pipeline Flow

```
data/questions.csv
       │
       ▼
 pipeline/answer.py  ──── prompt/answer.txt (system prompt)
       │
       ▼  asks 3 models in parallel
  prompt.csv  (question × model answers)
       │
       ▼
pipeline/evaluate.py ──── prompt/judge.txt (judge rubric)
       │
       ▼  judge scores each answer
   eval.csv  (scores + reasoning per answer)
       │
       ▼
pipeline/dashboard.py
       │
       ▼  streamlit web dashboard
  localhost:8501
```

---

## Project Structure

```
├── pipeline/
│   ├── config.py        # API clients (OpenAI, Anthropic, Groq)
│   ├── main.py          # Shared ask() and load_questions() — imported by other scripts
│   ├── answer.py        # Step 1: send questions to models, save answers
│   ├── evaluate.py      # Step 2: judge scores each answer
│   └── dashboard.py     # Step 3: Streamlit visualisation
│
├── prompt/
│   ├── answer.txt       # System prompt given to answer models
│   └── judge.txt        # Scoring rubric given to judge model
│
├── data/
│   └── questions.csv    # 30 Python questions with accepted answers
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

Run all commands from the project root folder.

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
Opens browser at `http://localhost:8501`

---

## Output Files

| File | Description |
|---|---|
| `prompt.csv` | One row per question × model — contains the full model answer |
| `eval.csv` | One row per question × model — contains LLM score (0–3) and judge reasoning |

Both files are excluded from git (`.gitignore`) since they are generated outputs.

---

## Re-running After Changes

| What changed | What to rerun |
|---|---|
| Answer prompt (`prompt/answer.txt`) | answer → evaluate → dashboard |
| Judge rubric (`prompt/judge.txt`) | evaluate only → dashboard |
| Questions dataset | answer → evaluate → dashboard |
| Dashboard code only | dashboard only |

The dashboard auto-refreshes when CSV files change on disk — leave it running while re-running the pipeline.

---

## Notes

- `pipeline/main.py` is not run directly — it is a shared library imported by `answer.py` and `evaluate.py`
- Answers that return empty or error responses are automatically skipped by the judge (`llm_score = SKIP`) to prevent evaluation bias
- The `human_score` column in `eval.csv` is intentionally blank — fill it in manually to validate judge reliability against your own judgment
