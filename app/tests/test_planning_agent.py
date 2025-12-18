from app.agents.planning_agent import PlanningAgent


def test_planning_agent_fallback_blocks_without_time_frame_for_loki():
    agent = PlanningAgent(client=None, model="dummy")

    plan = agent.run(
        text="Find timeout errors in bKash transactions",
        project="NCC",
        env="prod",
        domain="transactions",
        extracted_params={"time_frame": None, "domain": "transactions", "query_keys": []},
    )

    assert plan["can_proceed"] is False
    assert any("date" in q.lower() for q in plan["blocking_questions"])
    assert any("loki" in w.lower() for w in plan["warnings"])
    assert len(plan["steps"]) == 6


def test_planning_agent_fallback_can_proceed_with_time_frame():
    agent = PlanningAgent(client=None, model="dummy")

    plan = agent.run(
        text="Show me failed NPSB transactions from yesterday",
        project="MMBL",
        env="prod",
        domain="transactions",
        extracted_params={"time_frame": "2025-12-17", "domain": "transactions", "query_keys": ["npsb", "status"]},
    )

    assert plan["can_proceed"] is True
    assert plan["blocking_questions"] == [] or all(isinstance(q, str) for q in plan["blocking_questions"])
    assert len(plan["steps"]) == 6


def test_planning_agent_fallback_blocks_without_query_keys():
    """Pipeline should block when query_keys is empty, even if time_frame is present."""
    agent = PlanningAgent(client=None, model="dummy")

    plan = agent.run(
        text="Find errors",
        project="NCC",
        env="prod",
        domain="transactions",
        extracted_params={"time_frame": "2025-12-17", "domain": "transactions", "query_keys": []},
    )

    assert plan["can_proceed"] is False
    assert any("identifier" in q.lower() or "keyword" in q.lower() for q in plan["blocking_questions"])


def test_planning_agent_fallback_blocks_without_both_time_frame_and_query_keys():
    """Pipeline should block and ask for both when both are missing."""
    agent = PlanningAgent(client=None, model="dummy")

    plan = agent.run(
        text="Find errors",
        project="NCC",
        env="prod",
        domain="transactions",
        extracted_params={"time_frame": None, "domain": "transactions", "query_keys": []},
    )

    assert plan["can_proceed"] is False
    assert len(plan["blocking_questions"]) >= 2
    assert any("date" in q.lower() for q in plan["blocking_questions"])
    assert any("identifier" in q.lower() or "keyword" in q.lower() for q in plan["blocking_questions"])
