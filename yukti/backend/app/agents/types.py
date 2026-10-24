from typing import Any, Dict
from pydantic import BaseModel
from dataclasses import dataclass

@dataclass
class AgentContext:
    persona: str
    session: Any
    turn_id: str
    language: str

AgentResult = Dict[str, Any]
