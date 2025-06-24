import pytest
from pydantic import ValidationError
# Assuming 'python-ai-services' is in PYTHONPATH or tests are run in a way that resolves this:
from python_ai_services.main import CrewBlueprint, LLMParameter, LLMConfig
# Import New Models for Monitoring
from python_ai_services.models.monitoring_models import AgentTaskSummary, TaskListResponse, DependencyStatus, SystemHealthSummary
from typing import List, Optional, Any # Ensure List, Optional, Any are imported
from datetime import datetime, timezone # Ensure datetime, timezone are imported
import uuid # Ensure uuid is imported


# Test data
VALID_CREW_BLUEPRINT_DATA = {
    "id": "crew_bp_1",
    "name": "Test Crew",
    "description": "A crew for testing purposes."
}

VALID_LLM_PARAMETER_DATA = {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9,
    "top_k": 40,
    "frequency_penalty": 0.5,
    "presence_penalty": 0.5
}

VALID_LLM_CONFIG_DATA = {
    "id": "llm_cfg_1",
    "model_name": "test-model-v1",
    "api_key_env_var": "TEST_API_KEY",
    "parameters": VALID_LLM_PARAMETER_DATA
}

# --- Tests for CrewBlueprint ---

def test_crew_blueprint_valid_data():
    """Test CrewBlueprint creation with valid data."""
    bp = CrewBlueprint(**VALID_CREW_BLUEPRINT_DATA)
    assert bp.id == VALID_CREW_BLUEPRINT_DATA["id"]
    assert bp.name == VALID_CREW_BLUEPRINT_DATA["name"]
    assert bp.description == VALID_CREW_BLUEPRINT_DATA["description"]

def test_crew_blueprint_missing_required_fields():
    """Test CrewBlueprint raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError):
        CrewBlueprint(name="Test Crew", description="Desc")  # Missing id
    with pytest.raises(ValidationError):
        CrewBlueprint(id="bp1", description="Desc")  # Missing name
    with pytest.raises(ValidationError):
        CrewBlueprint(id="bp1", name="Test Crew")  # Missing description

def test_crew_blueprint_invalid_types():
    """Test CrewBlueprint raises ValidationError for invalid data types."""
    with pytest.raises(ValidationError):
        CrewBlueprint(id=123, name="Test Crew", description="Desc")  # id as int
    with pytest.raises(ValidationError):
        CrewBlueprint(id="bp1", name=123, description="Desc")  # name as int
    with pytest.raises(ValidationError):
        CrewBlueprint(id="bp1", name="Test Crew", description=True)  # description as bool

# --- Tests for LLMParameter ---

def test_llm_parameter_valid_data_all_fields():
    """Test LLMParameter creation with all fields valid."""
    params = LLMParameter(**VALID_LLM_PARAMETER_DATA)
    assert params.temperature == VALID_LLM_PARAMETER_DATA["temperature"]
    assert params.max_tokens == VALID_LLM_PARAMETER_DATA["max_tokens"]
    assert params.top_p == VALID_LLM_PARAMETER_DATA["top_p"]

def test_llm_parameter_valid_data_optional_missing():
    """Test LLMParameter creation with some optional fields missing."""
    data = {"temperature": 0.8}
    params = LLMParameter(**data)
    assert params.temperature == 0.8
    assert params.max_tokens is None  # Or default if specified in model
    assert params.top_p is None

    params_empty = LLMParameter() # All optional, should be fine
    assert params_empty.temperature is None


def test_llm_parameter_invalid_types():
    """Test LLMParameter raises ValidationError for invalid data types."""
    with pytest.raises(ValidationError):
        LLMParameter(temperature="hot")
    with pytest.raises(ValidationError):
        LLMParameter(max_tokens="one thousand")
    with pytest.raises(ValidationError):
        LLMParameter(top_p="high")
    with pytest.raises(ValidationError):
        LLMParameter(top_k="many")

# --- Tests for LLMConfig ---

def test_llm_config_valid_data():
    """Test LLMConfig creation with valid data."""
    config = LLMConfig(**VALID_LLM_CONFIG_DATA)
    assert config.id == VALID_LLM_CONFIG_DATA["id"]
    assert config.model_name == VALID_LLM_CONFIG_DATA["model_name"]
    assert config.parameters.temperature == VALID_LLM_PARAMETER_DATA["temperature"]

def test_llm_config_missing_required_fields():
    """Test LLMConfig raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError):
        LLMConfig(model_name="test", parameters=VALID_LLM_PARAMETER_DATA)  # Missing id
    with pytest.raises(ValidationError):
        LLMConfig(id="cfg1", parameters=VALID_LLM_PARAMETER_DATA)  # Missing model_name
    with pytest.raises(ValidationError):
        LLMConfig(id="cfg1", model_name="test")  # Missing parameters

