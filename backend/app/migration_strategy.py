from .models import (
    MigrationGoal,
    RepositoryAnalysis,
    MigrationStrategyResult,
    StrategyAssessment
)


def determine_migration_strategy(
    goal: MigrationGoal,
    analysis: RepositoryAnalysis
) -> MigrationStrategyResult:

    scores = {
        "Rehost": 0,
        "Replatform": 0,
        "Refactor": 0,
        "Containerize": 0
    }

    reasons: list[str] = []

    # --------------------------------------------------
    # User Goal
    # --------------------------------------------------

    if goal == MigrationGoal.lift_shift:
        scores["Rehost"] += 20
        reasons.append(
            "Lift-and-Shift migration goal selected."
        )

    elif goal == MigrationGoal.modernization:
        scores["Replatform"] += 10
        scores["Refactor"] += 10
        reasons.append(
            "Application Modernization goal selected."
        )

    elif goal == MigrationGoal.cost:
        scores["Replatform"] += 15
        reasons.append(
            "Cost Optimization goal selected."
        )

    elif goal == MigrationGoal.scalability:
        scores["Containerize"] += 15
        scores["Replatform"] += 10
        reasons.append(
            "Scalability goal selected."
        )

    elif goal == MigrationGoal.performance:
        scores["Containerize"] += 10
        scores["Refactor"] += 10
        reasons.append(
            "Performance Improvement goal selected."
        )

    # --------------------------------------------------
    # Runtime Analysis
    # --------------------------------------------------

    runtimes = [runtime.lower() for runtime in analysis.runtimes]

    if any(".net framework" in runtime for runtime in runtimes):
        scores["Refactor"] += 15
        reasons.append(
            ".NET Framework detected."
        )

    if any(".net" in runtime for runtime in runtimes):
        scores["Replatform"] += 5
        reasons.append(
            ".NET runtime detected."
        )

    if "node.js" in runtimes:
        scores["Containerize"] += 5
        reasons.append(
            "Node.js runtime detected."
        )

    # --------------------------------------------------
    # Containers
    # --------------------------------------------------

    if analysis.container_configs:
        scores["Containerize"] += 20
        reasons.append(
            "Container configuration detected."
        )

    # --------------------------------------------------
    # CI/CD
    # --------------------------------------------------

    if analysis.cicd_configs:
        scores["Containerize"] += 5
        scores["Replatform"] += 5
        reasons.append(
            "CI/CD pipeline detected."
        )

    # --------------------------------------------------
    # Database
    # --------------------------------------------------

    if analysis.databases:
        scores["Replatform"] += 5
        reasons.append(
            "Database dependency detected."
        )

    # --------------------------------------------------
    # Stateful Services
    # --------------------------------------------------

    if analysis.stateful_services:
        scores["Replatform"] += 5
        reasons.append(
            "Stateful services detected."
        )

    # --------------------------------------------------
    # Cloud Dependencies
    # --------------------------------------------------

    if analysis.cloud_dependencies:
        scores["Replatform"] += 10
        reasons.append(
            "Cloud services already detected."
        )

    # --------------------------------------------------
    # Governance
    # --------------------------------------------------

    if analysis.governance_findings:
        scores["Refactor"] += 5
        reasons.append(
            "Governance issues identified."
        )

    # --------------------------------------------------
    # Determine Winner
    # --------------------------------------------------

    strategy = max(
        scores,
        key=scores.get
    )

    winning_score = scores[strategy]

    if winning_score >= 25:
        confidence = "High"
    elif winning_score >= 15:
        confidence = "Medium"
    else:
        confidence = "Low"

    return MigrationStrategyResult(
        strategy=strategy,
        confidence=confidence,
        reasons=reasons
    )

def assess_strategy_alignment(
    user_goal: MigrationGoal,
    strategy_result: MigrationStrategyResult
) -> StrategyAssessment:

    goal_mapping = {
        MigrationGoal.lift_shift: "Rehost",
        MigrationGoal.modernization: "Replatform",
        MigrationGoal.cost: "Replatform",
        MigrationGoal.scalability: "Containerize",
        MigrationGoal.performance: "Refactor"
    }

    expected = goal_mapping.get(user_goal)

    return StrategyAssessment(
        user_goal=user_goal.value,
        recommended_strategy=strategy_result.strategy,
        confidence=strategy_result.confidence,
        is_aligned=expected == strategy_result.strategy,
        recommendation_reason=strategy_result.reasons
    )