from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indonesian_slang import normalize_slang


MODEL_PATH = Path(__file__).with_name("ngram_spell_checker.json.gz")
DATA_PATH = Path(__file__).resolve().parents[1] / "specil_train.csv"
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)*")
TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)*|\S")
CONFIG = {
    "language": "id",
    "model": "indonesian_char_ngram_spellchecker",
    "model_version": "2026.1.0",
    "n_values": [1, 2, 3],
    "use_boundary_markers": True,
    "auto_correct_threshold": 0.55,
    "suggestion_threshold": 0.50,
    "max_length_difference": 3,
    "candidate_pool_limit": 120,
    "weights": {
        "jaccard": 0.10,
        "weighted_overlap": 0.10,
        "frequency": 0.35,
        "edit": 0.25,
        "length": 0.20,
    },
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def tokenize_words(text: str) -> list[str]:
    return WORD_RE.findall(normalize(text))


def token_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def generate_ngrams(word: str, n_values: list[int] | None = None, use_boundary_markers: bool = True) -> dict[str, list[str]]:
    word = normalize(word)
    source = f"<{word}>" if use_boundary_markers else word
    n_values = n_values or CONFIG["n_values"]
    return {str(n): sorted({source[i : i + n] for i in range(max(0, len(source) - n + 1))}) for n in n_values}


def edit_distance(a: str, b: str, limit: int = 3) -> int:
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def apply_case(original: str, corrected: str) -> str:
    if original.isupper():
        return corrected.upper()
    if original[:1].isupper():
        return corrected.capitalize()
    return corrected


class NGramSpellChecker:
    def __init__(
        self,
        vocabulary: dict[str, int],
        ngram_frequency: dict[str, dict[str, int]],
        inverted_index: dict[str, dict[str, list[str]]],
        config: dict,
        corpus_metadata: dict,
    ):
        self.vocabulary = vocabulary
        self.word_frequency = vocabulary
        self.ngram_frequency = ngram_frequency
        self.inverted_index = inverted_index
        self.config = config
        self.corpus_metadata = corpus_metadata
        self.max_frequency = max(vocabulary.values()) if vocabulary else 1

    def candidates(self, word: str) -> list[str]:
        word = normalize(word)
        slang = normalize_slang([word])[0]
        if slang != word:
            return [slang]
        if word in self.vocabulary:
            return [word]

        grams = generate_ngrams(word, self.config["n_values"], self.config["use_boundary_markers"])
        counts: Counter[str] = Counter()
        for n, values in grams.items():
            for gram in values:
                counts.update(self.inverted_index.get(n, {}).get(gram, []))

        max_len_diff = self.config["max_length_difference"]
        pool = [w for w, _ in counts.most_common(self.config["candidate_pool_limit"] * 3) if abs(len(w) - len(word)) <= max_len_diff]
        if len(word) <= 6:
            # ponytail: short typo fallback; replace with BK-tree only if vocab size becomes a measured problem.
            pool.extend(w for w in self.vocabulary if abs(len(w) - len(word)) <= max_len_diff and edit_distance(word, w, 2) <= 2)
        seen = set()
        return [w for w in pool if not (w in seen or seen.add(w))][: self.config["candidate_pool_limit"]] or [word]

    def features(self, word: str, candidate: str) -> dict:
        word_grams = generate_ngrams(word, self.config["n_values"], self.config["use_boundary_markers"])
        cand_grams = generate_ngrams(candidate, self.config["n_values"], self.config["use_boundary_markers"])
        all_word = set().union(*(set(v) for v in word_grams.values()))
        all_cand = set().union(*(set(v) for v in cand_grams.values()))
        shared = all_word & all_cand
        union = all_word | all_cand
        weights = {"1": 0.10, "2": 0.35, "3": 0.55}
        weighted = 0.0
        possible = 0.0
        for n in word_grams:
            w = weights.get(n, 0.0)
            shared_n = set(word_grams[n]) & set(cand_grams[n])
            union_n = set(word_grams[n]) | set(cand_grams[n])
            weighted += w * len(shared_n)
            possible += w * max(len(union_n), 1)
        dist = edit_distance(word, candidate, 3)
        return {
            "jaccard_similarity": len(shared) / max(len(union), 1),
            "weighted_ngram_overlap": weighted / max(possible, 1e-9),
            "edit_distance": dist,
            "edit_distance_score": max(0.0, 1.0 - dist / max(len(word), len(candidate), 1)),
            "word_frequency": self.vocabulary.get(candidate, 0),
            "frequency_score": math.log1p(self.vocabulary.get(candidate, 0)) / math.log1p(self.max_frequency),
            "length_similarity": 1.0 - abs(len(word) - len(candidate)) / max(len(word), len(candidate), 1),
        }

    def score(self, word: str, candidate: str) -> tuple[float, dict]:
        f = self.features(word, candidate)
        weights = self.config["weights"]
        score = (
            weights["jaccard"] * f["jaccard_similarity"]
            + weights["weighted_overlap"] * f["weighted_ngram_overlap"]
            + weights["frequency"] * f["frequency_score"]
            + weights["edit"] * f["edit_distance_score"]
            + weights["length"] * f["length_similarity"]
        )
        return score, f

    def correct_word(self, original: str, start: int, end: int) -> tuple[str, dict | None]:
        word = normalize(original)
        candidates = self.candidates(word)
        if candidates == [word]:
            return original, None

        ranked = []
        for candidate in candidates:
            score, features = self.score(word, candidate)
            ranked.append((score, candidate, features))
        ranked.sort(reverse=True, key=lambda item: item[0])
        best_score, best, _ = ranked[0]
        corrected = best if best_score >= self.config["auto_correct_threshold"] or normalize_slang([word])[0] == best else word
        status = "corrected" if corrected != word else "suggested"
        detail = {
            "original": original,
            "corrected": apply_case(original, corrected) if status == "corrected" else None,
            "status": status,
            "confidence": round(best_score, 4),
            "start_index": start,
            "end_index": end,
            "candidates": [
                {
                    "word": apply_case(original, cand),
                    "score": round(score, 4),
                    "jaccard_similarity": round(f["jaccard_similarity"], 4),
                    "weighted_ngram_overlap": round(f["weighted_ngram_overlap"], 4),
                    "edit_distance": f["edit_distance"],
                    "word_frequency": f["word_frequency"],
                    "length_similarity": round(f["length_similarity"], 4),
                }
                for score, cand, f in ranked[:5]
            ],
        }
        return apply_case(original, corrected), detail

    def correct_with_details(self, text: str) -> dict:
        out = []
        corrections = []
        pos = 0
        for token, start, end in token_spans(text):
            out.append(text[pos:start])
            if WORD_RE.fullmatch(token):
                fixed, detail = self.correct_word(token, start, end)
                out.append(fixed)
                if detail:
                    corrections.append(detail)
            else:
                out.append(token)
            pos = end
        out.append(text[pos:])
        return {
            "original_text": text,
            "corrected_text": "".join(out),
            "language": self.config["language"],
            "model": self.config["model"],
            "model_version": self.config["model_version"],
            "corrections": corrections,
        }

    def correct(self, text: str) -> str:
        return self.correct_with_details(text)["corrected_text"]

    def save(self, path: Path = MODEL_PATH) -> None:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(
                {
                    "indonesian_vocabulary": self.vocabulary,
                    "word_frequency_table": self.word_frequency,
                    "char_ngram_frequency_table": self.ngram_frequency,
                    "ngram_inverted_index": self.inverted_index,
                    "model_config": self.config,
                    "thresholds": {
                        "auto_correct": self.config["auto_correct_threshold"],
                        "suggestion": self.config["suggestion_threshold"],
                    },
                    "ranking_weights": self.config["weights"],
                    "corpus_metadata": self.corpus_metadata,
                    "model_version": self.config["model_version"],
                },
                f,
                ensure_ascii=False,
            )

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "NGramSpellChecker":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            data["indonesian_vocabulary"],
            data["char_ngram_frequency_table"],
            data["ngram_inverted_index"],
            data["model_config"],
            data["corpus_metadata"],
        )