def test_llm_config_invalid_parameters_type():
    """Test LLMConfig raises ValidationError for invalid parameters structure."""
    with pytest.raises(ValidationError):
        LLMConfig(id="cfg1", model_name="test", parameters={"temp": 0.7}) # Invalid structure
    with pytest.raises(ValidationError):
        LLMConfig(id="cfg1", model_name="test", parameters="not a dict")

def test_llm_config_invalid_field_types():
    """Test LLMConfig raises ValidationError for invalid field types."""
    with pytest.raises(ValidationError):
        LLMConfig(id=123, model_name="test", parameters=VALID_LLM_PARAMETER_DATA) # id as int
    with pytest.raises(ValidationError):
        LLMConfig(id="cfg1", model_name=True, parameters=VALID_LLM_PARAMETER_DATA) # model_name as bool
    with pytest.raises(ValidationError):
        LLMConfig(id="cfg1", model_name="test", api_key_env_var=123, parameters=VALID_LLM_PARAMETER_DATA) # api_key_env_var as int

def test_llm_parameter_all_fields_none():
    """Test LLMParameter creation with all fields explicitly set to None (if allowed by model)."""
    # This test assumes that all fields in LLMParameter are Optional and can be None.
    # If some fields have defaults that are not None, this test might need adjustment
    # or the model definition implies they can be None.
    data = {
        "temperature": None,
        "max_tokens": None,
        "top_p": None,
        "top_k": None,
        "frequency_penalty": None,
        "presence_penalty": None
    }
    params = LLMParameter(**data)
    assert params.temperature is None
    assert params.max_tokens is None
    assert params.top_p is None
    assert params.top_k is None
    assert params.frequency_penalty is None
    assert params.presence_penalty is None

def test_llm_config_api_key_env_var_optional():
    """Test LLMConfig creation when optional api_key_env_var is missing."""
    data_no_api_key = {
        "id": "llm_cfg_2",
        "model_name": "test-model-v2",
        "parameters": VALID_LLM_PARAMETER_DATA
    }
    config = LLMConfig(**data_no_api_key)
    assert config.id == data_no_api_key["id"]
    assert config.api_key_env_var is None # Or default if specified in model
    assert config.parameters.max_tokens == VALID_LLM_PARAMETER_DATA["max_tokens"]

def test_crew_blueprint_extra_fields():
    """Test CrewBlueprint creation with extra fields (should be ignored by default)."""
    data_with_extra = {**VALID_CREW_BLUEPRINT_DATA, "extra_field": "should_be_ignored"}
    bp = CrewBlueprint(**data_with_extra)
    assert bp.id == VALID_CREW_BLUEPRINT_DATA["id"]
    with pytest.raises(AttributeError): # Pydantic models don't store extra fields by default
        _ = bp.extra_field

# To make this runnable with `pytest`, one might need to:
# 1. Ensure `python-ai-services/main.py` and the models within it are importable.
#    This might involve setting PYTHONPATH or running pytest from a project root
#    that recognizes `python_ai_services` as a package.
# 2. Install pytest: `pip install pytest`
# 3. Run pytest from the terminal in the directory containing `python-ai-services`
#    or a higher-level project root.
#    Example: `cd /path/to/project_root && pytest`
#
# If direct import `from python_ai_services.main import ...` fails due to path issues
# in the execution environment, the models might need to be redefined in this test file
# or a conftest.py used to adjust sys.path, but this is beyond what the agent can
# configure in the environment itself.
# For now, assuming the import works.

# --- Test Data for Monitoring Models ---
VALID_AGENT_TASK_SUMMARY_DATA = {
    "task_id": str(uuid.uuid4()),
    "status": "COMPLETED",
    "agent_name": "TestAgent",
    "crew_name": "TestCrew",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "duration_ms": 1234.5,
    "result_summary": "Task finished successfully.",
    "error_message": None
}

VALID_TASK_LIST_RESPONSE_DATA = {
    "tasks": [VALID_AGENT_TASK_SUMMARY_DATA],
    "total_tasks": 1,
    "page": 1,
    "page_size": 20
}

