from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional


def handle_ui_control(
    query: str,
    session_state: Any,
    norm_persona: str,
    det_lang: str,
    turn_id: str,
    t0: float,
    sc_intent: Dict[str, Any],
) -> Dict[str, Any]:
    from app.auth import PERSONA_DIRECTORY
    from app.tools.chart_rules import build_chart_spec

    cmd = sc_intent.get("command")
    val = sc_intent.get("value")

    if cmd == "set_persona":
        from app.answer_composer import render_refusal_copy

        info = PERSONA_DIRECTORY.get(
            norm_persona,
            {
                "emp_id": "",
                "display_name": norm_persona,
                "designation": norm_persona,
                "function": "",
                "grade": "",
            },
        )
        rc_role = render_refusal_copy(
            "R-ROLE",
            lang=det_lang,
            persona=norm_persona,
            display_name=info["display_name"],
            designation=info["designation"],
        )
        text = rc_role["text"]
        return {
            "turn_id": turn_id,
            "language": det_lang,
            "persona": norm_persona,
            "spoken_summary": text,
            "display_text": text,
            "visual": {"type": "none", "mode": "replace"},
            "insights": [],
            "sources": [{"kind": "policy", "title": "SPEC-06 §4.4 (R-ROLE)"}],
            "suggestions": ["What can I ask?"],
            "access": {
                "status": "refused",
                "code": "R-ROLE",
                "reason": "Access level cannot be changed from a conversation.",
                "rule_ref": "SPEC-06 §4.4 R-ROLE",
                "alternative": rc_role["alternative"],
                "alternatives": rc_role["alternatives"],
            },
            "export_options": [],
            "status_events": ["Role change from conversation refused (R-ROLE)"],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }

    last_vis = dict(session_state.get_last_visual() or {"type": "none", "mode": "replace"})
    sc_suggestions = [
        "Plot this as a pie chart",
        "Show as a horizontal bar chart",
        "Draft a briefing note on this",
    ]
    sc_ui_action: Optional[Dict[str, str]] = {"command": str(cmd or ""), "value": str(val or "")}
    spoken_sc = ""

    if cmd == "go_home":
        last_vis = {"type": "none", "mode": "replace"}
        spoken_sc = "Returned to the Yukti home screen."
    elif cmd == "set_theme":
        spoken_sc = f"Switched the display to {val} mode."
    elif cmd == "set_language":
        det_lang = val if val in ("en", "hi", "hi-en") else "en"
        session_state.language = det_lang
        spoken_sc = f"Switched language to {det_lang}."
    elif cmd == "set_panel_mode":
        spoken_sc = f"Adjusted the conversation panel to {val}."
    elif cmd == "set_chart_kind":
        from app.brain.bridge import (
            BridgeError,
            BridgeOk,
            bridge,
            bridge_class_of,
            no_visual_copy,
            non_bridge_data_copy,
            replot_success_copy,
            single_value_error,
            which_year_copy,
        )
        from app.semantic.normalize import resolve_fy

        tbl = last_vis.get("table") or {}
        cols = tbl.get("columns") or session_state.last_columns or []
        rows = session_state.last_rows or tbl.get("rows") or []
        if not rows and last_vis.get("chart") and isinstance(last_vis["chart"].get("data"), list):
            rows = last_vis["chart"]["data"]
            cols = list(rows[0].keys()) if rows else []

        existing_chart = last_vis.get("chart") if isinstance(last_vis.get("chart"), dict) else None
        has_typed_wf = bool(
            existing_chart
            and existing_chart.get("kind") == "waterfall"
            and isinstance(existing_chart.get("data"), list)
            and existing_chart["data"]
            and all(isinstance(r, dict) and r.get("type") in ("total", "delta") for r in existing_chart["data"])
        )
        rows_are_typed_wf = bool(
            rows and all(isinstance(r, dict) and r.get("type") in ("total", "delta") for r in rows)
        )

        stmt_dict = last_vis.get("statement") if isinstance(last_vis.get("statement"), dict) else None
        stmt_periods = [str(p) for p in (stmt_dict.get("periods") or []) if p] if stmt_dict else []
        flat_stmt_rows = (
            [
                r
                for s in (stmt_dict.get("sections") or [])
                if isinstance(s, dict)
                for r in (s.get("rows") or [])
                if isinstance(r, dict)
            ]
            if stmt_dict
            else []
        )
        candidate_stmt_rows = flat_stmt_rows or [r for r in rows if isinstance(r, dict)]
        is_pnl_stmt_vis = bool(
            (stmt_dict and stmt_dict.get("statement") == "pnl")
            or any(bridge_class_of(r.get("line_code")) == "start" for r in candidate_stmt_rows)
            or (
                not has_typed_wf
                and any(bridge_class_of(r.get("line_code")) is not None for r in candidate_stmt_rows)
            )
        )
        is_other_stmt_vis = bool(
            not is_pnl_stmt_vis
            and (
                last_vis.get("type") == "statement"
                or stmt_dict is not None
                or ("line_code" in cols)
                or any(isinstance(r, dict) and r.get("line_code") for r in rows)
            )
        )

        fy_res = resolve_fy(query)
        req_fy = fy_res.get("fy") if isinstance(fy_res, dict) and fy_res.get("fy") else (fy_res if isinstance(fy_res, str) else None)
        if (
            req_fy is None
            and len(stmt_periods) == 2
            and getattr(session_state, "spec_history", None)
            and isinstance(session_state.spec_history[-1], dict)
        ):
            last_p = session_state.spec_history[-1].get("period") or {}
            if isinstance(last_p, dict) and last_p.get("fy") and not last_p.get("from"):
                req_fy = str(last_p["fy"]).upper()

        multi_fy_list: List[str] = []
        if len(stmt_periods) > 1:
            multi_fy_list = stmt_periods
        elif len(rows) > 1 and not is_pnl_stmt_vis:
            fy_col = next((c for c in cols if str(c).lower() in ("fiscal_year", "fy", "financial_year")), None)
            has_fin_cols = any(
                re.search(r"revenue|pbt|pat|ebitda|income|expense|profit|margin|assets|cash", str(c), re.I)
                for c in cols
            )
            if fy_col and has_fin_cols:
                seen_fys: List[str] = []
                for r in rows:
                    if isinstance(r, dict) and r.get(fy_col):
                        fy_v = str(r[fy_col])
                        if fy_v not in seen_fys:
                            seen_fys.append(fy_v)
                if len(seen_fys) > 1:
                    multi_fy_list = sorted(seen_fys, reverse=True)

        if val == "table":
            if isinstance(last_vis.get("statement"), dict):
                last_vis["type"] = "statement"
                last_vis["mode"] = "refine"
            elif isinstance(last_vis.get("table"), dict) and last_vis["table"].get("rows"):
                last_vis["type"] = "table"
                last_vis["mode"] = "refine"
            elif rows:
                last_vis["type"] = "table"
                last_vis["mode"] = "refine"
                last_vis["table"] = {"columns": cols, "rows": rows[:50]}
        elif val == "waterfall":
            if len(multi_fy_list) > 1 and (not req_fy or not is_pnl_stmt_vis):
                spoken_sc = which_year_copy(multi_fy_list, lang=det_lang)
                sc_suggestions = [f"Show {p} P&L as a waterfall" for p in multi_fy_list[:3]]
                sc_ui_action = None
            elif is_pnl_stmt_vis:
                stmt_source = stmt_dict if stmt_dict is not None else rows
                selected_period = req_fy or (stmt_periods[0] if len(stmt_periods) == 1 else None)
                if selected_period is None:
                    row_fys = {str(r.get("fiscal_year")) for r in candidate_stmt_rows if r.get("fiscal_year")}
                    if len(row_fys) == 1:
                        selected_period = next(iter(row_fys))
                if selected_period is None:
                    if getattr(session_state, "spec_history", None) and isinstance(session_state.spec_history[-1], dict):
                        p_obj = session_state.spec_history[-1].get("period") or {}
                        if isinstance(p_obj, dict) and p_obj.get("fy"):
                            selected_period = str(p_obj["fy"]).upper()
                    if selected_period is None:
                        fy_m = re.search(
                            r"\b(FY\d{2})\b",
                            f"{last_vis.get('title') or ''} {last_vis.get('subtitle') or ''} {json.dumps(last_vis.get('kpis') or [])}",
                            re.I,
                        )
                        if fy_m:
                            selected_period = fy_m.group(1).upper()
                b_res = bridge(stmt_source, period=selected_period)
                if isinstance(b_res, BridgeOk):
                    last_vis["type"] = "chart"
                    last_vis["mode"] = "refine"
                    last_vis["chart"] = b_res.to_chart_spec()
                    spoken_sc = b_res.spoken_summary(lang=det_lang)
                else:
                    spoken_sc = b_res.message(lang=det_lang)
                    sc_ui_action = None
            elif has_typed_wf:
                last_vis["type"] = "chart"
                last_vis["mode"] = "refine"
            elif is_other_stmt_vis:
                stmt_source = stmt_dict if stmt_dict is not None else rows
                selected_period = req_fy or (stmt_periods[0] if len(stmt_periods) == 1 else None)
                b_res = bridge(stmt_source, period=selected_period)
                spoken_sc = b_res.message(lang=det_lang) if isinstance(b_res, BridgeError) else single_value_error().message(lang=det_lang)
                sc_ui_action = None
            elif len(rows) <= 1 or last_vis.get("type") in ("kpi", "none"):
                b_err = single_value_error()
                spoken_sc = b_err.message(lang=det_lang)
                ent_name = None
                for ek in ("wc_name", "asset_name", "field_name"):
                    if session_state.active_entities.get(ek):
                        ent_name = str(session_state.active_entities[ek])
                        break
                if not ent_name:
                    vis_title = str(last_vis.get("title") or "")
                    if ":" in vis_title:
                        cand = vis_title.split(":", 1)[0].strip()
                        cand = re.sub(r"\s+Asset$", "", cand, flags=re.I).strip()
                        if cand:
                            ent_name = cand
                sug = b_err.suggestion(lang=det_lang, entity=ent_name)
                if sug:
                    sc_suggestions = [sug] + sc_suggestions[:2]
                sc_ui_action = None
            elif rows_are_typed_wf and cols:
                last_vis["type"] = "chart"
                last_vis["mode"] = "refine"
                last_vis["chart"] = build_chart_spec(
                    kind=val,
                    columns=cols,
                    rows=rows,
                    title=last_vis.get("title", "Updated Chart View"),
                )
            else:
                cur_kind = (
                    existing_chart.get("kind")
                    if (last_vis.get("type") == "chart" and existing_chart and existing_chart.get("kind"))
                    else str(last_vis.get("type") or "table")
                )
                spoken_sc = non_bridge_data_copy(str(cur_kind), lang=det_lang)
                sc_ui_action = None
        elif existing_chart and existing_chart.get("kind") == val and existing_chart.get("data"):
            last_vis["type"] = "chart"
            last_vis["mode"] = "refine"
        elif rows and cols:
            last_vis["type"] = "chart"
            last_vis["mode"] = "refine"
            last_vis["chart"] = build_chart_spec(
                kind=val,
                columns=cols,
                rows=rows,
                title=last_vis.get("title", "Updated Chart View"),
            )
            if not last_vis.get("table"):
                last_vis["table"] = {"columns": cols, "rows": rows[:30]}

        if val == "table":
            visual_ok = last_vis.get("type") in ("table", "statement") and bool(
                (last_vis.get("table") or {}).get("rows") or last_vis.get("statement")
            )
        else:
            visual_ok = (
                sc_ui_action is not None
                and last_vis.get("type") == "chart"
                and isinstance(last_vis.get("chart"), dict)
                and bool(last_vis["chart"].get("data"))
            )

        if not visual_ok:
            sc_ui_action = None
            if not spoken_sc:
                spoken_sc = no_visual_copy(val, lang=det_lang)
        elif not spoken_sc:
            spoken_sc = replot_success_copy(val, lang=det_lang)
    elif cmd == "export":
        spoken_sc = f"Exporting the current view to {str(val or '').upper()}."
    elif cmd == "navigate_history":
        restored = session_state.restore_cohort(query)
        if restored and isinstance(restored.get("visual"), dict):
            last_vis = dict(restored["visual"])
            last_vis["mode"] = "restore"
            spoken_sc = (
                f"Restored the parent cohort ({restored.get('cohort_id', 'C0')}: "
                f"{restored.get('row_count', 0):,} employees) on screen."
            )
        else:
            if len(session_state.visual_history) >= 2:
                last_vis = dict(session_state.visual_history[-2])
            last_vis["mode"] = "restore"
            spoken_sc = "Restored the previous visual on screen."
    else:
        spoken_sc = f"Applied screen command {cmd}."

    sc_contract: Dict[str, Any] = {
        "turn_id": turn_id,
        "language": det_lang,
        "persona": norm_persona,
        "spoken_summary": spoken_sc,
        "display_text": spoken_sc,
        "visual": last_vis,
        "insights": [f"Visual mode updated to {val}" if sc_ui_action else "Visual unchanged"],
        "sources": [{"kind": "data", "object": "hrfin_gold", "sql": session_state.last_sql or ""}],
        "suggestions": sc_suggestions,
        "access": {"status": "allowed"},
        "export_options": ["pdf", "xlsx", "sheets"],
        "status_events": [spoken_sc],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
    if sc_ui_action is not None:
        sc_contract["ui_action"] = sc_ui_action
    return sc_contract
