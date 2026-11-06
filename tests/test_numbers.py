from parda.numbers import spoken_numbers, to_ascii_digits


def found(text):
    return [(text[s.start : s.end], s.digits) for s in spoken_numbers(text)]


def test_devanagari_digits_keep_offsets():
    s = "नंबर ९८७६५ ४३२१०"
    assert to_ascii_digits(s) == "नंबर 98765 43210"
    assert len(to_ascii_digits(s)) == len(s)


def test_romanised_hindi_with_double():
    text = "mera number nau aath double saat chhe paanch chaar teen do ek hai"
    assert found(text) == [("nau aath double saat chhe paanch chaar teen do ek", "9877654321")]


def test_devanagari_words():
    assert found("नौ आठ डबल सात छह पांच चार तीन दो एक")[0][1] == "9877654321"


def test_mixed_digits_and_words():
    assert found("call 98 double 7 6 5 4 3 2 1 please")[0][1] == "9877654321"


def test_ordinary_sentences_are_not_numbers():
    assert found("do kurtas chahiye, ek blue ek green") == []
    assert found("I have two kurtas and one dupatta") == []


def test_pure_digit_runs_are_left_to_regex_detectors():
    assert found("98765 43210") == []


def test_danda_ends_a_word():
    assert found("नौ आठ सात छह पांच चार।")[0][1] == "987654"