def train(data_path: Path = DATA_PATH, limit: int | None = None, min_count: int = 2) -> NGramSpellChecker:
    vocabulary: Counter[str] = Counter()
    ngram_frequency: dict[str, Counter[str]] = {str(n): Counter() for n in CONFIG["n_values"]}
    inverted: dict[str, dict[str, set[str]]] = {str(n): defaultdict(set) for n in CONFIG["n_values"]}
    rows = 0

    with data_path.open(encoding="utf-8", newline="") as f:
        for rows, row in enumerate(csv.DictReader(f), 1):
            if limit and rows > limit:
                break
            for word in tokenize_words(row["correct_text"]):
                vocabulary[word] += 1

    vocabulary = Counter({word: count for word, count in vocabulary.items() if count >= min_count})
    for word in vocabulary:
        for n, grams in generate_ngrams(word, CONFIG["n_values"], CONFIG["use_boundary_markers"]).items():
            ngram_frequency[n].update(grams)
            for gram in grams:
                inverted[n][gram].add(word)

    return NGramSpellChecker(
        dict(vocabulary),
        {n: dict(counts) for n, counts in ngram_frequency.items()},
        {n: {gram: sorted(words) for gram, words in grams.items()} for n, grams in inverted.items()},
        CONFIG,
        {
            "source_name": "SPECIL train split",
            "source_path": str(data_path),
            "row_count": rows,
            "unique_token_count": len(vocabulary),
            "included": True,
            "notes": "Built from correct_text in specil_train.csv; specil_test.csv is held out.",
        },
    )


def demo(checker: NGramSpellChecker) -> None:
    checks = {
        "ak mw makn": "aku mau makan",
        "aku mau meken": "aku mau makan",
        "saya pergi ke sekolh": "saya pergi ke sekolah",
        "Indonesai adalah negara besar": "Indonesia adalah negara besar",
        "anak-anak bermain": "anak-anak bermain",
    }
    for text, expected in checks.items():
        corrected = checker.correct(text)
        print(f"{text} -> {corrected}")
        assert corrected == expected, f"expected {expected!r}, got {corrected!r}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "demo", "correct"])
    parser.add_argument("text", nargs="?")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.command == "train":
        checker = train(limit=args.limit)
        checker.save()
        print(f"saved {MODEL_PATH}")
        print(f"vocab={len(checker.vocabulary):,} ngrams={sum(len(v) for v in checker.ngram_frequency.values()):,}")
    elif args.command == "correct":
        if not args.text:
            raise SystemExit("usage: ngram_spell_checker.py correct \"kalimat salah\"")
        print(NGramSpellChecker.load().correct(args.text))
    else:
        demo(NGramSpellChecker.load())


if __name__ == "__main__":
    main()
