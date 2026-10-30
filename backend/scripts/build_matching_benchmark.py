#!/usr/bin/env python3
"""Build the versioned synthetic complaint-matching benchmark.

This script deliberately generates every pair from a labelled construction rule.
The resulting labels are synthetic by design, not human annotations, and no
inter-annotator agreement is claimed. The generated JSON is committed so that
benchmark runs are reproducible even if the narrative templates evolve later.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from seed.narratives.engine import NarrativeEngine  # noqa: E402
from seed.narratives.taxonomy import CATEGORY_SUBTYPES  # noqa: E402

DATASET_VERSION = "1.0.0"
DATASET_ID = "aicte-complaint-matching"
GENERATION_SEED = 20261029
GROUP_COUNT = 60
LABELS = ("DUPLICATE", "RELATED", "UNRELATED")
LANGUAGES = ("en", "hi", "ta", "te", "bn", "mr")

INSTITUTIONS = [
    ("SYN-INST-01", "Kaveri College of Engineering", "Pune"),
    ("SYN-INST-02", "Deccan Institute of Technology and Management", "Hyderabad"),
    ("SYN-INST-03", "Yamuna Institute of Engineering", "Kanpur"),
    ("SYN-INST-04", "Hooghly College of Technology", "Kolkata"),
    ("SYN-INST-05", "Cauvery Institute of Science and Technology", "Chennai"),
    ("SYN-INST-06", "Narmada College of Engineering", "Bhopal"),
    ("SYN-INST-07", "Brahmaputra Institute of Technology", "Guwahati"),
    ("SYN-INST-08", "Aravalli College of Engineering", "Jaipur"),
    ("SYN-INST-09", "Krishna Institute of Management and Technology", "Bengaluru"),
    ("SYN-INST-10", "Sutlej College of Engineering", "Chandigarh"),
    ("SYN-INST-11", "Tapti Institute of Technology", "Surat"),
    ("SYN-INST-12", "Godavari College of Engineering", "Nagpur"),
    ("SYN-INST-13", "Mahanadi Institute of Engineering", "Bhubaneswar"),
    ("SYN-INST-14", "Alaknanda College of Technology", "Dehradun"),
    ("SYN-INST-15", "Pampa Institute of Science and Technology", "Kochi"),
    ("SYN-INST-16", "Saryu College of Engineering", "Lucknow"),
    ("SYN-INST-17", "Chambal Institute of Technology", "Indore"),
    ("SYN-INST-18", "Beas College of Engineering", "Amritsar"),
    ("SYN-INST-19", "Kosi Institute of Technology", "Patna"),
    ("SYN-INST-20", "Wainganga College of Engineering", "Nashik"),
]

CATEGORIES = tuple(CATEGORY_SUBTYPES.keys())


def _institution(index: int) -> tuple[str, str, str]:
    return INSTITUTIONS[index % len(INSTITUTIONS)]


def _fake_institution(index: int) -> SimpleNamespace:
    _, name, city = _institution(index)
    return SimpleNamespace(name=name, city=city)


def _text(generated, language: str) -> str:
    if language == "en":
        return generated.narrative.strip()
    return (generated.narrative_original or generated.narrative).strip()


def _case(key: str, generated, language: str, category: str, subtype: str, inst_index: int) -> dict:
    inst_id, name, city = _institution(inst_index)
    return {
        "case_key": key,
        "text": _text(generated, language),
        "language": language,
        "category": category,
        "category_subtype": subtype,
        "institution_id": inst_id,
        "institution": name,
        "city": city,
        "source_type": "SYNTHETIC_BENCHMARK",
        "synthetic": True,
    }


def _annotation(label: str) -> dict:
    return {
        "annotator_labels": [
            {
                "annotator_id": "synthetic-construction-v1",
                "label": label,
                "human": False,
            }
        ],
        "adjudicated_label": label,
        "adjudication": {
            "method": "construction_rule",
            "human": False,
            "note": "Label assigned by the dataset generator from the pair construction; it is not a human judgement.",
        },
    }


def _pair(pair_id: str, group_index: int, label: str, case_a: dict, case_b: dict, note: str) -> dict:
    same_language = case_a["language"] == case_b["language"]
    language_group = case_a["language"] if same_language else "-".join(sorted({case_a["language"], case_b["language"]}))
    return {
        "pair_id": pair_id,
        "source_group_id": f"MB-GROUP-{group_index:03d}",
        "case_a": case_a,
        "case_b": case_b,
        "language_group": language_group,
        "cross_language": not same_language,
        "source_type": "SYNTHETIC_BENCHMARK",
        "synthetic": True,
        "notes": note,
        **_annotation(label),
    }


def build_dataset(seed: int = GENERATION_SEED) -> dict:
    rng = random.Random(seed)
    engine = NarrativeEngine(seed)
    pairs: list[dict] = []

    for group_index in range(GROUP_COUNT):
        primary_lang = LANGUAGES[group_index % len(LANGUAGES)]
        cross_lang = "hi" if primary_lang == "en" else "en"
        base_inst_index = group_index % len(INSTITUTIONS)
        related_inst_index = (base_inst_index + 7) % len(INSTITUTIONS)
        unrelated_inst_index = (base_inst_index + 13) % len(INSTITUTIONS)
        base_inst = _fake_institution(base_inst_index)
        related_inst = _fake_institution(related_inst_index)
        unrelated_inst = _fake_institution(unrelated_inst_index)

        base_category = CATEGORIES[group_index % len(CATEGORIES)]
        base_subtype = rng.choice(list(CATEGORY_SUBTYPES[base_category].keys()))
        other_subtypes = [s for s in CATEGORY_SUBTYPES[base_category] if s != base_subtype]
        related_subtype = rng.choice(other_subtypes)

        unrelated_category = CATEGORIES[(group_index + 3) % len(CATEGORIES)]
        if unrelated_category == base_category:
            unrelated_category = CATEGORIES[(group_index + 4) % len(CATEGORIES)]
        unrelated_subtype = rng.choice(list(CATEGORY_SUBTYPES[unrelated_category].keys()))

        base_key = f"SYN-{group_index:03d}-A"
        base = engine.build(
            case_id=base_key,
            institution=base_inst,
            category=base_category,
            subtype=base_subtype,
            persona="STUDENT",
            channel="CSS",
            bucket="LONG",
            force_language=primary_lang,
        )
        shared = {
            key: value
            for key, value in base.metadata["values"].items()
            if key not in {"sname", "sname_designation", "channel_label", "ref", "case_id"}
        }

        same_duplicate = engine.build(
            case_id=f"SYN-{group_index:03d}-D1",
            institution=base_inst,
            category=base_category,
            subtype=base_subtype,
            persona="PARENT",
            channel="CPGRAMS",
            bucket="MEDIUM",
            shared_values=shared,
            force_language=primary_lang,
        )
        cross_duplicate = engine.build(
            case_id=f"SYN-{group_index:03d}-D2",
            institution=base_inst,
            category=base_category,
            subtype=base_subtype,
            persona="ANONYMOUS_WELLWISHER",
            channel="EMAIL",
            bucket="SHORT",
            shared_values=shared,
            force_language=cross_lang,
        )
        related = engine.build(
            case_id=f"SYN-{group_index:03d}-R1",
            institution=related_inst,
            category=base_category,
            subtype=related_subtype,
            persona="FACULTY",
            channel="PHYSICAL",
            bucket="MEDIUM",
            force_language=primary_lang,
        )
        unrelated = engine.build(
            case_id=f"SYN-{group_index:03d}-U1",
            institution=unrelated_inst,
            category=unrelated_category,
            subtype=unrelated_subtype,
            persona="STUDENT",
            channel="CSS",
            bucket="MEDIUM",
            force_language=primary_lang,
        )

        case_a = _case(base_key, base, primary_lang, base_category, base_subtype, base_inst_index)
        case_d1 = _case(
            f"SYN-{group_index:03d}-D1", same_duplicate, primary_lang, base_category, base_subtype, base_inst_index
        )
        case_d2 = _case(
            f"SYN-{group_index:03d}-D2", cross_duplicate, cross_lang, base_category, base_subtype, base_inst_index
        )
        case_r1 = _case(
            f"SYN-{group_index:03d}-R1", related, primary_lang, base_category, related_subtype, related_inst_index
        )
        case_u1 = _case(
            f"SYN-{group_index:03d}-U1", unrelated, primary_lang, unrelated_category, unrelated_subtype, unrelated_inst_index
        )

        pairs.append(
            _pair(
                f"MB-{group_index:03d}-D1",
                group_index,
                "DUPLICATE",
                case_a,
                case_d1,
                "Same underlying complaint facts and institution, different persona and channel.",
            )
        )
        pairs.append(
            _pair(
                f"MB-{group_index:03d}-D2",
                group_index,
                "DUPLICATE",
                case_a,
                case_d2,
                "Same underlying complaint facts and institution, expressed in a different language.",
            )
        )
        pairs.append(
            _pair(
                f"MB-{group_index:03d}-R1",
                group_index,
                "RELATED",
                case_a,
                case_r1,
                "Same broad category but a different sub-issue and institution.",
            )
        )
        pairs.append(
            _pair(
                f"MB-{group_index:03d}-U1",
                group_index,
                "UNRELATED",
                case_a,
                case_u1,
                "Different category, sub-issue and institution.",
            )
        )

    label_counts = {label: sum(1 for pair in pairs if pair["adjudicated_label"] == label) for label in LABELS}
    language_counts: dict[str, int] = {}
    for pair in pairs:
        language_counts[pair["language_group"]] = language_counts.get(pair["language_group"], 0) + 1

    return {
        "dataset_id": DATASET_ID,
        "version": DATASET_VERSION,
        "created_at": "2026-10-29",
        "description": "Synthetic complaint-to-complaint matching benchmark for AICTE grievance narratives.",
        "provenance": {
            "kind": "SYNTHETIC",
            "human_annotation": False,
            "human_agreement": False,
            "generator": "backend/scripts/build_matching_benchmark.py",
            "generation_seed": seed,
            "note": (
                "Every pair and label is synthetic by construction. No human annotators, "
                "adjudicators or inter-annotator agreement were involved. Treat all metrics "
                "as an offline engineering benchmark, not an official evaluation."
            ),
        },
        "label_definitions": {
            "DUPLICATE": "The two complaints describe the same underlying grievance and institution.",
            "RELATED": "The complaints share a broad issue category but describe different sub-issues or facts.",
            "UNRELATED": "The complaints concern different issue categories and institutions.",
        },
        "split_policy": {
            "method": "group_by_source_group_id",
            "seed": 20261025,
            "development_fraction": 0.5,
            "note": "All pairs from one source group stay in the same partition to prevent leakage.",
        },
        "counts": {
            "pairs": len(pairs),
            "source_groups": len({pair["source_group_id"] for pair in pairs}),
            "labels": label_counts,
            "language_groups": dict(sorted(language_counts.items())),
        },
        "pairs": pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BACKEND_ROOT / "data" / "matching_benchmark_v1.json")
    parser.add_argument("--seed", type=int, default=GENERATION_SEED)
    args = parser.parse_args()
    dataset = build_dataset(seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(dataset['pairs'])} pairs to {args.output}")


if __name__ == "__main__":
    main()
