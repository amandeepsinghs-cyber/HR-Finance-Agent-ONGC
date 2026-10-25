import datetime
import uuid
import time
import os
from typing import Any, Dict, List, Optional
from app.brain.rbac import persona_class
from app.config import GCP_PROJECT, EXPORTS_DIR
from app.auth import PERSONA_DIRECTORY
from app.export_audit import register_artifact, write_export_audit, build_export_filename

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
    active_cohort = session_state.get_active_cohort() or {}
    rows = active_cohort.get("rows") or tbl.get("rows") or []
    
    active_cohort = session_state.get_active_cohort() or {}
    is_cohort_c0 = active_cohort.get("cohort_id") == "C0" or not active_cohort.get("definition_id")
    
    n_exec = active_cohort.get("row_count") or len([r for r in rows if str(r.get('grade', '')).startswith('E')])
    n_nonexec = active_cohort.get("all_cadres_count", 645) - n_exec if active_cohort else len(rows) - n_exec
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
            "access": {"status": "refused", "reason": "R-FUNC", "code": "R-FUNC"},
            "visual": {"type": "refusal", "mode": "replace"}
        }
        
    if is_cohort_c0 and "cohort" not in query.lower():
        # Ask which group the email should cover
        return {
            "contract_version": 2,
            "turn_id": turn_id,
            "language": language,
            "display_text": "Which group should the email cover?",
            "spoken_summary": "Which group should the email cover?",
            "chips": ["Delhi > 5 yrs", "Mumbai > 5 yrs"],
            "access": {"status": "allowed"},
            "visual": {"type": "clarification"}
        }
        
    is_aggregate = not is_admin and (persona == "DIR_FIN" or persona.startswith("E"))
    
    my_info = PERSONA_DIRECTORY.get(persona, {})
    my_name = my_info.get("display_name", persona)
    my_desig = my_info.get("designation", "")
    from_info = {"name": f"{my_name}, {my_desig}" if my_desig else my_name, "email": my_info.get("email", f"{persona.lower()}@ongc.example")}
    
    to_info = [{"name": "Director (HR)", "email": "director.hr@ongc.example"}]
    chips = []
    
    if persona == "DIR_HR":
        to_info = []
        chips = ["CMD", "Transfer Board"]
        
    as_of = datetime.date.today().strftime('%Y-%m-%d')
    as_of_30 = (datetime.date.today() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    
    count_table = "| Level | Count |\n|---|---|"
    
    level_rows = active_cohort.get("level_rows")
    if level_rows:
        for r in level_rows:
            count_table += f"\n| {r.get('grade')} | {r.get('headcount')} |"
    else:
        levels = {}
        for r in rows:
            g = str(r.get('grade', 'UNKNOWN'))
            headcount = r.get("headcount", 1)
            if g.startswith('E') or 'headcount' in r:
                levels[g] = levels.get(g, 0) + headcount
        for k in sorted(levels.keys()):
            count_table += f"\n| {k} | {levels[k]} |"
            
    count_table += f"\n| **Total** | **{n_exec}** |"
    
    attachment_note = ""
    if is_aggregate:
        attachment_note = "Counts only; the named list is available to Director (HR)."
    else:
        attachment_note = f"The full list ({len(rows)} rows: name, designation, level, tenure in Delhi) is attached."
        
    # Apply to template
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    if language == "hi":
        tmpl_path = os.path.join(templates_dir, "email_transfer_review_hi.md")
    else:
        tmpl_path = os.path.join(templates_dir, "email_transfer_review.md")
        
    with open(tmpl_path, "r", encoding="utf-8") as f:
        body_md = f.read()
        
    body_md = body_md.replace("{{ n_exec }}", str(n_exec))
    body_md = body_md.replace("{{ n_nonexec }}", str(n_nonexec))
    body_md = body_md.replace("{{ as_of }}", str(as_of))
    body_md = body_md.replace("{{ count_table }}", str(count_table))
    body_md = body_md.replace("{{ n_exempt }}", str(n_exempt))
    body_md = body_md.replace("{{ horizon_days }}", "30")
    body_md = body_md.replace("{{ as_of_30 }}", str(as_of_30))
    body_md = body_md.replace("{{ attachment_note }}", str(attachment_note))
    body_md = body_md.replace("{{ sender_name }}", str(my_name))
    body_md = body_md.replace("{{ persona }}", str(persona))
    
    display_text = "Drafted the email. Please review it on screen."
    spoken_summary = "I have drafted the email. You can review and edit the fields on screen."
    if persona == "DIR_HR":
        display_text = "Who should this go to?"
        spoken_summary = "Who should this go to?"
        
    # Check if artifact exists in session cohort
    from app.tools.export_tool import DocumentExporter
    import time
    export_id = f"exp_{uuid.uuid4().hex}"
    filename = build_export_filename("delhi_gt5y_roster", "WC-DEL".lower(), "asof-20261019", persona.lower(), "xlsx", is_aggregate=is_aggregate)
    
    exporter = DocumentExporter()
    disk_filename = f"{export_id}.xlsx"
    file_path = exporter.export_xlsx(
        rows=rows,
        filename=disk_filename,
        persona=persona,
        masked=is_aggregate
    )
    
    rec = register_artifact(
        export_id=export_id,
        disk_path=EXPORTS_DIR / disk_filename,
        kind="xlsx",
        filename=filename,
        rows=len(rows),
        columns=list(rows[0].keys()) if rows else [],
        
        masked=is_aggregate,
        is_aggregate=is_aggregate,
        emp_id=PERSONA_DIRECTORY.get(persona, {}).get("emp_id", "EMP-000000"),
        persona=persona,
        session_id=getattr(session_state, "session_id", "test-session"),
        turn_id=turn_id
    )
    
    write_export_audit(
        emp_id=PERSONA_DIRECTORY.get(persona, {}).get("emp_id", "EMP-000000"),
        persona=persona,
        session_id=getattr(session_state, "session_id", "test-session"),
        turn_id=turn_id,
        fmt="xlsx",
        filename=filename,
        sha256=rec.sha256,
        rows=len(rows),
        columns=list(rows[0].keys()) if rows else [],
        data_classes=["general"],
        masked=is_aggregate,
        delivery="download",
        
        client_ip="test"
    )
    
    artifacts = [{
        "export_id": export_id,
        "kind": "xlsx",
        "filename": filename,
        "url": f"/api/export/{export_id}",
        "rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "masked": is_aggregate,
        "created_at": rec.created_at,
        "expires_at": rec.expires_at,
        "sha256": rec.sha256
    }]
    
    return {
        "contract_version": 2,
        "turn_id": turn_id,
        "language": language,
        "display_text": display_text,
        "spoken_summary": spoken_summary,
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
