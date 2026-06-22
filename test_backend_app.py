from backend_app import SentenceIn, correct_text, esp32_sentence_get, home, latest_state, legacy_message, model_status


def main():
    page = home()
    assert "Morse NLP Backend" in page.body.decode()

    data = correct_text(SentenceIn(text="ak mw makn"))
    assert data["input"] == "ak mw makn"
    assert data["corrected"]["ngram"] == "aku mau makan"
    assert data["corrected"]["rnn"] == "aku mau makan"
    assert data["models"]["ngram"] == "ready"
    assert data["models"]["rnn"] == "ready"

    assert latest_state()["input"] == "ak mw makn"
    assert esp32_sentence_get("Aku belajra bahasa indonesia.")["corrected"]["rnn"] == "aku belajar bahasa indonesia."
    assert legacy_message(SentenceIn(text="ak mw makn"))["corrected"]["rnn"] == "aku mau makan"
    assert model_status()["models"]["rnn"] == "ready"
    print("ok")


if __name__ == "__main__":
    main()
