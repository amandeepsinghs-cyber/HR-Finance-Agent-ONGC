import pytest
import asyncio
from app.jobs.executor import get_executor
from app.jobs.store import get_job_store, reset_store_for_tests
from app.session_memory import get_session_manager

@pytest.fixture(autouse=True)
def setup_teardown():
    reset_store_for_tests()
    executor = get_executor()
    executor.store = get_job_store()
    executor._running_tasks.clear()
    sm = get_session_manager()
    sm.sessions.clear()
    yield

@pytest.mark.asyncio
async def test_executor_idempotency():
    executor = get_executor()
    session_id = "test_sess"
    
    proposed_action = {"id": "pa_1", "agent": "dcf_agent"}
    
    job1 = await executor.submit_job(proposed_action, session_id)
    job2 = await executor.submit_job(proposed_action, session_id)
    assert job1["id"] == job2["id"]

@pytest.mark.asyncio
async def test_executor_limits():
    executor = get_executor()
    session_id = "test_sess"
    
    proposed_action1 = {"id": "pa_1", "agent": "dcf_agent"}
    await executor.submit_job(proposed_action1, session_id)
    
    proposed_action2 = {"id": "pa_2", "agent": "dcf_agent"}
    await executor.submit_job(proposed_action2, session_id)
    
    proposed_action3 = {"id": "pa_3", "agent": "dcf_agent"}
    with pytest.raises(ValueError, match="Limit of 2 concurrent jobs per session reached"):
        await executor.submit_job(proposed_action3, session_id)

@pytest.mark.asyncio
async def test_executor_execution():
    executor = get_executor()
    session_id = "test_sess"
    sm = get_session_manager()
    sess = sm.get_or_create(session_id)
    
    proposed_action = {"id": "pa_1", "agent": "dcf_agent"}
    job = await executor.submit_job(proposed_action, session_id)
    
    # Wait for execution
    await asyncio.sleep(1.5)
    
    store = get_job_store()
    job_updated = store.get_job(job["id"])
    assert job_updated["status"] == "succeeded"
    assert job_updated["progress"] == 1
    assert "dcf_model" in job_updated["result"]["visual"]["type"]
    
    assert len(sess.jobs) == 1
    assert sess.last_agent_result["turn_id"] == f"job:{job['id']}"


def test_startup_sweep_marks_stale_running_jobs_e_instance_lost():
    """SPEC-03 AC-09: Killing the instance mid-job leaves the job failed: E_INSTANCE_LOST on restart."""
    store = get_job_store()
    store.create_job({
        "id": "job_stale_1",
        "session_id": "sess_stale",
        "agent": "dcf_agent",
        "status": "running",
        "progress": 0.5,
    })
    executor = get_executor()
    executor._running_tasks.clear()
    executor._sweep_stale_jobs()

    swept = store.get_job("job_stale_1")
    assert swept["status"] == "failed"
    assert swept["error"]["code"] == "E_INSTANCE_LOST"
    assert swept["error"]["message"] == "Please run again"
