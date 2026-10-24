import re
import math
import logging
from typing import Optional, List, Tuple
from google import genai
from pydantic import BaseModel
from app.agents.registry import get_registry

logger = logging.getLogger(__name__)

def cosine_sim(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0: return 0.0
    return dot / (n1 * n2)

class IntentRouter:
    def __init__(self, registry=None):
        self.registry = registry or get_registry()
        self.client = genai.Client()
        self._cached_embeddings = {}

    def _get_embedding(self, text: str) -> List[float]:
        if text in self._cached_embeddings:
            return self._cached_embeddings[text]
        try:
            res = self.client.models.embed_content(model="text-embedding-004", contents=text)
            vec = res.embeddings[0].values
            self._cached_embeddings[text] = vec
            return vec
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return []

    def route(self, query: str) -> str:
        # 1. Regex
        for agent in self.registry.agents:
            for trig in agent.triggers:
                if re.search(trig, query, re.IGNORECASE):
                    logger.info(f"Regex match for {agent.id} on '{trig}'")
                    return agent.id
                    
        # 2. Embedding similarity over registry examples
        q_vec = self._get_embedding(query)
        if not q_vec:
            return self._llm_fallback(query)
            
        scores: List[Tuple[float, str]] = []
        for agent in self.registry.agents:
            max_sim = 0.0
            for ex in agent.examples:
                ex_vec = self._get_embedding(ex)
                if ex_vec:
                    sim = cosine_sim(q_vec, ex_vec)
                    max_sim = max(max_sim, sim)
            scores.append((max_sim, agent.id))
            
        scores.sort(reverse=True)
        logger.info(f"Router scores: {scores}")
        
        if not scores:
            return self._llm_fallback(query)
            
        top1_score, top1_id = scores[0]
        
        if top1_score < 0.6:
            return self._llm_fallback(query)
            
        if len(scores) > 1:
            top2_score, _ = scores[1]
            if top1_score - top2_score < 0.1:
                return self._llm_fallback(query)
                
        return top1_id

    def _llm_fallback(self, query: str) -> str:
        # Simple fallback for now
        # Actually this uses the LLM Coordinator
        try:
            prompt = f"Route the query '{query}' to one of: analyst, fin_diagnostics_agent, dcf_agent, hr_transfer_agent, doc_export_agent."
            res = self.client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            text = res.text.lower()
            for a in self.registry.agents:
                if a.id in text:
                    return a.id
        except Exception:
            pass
        return "analyst"

_router = None
def get_router() -> IntentRouter:
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router
