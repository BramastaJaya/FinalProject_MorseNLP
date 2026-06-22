from specil_rnn_spellchecker import SpecilRnnSpellChecker


def main():
    checker = SpecilRnnSpellChecker.load()
    assert checker.backend == "tensorflow-keras"
    assert checker.split_counts["train"] > 0
    assert checker.split_counts["test"] > 0
    assert not hasattr(checker, "exact")
    assert checker.correct("ak mw makn") == "aku mau makan"
    assert "bunyi" in checker.correct("Buni apa?").lower()
    assert "atas" in checker.correct("Guru memberi contoh lagu di wtas papan.").lower()
    print("ok")


if __name__ == "__main__":
    main()