VALID_DEPENDENCY_STATUS_DATA = {
    "name": "Redis",
    "status": "operational",
    "details": "Connection healthy.",
    "last_checked": datetime.now(timezone.utc).isoformat()
}

VALID_SYSTEM_HEALTH_SUMMARY_DATA = {
    "overall_status": "healthy",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "dependencies": [VALID_DEPENDENCY_STATUS_DATA],
    "system_metrics": {"cpu_load": 0.75}
}

# --- Tests for AgentTaskSummary ---
def test_agent_task_summary_valid_data():
    summary = AgentTaskSummary(**VALID_AGENT_TASK_SUMMARY_DATA)
    assert summary.task_id == VALID_AGENT_TASK_SUMMARY_DATA["task_id"]
    assert summary.status == VALID_AGENT_TASK_SUMMARY_DATA["status"]
    assert summary.agent_name == VALID_AGENT_TASK_SUMMARY_DATA["agent_name"]
    assert summary.crew_name == VALID_AGENT_TASK_SUMMARY_DATA["crew_name"]
    assert summary.timestamp == VALID_AGENT_TASK_SUMMARY_DATA["timestamp"]
    assert summary.duration_ms == VALID_AGENT_TASK_SUMMARY_DATA["duration_ms"]
    assert summary.result_summary == VALID_AGENT_TASK_SUMMARY_DATA["result_summary"]
    assert summary.error_message == VALID_AGENT_TASK_SUMMARY_DATA["error_message"]

def test_agent_task_summary_optional_fields_none():
    data = VALID_AGENT_TASK_SUMMARY_DATA.copy()
    data["agent_name"] = None
    data["crew_name"] = None
    data["duration_ms"] = None
    data["result_summary"] = None
    data["error_message"] = None
    summary = AgentTaskSummary(**data)
    assert summary.agent_name is None
    assert summary.crew_name is None
    assert summary.duration_ms is None
    assert summary.result_summary is None
    assert summary.error_message is None

def test_agent_task_summary_missing_required_fields():
    with pytest.raises(ValidationError): # Missing task_id
        AgentTaskSummary(status="PENDING", timestamp=datetime.now(timezone.utc).isoformat())
    with pytest.raises(ValidationError): # Missing status
        AgentTaskSummary(task_id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc).isoformat())
    with pytest.raises(ValidationError): # Missing timestamp
        AgentTaskSummary(task_id=str(uuid.uuid4()), status="PENDING")

def test_agent_task_summary_invalid_types():
    with pytest.raises(ValidationError): # task_id as int
        AgentTaskSummary(**{**VALID_AGENT_TASK_SUMMARY_DATA, "task_id": 123})
    with pytest.raises(ValidationError): # status not a valid enum string (if enum was used strictly) or type
        AgentTaskSummary(**{**VALID_AGENT_TASK_SUMMARY_DATA, "status": 123})
    with pytest.raises(ValidationError): # timestamp not a valid datetime string
        AgentTaskSummary(**{**VALID_AGENT_TASK_SUMMARY_DATA, "timestamp": "not-a-date"})
    with pytest.raises(ValidationError): # duration_ms not a float
        AgentTaskSummary(**{**VALID_AGENT_TASK_SUMMARY_DATA, "duration_ms": "long time"})

# --- Tests for TaskListResponse ---
def test_task_list_response_valid_data():
    response = TaskListResponse(**VALID_TASK_LIST_RESPONSE_DATA)
    assert len(response.tasks) == 1
    assert response.tasks[0].task_id == VALID_AGENT_TASK_SUMMARY_DATA["task_id"]
    assert response.total_tasks == VALID_TASK_LIST_RESPONSE_DATA["total_tasks"]
    assert response.page == VALID_TASK_LIST_RESPONSE_DATA["page"]
    assert response.page_size == VALID_TASK_LIST_RESPONSE_DATA["page_size"]

def test_task_list_response_empty_tasks():
    data = {"tasks": [], "total_tasks": 0, "page": 1, "page_size": 20}
    response = TaskListResponse(**data)
    assert len(response.tasks) == 0
    assert response.total_tasks == 0

def test_task_list_response_missing_required_fields():
    with pytest.raises(ValidationError): # Missing tasks
        TaskListResponse(total_tasks=0, page=1, page_size=20)
    with pytest.raises(ValidationError): # Missing total_tasks
        TaskListResponse(tasks=[], page=1, page_size=20)
    # page and page_size are optional based on monitoring_models.py

