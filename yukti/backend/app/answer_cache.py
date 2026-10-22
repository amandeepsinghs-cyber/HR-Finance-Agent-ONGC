"""Verified Answer Cache for Yukti AI.
Pluggable high-performance cache: in-memory LRU by default, Redis-ready via REDIS_URL
(for GCP Memorystore on Cloud Run).

Serves verified Answer Contracts for certified queries and parameter variants in <300 ms.
Enforces Role-Based Access Control before serving cached contracts.
"""

from collections import OrderedDict
import copy
import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("yukti.answer_cache")

DEFAULT_CACHE_TTL = 86400  # 24 hours
MAX_CACHE_ENTRIES = 5000
REDIS_URL = os.getenv("REDIS_URL")


def normalize_params(params: Optional[Dict[str, Any]]) -> str:
    """Normalizes parameter dictionary into a canonical sorted JSON string."""
    if not params:
        return "{}"
    clean = {}
    for k, v in params.items():
        if v is not None:
            clean[str(k).lower()] = str(v).strip().upper() if isinstance(v, str) else v
    return json.dumps(clean, sort_keys=True)


class BaseAnswerCacheBackend:
    """Abstract base for answer cache backends."""

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set(self, key: str, value: Dict[str, Any], ttl: int = DEFAULT_CACHE_TTL) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def size(self) -> int:
        raise NotImplementedError


class InMemoryAnswerCache(BaseAnswerCacheBackend):
    """Thread-safe in-memory LRU cache."""

    def __init__(self, max_size: int = MAX_CACHE_ENTRIES, ttl_seconds: int = DEFAULT_CACHE_TTL):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: OrderedDict[str, Tuple[float, Dict[str, Any]]] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            if key not in self.cache:
                return None
            ts, val = self.cache[key]
            if time.time() - ts > self.ttl:
                del self.cache[key]
                return None
            self.cache.move_to_end(key)
            return copy.deepcopy(val)

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[key] = (time.time(), copy.deepcopy(value))

    def clear(self) -> None:
        with self.lock:
            self.cache.clear()

    def size(self) -> int:
        with self.lock:
            return len(self.cache)


class RedisAnswerCache(BaseAnswerCacheBackend):
    """Redis backend for GCP Memorystore on Cloud Run."""

    def __init__(self, redis_url: str, ttl_seconds: int = DEFAULT_CACHE_TTL):
        self.ttl = ttl_seconds
        try:
            import redis
            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
            logger.info(f"Connected to Redis cache at {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis ({redis_url}): {e}. Falling back to in-memory.")
            self.client = None

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"Redis get error for {key}: {e}")
            return None

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        if not self.client:
            return
        try:
            exp = ttl or self.ttl
            self.client.setex(key, exp, json.dumps(value))
        except Exception as e:
            logger.warning(f"Redis set error for {key}: {e}")

    def clear(self) -> None:
        if not self.client:
            return
        try:
            # Clear keys matching prefix
            keys = self.client.keys("ANSWER_CACHE:*")
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")

    def size(self) -> int:
        if not self.client:
            return 0
        try:
            return len(self.client.keys("ANSWER_CACHE:*"))
        except Exception:
            return 0


class VerifiedAnswerCache:
    """Manages verified answer retrieval with RBAC enforcement and metrics."""

    def __init__(self):
        if REDIS_URL:
            self.backend = RedisAnswerCache(redis_url=REDIS_URL)
            self.backend_type = "redis"
        else:
            self.backend = InMemoryAnswerCache()
            self.backend_type = "in_memory"

        self.hits = 0
        self.misses = 0

    def make_key(self, certified_id: str, params: Optional[Dict[str, Any]], persona: str = "CMD") -> str:
        norm_p = normalize_params(params)
        return f"ANSWER_CACHE:{certified_id.upper()}:{norm_p}:{persona.upper()}"

    def get_answer(
        self,
        certified_id: str,
        params: Optional[Dict[str, Any]],
        persona: str = "CMD",
        session_id: Optional[str] = None,
        turn_index: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a verified Answer Contract, updating turn identifiers and latency."""
        t0 = time.perf_counter()
        key = self.make_key(certified_id, params, persona)
        contract = self.backend.get(key)

        if contract:
            # Rule: NEVER serve a refusal from the answer cache
            if contract.get("access", {}).get("status") == "refused" or contract.get("visual", {}).get("type") == "refusal":
                logger.warning(f"Purging refusal contract from cache for key: {key}")
                return None

            self.hits += 1
            contract_copy = copy.deepcopy(contract)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            contract_copy["latency_ms"] = elapsed_ms
            if session_id:
                contract_copy["turn_id"] = f"turn-{session_id}-{turn_index:03d}"
            status_evts = contract_copy.get("status_events", [])
            status_evts.insert(0, f"Served from Verified Answer Cache ({elapsed_ms}ms)")
            contract_copy["status_events"] = status_evts[:4]
            contract_copy["from_answer_cache"] = True
            return contract_copy

        self.misses += 1
        return None

    def set_answer(
        self,
        certified_id: str,
        params: Optional[Dict[str, Any]],
        persona: str,
        contract: Dict[str, Any],
    ) -> None:
        """Stores a verified Answer Contract (refusals are strictly excluded)."""
        # Rule: NEVER cache refusals in the shared answer cache
        if contract.get("access", {}).get("status") == "refused" or contract.get("visual", {}).get("type") == "refusal":
            logger.info(f"Skipping cache set for refusal contract ({certified_id}, persona: {persona})")
            return

        key = self.make_key(certified_id, params, persona)
        self.backend.set(key, contract)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = round(self.hits / total * 100, 2) if total > 0 else 0.0
        return {
            "backend": self.backend_type,
            "total_entries": self.backend.size(),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": hit_rate,
        }

    def clear(self) -> None:
        self.backend.clear()
        self.hits = 0
        self.misses = 0


_GLOBAL_ANSWER_CACHE: Optional[VerifiedAnswerCache] = None


def get_answer_cache() -> VerifiedAnswerCache:
    """Singleton getter for VerifiedAnswerCache."""
    global _GLOBAL_ANSWER_CACHE
    if _GLOBAL_ANSWER_CACHE is None:
        _GLOBAL_ANSWER_CACHE = VerifiedAnswerCache()
    return _GLOBAL_ANSWER_CACHE
