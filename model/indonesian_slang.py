SLANG = {
    "ak": "aku", "aq": "aku", "gw": "aku", "gue": "aku", "gua": "aku", "q": "aku",
    "sy": "saya", "sya": "saya", "km": "kamu", "kmu": "kamu", "lu": "kamu", "lo": "kamu", "lw": "kamu",
    "dy": "dia", "dya": "dia", "mrk": "mereka",
    "mw": "mau", "mo": "mau", "pgn": "ingin", "pngn": "ingin",
    "tdk": "tidak", "gak": "tidak", "ga": "tidak", "g": "tidak", "nggak": "tidak", "ngga": "tidak",
    "blm": "belum", "sdh": "sudah", "udh": "sudah", "dah": "sudah",
    "lg": "lagi", "lgi": "lagi", "skrg": "sekarang", "skrng": "sekarang", "bsk": "besok", "kmrn": "kemarin",
    "krn": "karena", "karna": "karena", "yg": "yang", "dgn": "dengan", "dg": "dengan",
    "utk": "untuk", "buat": "untuk", "dr": "dari", "dri": "dari", "dlm": "dalam",
    "sm": "sama", "sma": "sama", "aja": "saja", "aj": "saja", "bgt": "banget", "bngt": "banget",
    "trs": "terus", "trus": "terus", "tp": "tapi", "tpi": "tapi", "klo": "kalau", "kl": "kalau",
    "jd": "jadi", "jdi": "jadi", "bs": "bisa", "bsa": "bisa", "knp": "kenapa", "knapa": "kenapa",
    "gmn": "bagaimana", "gmna": "bagaimana", "dimna": "dimana", "dmn": "dimana",
    "mkn": "makan", "makn": "makan", "mnm": "minum", "minm": "minum", "tdr": "tidur",
    "bljr": "belajar", "belajra": "belajar", "indo": "indonesia", "bhs": "bahasa",
}


def normalize_slang(tokens):
    return [SLANG.get(token, token) for token in tokens]
