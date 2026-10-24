from app.brain.grounding import check_numeric_grounding

def test_grounding_accepts_allowed():
    text = "Revenue was 15280.5 crore in FY24."
    allowed = {15280.5}
    res, dropped = check_numeric_grounding(text, allowed)
    assert not dropped
    assert "15280.5" in res

def test_grounding_drops_unallowed():
    text = "Revenue was 15280.5 crore in FY24. But profit was 3000 crore."
    allowed = {15280.5}
    res, dropped = check_numeric_grounding(text, allowed, "Fallback.")
    assert len(dropped) == 1
    assert "3000" in dropped[0]
    assert "Revenue" in res
    assert "profit" not in res

def test_grounding_fallback_on_multiple_drops():
    text = "Revenue was 15280.5. Profit was 3000. Tax was 500."
    allowed = {15280.5}
    res, dropped = check_numeric_grounding(text, allowed, "Fallback text.")
    assert len(dropped) == 2
    assert res == "Fallback text."

def test_grounding_quotes():
    text = 'Revenue dropped. "We saw a 5000 cr impact" [AR FY26 p.98].'
    allowed = set()
    res, dropped = check_numeric_grounding(text, allowed, "Fallback text.")
    assert not dropped
    assert "5000" in res

