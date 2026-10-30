from __future__ import annotations

import importlib.util
import json
import os
import random
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

LABELS = ("DUPLICATE", "RELATED", "UNRELATED")
POSITIVE_LABELS = {"DUPLICATE", "RELATED"}
DEFAULT_SEED = 20261025
DEFAULT_DEV_FRACTION = 0.5
DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "matching_benchmark_v1.json"

EN_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "hers", "him", "his", "i", "if", "in", "into", "is",
    "it", "its", "me", "my", "of", "on", "or", "our", "ours", "she", "that", "the", "their",
    "them", "there", "these", "they", "this", "those", "to", "was", "we", "were", "what",
    "when", "where", "which", "who", "will", "with", "would", "you", "your", "yours",
    "kindly", "please", "sir", "madam", "dear", "subject",
}

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def load_dataset(path: str | Path | None = None) -> dict:
    dataset_path = Path(path or os.getenv("MATCHING_BENCHMARK_PATH") or DATASET_PATH)
    with dataset_path.open(encoding="utf-8") as handle:
        dataset = json.load(handle)
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: dict) -> None:
    if not dataset.get("dataset_id") or not dataset.get("version"):
        raise ValueError("Benchmark dataset must have a dataset_id and version")
    pairs = dataset.get("pairs")
    if not isinstance(pairs, list) or not 200 <= len(pairs) <= 300:
        raise ValueError("Benchmark dataset must contain approximately 200-300 pairs")
    seen_pair_ids: set[str] = set()
    seen_groups: set[str] = set()
    for pair in pairs:
        pair_id = pair.get("pair_id")
        if not pair_id or pair_id in seen_pair_ids:
            raise ValueError(f"Duplicate or missing pair_id: {pair_id!r}")
        seen_pair_ids.add(pair_id)
        source_group = pair.get("source_group_id")
        if not source_group:
            raise ValueError(f"Pair {pair_id} is missing source_group_id")
        seen_groups.add(source_group)
        if pair.get("adjudicated_label") not in LABELS:
            raise ValueError(f"Pair {pair_id} has an invalid adjudicated_label")
        annotations = pair.get("annotator_labels")
        if not isinstance(annotations, list) or not annotations:
            raise ValueError(f"Pair {pair_id} is missing annotator_labels")
        for side in ("case_a", "case_b"):
            case = pair.get(side)
            if not case or not case.get("text") or not case.get("language"):
                raise ValueError(f"Pair {pair_id} has an incomplete {side} case")
    if len(seen_groups) < 2:
        raise ValueError("Benchmark dataset needs at least two source groups for a split")


def normalize_text(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", text or "").lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = value.replace("_", " ")
    return re.sub(r"\s+", " ", value).strip()


def tokenize(text: str | None) -> list[str]:
    return [token for token in _TOKEN_RE.findall(normalize_text(text)) if token not in EN_STOPWORDS]


def jaccard(a: str | None, b: str | None) -> float:
    left, right = set(tokenize(a)), set(tokenize(b))
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 6)


def token_set_similarity(a: str | None, b: str | None) -> float:
    left, right = normalize_text(a), normalize_text(b)
    if not left or not right:
        return 0.0
    return round(fuzz.token_set_ratio(left, right) / 100.0, 6)


def split_dataset(dataset: dict, seed: int = DEFAULT_SEED, development_fraction: float = DEFAULT_DEV_FRACTION) -> tuple[list[dict], list[dict], dict]:
    groups = sorted({pair["source_group_id"] for pair in dataset["pairs"]})
    rng = random.Random(seed)
    rng.shuffle(groups)
    development_count = min(len(groups) - 1, max(1, round(len(groups) * development_fraction)))
    development_groups = set(groups[:development_count])
    development = [pair for pair in dataset["pairs"] if pair["source_group_id"] in development_groups]
    test = [pair for pair in dataset["pairs"] if pair["source_group_id"] not in development_groups]
    overlap = {pair["source_group_id"] for pair in development} & {pair["source_group_id"] for pair in test}
    if overlap:
        raise AssertionError(f"Source-group leakage detected: {sorted(overlap)}")
    split = {
        "seed": seed,
        "development_fraction": development_fraction,
        "development_pairs": len(development),
        "test_pairs": len(test),
        "development_groups": len(development_groups),
        "test_groups": len(groups) - len(development_groups),
        "source_group_overlap": False,
        "development_labels": _label_counts(development),
        "test_labels": _label_counts(test),
    }
    return development, test, split


