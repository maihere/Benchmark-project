import csv
import re
import sys
import time
from pipeline.main import ask, load_questions

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("prompt/judge.txt", encoding="utf-8") as f:
    JUDGE_PROMPT = f.read().strip()

JUDGE_MODEL = {
    "label": "gpt-4o",
    "provider": "openai",
    "model_id": "gpt-4o",
}

def extract_score_and_reason(raw: str) -> tuple[str, str]:
    """
    Parses the judge's response for a Score line and a Reason line.
    Expected format:
        Score: 2
        Reason: The answer is correct but missing error handling.
    Returns ('?', raw) if the format isn't found so the row is still saved.
    """
    score_match = re.search(r'Score:\s*([0-3])', raw)
    reason_match = re.search(r'Reason:\s*(.+)', raw)
    score = score_match.group(1) if score_match else "?"
    reason = reason_match.group(1).strip() if reason_match else raw.strip()
    return score, reason


def build_user_message(question: str, reference: str, model_answer: str) -> str:
    """
    Formats the three pieces the judge needs to evaluate one answer.
    Asks for Score on one line and Reason on the next so they're easy to parse.
    """
    return (
        f"Question:\n{question}\n\n"
        f"Reference Answer:\n{reference}\n\n"
        f"Model Answer:\n{model_answer}\n\n"
        "Reply in exactly this format:\n"
        "Score: [0, 1, 2, or 3]\n"
        "Reason: [one sentence explaining why]"
    )


def load_answers(filepath: str = "prompt_outputs.csv") -> list[dict]:
    """Reads the answer CSV produced by answer.py.""" 
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_evaluation(answers: list[dict]) -> list[dict]:
    """
    For each row in prompt_outputs.csv, sends the question + reference + model answer
    to the judge and records its score.
 
    The human_score column is intentionally left blank.
    After this script runs, open eval_outputs.csv and fill in human_score manually
    for a subset of rows (5-10 is enough) to validate the judge against your own judgment.
    """
    rows = []
    total = len(answers)
    for i, row in enumerate(answers):
        model_label = row["model"]
        q_id = row["question_id"]
        print(f"\n[{i+1}/{total}] {q_id} / {model_label}")

        # Skip empty or failed answers — sending "ERROR: ..." to the judge causes bias
        # because the judge may still score error text as partially useful
        answer_text = str(row["model_answer"]).strip()
        if not answer_text or answer_text in ("nan",) or answer_text.startswith("ERROR:"):
            reason = "failed answer" if answer_text.startswith("ERROR:") else "empty answer"
            print(f"  skipped — {reason}: {answer_text[:60]}")
            rows.append({
                "question_id": q_id,
                "category":    row["category"],
                "difficulty":  row.get("difficulty", ""),
                "model":       model_label,
                "llm_score":   "SKIP",
                "llm_reason":  "skipped — empty model answer",
            })
            continue

        try:
            user_msg = build_user_message(
                row["question_text"],
                row["accepted_answer"],
                row["model_answer"],
            )
            raw = ask(JUDGE_MODEL, user_msg, system_prompt=JUDGE_PROMPT)
            llm_score, llm_reason = extract_score_and_reason(raw)
        except Exception as e:
            llm_score, llm_reason = "ERROR", str(e)
        print(f"  Model answer: {row['model_answer']}")
        print(f"  Score:  {llm_score}")
        print(f"  Reason: {llm_reason}")
        rows.append({
            "question_id":  q_id,
            "category":     row["category"],
            "difficulty":   row.get("difficulty", ""),
            "model":        model_label,
            "llm_score":    llm_score,
            "llm_reason":   llm_reason
        })
        time.sleep(0.3)
    return rows


def save_csv(rows: list[dict], filepath: str = "eval.csv") -> None:
    """Writes evaluation results to CSV. human_score column stays blank for manual entry."""
    if not rows:
        print("No rows to save.")
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} rows to {filepath}")

def print_summary(rows: list[dict]) -> None:
    """Prints acceptance rate and average score per model after evaluation."""
    from collections import defaultdict

    stats = defaultdict(lambda: {"total": 0, "accepted": 0, "scores": []})
    for r in rows:
        s = r["llm_score"]
        if s not in ("0", "1", "2", "3"):
            continue
        m = r["model"]
        stats[m]["total"] += 1
        stats[m]["scores"].append(int(s))
        if int(s) >= 2:
            stats[m]["accepted"] += 1

    print("\n" + "=" * 50)
    print("BENCHMARK SUMMARY")
    print("=" * 50)
    for model, d in stats.items():
        if d["total"] == 0:
            continue
        rate = d["accepted"] / d["total"] * 100
        avg  = sum(d["scores"]) / len(d["scores"])
        print(f"{model}")
        print(f"  Acceptance rate : {rate:.1f}%  ({d['accepted']}/{d['total']})")
        print(f"  Average score   : {avg:.2f}")
    print("=" * 50)


if __name__ == "__main__":
    answers = load_answers("prompt.csv")
    print(f"Loaded {len(answers)} answers to evaluate\n")
    rows = run_evaluation(answers)
    save_csv(rows)
    print_summary(rows)

