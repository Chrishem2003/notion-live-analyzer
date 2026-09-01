from .base import Agent
from .specialists import (
    GeneralAgent,
    ResearchAgent,
    CodingAgent,
    DataAgent,
    MathematicsAgent,
    EngineeringAgent,
    DocumentAgent,
    CADAgent,
)


class AgentRegistry:

    def __init__(self):

        self._agents: dict[str, Agent] = {}

        for agent in [
            GeneralAgent(),
            ResearchAgent(),
            CodingAgent(),
            DataAgent(),
            MathematicsAgent(),
            EngineeringAgent(),
            DocumentAgent(),
            CADAgent(),
        ]:
            self.register(agent)

    def register(self, agent: Agent):
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        return self._agents.get(
            name,
            self._agents["general"],
        )

    def names(self):
        return sorted(self._agents.keys())