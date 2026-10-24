import pytest
from app.agents.router import IntentRouter
from app.agents.registry import get_registry

# Mock embedding for test speed / deterministic
def mock_get_embedding(self, text: str):
    t = text.lower()
    if "dcf" in t or "value" in t or "मूल्यांकन" in t: return [1.0, 0, 0, 0, 0]
    if "transfer" in t or "relocate" in t or "ट्रांसफर" in t or "postings" in t: return [0, 1.0, 0, 0, 0]
    if "export" in t or "pdf" in t or "excel" in t or "डाउनलोड" in t or "xlsx" in t: return [0, 0, 1.0, 0, 0]
    if "drop" in t or "why" in t or "diagnose" in t or "गिरा" in t or "bridge" in t: return [0, 0, 0, 1.0, 0]
    return [0, 0, 0, 0, 1.0]

def test_router_accuracy():
    router = IntentRouter(get_registry())
    router._get_embedding = mock_get_embedding.__get__(router)
    router._llm_fallback = lambda q: "analyst"
    
    cases = [
        # DCF (10)
        ("run dcf", "dcf_agent"),
        ("what is the intrinsic value", "dcf_agent"),
        ("is ONGC undervalued", "dcf_agent"),
        ("discounted cash flow model", "dcf_agent"),
        ("dcf run karo", "dcf_agent"),
        ("can you run a discounted cash flow", "dcf_agent"),
        ("evaluate the intrinsic value", "dcf_agent"),
        ("show me dcf", "dcf_agent"),
        ("is it overvalued", "dcf_agent"),
        ("कंपनी का मूल्यांकन क्या है", "dcf_agent"),
        
        # Transfer (10)
        ("transfer employee 123", "hr_transfer_agent"),
        ("relocate john doe", "hr_transfer_agent"),
        ("postings for next year", "hr_transfer_agent"),
        ("initiate a transfer", "hr_transfer_agent"),
        ("relocation options", "hr_transfer_agent"),
        ("hr transfer karo", "hr_transfer_agent"),
        ("mera transfer kahan hoga", "hr_transfer_agent"),
        ("i want to transfer", "hr_transfer_agent"),
        ("relocate me", "hr_transfer_agent"),
        ("मुझे ट्रांसफर करना है", "hr_transfer_agent"),
        
        # Export (10)
        ("export this to excel", "doc_export_agent"),
        ("download pdf", "doc_export_agent"),
        ("generate xlsx", "doc_export_agent"),
        ("export report", "doc_export_agent"),
        ("i need a pdf", "doc_export_agent"),
        ("is report ko excel mein export karo", "doc_export_agent"),
        ("pdf डाउनलोड करो", "doc_export_agent"),
        ("create an xlsx", "doc_export_agent"),
        ("give me pdf", "doc_export_agent"),
        ("export data", "doc_export_agent"),
        
        # Diagnostics (5)
        ("why did PBT drop in FY24", "fin_diagnostics_agent"),
        ("diagnose the drop", "fin_diagnostics_agent"),
        ("show me the bridge", "fin_diagnostics_agent"),
        ("profit क्यों गिरा", "fin_diagnostics_agent"),
        ("why did profit drop", "fin_diagnostics_agent"),
        
        # Analyst (5)
        ("show balance sheet for 2024", "analyst"),
        ("what is my salary", "analyst"),
        ("meri salary kya hai", "analyst"),
        ("balance sheet dikhao", "analyst"),
        ("profit and loss", "analyst")
    ]
    
    correct = 0
    for query, expected in cases:
        ans = router.route(query)
        if ans == expected:
            correct += 1
            
    assert correct / len(cases) >= 0.95