def _label_counts(pairs: list[dict]) -> dict[str, int]:
    return {label: sum(1 for pair in pairs if pair["adjudicated_label"] == label) for label in LABELS}


def _language_group(pair: dict) -> str:
    return pair.get("language_group") or "-".join(
        sorted({pair["case_a"]["language"], pair["case_b"]["language"]})
    )


class _FeatureBank:
    def __init__(self, development: list[dict], test: list[dict]):
        self.development = development
        self.test = test
        self.development_texts = self._unique_texts(development)
        self.test_texts = self._unique_texts(test)

        self.char_vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True
        )
        self.word_vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self.char_vectorizer.fit(self.development_texts)
        self.word_vectorizer.fit(self.development_texts)
        self.char_vectors = {
            "development": self._vectors(self.char_vectorizer, self.development_texts),
            "test": self._vectors(self.char_vectorizer, self.test_texts),
        }
        self.word_vectors = {
            "development": self._vectors(self.word_vectorizer, self.development_texts),
            "test": self._vectors(self.word_vectorizer, self.test_texts),
        }

        self.scores: dict[str, dict[str, list[float]]] = {
            "jaccard": {"development": [], "test": []},
            "token_set": {"development": [], "test": []},
            "char": {"development": [], "test": []},
            "word": {"development": [], "test": []},
        }
        for split_name, pairs in (("development", development), ("test", test)):
            for pair in pairs:
                left, right = pair["case_a"]["text"], pair["case_b"]["text"]
                self.scores["jaccard"][split_name].append(jaccard(left, right))
                self.scores["token_set"][split_name].append(token_set_similarity(left, right))
                self.scores["char"][split_name].append(
                    self._cosine(split_name, "char", left, right)
                )
                self.scores["word"][split_name].append(
                    self._cosine(split_name, "word", left, right)
                )

    @staticmethod
    def _unique_texts(pairs: list[dict]) -> list[str]:
        seen: list[str] = []
        for pair in pairs:
            for side in ("case_a", "case_b"):
                text = pair[side]["text"]
                if text not in seen:
                    seen.append(text)
        return seen

    @staticmethod
    def _vectors(vectorizer: TfidfVectorizer, texts: list[str]):
        return dict(zip(texts, vectorizer.transform(texts)))

    def _cosine(self, split_name: str, kind: str, left: str, right: str) -> float:
        vectors = self.char_vectors if kind == "char" else self.word_vectors
        left_vector = vectors[split_name][left]
        right_vector = vectors[split_name][right]
        return round(float(cosine_similarity(left_vector, right_vector)[0][0]), 6)


def _combine(*parts: tuple[list[float], float]) -> list[float]:
    if not parts:
        return []
    scores = [0.0] * len(parts[0][0])
    for values, weight in parts:
        for index, value in enumerate(values):
            scores[index] += value * weight
    return [round(min(1.0, max(0.0, value)), 6) for value in scores]


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _label_for_score(score: float, thresholds: dict[str, float]) -> str:
    if score >= thresholds["duplicate"]:
        return "DUPLICATE"
    if score >= thresholds["related"]:
        return "RELATED"
    return "UNRELATED"


