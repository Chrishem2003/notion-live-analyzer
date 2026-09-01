from .models import Goal, Objective


class GoalEngine:

    def create_goal(
        self,
        title: str,
        description: str,
        constraints: list[str] | None = None,
    ) -> Goal:

        if not title.strip():
            raise ValueError("Goal title cannot be empty.")

        if not description.strip():
            raise ValueError(
                "Goal description cannot be empty."
            )

        return Goal.create(
            title=title,
            description=description,
            constraints=constraints,
        )

    def add_objective(
        self,
        goal: Goal,
        description: str,
        priority: int = 50,
    ) -> Objective:

        if not description.strip():
            raise ValueError(
                "Objective description cannot be empty."
            )

        priority = max(
            0,
            min(100, int(priority)),
        )

        objective = Objective(
            id=__import__("uuid").uuid4().__str__(),
            description=description,
            priority=priority,
        )

        goal.objectives.append(objective)

        return objective

    def update_progress(
        self,
        goal: Goal,
        objective_id: str,
        progress: float,
    ):

        progress = max(
            0.0,
            min(1.0, float(progress)),
        )

        for objective in goal.objectives:

            if objective.id == objective_id:

                objective.progress = progress
                objective.completed = progress >= 1.0

                self._refresh_status(goal)

                return objective

        raise KeyError(
            f"Objective not found: {objective_id}"
        )

    def _refresh_status(
        self,
        goal: Goal,
    ):

        if not goal.objectives:

            goal.status = "pending"
            return

        if all(
            objective.completed
            for objective in goal.objectives
        ):
            goal.status = "completed"
            return

        if any(
            objective.progress > 0
            for objective in goal.objectives
        ):
            goal.status = "in_progress"
            return

        goal.status = "pending"

    def completion(
        self,
        goal: Goal,
    ) -> float:

        if not goal.objectives:
            return 0.0

        total = sum(
            objective.progress
            for objective in goal.objectives
        )

        return total / len(goal.objectives)

    def prioritized_objectives(
        self,
        goal: Goal,
    ) -> list[Objective]:

        return sorted(
            goal.objectives,
            key=lambda item: item.priority,
            reverse=True,
        )
