from app.agents.parameter_agent import ParametersAgent
from app.agents import analyze_agent as analyze_module
from app.agents import verify_agent as verify_module
from app.config import settings


class DummyLLMProvider:
    def __init__(self):
        self.last_messages = None

    def chat(self, model, messages, options=None):
        self.last_messages = messages
        return {"message": {"content": "{}"}}


class DummyGateway:
    def __init__(self):
        self.last_messages = None

    def cached(self, **kwargs):
        self.last_messages = kwargs.get("messages")
        result = kwargs["compute"]()
        return result.value, {}


def test_parameter_agent_uses_db_prompt_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "USE_DB_PROMPTS", True)

    captured = {}

    class StubPromptService:
        def render_prompt(self, name, variables=None):
            captured["name"] = name
            captured["variables"] = variables
            return "DB_PROMPT"

    import app.services.prompt_service as prompt_service

    monkeypatch.setattr(prompt_service, "get_prompt_service", lambda: StubPromptService())

    agent = ParametersAgent(client=None, model="dummy")
    prompt = agent._build_system_prompt()

    assert prompt == "DB_PROMPT"
    assert captured["name"] == "parameter_extraction_system"
    assert "allowed_query_keys" in captured["variables"]
    assert "excluded_domains" in captured["variables"]


def _call_trace_analysis(agent):
    trace_data = {
        "log_entries": [{"message": "Error processing transaction id=12345"}],
        "timeline": [{"operation": "process", "timestamp": "2025-01-01T00:00:00Z", "level": "INFO"}],
        "total_entries": 1,
        "source_files": ["file1.log"],
    }
    parameters = {"time_frame": "2025-01-01", "query_keys": ["merchant"], "domain": "transactions"}
    agent._analyze_single_trace("trace-1", trace_data, "context", parameters)


def _call_entries_analysis(agent):
    trace_entries = [{"message": "Entry content for analysis"}]
    parameters = {"time_frame": "2025-01-01", "query_keys": ["merchant"], "domain": "transactions"}
    agent._analyze_single_trace_from_entries("trace-2", trace_entries, "context", parameters)


def _call_quality_assessment(agent):
    search_results = {"total_files": 1, "total_matches": 2}
    trace_data = {"all_trace_data": {"trace-1": {}}}
    parameters = {"time_frame": "2025-01-01", "query_keys": ["merchant"], "domain": "transactions"}
    agent._assess_overall_quality("context", search_results, trace_data, parameters)


def test_analyze_agent_uses_db_trace_prompts(monkeypatch, tmp_path):
    dummy_client = DummyLLMProvider()
    gateway = DummyGateway()
    monkeypatch.setattr(analyze_module, "get_llm_cache_gateway", lambda: gateway)

    def fake_get_prompt(name, variables=None):
        return {
            "trace_analysis_system": "DB_SYSTEM",
            "trace_analysis_user": "DB_USER",
        }.get(name)

    monkeypatch.setattr(analyze_module, "_get_prompt_from_db", fake_get_prompt)

    agent = analyze_module.AnalyzeAgent(client=dummy_client, model="dummy", output_dir=str(tmp_path))
    _call_trace_analysis(agent)

    assert dummy_client.last_messages[0]["content"] == "DB_SYSTEM"
    assert dummy_client.last_messages[1]["content"] == "DB_USER"


def test_analyze_agent_uses_db_entries_prompts(monkeypatch, tmp_path):
    dummy_client = DummyLLMProvider()
    gateway = DummyGateway()
    monkeypatch.setattr(analyze_module, "get_llm_cache_gateway", lambda: gateway)

    def fake_get_prompt(name, variables=None):
        return {
            "entries_analysis_system": "DB_SYSTEM",
            "entries_analysis_user": "DB_USER",
        }.get(name)

    monkeypatch.setattr(analyze_module, "_get_prompt_from_db", fake_get_prompt)

    agent = analyze_module.AnalyzeAgent(client=dummy_client, model="dummy", output_dir=str(tmp_path))
    _call_entries_analysis(agent)

    assert dummy_client.last_messages[0]["content"] == "DB_SYSTEM"
    assert dummy_client.last_messages[1]["content"] == "DB_USER"


def test_analyze_agent_uses_db_quality_prompts(monkeypatch, tmp_path):
    dummy_client = DummyLLMProvider()
    gateway = DummyGateway()
    monkeypatch.setattr(analyze_module, "get_llm_cache_gateway", lambda: gateway)

    def fake_get_prompt(name, variables=None):
        return {
            "quality_assessment_system": "DB_SYSTEM",
            "quality_assessment_user": "DB_USER",
        }.get(name)

    monkeypatch.setattr(analyze_module, "_get_prompt_from_db", fake_get_prompt)

    agent = analyze_module.AnalyzeAgent(client=dummy_client, model="dummy", output_dir=str(tmp_path))
    _call_quality_assessment(agent)

    assert dummy_client.last_messages[0]["content"] == "DB_SYSTEM"
    assert dummy_client.last_messages[1]["content"] == "DB_USER"


def test_verify_agent_uses_db_relevance_prompts(monkeypatch, tmp_path):
    dummy_client = DummyLLMProvider()
    gateway = DummyGateway()
    monkeypatch.setattr(verify_module, "get_llm_cache_gateway", lambda: gateway)

    def fake_get_prompt(name, variables=None):
        return {
            "relevance_analysis_system": "DB_SYSTEM",
            "relevance_analysis_user": "DB_USER",
        }.get(name)

    monkeypatch.setattr(verify_module, "_get_prompt_from_db", fake_get_prompt)

    agent = verify_module.RelevanceAnalyzerAgent(
        client=dummy_client,
        model="dummy",
        output_dir=str(tmp_path),
        context_file=str(tmp_path / "context_rules.csv"),
    )

    trace_info = {
        "trace_id": "trace-3",
        "total_entries": 2,
        "log_samples": ["message 1", "message 2"],
        "timeline_summary": "step 1",
        "service_names": ["svc1"],
        "operations": ["op1"],
        "timestamp": "2025-01-01T00:00:00Z",
    }
    parameters = {"time_frame": "2025-01-01", "query_keys": ["merchant"], "domain": "transactions"}

    agent._analyze_relevance_with_rag(
        "context",
        parameters,
        trace_info,
        "full content",
        relevant_rules=[],
    )

    assert dummy_client.last_messages[0]["content"] == "DB_SYSTEM"
    assert dummy_client.last_messages[1]["content"] == "DB_USER"