def test_task_list_response_invalid_types():
    with pytest.raises(ValidationError): # tasks not a list
        TaskListResponse(tasks="not-a-list", total_tasks=0)
    with pytest.raises(ValidationError): # total_tasks not an int
        TaskListResponse(tasks=[], total_tasks="zero")
    with pytest.raises(ValidationError): # page not an int
        TaskListResponse(**{**VALID_TASK_LIST_RESPONSE_DATA, "page": "first"})

# --- Tests for DependencyStatus ---
def test_dependency_status_valid_data():
    status = DependencyStatus(**VALID_DEPENDENCY_STATUS_DATA)
    assert status.name == VALID_DEPENDENCY_STATUS_DATA["name"]
    assert status.status == VALID_DEPENDENCY_STATUS_DATA["status"]
    assert status.details == VALID_DEPENDENCY_STATUS_DATA["details"]
    assert status.last_checked == VALID_DEPENDENCY_STATUS_DATA["last_checked"]

def test_dependency_status_optional_details_none():
    data = VALID_DEPENDENCY_STATUS_DATA.copy()
    data["details"] = None
    status = DependencyStatus(**data)
    assert status.details is None

def test_dependency_status_missing_required_fields():
    with pytest.raises(ValidationError): # Missing name
        DependencyStatus(status="operational", last_checked=datetime.now(timezone.utc).isoformat())
    with pytest.raises(ValidationError): # Missing status
        DependencyStatus(name="Redis", last_checked=datetime.now(timezone.utc).isoformat())
    with pytest.raises(ValidationError): # Missing last_checked
        DependencyStatus(name="Redis", status="operational")

def test_dependency_status_invalid_types():
    with pytest.raises(ValidationError): # name not a string
        DependencyStatus(**{**VALID_DEPENDENCY_STATUS_DATA, "name": 123})
    with pytest.raises(ValidationError): # last_checked not a datetime string
        DependencyStatus(**{**VALID_DEPENDENCY_STATUS_DATA, "last_checked": "yesterday"})

# --- Tests for SystemHealthSummary ---
def test_system_health_summary_valid_data():
    summary = SystemHealthSummary(**VALID_SYSTEM_HEALTH_SUMMARY_DATA)
    assert summary.overall_status == VALID_SYSTEM_HEALTH_SUMMARY_DATA["overall_status"]
    assert summary.timestamp == VALID_SYSTEM_HEALTH_SUMMARY_DATA["timestamp"]
    assert len(summary.dependencies) == 1
    assert summary.dependencies[0].name == VALID_DEPENDENCY_STATUS_DATA["name"]
    assert summary.system_metrics["cpu_load"] == VALID_SYSTEM_HEALTH_SUMMARY_DATA["system_metrics"]["cpu_load"]

def test_system_health_summary_optional_metrics_none():
    data = VALID_SYSTEM_HEALTH_SUMMARY_DATA.copy()
    data["system_metrics"] = None
    summary = SystemHealthSummary(**data)
    assert summary.system_metrics is None

def test_system_health_summary_empty_dependencies():
    data = VALID_SYSTEM_HEALTH_SUMMARY_DATA.copy()
    data["dependencies"] = []
    summary = SystemHealthSummary(**data)
    assert len(summary.dependencies) == 0

def test_system_health_summary_missing_required_fields():
    with pytest.raises(ValidationError): # Missing overall_status
        SystemHealthSummary(timestamp=datetime.now(timezone.utc).isoformat(), dependencies=[])
    with pytest.raises(ValidationError): # Missing timestamp
        SystemHealthSummary(overall_status="healthy", dependencies=[])
    with pytest.raises(ValidationError): # Missing dependencies
        SystemHealthSummary(overall_status="healthy", timestamp=datetime.now(timezone.utc).isoformat())

def test_system_health_summary_invalid_types():
    with pytest.raises(ValidationError): # overall_status not a string
        SystemHealthSummary(**{**VALID_SYSTEM_HEALTH_SUMMARY_DATA, "overall_status": False})
    with pytest.raises(ValidationError): # dependencies not a list
        SystemHealthSummary(**{**VALID_SYSTEM_HEALTH_SUMMARY_DATA, "dependencies": "status1"})
    with pytest.raises(ValidationError): # system_metrics not a dict
        SystemHealthSummary(**{**VALID_SYSTEM_HEALTH_SUMMARY_DATA, "system_metrics": ["metric1"]})
