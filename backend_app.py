from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "model" / "n_gram"))
sys.path.insert(0, str(ROOT / "model" / "RNN"))

from ngram_spell_checker import NGramSpellChecker
from specil_rnn_spellchecker import DEFAULT_SLANG, SpecilRnnSpellChecker, detokenize, words


app = FastAPI(title="Morse NLP Backend")

_ngram: NGramSpellChecker | None = None
_rnn: SpecilRnnSpellChecker | None = None
_model_status = {"ngram": "loading", "rnn": "loading"}
_latest = {"input": "", "corrected": {"ngram": "", "rnn": ""}, "models": _model_status.copy()}


class SentenceIn(BaseModel):
    text: str


def ngram_model() -> NGramSpellChecker:
    global _ngram
    if _ngram is None:
        _ngram = NGramSpellChecker.load(ROOT / "model" / "n_gram" / "ngram_spell_checker.json.gz")
        _model_status["ngram"] = "ready"
    return _ngram


def rnn_model() -> SpecilRnnSpellChecker:
    global _rnn
    if _rnn is None:
        _rnn = SpecilRnnSpellChecker.load()
        _model_status["rnn"] = "ready"
    return _rnn


def run_models(text: str) -> dict:
    text = text.strip()
    ngram_input = detokenize([DEFAULT_SLANG.get(word, word) for word in words(text)])
    result = {
        "input": text,
        "corrected": {
            "ngram": ngram_model().correct(ngram_input) if text else "",
            "rnn": rnn_model().correct(text) if text else "",
        },
        "models": _model_status.copy(),
    }
    _latest.update(result)
    return result


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Morse NLP Backend</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #f6f7f9; color: #15171a; }
    header { padding: 16px 22px; background: #111827; color: white; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    main { max-width: 900px; margin: 28px auto; padding: 0 18px; display: grid; gap: 14px; }
    textarea, pre { width: 100%; box-sizing: border-box; border: 1px solid #cfd6df; border-radius: 8px; padding: 14px; font: inherit; background: white; }
    textarea { min-height: 90px; resize: vertical; }
    button { width: fit-content; border: 0; border-radius: 8px; padding: 10px 16px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
    section { display: grid; gap: 8px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
    .status { font-size: 14px; color: #d1d5db; }
    label { font-weight: 700; }
  </style>
</head>
<body>
  <header>
    <strong>Morse NLP Backend</strong>
    <span class="status" id="status">Model status: checking...</span>
  </header>
  <main>
    <section>
      <label for="text">Input sentence from ESP32 / manual test</label>
      <textarea id="text" placeholder="contoh: ak mw makn"></textarea>
      <button onclick="sendText()">Correct</button>
    </section>
    <div class="grid">
      <section><label>Raw input</label><pre id="raw">-</pre></section>
      <section><label>N-gram correction</label><pre id="ngram">-</pre></section>
      <section><label>RNN correction</label><pre id="rnn">-</pre></section>
    </div>
  </main>
  <script>
    async function render(data) {
      document.getElementById("raw").textContent = data.input || "-";
      document.getElementById("ngram").textContent = data.corrected?.ngram || "-";
      document.getElementById("rnn").textContent = data.corrected?.rnn || "-";
      document.getElementById("status").textContent = `Model status: n-gram ${data.models?.ngram || "unknown"} | RNN ${data.models?.rnn || "unknown"}`;
    }
    async function sendText() {
      const text = document.getElementById("text").value;
      const res = await fetch("/api/correct", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({text}) });
      render(await res.json());
    }
    async function poll() {
      const res = await fetch("/api/latest");
      render(await res.json());
    }
    poll();
    setInterval(poll, 1000);
  </script>
</body>
</html>"""
    )


@app.get("/api/latest")
def latest_state() -> dict:
    return _latest


@app.get("/api/status")
def model_status() -> dict:
    return {"models": _model_status.copy()}


@app.post("/api/correct")
def correct_text(payload: SentenceIn) -> dict:
    return run_models(payload.text)


@app.post("/api/esp32")
def esp32_sentence(payload: SentenceIn) -> dict:
    return run_models(payload.text)


@app.post("/api/message")
def legacy_message(payload: SentenceIn) -> dict:
    return run_models(payload.text)


@app.get("/api/esp32")
def esp32_sentence_get(text: str) -> dict:
    return run_models(text)
