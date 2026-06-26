from app import SentenceIn, correct_text, esp32_sentence_get, home, latest_state, legacy_message, model_status


def main():
    page = home()
    assert "Morse NLP Backend" in page.body.decode()
    assert model_status()["models"] == {"ngram": "ready", "rnn": "ready"}

    data = correct_text(SentenceIn(text="ak mw makn"))
    assert data["input"] == "ak mw makn"
    assert data["corrected"]["ngram"] == "aku mau makan"
    assert data["corrected"]["rnn"] == "aku mau makan"
    assert data["details"]["ngram"]["model"] == "indonesian_char_ngram_spellchecker"
    assert data["models"]["ngram"] == "ready"
    assert data["models"]["rnn"] == "ready"
    assert latest_state()["input"] == "ak mw makn"

    harder_cases = {
        "kami pergi ke sekolh pagi ini": "kami pergi ke sekolah pagi ini",
        "Indonesai punya banyak pulau.": "Indonesia punya banyak pulau.",
        "anak-anak bermain di rumah": "anak-anak bermain di rumah",
        "dia mau meken nasi": "dia mau makan nasi",
        "pemerinta membuat aturan baru": "pemerintah membuat aturan baru",
    }
    for raw, expected in harder_cases.items():
        data = correct_text(SentenceIn(text=raw))
        assert data["corrected"]["ngram"] == expected
        assert data["details"]["ngram"]["model"] == "indonesian_char_ngram_spellchecker"

    assert latest_state()["input"] == "pemerinta membuat aturan baru"
    assert esp32_sentence_get("Aku belajra bahasa indonesia.").body == b"OK"
    assert latest_state()["corrected"]["rnn"] == "aku belajar bahasa indonesia."
    assert legacy_message(SentenceIn(text="ak mw makn")).body == b"OK"
    assert latest_state()["corrected"]["rnn"] == "aku mau makan"
    assert model_status()["models"]["rnn"] == "ready"
    print("ok")


if __name__ == "__main__":
    main()
