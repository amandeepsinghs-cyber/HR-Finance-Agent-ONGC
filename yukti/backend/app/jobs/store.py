from __future__ import annotations
import uuid
import time
from typing import Any, Dict, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

class JobStore:
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]: pass
    def create_job(self, job: Dict[str, Any]) -> str: pass
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> None: pass
    def list_jobs(self, session_id: str) -> List[Dict[str, Any]]: pass
    def get_active_jobs(self) -> List[Dict[str, Any]]: pass

class InMemoryJobStore(JobStore):
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if job:
            return dict(job)
        return None
        
    def create_job(self, job: Dict[str, Any]) -> str:
        job_id = job.get("id") or f"job_{uuid.uuid4().hex}"
        job["id"] = job_id
        if "created_at" not in job:
            job["created_at"] = time.time()
        self._jobs[job_id] = dict(job)
        return job_id
        
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update(updates)
            
    def list_jobs(self, session_id: str) -> List[Dict[str, Any]]:
        return [dict(j) for j in self._jobs.values() if j.get("session_id") == session_id]
        
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        return [dict(j) for j in self._jobs.values() if j.get("status") in ("queued", "running")]

class FirestoreJobStore(JobStore):
    def __init__(self):
        from google.cloud import firestore
        self.db = firestore.Client()
        self.collection = self.db.collection("jobs")
        
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        doc = self.collection.document(job_id).get()
        return doc.to_dict() if doc.exists else None
        
    def create_job(self, job: Dict[str, Any]) -> str:
        job_id = job.get("id") or f"job_{uuid.uuid4().hex}"
        job["id"] = job_id
        if "created_at" not in job:
            job["created_at"] = time.time()
        self.collection.document(job_id).set(job)
        return job_id
        
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        self.collection.document(job_id).update(updates)
        
    def list_jobs(self, session_id: str) -> List[Dict[str, Any]]:
        docs = self.collection.where("session_id", "==", session_id).stream()
        return [doc.to_dict() for doc in docs]
        
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        docs = self.collection.where("status", "in", ["queued", "running"]).stream()
        return [doc.to_dict() for doc in docs]

_store: Optional[JobStore] = None

def get_job_store() -> JobStore:
    global _store
    if _store is None:
        if os.getenv("FIRESTORE_EMULATOR_HOST") or os.getenv("GOOGLE_CLOUD_PROJECT"):
            try:
                _store = FirestoreJobStore()
            except Exception as e:
                logger.warning(f"Firestore unavailable, falling back to InMemoryJobStore: {e}")
                _store = InMemoryJobStore()
        else:
            _store = InMemoryJobStore()
    return _store

def reset_store_for_tests():
    global _store
    _store = InMemoryJobStore()
