from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from indonesian_slang import SLANG as DEFAULT_SLANG

TRAIN_PATH = ROOT / "specil_train.csv"
TEST_PATH = ROOT / "specil_test.csv"
MODEL_PATH = Path(__file__).with_name("specil_rnn_spellchecker.keras")
META_PATH = Path(__file__).with_name("specil_rnn_spellchecker_meta.json")
WORD_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?|[.,!?;:\"'()]")
SPACE_RE = re.compile(r"\s+")
LETTERS = "abcdefghijklmnopqrstuvwxyz"
BACKEND = "tensorflow-keras"


def norm(text: str) -> str:
    text = text.lower().replace("_", " ")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"([.,!?;:\"'()])", r" \1 ", text)
    return SPACE_RE.sub(" ", text).strip()


def words(text: str) -> list[str]:
    return WORD_RE.findall(norm(text))


def detokenize(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = text.replace("( ", "(").replace(" )", ")")
    return text.strip()


def edits1(word: str) -> set[str]:
    parts = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return {
        *(a + b[1:] for a, b in parts if b),
        *(a + b[1] + b[0] + b[2:] for a, b in parts if len(b) > 1),
        *(a + c + b[1:] for a, b in parts if b for c in LETTERS),
        *(a + c + b for a, b in parts for c in LETTERS),
    }


def close_enough(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 2:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > 2:
            return False
        prev = cur
    return prev[-1] <= 2


def load_pairs(path: Path, limit: int | None = None) -> list[tuple[str, str]]:
    pairs = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pairs.append((row["wrong_text"], row["correct_text"]))
            if limit and len(pairs) >= limit:
                break
    return pairs


def build_rnn(vocab_size: int, seq_len: int) -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(seq_len,)),
            tf.keras.layers.Embedding(vocab_size, 24),
            tf.keras.layers.GRU(64),
            tf.keras.layers.Dense(vocab_size, activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    return model


class SpecilRnnSpellChecker:
    backend = BACKEND

    def __init__(
        self,
        model: tf.keras.Model,
        chars: list[str],
        seq_len: int,
        typo: dict[str, list[str]],
        vocab: dict[str, int],
        split_counts: dict[str, int],
        slang: dict[str, str],
    ):
        self.model = model
        self.chars = chars
        self.c2i = {c: i for i, c in enumerate(chars)}
        self.seq_len = seq_len
        self.typo = typo
        self.vocab = vocab
        self.split_counts = split_counts
        self.slang = slang

    @classmethod
    def train(
        cls,
        limit: int | None = None,
        train_chars: int = 500_000,
        seq_len: int = 40,
        epochs: int = 1,
    ) -> "SpecilRnnSpellChecker":
        train_pairs = load_pairs(TRAIN_PATH, limit)
        test_count = sum(1 for _ in TEST_PATH.open(encoding="utf-8")) - 1
        typo_counts: dict[str, Counter[str]] = defaultdict(Counter)
        vocab = Counter()
        clean_lines = []

        for wrong_raw, correct_raw in train_pairs:
            wrong, correct = words(wrong_raw), words(correct_raw)
            vocab.update(w for w in correct if w.isalpha())
            clean_lines.append(norm(correct_raw))
            if len(wrong) == len(correct):
                for bad, good in zip(wrong, correct):
                    if bad != good and bad.isalpha() and good.isalpha() and close_enough(bad, good):
                        typo_counts[bad][good] += 1

        train_text = ("\n".join(clean_lines) + "\n")[:train_chars]
        chars = sorted(set(train_text))
        c2i = {c: i for i, c in enumerate(chars)}
        ids = np.array([c2i[c] for c in train_text], dtype=np.int32)
        if len(ids) <= seq_len:
            raise ValueError("not enough SPECIL text to train the RNN")

        x = np.stack([ids[i : i + seq_len] for i in range(len(ids) - seq_len)])
        y = ids[seq_len:]
        model = build_rnn(len(chars), seq_len)
        model.fit(x, y, epochs=epochs, batch_size=256, verbose=2)

        typo = {bad: [good for good, _ in counts.most_common(5)] for bad, counts in typo_counts.items()}
        slang = {bad: good for bad, good in DEFAULT_SLANG.items() if good in vocab or good in {"aku", "mau", "makan"}}
        return cls(model, chars, seq_len, typo, dict(vocab), {"train": len(train_pairs), "test": test_count}, slang)

    def _encode_context(self, text: str) -> np.ndarray:
        ids = [self.c2i.get(c, 0) for c in ("\n" + norm(text))[-self.seq_len :]]
        ids = [0] * max(0, self.seq_len - len(ids)) + ids
        return np.array([ids], dtype=np.int32)

    def score(self, text: str) -> float:
        clean = "\n" + norm(text) + "\n"
        if len(clean) < 2:
            return -999.0
        total = 0.0
        count = 0
        for i in range(1, len(clean)):
            target = clean[i]
            if target not in self.c2i:
                continue
            pred = self.model.predict(self._encode_context(clean[:i]), verbose=0)[0]
            total += math.log(float(pred[self.c2i[target]]) + 1e-12)
            count += 1
        return total / max(count, 1)

    def candidates(self, word: str) -> set[str]:
        if not word.isalpha():
            return {word}
        if word in self.slang:
            return {self.slang[word]}
        if word in self.vocab:
            return {word}
        return set(self.typo.get(word, [])) or {w for w in edits1(word) if w in self.vocab} or {word}

    def correct(self, text: str) -> str:
        toks = words(text)
        for i, word in enumerate(toks):
            cands = self.candidates(word)
            if len(cands) == 1:
                toks[i] = next(iter(cands))
                continue
            toks[i] = max(cands, key=lambda c: self.score(" ".join([*toks[:i], c, *toks[i + 1 :]])) + math.log(self.vocab.get(c, 0) + 1))
        return detokenize(toks)

    def save(self, model_path: Path = MODEL_PATH, meta_path: Path = META_PATH) -> None:
        self.model.save(model_path)
        meta = {
            "backend": self.backend,
            "chars": self.chars,
            "seq_len": self.seq_len,
            "typo": self.typo,
            "vocab": self.vocab,
            "split_counts": self.split_counts,
            "slang": self.slang,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, model_path: Path = MODEL_PATH, meta_path: Path = META_PATH) -> "SpecilRnnSpellChecker":
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model = tf.keras.models.load_model(model_path)
        slang = meta.get("slang", DEFAULT_SLANG)
        return cls(model, meta["chars"], meta["seq_len"], meta["typo"], meta["vocab"], meta["split_counts"], slang)

    def evaluate(self, limit: int = 200) -> tuple[int, int]:
        checked = correct = 0
        for wrong_raw, correct_raw in load_pairs(TEST_PATH):
            wrong, target = words(wrong_raw), words(correct_raw)
            if len(wrong) != len(target):
                continue
            diffs = [(bad, good) for bad, good in zip(wrong, target) if bad != good and bad.isalpha() and good.isalpha()]
            if len(diffs) != 1:
                continue
            fixed = words(self.correct(wrong_raw))
            if len(fixed) == len(target):
                checked += 1
                correct += fixed == target
            if checked >= limit:
                break
        return correct, checked


def demo(checker: SpecilRnnSpellChecker) -> None:
    for text in ("Aku belajra bahasa indonesia.", "Guru memberi contoh lagu di wtas papan.", "Dokumen harus dijaga dan diraawat."):
        print(f"{text} -> {checker.correct(text)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "demo", "correct", "evaluate"])
    parser.add_argument("text", nargs="?", help="Sentence to correct when command is 'correct'.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--train-chars", type=int, default=500_000)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()

    if args.command == "train":
        checker = SpecilRnnSpellChecker.train(limit=args.limit, train_chars=args.train_chars, epochs=args.epochs)
        checker.save()
        print(f"saved {MODEL_PATH}")
        print(f"backend={checker.backend} train={checker.split_counts['train']:,} test={checker.split_counts['test']:,} typo={len(checker.typo):,} vocab={len(checker.vocab):,}")
    elif args.command == "correct":
        if not args.text:
            raise SystemExit("usage: specil_rnn_spellchecker.py correct \"kalimat salah\"")
        print(SpecilRnnSpellChecker.load().correct(args.text))
    elif args.command == "evaluate":
        correct, checked = SpecilRnnSpellChecker.load().evaluate()
        print(f"heldout_word_accuracy={correct}/{checked} ({correct / max(checked, 1):.2%})")
    else:
        demo(SpecilRnnSpellChecker.load())


if __name__ == "__main__":
    main()
