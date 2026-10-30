from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.services.matching_benchmark import (
    DEFAULT_DEV_FRACTION,
    DEFAULT_SEED,
    evaluate_matching_benchmark,
    load_dataset,
)


def _row(kind: str, item: dict) -> dict:
    test = item.get("test") or {}
    binary = test.get("binary") or {}
    three = test.get("three_class") or {}
    thresholds = item.get("thresholds") or {}
    cross = test.get("cross_language") or {}
    cross_binary = cross.get("binary") or {}
    return {
        "kind": kind,
        "id": item.get("id"),
        "label": item.get("label") or item.get("description"),
        "available": item.get("available", True),
        "reason": item.get("reason", ""),
        "threshold_related": thresholds.get("related", ""),
        "threshold_duplicate": thresholds.get("duplicate", ""),
        "binary_precision": binary.get("precision", ""),
        "binary_recall": binary.get("recall", ""),
        "binary_f1": binary.get("f1", item.get("binary_f1", "")),
        "binary_accuracy": binary.get("accuracy", ""),
        "macro_f1": three.get("macro_f1", item.get("macro_f1", "")),
        "three_class_accuracy": three.get("accuracy", item.get("accuracy", "")),
        "cross_language_binary_f1": cross_binary.get("f1", ""),
        "development_binary_f1": thresholds.get("development_binary_f1", ""),
        "development_macro_f1": thresholds.get("development_macro_f1", ""),
    }


def write_csv(report: dict, path: Path) -> None:
    rows = [_row("method", method) for method in report["methods"]]
    rows.extend(_row("unavailable", method) for method in report["unavailable_methods"])
    rows.extend(_row("ablation", variant) for variant in report["ablation"])
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the synthetic complaint-matching benchmark.")
    parser.add_argument("--json", type=Path, help="Write the full report as JSON.")
    parser.add_argument("--csv", type=Path, help="Write method and ablation summaries as CSV.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Fixed seed for the group-aware split.")
    parser.add_argument("--dev-fraction", type=float, default=DEFAULT_DEV_FRACTION, help="Development partition fraction.")
    parser.add_argument("--dataset", type=Path, help="Optional path to a versioned benchmark dataset JSON.")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset) if args.dataset else None
    report = evaluate_matching_benchmark(dataset, seed=args.seed, development_fraction=args.dev_fraction)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        write_csv(report, args.csv)

    print(
        f"dataset={report['dataset']['dataset_id']}@{report['dataset']['version']} "
        f"dev={report['split']['development_pairs']} test={report['split']['test_pairs']} "
        f"groups_overlap={report['split']['source_group_overlap']}"
    )
    for method in report["methods"]:
        print(
            f"{method['id']}: binary_f1={method['test']['binary']['f1']:.4f} "
            f"macro_f1={method['test']['three_class']['macro_f1']:.4f} "
            f"thresholds={method['thresholds']['related']:.3f}/{method['thresholds']['duplicate']:.3f}"
        )
    for method in report["unavailable_methods"]:
        print(f"{method['id']}: UNAVAILABLE - {method['reason']}")


if __name__ == "__main__":
    main()
