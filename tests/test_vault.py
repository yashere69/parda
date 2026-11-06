import pytest

from parda import Parda


def test_same_value_same_token_across_calls():
    p = Parda()
    a = p.redact("call 9876543210")
    b = p.redact("I said +91 98765 43210")
    assert a.text == "call [PHONE_1]"
    assert b.text == "I said [PHONE_1]"
    assert p.redact("or 9123456789").text == "or [PHONE_2]"


@pytest.mark.parametrize(
    "reply",
    [
        "sent to [UPI_1]",
        "sent to [upi_1]",
        "sent to UPI_1",
        "sent to UPI 1",
        "sent to **[UPI_1]**",
        "sent to <<UPI_1>>",
        "भेज दिया [यूपीआई_1]",
        "भेज दिया यूपीआई_१",
    ],
)
def test_restore_tolerates_rewrites(reply):
    p = Parda()
    p.redact("refund asha.k@okicici")
    res = p.restore(reply)
    assert "asha.k@okicici" in res.text
    assert res.restored == 1


def test_unknown_index_is_reported_not_filled():
    p = Parda()
    p.redact("refund asha.k@okicici")
    res = p.restore("also check [UPI_2]")
    assert res.restored == 0
    assert res.unknown == ["[UPI_2]"]
    assert "[UPI_2]" in res.text


def test_words_that_merely_contain_labels_are_untouched():
    p = Parda()
    p.redact("call 9876543210")
    assert p.restore("SMARTPHONE_1 is a product code").text == "SMARTPHONE_1 is a product code"


def test_styles():
    for style, expected in [("angle", "<<PAN_1>>"), ("bare", "PAN_1")]:
        p = Parda(style=style)
        assert p.redact("PAN ABCPE1234F").text == f"PAN {expected}"
        assert p.restore(f"ok {expected}").text == "ok ABCPE1234F"
    with pytest.raises(ValueError):
        Parda(style="emoji")


def test_redacted_text_has_no_leaks():
    p = Parda()
    red = p.redact("PAN ABCPE1234F, call nau aath saat chhe paanch chaar teen do ek shunya")
    assert p.leaks(red.text) == []
    assert red.text == "PAN [PAN_1], call [PHONE_1]"
