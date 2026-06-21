from __future__ import annotations

from app.migration_strategy import assess_strategy_alignment, determine_migration_strategy
from app.models import MigrationGoal, RepositoryAnalysis


def test_determine_migration_strategy_prefers_containerize_for_scalability_with_docker():
    """Verify scalability plus container evidence recommends containerization."""
    analysis = RepositoryAnalysis(
        runtimes=["Node.js"],
        container_configs=["Dockerfile"],
        cicd_configs=["GitHub Actions"],
        databases=[],
        stateful_services=[],
        cloud_dependencies=[],
        governance_findings=[],
    )

    result = determine_migration_strategy(MigrationGoal.scalability, analysis)

    assert result.strategy == "Containerize"
    assert result.confidence == "High"
    assert "Scalability goal selected." in result.reasons

def test_assess_strategy_alignment_marks_expected_strategy():
    """Verify strategy alignment is true when recommendation matches the goal mapping."""
    analysis = RepositoryAnalysis(databases=["SQL Server"])
    strategy = determine_migration_strategy(MigrationGoal.cost, analysis)

    alignment = assess_strategy_alignment(MigrationGoal.cost, strategy)

    assert alignment.user_goal == "Cost Optimization"
    assert alignment.recommended_strategy == "Replatform"
    assert alignment.is_aligned is True
