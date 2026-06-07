"""
Consolidates eval.csv into the final benchmark summary used as evidence for
Decision Log 5 (Managing phase): overall leaderboard, per-category acceptance
rates, and a list of any rows excluded from scoring (SKIP/ERROR).

Run from the project root: python -m pipeline.summary_report
"""
import csv
from collections import defaultdict


def load_eval(filepath: str = "eval.csv") -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_stats(rows: list[dict]):
    stats = defaultdict(lambda: {"total": 0, "accepted": 0, "scores": []})
    cat_stats = defaultdict(lambda: defaultdict(lambda: {"total": 0, "accepted": 0}))
    excluded = []

    for r in rows:
        score, model = r["llm_score"], r["model"]
        if score not in ("0", "1", "2", "3"):
            excluded.append((r["question_id"], model, score, r.get("llm_reason", "")))
            continue

        stats[model]["total"] += 1
        stats[model]["scores"].append(int(score))
        accepted = int(score) >= 2
        if accepted:
            stats[model]["accepted"] += 1

        cat = cat_stats[model][r["category"]]
        cat["total"] += 1
        if accepted:
            cat["accepted"] += 1

    return stats, cat_stats, excluded


def print_report(stats, cat_stats, excluded):
    print("=" * 60)
    print("FINAL BENCHMARK SUMMARY — evidence for Decision Log 5")
    print("=" * 60)

    print("\nExcluded rows (SKIP / ERROR — not counted in acceptance rate):")
    if not excluded:
        print("  none")
    for q, m, s, reason in excluded:
        print(f"  {q} / {m}: llm_score={s}  ({reason})")

    print("\nOverall leaderboard (acceptance = score >= 2):")
    ranked = sorted(stats.items(), key=lambda kv: -(kv[1]["accepted"] / kv[1]["total"]))
    for model, d in ranked:
        rate = d["accepted"] / d["total"] * 100
        avg = sum(d["scores"]) / len(d["scores"])
        print(f"  {model:20s} {rate:5.1f}%  ({d['accepted']}/{d['total']})   avg score {avg:.2f}")

    if len(ranked) >= 2:
        top_rate = ranked[0][1]["accepted"] / ranked[0][1]["total"] * 100
        bottom_rate = ranked[-1][1]["accepted"] / ranked[-1][1]["total"] * 100
        print(f"\n  Spread: {top_rate - bottom_rate:.1f} percentage points "
              f"between {ranked[0][0]} and {ranked[-1][0]}")

    print("\nPer-category acceptance rate by model:")
    categories = sorted({c for m in cat_stats.values() for c in m})
    header = f"  {'model':20s}" + "".join(f"{c:>15s}" for c in categories)
    print(header)
    for model, cats in cat_stats.items():
        line = f"  {model:20s}"
        for c in categories:
            d = cats.get(c)
            if d and d["total"]:
                line += f"{d['accepted']/d['total']*100:>13.1f}% "
            else:
                line += f"{'—':>15s}"
        print(line)

    print("=" * 60)


if __name__ == "__main__":
    rows = load_eval("eval.csv")
    stats, cat_stats, excluded = build_stats(rows)
    print_report(stats, cat_stats, excluded)