def _binary_metrics(true_labels: list[str], predicted_labels: list[str]) -> dict[str, float | int]:
    true_positive = sum(
        1 for truth, predicted in zip(true_labels, predicted_labels)
        if truth in POSITIVE_LABELS and predicted in POSITIVE_LABELS
    )
    false_positive = sum(
        1 for truth, predicted in zip(true_labels, predicted_labels)
        if truth not in POSITIVE_LABELS and predicted in POSITIVE_LABELS
    )
    false_negative = sum(
        1 for truth, predicted in zip(true_labels, predicted_labels)
        if truth in POSITIVE_LABELS and predicted not in POSITIVE_LABELS
    )
    true_negative = sum(
        1 for truth, predicted in zip(true_labels, predicted_labels)
        if truth not in POSITIVE_LABELS and predicted not in POSITIVE_LABELS
    )
    precision = _safe_divide(true_positive, true_positive + false_positive)
    recall = _safe_divide(true_positive, true_positive + false_negative)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    accuracy = _safe_divide(true_positive + true_negative, len(true_labels))
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
    }


def _three_class_metrics(true_labels: list[str], predicted_labels: list[str]) -> dict[str, Any]:
    per_class: dict[str, dict[str, float | int]] = {}
    for label in LABELS:
        true_positive = sum(1 for truth, predicted in zip(true_labels, predicted_labels) if truth == label and predicted == label)
        false_positive = sum(1 for truth, predicted in zip(true_labels, predicted_labels) if truth != label and predicted == label)
        false_negative = sum(1 for truth, predicted in zip(true_labels, predicted_labels) if truth == label and predicted != label)
        precision = _safe_divide(true_positive, true_positive + false_positive)
        recall = _safe_divide(true_positive, true_positive + false_negative)
        f1 = _safe_divide(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for truth in true_labels if truth == label),
        }
    macro_f1 = sum(value["f1"] for value in per_class.values()) / len(LABELS)
    accuracy = _safe_divide(
        sum(1 for truth, predicted in zip(true_labels, predicted_labels) if truth == predicted),
        len(true_labels),
    )
    matrix = [
        [
            sum(1 for truth, predicted in zip(true_labels, predicted_labels) if truth == true_label and predicted == predicted_label)
            for predicted_label in LABELS
        ]
        for true_label in LABELS
    ]
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "confusion_matrix": {"labels": list(LABELS), "matrix": matrix},
    }


def evaluate_predictions(true_labels: list[str], predicted_labels: list[str], language_groups: list[str]) -> dict[str, Any]:
    grouped = {group: {"truth": [], "predicted": []} for group in sorted(set(language_groups))}
    for truth, predicted, group in zip(true_labels, predicted_labels, language_groups):
        grouped[group]["truth"].append(truth)
        grouped[group]["predicted"].append(predicted)
    by_language = []
    for group, data in grouped.items():
        binary = _binary_metrics(data["truth"], data["predicted"])
        three = _three_class_metrics(data["truth"], data["predicted"])
        by_language.append(
            {
                "language_group": group,
                "pairs": len(data["truth"]),
                "binary_f1": binary["f1"],
                "precision": binary["precision"],
                "recall": binary["recall"],
                "macro_f1": three["macro_f1"],
                "accuracy": three["accuracy"],
            }
        )
    cross_truth = [truth for truth, group in zip(true_labels, language_groups) if "-" in group]
    cross_predicted = [predicted for predicted, group in zip(predicted_labels, language_groups) if "-" in group]
    cross_binary = _binary_metrics(cross_truth, cross_predicted) if cross_truth else None
    cross_three = _three_class_metrics(cross_truth, cross_predicted) if cross_truth else None
    return {
        "binary": _binary_metrics(true_labels, predicted_labels),
        "three_class": _three_class_metrics(true_labels, predicted_labels),
        "by_language": by_language,
        "cross_language": (
            {
                "pairs": len(cross_truth),
                "binary": cross_binary,
                "three_class": cross_three,
            }
            if cross_truth
            else {"pairs": 0, "binary": None, "three_class": None}
        ),
    }


