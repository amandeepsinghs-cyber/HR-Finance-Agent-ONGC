from app.intents.confirm import detect_confirm_intent

def test_detect_confirm():
    assert detect_confirm_intent("yes, run it") == "confirm"
    assert detect_confirm_intent("haan, chalao") == "confirm"
    assert detect_confirm_intent("proceed") == "confirm"
    
    assert detect_confirm_intent("no, cancel") == "cancel"
    assert detect_confirm_intent("stop") == "cancel"
    assert detect_confirm_intent("mat karo") == "cancel"
    
    assert detect_confirm_intent("I want to edit") == "edit"
    assert detect_confirm_intent("change the inputs") == "edit"
    
    assert detect_confirm_intent("what is dcf") is None
