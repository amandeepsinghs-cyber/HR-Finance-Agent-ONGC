import asyncio
from datetime import datetime, timezone
import uuid
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, List

from app.jobs.store import get_job_store
from app.jobs.events import get_event_broker
from app.session_memory import get_session_manager

logger = logging.getLogger(__name__)

AgentRunnerFn = Callable[[str, Dict[str, Any], str, Callable[[str, str, float], Awaitable[None]]], Awaitable[Dict[str, Any]]]
WsNotifierFn = Callable[[str, Dict[str, Any]], Awaitable[None]]


class JobExecutor:
    def __init__(self):
        self.store = get_job_store()
        self.broker = get_event_broker()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._agent_runners: Dict[str, AgentRunnerFn] = {}
        self._ws_notifiers: List[WsNotifierFn] = []
        self.max_jobs_per_instance = 8
        self.max_jobs_per_session = 2
        self.job_timeout = 120
        self.step_delay_sec = 0.05
        self._sweep_stale_jobs()

    def register_agent_runner(self, agent_id: str, runner: AgentRunnerFn) -> None:
        self._agent_runners[agent_id] = runner

    def register_ws_notifier(self, notifier: WsNotifierFn) -> None:
        if notifier not in self._ws_notifiers:
            self._ws_notifiers.append(notifier)

    async def _notify_ws(self, session_id: str, job: Optional[Dict[str, Any]]) -> None:
        if not job:
            return
        for fn in list(self._ws_notifiers):
            try:
                await fn(session_id, {"type": "job_update", "job": job})
            except Exception as exc:
                logger.debug("WS notifier error for session %s: %s", session_id, exc)

    def _sweep_stale_jobs(self):
        try:
            active_jobs = self.store.get_active_jobs()
            for job in active_jobs:
                if job.get("status") == "running" and job["id"] not in self._running_tasks:
                    logger.info(f"Sweeping stale job {job['id']}")
                    self._mark_failed(job["id"], "E_INSTANCE_LOST", "Please run again")
        except Exception as e:
            logger.error(f"Error sweeping stale jobs: {e}")

    def _mark_failed(self, job_id: str, code: str, message: str):
        updates = {
            "status": "failed",
            "error": {"code": code, "message": message},
            "finished_at": datetime.now(timezone.utc).isoformat()
        }
        self.store.update_job(job_id, updates)
        job = self.store.get_job(job_id)
        self.broker.publish(job_id, "job.failed", {"job": job})

    def cancel_job(self, job_id: str):
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
        updates = {
            "status": "cancelled",
            "finished_at": datetime.now(timezone.utc).isoformat()
        }
        self.store.update_job(job_id, updates)
        job = self.store.get_job(job_id)
        self.broker.publish(job_id, "job.cancelled", {"job": job})

    async def submit_job(self, proposed_action: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        proposed_action_id = proposed_action.get("id")

        # Idempotency check on proposed_action_id
        session_jobs = self.store.list_jobs(session_id)
        for j in session_jobs:
            if j.get("proposed_action_id") == proposed_action_id and j.get("status") not in ("failed", "cancelled", "expired"):
                return j

        job_id = f"job_{uuid.uuid4().hex}"

        # Check session limit
        active_in_session = sum(1 for j in session_jobs if j.get("status") in ("queued", "running"))
        if active_in_session >= self.max_jobs_per_session:
            raise ValueError(f"Limit of {self.max_jobs_per_session} concurrent jobs per session reached")

        # Check instance limit
        if len(self._running_tasks) >= self.max_jobs_per_instance:
            raise ValueError(f"Limit of {self.max_jobs_per_instance} concurrent jobs per instance reached")

        agent_id = proposed_action.get("agent")
        steps_list = proposed_action.get("steps") or (
            ["load_inputs", "wacc_build", "forecast", "valuation", "sensitivity_grid", "tornado", "xlsx", "publish"]
            if agent_id == "dcf_agent"
            else ["prepare", "execute", "publish"]
        )
        initial_steps = [
            {"id": s, "label": s.replace("_", " ").title(), "status": "pending"}
            for s in steps_list
        ]

        job = {
            "id": job_id,
            "proposed_action_id": proposed_action_id,
            "session_id": session_id,
            "owner_persona": proposed_action.get("owner_persona"),
            "owner_emp_id": proposed_action.get("owner_emp_id"),
            "agent": agent_id,
            "status": "queued",
            "progress": 0.0,
            "steps": initial_steps,
            "artifacts": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.store.create_job(job)
        self.broker.publish(job_id, "job.queued", {"job": job})

        task = asyncio.create_task(self._run_job_with_timeout(job_id, proposed_action, session_id))
        self._running_tasks[job_id] = task
        task.add_done_callback(lambda t: self._running_tasks.pop(job_id, None))

        return job

    async def _run_job_with_timeout(self, job_id: str, proposed_action: Dict[str, Any], session_id: str):
        try:
            await asyncio.wait_for(self._run_job(job_id, proposed_action, session_id), timeout=self.job_timeout)
        except asyncio.TimeoutError:
            logger.error(f"Job {job_id} timed out")
            self._mark_failed(job_id, "E_TIMEOUT", "The background job timed out. Please try again.")
            await self._notify_ws(session_id, self.store.get_job(job_id))
        except asyncio.CancelledError:
            logger.info(f"Job {job_id} cancelled")
            updates = {
                "status": "cancelled",
                "finished_at": datetime.now(timezone.utc).isoformat()
            }
            self.store.update_job(job_id, updates)
            job = self.store.get_job(job_id)
            self.broker.publish(job_id, "job.cancelled", {"job": job})
            await self._notify_ws(session_id, job)
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self._mark_failed(job_id, "E_INTERNAL", "An internal error occurred. Please run again.")
            await self._notify_ws(session_id, self.store.get_job(job_id))

    async def _run_job(self, job_id: str, proposed_action: Dict[str, Any], session_id: str):
        updates = {"status": "running"}
        self.store.update_job(job_id, updates)
        job = self.store.get_job(job_id)
        self.broker.publish(job_id, "job.progress", {"job": job})
        await self._notify_ws(session_id, job)

        agent_id = proposed_action.get("agent")
        current_job = self.store.get_job(job_id) or {}
        job_steps = list(current_job.get("steps") or [])

        async def report_step(step_id: str, status: str, progress: float) -> None:
            now_iso = datetime.now(timezone.utc).isoformat()
            for st in job_steps:
                if st["id"] == step_id:
                    st["status"] = status
                    if status == "running" and "started_at" not in st:
                        st["started_at"] = now_iso
                    elif status in ("done", "failed", "skipped"):
                        st["ended_at"] = now_iso
            self.store.update_job(job_id, {"steps": job_steps, "progress": round(float(progress), 4)})
            snap = self.store.get_job(job_id)
            self.broker.publish(job_id, "job.step", {"step": step_id, "status": status, "job": snap})
            self.broker.publish(job_id, "job.progress", {"progress": round(float(progress), 4), "job": snap})

        if agent_id in self._agent_runners:
            result = await self._agent_runners[agent_id](job_id, proposed_action, session_id, report_step)
        elif agent_id in ("dcf_agent", "fin_diagnostics_agent", "hr_transfer_agent", "doc_export_agent"):
            for i, st in enumerate(job_steps):
                await report_step(st["id"], "running", i / max(len(job_steps), 1))
                await asyncio.sleep(self.step_delay_sec)
                if (self.store.get_job(job_id) or {}).get("status") == "cancelled":
                    raise asyncio.CancelledError()
                await report_step(st["id"], "done", (i + 1) / max(len(job_steps), 1))

            disclaimer = "Illustrative valuation, not investment advice."
            if agent_id == "dcf_agent":
                from app.agents.dcf_agent import build_dcf_assumptions_from_inputs
                from app.finance.dcf.inputs import (
                    DCFInputMissingError,
                    load_fy26_market_price_default,
                    load_fy26_wacc_default,
                )
                from app.finance.dcf.run import build_dcf_model_spec, run_dcf

                inputs = proposed_action.get("inputs") or {}
                try:
                    asm = build_dcf_assumptions_from_inputs(job_id, inputs)
                    dcf_res = run_dcf(asm)
                    _, _, wacc_meta = load_fy26_wacc_default()
                    _, _, px_meta = load_fy26_market_price_default()
                except DCFInputMissingError as exc:
                    refusal_msg = (
                        f"Cannot run the DCF valuation because required input `{exc.missing_input}` is missing or "
                        f"the FY26 cash-flow / WACC data hasn't passed verification yet. See coverage."
                    )
                    result = {
                        "contract_version": 3,
                        "turn_id": f"job:{job_id}",
                        "language": "en",
                        "spoken_summary": refusal_msg,
                        "display_text": refusal_msg,
                        "visual": {"type": "none", "mode": "replace"},
                        "access": {
                            "status": "refused",
                            "reason": "SSOT-UNVERIFIED",
                            "missing_input": exc.missing_input,
                        },
                        "sources": [],
                        "provenance": {"label": "illustrative", "detail": refusal_msg},
                    }
                else:
                    dcf_model = build_dcf_model_spec(dcf_res, asm)
                    iv = dcf_res["per_share"]["intrinsic_inr"]
                    px = dcf_res["per_share"]["market_inr"]
                    upside = dcf_res["per_share"]["upside_pct"]
                    verdict = dcf_res["per_share"]["verdict"]
                    spoken = (
                        f"The DCF valuation is ready. Intrinsic value is ₹{iv:.2f} per share against a market price of ₹{px:.2f} "
                        f"(as of {px_meta.get('date', '2026-03-30')}), so the model suggests ONGC is {verdict} by {abs(upside):.1f}%. "
                        f"{disclaimer}"
                    )
                    result = {
                        "contract_version": 3,
                        "turn_id": f"job:{job_id}",
                        "language": "en",
                        "spoken_summary": spoken,
                        "display_text": spoken,
                        "visual": {
                            "type": "dcf_model",
                            "mode": "replace",
                            "title": "ONGC Standalone DCF Valuation (Illustrative)",
                            "dcf_model": dcf_model,
                            "model_id": dcf_res.get("model_id") or f"dcf_{job_id}",
                            "as_of": dcf_res["as_of"],
                            "disclaimer": dcf_res["disclaimer"],
                            "assumptions": dcf_res["assumptions"],
                            "wacc_build": dcf_res["wacc_build"],
                            "forecast": dcf_model["forecast"],
                            "terminal": dcf_model["terminal"],
                            "bridge": dcf_res["bridge"],
                            "per_share": dcf_res["per_share"],
                            "sensitivity": dcf_res["sensitivity"],
                            "sensitivity_grid": dcf_model["sensitivity_grid"],
                            "tornado": dcf_model["tornado"],
                            "lineage_refs": dcf_res["lineage_refs"],
                        },
                        "access": {"status": "allowed"},
                        "sources": [
                            {
                                "kind": "data",
                                "object": wacc_meta.get("object", "hrfin_gold.fact_wacc_annual"),
                                "title": f"ONGC WACC SSOT FY26 ({asm.wacc_pct.value:.4f}%)",
                            },
                            {
                                "kind": "data",
                                "object": px_meta.get("source_doc", "market_prices_seed.csv"),
                                "title": f"NSE ONGC.NS Close ({px_meta.get('date', '2026-03-30')}: ₹{px:.2f})",
                            },
                        ],
                        "export_options": ["xlsx", "pdf"],
                        "caveat": disclaimer,
                        "provenance": {"label": "illustrative", "detail": disclaimer},
                    }
            else:
                spoken = "Background agent completed."
                result = {
                    "contract_version": 3,
                    "turn_id": f"job:{job_id}",
                    "language": "en",
                    "spoken_summary": spoken,
                    "display_text": spoken,
                    "visual": {
                        "type": "table",
                        "mode": "replace",
                        "title": "Agent Result",
                    },
                    "access": {"status": "allowed"},
                    "sources": [
                        {"kind": "data", "object": "hrfin_gold.fact_wacc_annual", "title": "ONGC WACC SSOT FY26"},
                    ],
                    "export_options": ["xlsx", "pdf"],
                    "caveat": disclaimer,
                    "provenance": {"label": "illustrative", "detail": disclaimer},
                }
        else:
            self._mark_failed(job_id, "E_UNKNOWN_AGENT", "Requested agent is not registered.")
            await self._notify_ws(session_id, self.store.get_job(job_id))
            return

        finished_iso = datetime.now(timezone.utc).isoformat()
        artifacts = list((result.get("job") or {}).get("artifacts") or result.get("artifacts") or [])
        job_summary_for_contract = {
            "id": job_id,
            "agent": agent_id,
            "status": "succeeded",
            "progress": 1.0,
            "steps": job_steps,
            "result_ref": f"job:{job_id}",
            "artifacts": artifacts,
            "created_at": current_job.get("created_at"),
            "finished_at": finished_iso,
        }
        result["job"] = job_summary_for_contract

        updates = {
            "status": "succeeded",
            "progress": 1.0,
            "steps": job_steps,
            "artifacts": artifacts,
            "result_ref": f"job:{job_id}",
            "result": result,
            "finished_at": finished_iso,
        }
        self.store.update_job(job_id, updates)

        sm = get_session_manager()
        if session_id in sm.sessions:
            sess = sm.sessions[session_id]
            sess.jobs.append({"id": job_id, "agent": agent_id, "status": "succeeded", "turn_id": f"job:{job_id}"})
            sess.last_agent_result = {"agent": agent_id, "run_id": job_id, "turn_id": f"job:{job_id}", "inputs": proposed_action.get("inputs") or {}}
            sess.record_turn(result)

        job_final = self.store.get_job(job_id)
        self.broker.publish(job_id, "job.completed", {"job": job_final, "result_ref": f"job:{job_id}"})
        await self._notify_ws(session_id, job_final)


_executor: Optional[JobExecutor] = None


def get_executor() -> JobExecutor:
    global _executor
    if _executor is None:
        _executor = JobExecutor()
    return _executor
