from typing import Dict, Any
import time
from typing import Optional
import re

def handle_greeting(query: str, session_state: Any, norm_persona: str, det_lang: str, turn_id: str, t0: float) -> Optional[Dict[str, Any]]:
    q_clean = query.strip().lower().rstrip("?!.")
    greeting_exact = {"hi", "hello", "hey", "yo", "namaste", "pranam", "sup", "yukti", "test"}
    is_hindi_cap_q = any(w in q_clean for w in ["hindi ati hai", "hindi aati hai", "hindi me", "hindi mein"])
    is_who_q = bool(re.search(r"who are you\b|what are you\b|who is this\b|tell me about yourself", q_clean))
    is_cap_q = "what can you do" in q_clean or "help" in q_clean
    is_greeting = (
        is_hindi_cap_q
        or is_who_q
        or is_cap_q
        or q_clean in greeting_exact
        or (len(q_clean.split()) <= 3 and any(w in q_clean.split() for w in ["hi", "hello", "hey", "yo", "namaste", "thanks", "test", "नमस्ते"]))
    )
    
    if not is_greeting:
        return None
        
    role_title = {
        "CMD": "Arun",
        "DIR_HR": "Director HR",
        "DIR_FIN": "Director Finance",
        "E1_HR": "Officer",
        "E2_HR": "Manager",
        "E3_HR": "Chief Manager",
        "E1_FIN": "Officer",
        "E2_FIN": "Manager",
    }.get(norm_persona, norm_persona)

    coverage_text = ""
    try:
        from app.coverage.manifest import get_manifest
        manifest = get_manifest()
        coverage_text = manifest.get_summary_text(lang=det_lang)
    except Exception:
        coverage_text = "I can analyze workforce tenure and vacancies across all work centres, track field-level P&L and lifting costs, run Brent crude what-if simulations, and draft Board Notes or Parliament replies."

    if is_hindi_cap_q:
        spoken_conv = f"हाँ {role_title}, मैं हिंदी में बात कर सकती हूँ और आपकी मदद कर सकती हूँ।"
    elif det_lang == "hi":
        spoken_conv = f"नमस्ते {role_title}। मैं युक्ति हूँ, आपकी एचआर और वित्त मुख्य सलाहकार। {coverage_text}"
    elif det_lang == "hi-en":
        spoken_conv = f"Namaste {role_title}! Main Yukti hoon, aapki HR aur Finance Chief of Staff. {coverage_text}"
    elif is_who_q or is_cap_q:
        spoken_conv = f"I am Yukti, your executive HR and Finance intelligence partner at ONGC. {coverage_text}"
    elif "thank" in q_clean or q_clean in ("ok", "okay", "great"):
        spoken_conv = f"Glad to help, {role_title}. Let me know what we should examine next."
    else:
        spoken_conv = f"Hello {role_title}, I'm right here with you. {coverage_text}"

    contract = {
        "turn_id": turn_id,
        "language": det_lang,
        "persona": norm_persona,
        "spoken_summary": spoken_conv,
        "display_text": spoken_conv,
        "visual": {"type": "none", "mode": "replace"},
        "insights": [],
        "sources": [],
        "suggestions": ["What can you do?", "Show me the balance sheet", "How many employees in Delhi?"],
        "access": {"status": "allowed"},
        "export_options": [],
        "status_events": ["Conversational greeting"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
    return contract
