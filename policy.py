import csv
import gzip
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    assert (ROOT / "model" / "model_pipeline.ipynb").exists()
    assert not (ROOT / "model" / "build_specil_split.py").exists()
    for name in ("specil_combined.csv", "specil_train.csv", "specil_test.csv"):
        path = ROOT / "model" / name
        assert path.exists(), name
        with path.open(encoding="utf-8", newline="") as f:
            row = next(csv.DictReader(f))
        assert set(row) == {"wrong_text", "correct_text", "error_type", "split"}

    rnn = json.loads((ROOT / "model" / "RNN" / "specil_rnn_spellchecker_meta.json").read_text(encoding="utf-8"))
    assert "exact" not in rnn
    assert rnn["split_counts"]["train"] > 0 and rnn["split_counts"]["test"] > 0
    assert rnn["slang"]["ak"] == "aku"

    with gzip.open(ROOT / "model" / "n_gram" / "ngram_spell_checker.json.gz", "rt", encoding="utf-8") as f:
        ngram = json.load(f)
    assert {"unigram", "bigram", "edits"} - set(ngram)
    assert "indonesian_vocabulary" in ngram
    assert "word_frequency_table" in ngram
    assert "char_ngram_frequency_table" in ngram
    assert "ngram_inverted_index" in ngram
    assert "model_config" in ngram
    assert "corpus_metadata" in ngram
    assert ngram["model_config"]["model"] == "indonesian_char_ngram_spellchecker"
    assert set(ngram["char_ngram_frequency_table"]) == {"1", "2", "3"}
    print("ok")


if __name__ == "__main__":
    main()
