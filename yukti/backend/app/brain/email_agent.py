import datetime
import uuid
import time
from typing import Any, Dict, List, Optional
from app.brain.rbac import persona_class
from app.config import GCP_PROJECT

def build_email_draft(
    query: str,
    session_state: Any,
    persona: str,
    turn_id: str,
    language: str
) -> Dict[str, Any]:
    
    # 1. extract cohort stats
    last_turn = session_state.turns[-1] if getattr(session_state, "turns", []) else {}
    last_vis = (last_turn.get("visual") or {}) if isinstance(last_turn, dict) else {}
    tbl = last_vis.get("table") or {}
    rows = session_state.last_rows or tbl.get("rows") or []
    
    n_exec = len([r for r in rows if str(r.get('grade', '')).startswith('E')]) if rows else 0
    n_nonexec = len(rows) - n_exec if rows else 0
    n_exempt = len([r for r in rows if r.get('exemption_tag')]) if rows else 0
    
    p_cls = persona_class(persona)
    is_admin = p_cls == "admin"
    is_junior = persona.startswith("E")
    
    if is_junior and "FIN" in persona:
        return {
            "contract_version": 2,
            "turn_id": turn_id,
            "language": language,
            "display_text": "Transfer reviews are raised by HR. I can prepare the counts table for you to share with HR.",
            "spoken_summary": "Transfer reviews are raised by HR. I can prepare the counts table for you to share with HR.",
            "chips": [{"text": "Prepare counts table", "action": "prepare_counts_table"}],
            "access": {"status": "refused", "reason": "R-FUNC"}
        }
        
    is_aggregate = not is_admin and (persona == "DIR_FIN" or persona.startswith("E"))
    
    from_info = {"name": f"ONGC {persona}", "email": f"{persona.lower()}@ongc.example"}
    to_info = [{"name": "Director (HR)", "email": "director.hr@ongc.example"}]
    
    chips = []
    if persona == "DIR_HR":
        chips = ["CMD", "Transfer Board"]
        
    as_of = datetime.date.today().strftime('%Y-%m-%d')
    as_of_30 = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    
    count_table = "| Level | Count |\n|---|---|"
    levels = {}
    for r in rows:
        g = str(r.get('grade', 'UNKNOWN'))
        if g.startswith('E'):
            levels[g] = levels.get(g, 0) + 1
    for k in sorted(levels.keys()):
        count_table += f"\n| {k} | {levels[k]} |"
    count_table += f"\n| **Total** | **{n_exec}** |"
    
    attachment_note = ""
    if is_aggregate:
        attachment_note = "Counts only; the named list is available to Director (HR)."
    else:
        attachment_note = f"The full list ({len(rows)} rows: name, designation, level, tenure in Delhi) is attached."
        
    # Apply to template
    body_md = f"As discussed, our records show **{n_exec} executives** (and {n_nonexec} non-executive staff) posted at Delhi (WC-DEL) continuously for more than five years as of {as_of}.\n\n{count_table}\n\nof which {n_exempt} carry a recorded exemption.\n\nPolicy basis: JRTP Rev 4 clause 3.2 (Illustrative) and J-03 Delhi HC 2018 ONGC v. B.V. Srihari Rao.\n\nPlease have the Transfer Board review this cohort for the next rotation cycle and advise on exemptions by {as_of_30}.\n\n{attachment_note}\n\n{persona}\nSent via Yukti (draft — please review before sending)\nData: synthetic employee records calibrated to ONGC AR FY26 (Illustrative)"
    
    # Check if artifact exists in session cohort
    # We can just generate it unconditionally for robustness
    from app.tools.export_tool import DocumentExporter
    import time
    export_id = f"exp_{uuid.uuid4().hex}"
    filename = f"yukti_delhi_tenure_export_{persona}_{time.strftime('%Y%m%d-%H%M')}"
    if is_aggregate:
        filename += "_aggregate"
    filename += ".xlsx"
    exporter = DocumentExporter()
    file_path = exporter.export_xlsx(
        rows=rows,
        filename=filename,
        persona=persona,
        masked=is_aggregate
    )
    
    artifacts = [{
        "export_id": export_id,
        "kind": "xlsx",
        "filename": filename,
        "url": f"/api/export/{export_id}",
        "rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "masked": is_aggregate,
        "created_at": time.time(),
        "expires_at": time.time() + 86400,
        "sha256": "dummy"
    }]
    
    return {
        "contract_version": 2,
        "turn_id": turn_id,
        "language": language,
        "display_text": "Drafted the email. Please review it on screen.",
        "spoken_summary": "I have drafted the email to Director HR. You can review and edit the fields on screen.",
        "visual": {
            "type": "email_draft",
            "mode": "replace",
            "email_draft": {
                "from": from_info,
                "to": to_info,
                "cc": [],
                "subject": f"Review requested: {n_exec} executives at Delhi beyond 5 years' continuous stay (as of {as_of})",
                "body_md": body_md,
                "attachments": [export_id] if not is_aggregate else [],
                "citations": [
                    "JRTP Rev 4 clause 3.2 (Illustrative)",
                    "Delhi HC 2018 ONGC v. B.V. Srihari Rao"
                ],
                "editable": True
            }
        },
        "artifacts": artifacts,
        "chips": chips,
        "access": {"status": "allowed"}
    }
