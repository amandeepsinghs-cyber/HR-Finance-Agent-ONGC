"""In-Memory Tool-Result Cache for Yukti AI (Option A Data Cache).
Caches raw BigQuery SQL results, Vertex AI Search policy clauses, and what-if simulation outputs.
Keyed on normalized query + persona access scope to guarantee role-based security.
LRU eviction with configurable TTL (default 24 hours) and max 2,000 entries.
"""

from collections import OrderedDict
import copy
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("yukti.tool_cache")

# Default TTL: 24 hours (86,400 seconds)
DEFAULT_CACHE_TTL = int(os.getenv("YUKTI_TOOL_CACHE_TTL", 86400))
MAX_CACHE_ENTRIES = 2000


def normalize_sql_for_key(sql: str) -> str:
    """Normalizes SQL query for cache key: collapses whitespace, trims trailing semicolons,

    preserves string/numeric literals.
    """
    clean = sql.strip().rstrip(";")
    clean = re.sub(r"\s+", " ", clean)
    return clean


class ToolResultCache:
    """Thread-safe, in-memory LRU cache for tool execution results."""

    def __init__(self, max_size: int = MAX_CACHE_ENTRIES, ttl_seconds: int = DEFAULT_CACHE_TTL):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            entry = self._cache[key]
            now = time.time()
            if now - entry["timestamp"] > self.ttl:
                # Expired
                del self._cache[key]
                self.misses += 1
                return None

            # Move to end for LRU
            self._cache.move_to_end(key)
            self.hits += 1
            return copy.deepcopy(entry["value"])

    def _set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            now = time.time()
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = {
                "value": copy.deepcopy(value),
                "timestamp": now,
            }
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # Evict oldest LRU

    def get_sql(self, sql: str, persona: str = "CMD") -> Optional[Dict[str, Any]]:
        norm_sql = normalize_sql_for_key(sql)
        key = f"sql:{persona.upper()}:{norm_sql}"
        return self._get(key)

    def set_sql(self, sql: str, persona: str, value: Dict[str, Any]) -> None:
        norm_sql = normalize_sql_for_key(sql)
        key = f"sql:{persona.upper()}:{norm_sql}"
        self._set(key, value)

    def get_policy(self, query: str, persona: str = "CMD") -> Optional[Dict[str, Any]]:
        norm_q = " ".join(query.strip().lower().split())
        key = f"policy:{persona.upper()}:{norm_q}"
        return self._get(key)

    def set_policy(self, query: str, persona: str, value: Dict[str, Any]) -> None:
        norm_q = " ".join(query.strip().lower().split())
        key = f"policy:{persona.upper()}:{norm_q}"
        self._set(key, value)

    def get_whatif(self, scenario: str, params: Optional[Dict[str, Any]], persona: str = "CMD") -> Optional[Dict[str, Any]]:
        param_str = json.dumps(params or {}, sort_keys=True)
        key = f"whatif:{persona.upper()}:{scenario.lower()}:{param_str}"
        return self._get(key)

    def set_whatif(self, scenario: str, params: Optional[Dict[str, Any]], persona: str, value: Dict[str, Any]) -> None:
        param_str = json.dumps(params or {}, sort_keys=True)
        key = f"whatif:{persona.upper()}:{scenario.lower()}:{param_str}"
        self._set(key, value)

    def clear(self) -> None:
        self._cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        rate = round((self.hits / total * 100), 2) if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": rate,
        }


_GLOBAL_TOOL_CACHE = ToolResultCache()


def get_tool_cache() -> ToolResultCache:
    return _GLOBAL_TOOL_CACHE
