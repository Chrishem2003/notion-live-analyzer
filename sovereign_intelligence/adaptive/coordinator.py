from .strategy_memory import StrategyMemory


class LearningCoordinator:

    def __init__(
        self,
        memory: StrategyMemory | None = None,
    ):
        self.memory = memory or StrategyMemory()

    def record_result(
        self,
        strategy: str,
        success: bool,
        confidence: float,
    ):
        self.memory.record(
            strategy=strategy,
            success=success,
            confidence=confidence,
        )

    def recommend(
        self,
        strategies: list[str],
    ) -> list[str]:

        if not strategies:
            return []

        return self.memory.recommend(
            strategies
        )

    def best_strategy(
        self,
        strategies: list[str],
    ) -> str | None:

        recommendations = self.recommend(
            strategies
        )

        if not recommendations:
            return None

        return recommendations[0]
