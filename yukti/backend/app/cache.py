"""Optional Root-Only Demo Cache Accelerator for Yukti AI.
Disabled by default (YUKTI_DEMO_CACHE=0).
When enabled (YUKTI_DEMO_CACHE=1), serves only the 89 canonical root questions.
Never includes held-out follow-ups or paraphrases.
Emits status_event: 'Served from verified demo cache'.
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import yaml

from app.config import CONTRACT_SCHEMA_PATH, ROOT_DIR, YUKTI_DEMO_CACHE
from app.tools.chart_rules import build_chart_spec, select_chart_kind

logger = logging.getLogger("yukti.cache")


class DemoCache:
    """Optional pre-warmed cache strictly for the 89 root questions."""

    def __init__(self):
        self.is_enabled = YUKTI_DEMO_CACHE
        self.root_entries: Dict[str, Dict[str, Any]] = {}
        self.query_to_id: Dict[str, str] = {}
        self._is_loaded = False

    def load(self) -> None:
        if not self.is_enabled or self._is_loaded:
            return

        answer_key_dir = ROOT_DIR / "data_bank" / "answer_key"
        expected_dir = answer_key_dir / "expected"
        questions_path = ROOT_DIR / "data_bank" / "world_bible" / "reference" / "questions.yaml"

        if not expected_dir.exists() or not questions_path.exists():
            return

        with open(questions_path, "r", encoding="utf-8") as f:
            qs = yaml.safe_load(f).get("questions", [])

        for q in qs:
            qid = q["id"]
            qtext = q.get("question", "")
            exp_file = expected_dir / f"{qid}.json"
            if exp_file.exists():
                try:
                    data = json.loads(exp_file.read_text(encoding="utf-8"))
                    self.root_entries[qid] = {
                        "id": qid,
                        "question": qtext,
                        "data": data,
                        "type": q.get("type", "data"),
                    }
                    norm_q = self._normalize(qtext)
                    self.query_to_id[norm_q] = qid
                except Exception as e:
                    logger.warning(f"Error loading {exp_file}: {e}")

        self._is_loaded = True
        logger.info(f"Loaded {len(self.root_entries)} root questions in optional demo cache.")

    def _normalize(self, text: str) -> str:
        t = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(t.split())

    def match_root(self, query: str) -> Optional[Dict[str, Any]]:
        """Matches only canonical root questions when cache is enabled."""
        if not self.is_enabled:
            return None
        if not self._is_loaded:
            self.load()

        norm_q = self._normalize(query)
        qid = self.query_to_id.get(norm_q)
        if qid and qid in self.root_entries:
            return self.root_entries[qid]
        return None


_DEMO_CACHE = DemoCache()


def get_demo_cache() -> DemoCache:
    return _DEMO_CACHE
