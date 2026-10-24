import yaml
import os
from pydantic import BaseModel
from typing import List, Optional

class AgentRegistryEntry(BaseModel):
    id: str
    class_path: str
    requires_role: List[str]
    description: str
    triggers: List[str]
    examples: List[str]

class AgentRegistry:
    def __init__(self):
        self.agents = []
        self._load()

    def _load(self):
        path = os.path.join(os.path.dirname(__file__), "registry.yaml")
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            if not data: return
            for a in data.get("agents", []):
                self.agents.append(AgentRegistryEntry(
                    id=a["id"],
                    class_path=a["class"],
                    requires_role=a.get("requires_role", []),
                    description=a.get("description", ""),
                    triggers=a.get("triggers", []),
                    examples=a.get("examples", [])
                ))

    def get_agent(self, agent_id: str) -> Optional[AgentRegistryEntry]:
        for a in self.agents:
            if a.id == agent_id:
                return a
        return None

_registry = AgentRegistry()

def get_registry() -> AgentRegistry:
    return _registry