def _candidate_thresholds(scores: list[float]) -> list[float]:
    values = sorted({round(score, 6) for score in scores})
    if len(values) <= 40:
        return sorted({0.0, 1.0, *values})
    sampled = values[:: max(1, len(values) // 40)]
    return sorted({0.0, 1.0, *sampled, values[-1]})


def tune_thresholds(scores: list[float], true_labels: list[str]) -> dict[str, float]:
    thresholds = _candidate_thresholds(scores)
    best_related = thresholds[0]
    best_duplicate = thresholds[0]
    best_macro_f1 = -1.0
    best_binary_f1 = -1.0
    for related_threshold in thresholds:
        for duplicate_threshold in thresholds:
            if duplicate_threshold < related_threshold:
                continue
            threshold_pair = {"related": related_threshold, "duplicate": duplicate_threshold}
            predicted = [_label_for_score(score, threshold_pair) for score in scores]
            three = _three_class_metrics(true_labels, predicted)
            binary = _binary_metrics(true_labels, predicted)
            if three["macro_f1"] > best_macro_f1 or (
                three["macro_f1"] == best_macro_f1 and binary["f1"] > best_binary_f1
            ):
                best_macro_f1 = three["macro_f1"]
                best_binary_f1 = binary["f1"]
                best_related = related_threshold
                best_duplicate = duplicate_threshold
    return {
        "related": round(best_related, 6),
        "duplicate": round(best_duplicate, 6),
        "development_binary_f1": round(best_binary_f1, 4),
        "development_macro_f1": round(best_macro_f1, 4),
    }


def _evaluate_score_set(scores: dict[str, list[float]], development: list[dict], test: list[dict]) -> dict[str, Any]:
    development_labels = [pair["adjudicated_label"] for pair in development]
    test_labels = [pair["adjudicated_label"] for pair in test]
    thresholds = tune_thresholds(scores["development"], development_labels)
    predicted = [_label_for_score(score, thresholds) for score in scores["test"]]
    metrics = evaluate_predictions(test_labels, predicted, [_language_group(pair) for pair in test])
    return {"thresholds": thresholds, **metrics}


def _semantic_status() -> dict[str, Any]:
    has_package = importlib.util.find_spec("sentence_transformers") is not None
    configured_model = os.getenv("MATCHING_SEMANTIC_MODEL", "").strip()
    if not has_package:
        reason = (
            "sentence-transformers is not installed in this environment, so no multilingual "
            "sentence-embedding model was loaded or executed. No semantic scores are reported."
        )
    elif not configured_model:
        reason = (
            "sentence-transformers is installed but MATCHING_SEMANTIC_MODEL is not configured; "
            "no semantic model was loaded or executed. No semantic scores are reported."
        )
    else:
        reason = (
            "A semantic model appears to be configured, but this benchmark run did not load it. "
            "No semantic scores are reported rather than fabricating model output."
        )
    return {
        "id": "multilingual_embedding",
        "label": "Multilingual sentence embeddings",
        "available": False,
        "reason": reason,
        "metrics": None,
    }


def _method_summary(identifier: str, label: str, description: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": identifier,
        "label": label,
        "description": description,
        "available": True,
        "thresholds": result["thresholds"],
        "test": {
            "binary": result["binary"],
            "three_class": result["three_class"],
            "by_language": result["by_language"],
            "cross_language": result["cross_language"],
        },
    }


def evaluate_matching_benchmark(
    dataset: dict | None = None,
    *,
    seed: int = DEFAULT_SEED,
    development_fraction: float = DEFAULT_DEV_FRACTION,
) -> dict[str, Any]:
    dataset = dataset or load_dataset()
    validate_dataset(dataset)
    development, test, split = split_dataset(dataset, seed=seed, development_fraction=development_fraction)
    bank = _FeatureBank(development, test)

    hybrid = {
        "development": _combine(
            (bank.scores["char"]["development"], 0.45),
            (bank.scores["token_set"]["development"], 0.35),
            (bank.scores["jaccard"]["development"], 0.20),
        ),
        "test": _combine(
            (bank.scores["char"]["test"], 0.45),
            (bank.scores["token_set"]["test"], 0.35),
            (bank.scores["jaccard"]["test"], 0.20),
        ),
    }
    score_sets: list[tuple[str, str, str, dict[str, list[float]]]] = [
        (
            "lexical_jaccard",
            "Token Jaccard",
            "Jaccard overlap over normalized word tokens after English stop-word removal.",
            bank.scores["jaccard"],
        ),
        (
            "tfidf_word",
            "TF-IDF word n-grams",
            "Cosine similarity over TF-IDF word unigrams and bigrams fitted on development text only.",
            bank.scores["word"],
        ),
        (
            "tfidf_char",
            "TF-IDF character n-grams",
            "Cosine similarity over TF-IDF character 3-5 grams fitted on development text only.",
            bank.scores["char"],
        ),
        (
            "fuzzy_token_set",
            "Fuzzy token-set",
            "RapidFuzz token-set ratio over normalized text; language-agnostic but still lexical.",
            bank.scores["token_set"],
        ),
        (
            "hybrid_lexical",
            "Hybrid lexical",
            "Weighted blend of character TF-IDF (0.45), fuzzy token-set (0.35) and token Jaccard (0.20).",
            hybrid,
        ),
    ]

    methods = []
    for identifier, label, description, scores in score_sets:
        result = _evaluate_score_set(scores, development, test)
        methods.append(_method_summary(identifier, label, description, result))

    ablation_variants: list[tuple[str, str, dict[str, list[float]]]] = [
        (
            "full_hybrid",
            "Full hybrid: char + token-set + Jaccard",
            hybrid,
        ),
        (
            "without_char",
            "Ablation: remove character TF-IDF",
            {
                "development": _combine(
                    (bank.scores["token_set"]["development"], 0.65),
                    (bank.scores["jaccard"]["development"], 0.35),
                ),
                "test": _combine(
                    (bank.scores["token_set"]["test"], 0.65),
                    (bank.scores["jaccard"]["test"], 0.35),
                ),
            },
        ),
        (
            "without_token_set",
            "Ablation: remove fuzzy token-set",
            {
                "development": _combine(
                    (bank.scores["char"]["development"], 0.75),
                    (bank.scores["jaccard"]["development"], 0.25),
                ),
                "test": _combine(
                    (bank.scores["char"]["test"], 0.75),
                    (bank.scores["jaccard"]["test"], 0.25),
                ),
            },
        ),
        (
            "without_jaccard",
            "Ablation: remove token Jaccard",
            {
                "development": _combine(
                    (bank.scores["char"]["development"], 0.55),
                    (bank.scores["token_set"]["development"], 0.45),
                ),
                "test": _combine(
                    (bank.scores["char"]["test"], 0.55),
                    (bank.scores["token_set"]["test"], 0.45),
                ),
            },
        ),
        (
            "char_only",
            "Ablation: character TF-IDF only",
            bank.scores["char"],
        ),
        (
            "word_only",
            "Ablation: word TF-IDF only",
            bank.scores["word"],
        ),
    ]
    ablation = []
    for identifier, description, scores in ablation_variants:
        result = _evaluate_score_set(scores, development, test)
        ablation.append(
            {
                "id": identifier,
                "description": description,
                "thresholds": result["thresholds"],
                "binary_f1": result["binary"]["f1"],
                "macro_f1": result["three_class"]["macro_f1"],
                "accuracy": result["three_class"]["accuracy"],
            }
        )

    provenance = dataset.get("provenance", {})
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "dataset": {
            "dataset_id": dataset["dataset_id"],
            "version": dataset["version"],
            "created_at": dataset.get("created_at"),
            "counts": dataset.get("counts", {}),
            "provenance": provenance,
            "label_definitions": dataset.get("label_definitions", {}),
        },
        "split": split,
        "methods": methods,
        "unavailable_methods": [_semantic_status()],
        "ablation": ablation,
        "notes": [
            "All pair labels are synthetic by construction; they are not human annotations.",
            "No inter-annotator agreement is claimed or measured.",
            "Both threshold values are selected on the development partition only and then applied unchanged to the test partition.",
            "Source groups are kept together across partitions to prevent leakage.",
            "Binary positives are DUPLICATE + RELATED; UNRELATED is the negative class.",
            "TF-IDF vocabularies are fitted on development text only; test text is transformed with that vocabulary.",
        ],
    }
