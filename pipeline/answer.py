import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pipeline.main import ask, load_questions

# Reconfigure stdout to UTF-8 so Unicode in model answers prints correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("prompt/answer.txt", encoding="utf-8") as f:
    PROMPT = f.read().strip()
    
MODELS = [
    {
        "label": "o4-mini",
        "provider": "openai",
        "model_id": "o4-mini",
        "token_params": {"max_completion_tokens": 1500},  # covers reasoning + visible output; o-series don't accept temperature
    },
    {
        "label": "claude-sonnet-4-6",
        "provider": "claude",
        "model_id": "claude-sonnet-4-6",
        "token_params": {"max_tokens": 1500},
        "temperature": 0.2,  # low = deterministic technical answers
    },
    {
        "label": "llama4-scout",
        "provider": "groq",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "temperature": 0.2,
    },
]


def _ask_one(model: dict, question_text: str) -> tuple[str, str, str]:
    """Worker function for threading — returns (label, answer, status)."""
    try:
        answer = ask(model, question_text, system_prompt=PROMPT)
        if not answer or answer.strip() == "":
            return model["label"], "ERROR: empty response returned", "EMPTY"
        return model["label"], answer, f"{len(answer)} chars"
    except Exception as e:
        return model["label"], f"ERROR: {e}", "ERROR"


def run(questions: list[dict], filepath: str = "prompt.csv") -> list[dict]:
    """
    For each question, asks all models IN PARALLEL using ThreadPoolExecutor.
    Saves to CSV after every question so progress is never lost mid-run.
    All 3 models run simultaneously — total time per question = slowest model, not sum of all.
    """
    all_rows = []
    for q in questions:
        print(f"\nQuestion {q['id']} [{q['category']}]")

        # Submit all 3 models at once, collect as they finish
        with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
            futures = {
                executor.submit(_ask_one, model, q["question_text"]): model
                for model in MODELS
            }
            q_rows = []
            for future in as_completed(futures):
                label, answer, status = future.result()
                print(f"  [{label}] {status}")
                q_rows.append({
                    "question_id":     q["id"],
                    "category":        q["category"],
                    "difficulty":      q.get("difficulty", ""),
                    "question_text":   q["question_text"],
                    "accepted_answer": q["accepted_answer"],
                    "model":           label,
                    "model_answer":    answer,
                })

        all_rows.extend(q_rows)
        # Save after every question — file stays readable mid-run
        save_csv(all_rows, filepath, silent=True)
        print(f"  → saved {len(all_rows)} rows so far")

    return all_rows


def save_csv(rows: list[dict], filepath: str = "prompt.csv", silent: bool = False) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    if not silent:
        print(f"\nSaved {len(rows)} rows to {filepath}")


if __name__ == "__main__":
    filepath = "prompt.csv"
    questions = load_questions("data/questions.csv")
    print(f"Loaded {len(questions)} questions | Prompt: {len(PROMPT)} chars\n")
    rows = run(questions, filepath)
    save_csv(rows, filepath)

