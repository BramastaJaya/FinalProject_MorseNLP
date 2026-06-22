from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indonesian_slang import normalize_slang


MODEL_PATH = Path(__file__).with_name("ngram_spell_checker.json.gz")
DATA_PATH = Path(__file__).resolve().parents[1] / "specil_train.csv"
WORD_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?|[.,!?;:\"'()]")
LETTERS = "abcdefghijklmnopqrstuvwxyz"


def tokens(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def edits1(word: str) -> set[str]:
    parts = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [left + right[1:] for left, right in parts if right]
    transposes = [left + right[1] + right[0] + right[2:] for left, right in parts if len(right) > 1]
    replaces = [left + c + right[1:] for left, right in parts if right for c in LETTERS]
    inserts = [left + c + right for left, right in parts for c in LETTERS]
    return set(deletes + transposes + replaces + inserts)


def known(words: set[str], vocab: dict[str, int]) -> set[str]:
    return {word for word in words if word in vocab}


def edit_distance_at_most_2(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 2:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            curr.append(min(prev[j] + 1, curr[-1] + 1, prev[j - 1] + (ca != cb)))
        if min(curr) > 2:
            return False
        prev = curr
    return prev[-1] <= 2


class NGramSpellChecker:
    def __init__(self, unigram: dict[str, int], bigram: dict[str, int], edits: dict[str, list[str]]):
        self.unigram = unigram
        self.bigram = bigram
        self.edits = edits
        self.total = sum(unigram.values()) or 1
        self.vocab_size = len(unigram) or 1

    def candidates(self, word: str) -> set[str]:
        if not word.isalpha():
            return {word}
        normalized = normalize_slang([word])[0]
        if normalized != word:
            return {normalized}
        observed = set(self.edits.get(word, []))
        if word in self.unigram:
            return {word}
        return observed or known(edits1(word), self.unigram) or {word}

    def score(self, prev: str, word: str) -> float:
        # ponytail: add-one bigram smoothing is enough; upgrade to trigram/Kneser-Ney only if eval says it matters.
        return math.log((self.bigram.get(f"{prev} {word}", 0) + 1) / (self.unigram.get(prev, 0) + self.vocab_size))

    def correct_tokens(self, words: list[str]) -> list[str]:
        out = []
        prev = "<s>"
        for word in words:
            best = max(self.candidates(word), key=lambda candidate: self.score(prev, candidate) + math.log(self.unigram.get(candidate, 0) + 1))
            out.append(best)
            prev = best
        return out

    def correct(self, text: str) -> str:
        return " ".join(self.correct_tokens(tokens(text)))

    def save(self, path: Path = MODEL_PATH) -> None:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump({"unigram": self.unigram, "bigram": self.bigram, "edits": self.edits}, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "NGramSpellChecker":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["unigram"], data["bigram"], data["edits"])


def train(data_path: Path = DATA_PATH, limit: int | None = None, min_count: int = 2) -> NGramSpellChecker:
    unigram: Counter[str] = Counter()
    bigram: Counter[str] = Counter()
    observed_edits: dict[str, Counter[str]] = {}

    with data_path.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if limit and i >= limit:
                break
            correct = tokens(row["correct_text"])
            wrong = tokens(row["wrong_text"])
            unigram.update(["<s>", *correct])
            bigram.update(f"{a} {b}" for a, b in zip(["<s>", *correct], correct))
            if len(wrong) == len(correct):
                for bad, good in zip(wrong, correct):
                    if bad != good and bad.isalpha() and good.isalpha() and edit_distance_at_most_2(bad, good):
                        observed_edits.setdefault(bad, Counter())[good] += 1

    vocab = {word: count for word, count in unigram.items() if count >= min_count or word == "<s>"}
    bigrams = {pair: count for pair, count in bigram.items() if pair.split()[0] in vocab and pair.split()[1] in vocab}
    edits = {bad: [good for good, _ in counts.most_common(5) if good in vocab] for bad, counts in observed_edits.items()}
    return NGramSpellChecker(vocab, bigrams, edits)


def demo(checker: NGramSpellChecker) -> None:
    checks = {
        "ak mw makn": "aku mau makan",
        "buni apa": "bunyi",
    }
    for text, expected in checks.items():
        corrected = checker.correct(text)
        print(f"{text} -> {corrected}")
        assert expected in corrected, f"expected {expected!r} in {corrected!r}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "demo"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.command == "train":
        checker = train(limit=args.limit)
        checker.save()
        print(f"saved {MODEL_PATH}")
        print(f"vocab={len(checker.unigram):,} bigrams={len(checker.bigram):,} edits={len(checker.edits):,}")
    else:
        demo(NGramSpellChecker.load())


if __name__ == "__main__":
    main()
