from typing import Any

import numpy as np


def select_winner(results: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    eligible = [item for item in results if item.get("execution_succeeded", item.get("status") != "failed") and item.get("best_score") is not None and np.isfinite(item["best_score"])]
    if not eligible:
        return {"winner": None, "ranking": [], "explanation": "No completed or early-stopped run produced a finite objective value."}
    if metric == "best_score":
        ordered = sorted(eligible, key=lambda item: (item["best_score"], item["runtime_ms"]))
        reason = "Lowest measured objective value among eligible runs with a finite measured result"
        values = {item["algorithm"]: item["best_score"] for item in eligible}
    elif metric == "runtime":
        ordered = sorted(eligible, key=lambda item: (item["runtime_ms"], item["best_score"]))
        reason = "Lowest measured runtime among eligible runs; this ranking prioritises speed over solution quality"
        values = {item["algorithm"]: item["runtime_ms"] for item in eligible}
    else:
        scores = np.asarray([item["best_score"] for item in eligible], dtype=float)
        runtimes = np.asarray([item["runtime_ms"] for item in eligible], dtype=float)
        score_span = max(float(np.ptp(scores)), 1e-12)
        runtime_span = max(float(np.ptp(runtimes)), 1e-12)
        reliability = {item["algorithm"]: float(item.get("success_rate")) if item.get("success_rate") is not None else 1.0 for item in eligible}
        values = {item["algorithm"]: 0.6 * ((item["best_score"] - float(scores.min())) / score_span) + 0.3 * ((item["runtime_ms"] - float(runtimes.min())) / runtime_span) + 0.1 * (1 - reliability[item["algorithm"]]) for item in eligible}
        ordered = sorted(eligible, key=lambda item: (values[item["algorithm"]], item["best_score"]))
        reason = "Lowest deterministic balanced score: 60% normalised objective quality, 30% normalised runtime and 10% unreliability penalty"
    ranking = [{"rank": index + 1, "algorithm": item["algorithm"], "metric_value": float(values[item["algorithm"]]), "best_score": item["best_score"], "runtime_ms": item["runtime_ms"], "target_attained": bool(item.get("target_attained", False)), "stagnation_observed": bool(item.get("stagnation_observed", False))} for index, item in enumerate(ordered)]
    winner = ordered[0]
    return {"winner": {"algorithm": winner["algorithm"], "best_score": winner["best_score"], "reason": reason}, "ranking": ranking, "explanation": reason}


def fastest_algorithm(results: list[dict[str, Any]]) -> str | None:
    eligible = [item for item in results if item.get("execution_succeeded", item.get("status") != "failed") and item.get("best_score") is not None and np.isfinite(item["best_score"])]
    return min(eligible, key=lambda item: item["runtime_ms"])["algorithm"] if eligible else None
