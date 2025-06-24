import pytest
import pytest_asyncio
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
import os
from copy import deepcopy

from crewai import Crew, Agent, Task, Process
from pydantic import ValidationError as PydanticValidationError

# Modules to test
from python_ai_services.crews.trading_crew_service import TradingCrewService, TradingCrewRequest
from python_ai_services.crews.trading_crew_definitions import (
    trading_analysis_crew,
    market_analyst_agent,
    strategy_agent,
    trade_advisor_agent,
    market_analysis_task,
    strategy_application_task,
    trade_decision_task
)

# Supporting Pydantic models and types
from python_ai_services.types.trading_types import TradingDecision, TradeAction
from python_ai_services.main import LLMConfig, LLMParameter # LLMConfig is in main.py

# Attempt to import actual LLM clients for type checking and patching targets
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None # Placeholder if not available

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None # Placeholder if not available


# --- Tests for trading_analysis_crew Definition ---

def test_trading_crew_structure():
    """Test the static structure of the trading_analysis_crew."""
    assert isinstance(trading_analysis_crew, Crew)
    assert len(trading_analysis_crew.agents) == 3
    assert len(trading_analysis_crew.tasks) == 3

    # Check if the correct agent instances are in the crew
    assert market_analyst_agent in trading_analysis_crew.agents
    assert strategy_agent in trading_analysis_crew.agents
    assert trade_advisor_agent in trading_analysis_crew.agents

    # Check if the correct task instances are in the crew
    assert market_analysis_task in trading_analysis_crew.tasks
    assert strategy_application_task in trading_analysis_crew.tasks
    assert trade_decision_task in trading_analysis_crew.tasks

    assert trading_analysis_crew.process == Process.sequential
    assert trading_analysis_crew.verbose == 2
    # Check other properties if necessary, e.g., memory, manager_llm, output_log_file
    assert trading_analysis_crew.memory is False # As defined
    assert trading_analysis_crew.manager_llm is None # As defined
    assert trading_analysis_crew.output_log_file is True # As defined

# --- Tests for TradingCrewService._get_llm_instance ---

@pytest.fixture
def trading_crew_service_instance_for_llm_test():
    """Provides a TradingCrewService instance for testing _get_llm_instance."""
    # No mocks needed for __init__ for this specific helper method test
    return TradingCrewService()

# Patch targets need to be where the object is looked up, which is in trading_crew_service module
LANGCHAIN_OPENAI_PATH = "python_ai_services.crews.trading_crew_service.ChatOpenAI"
LANGCHAIN_GEMINI_PATH = "python_ai_services.crews.trading_crew_service.ChatGoogleGenerativeAI"
OS_GETENV_PATH = "python_ai_services.crews.trading_crew_service.os.getenv"

@patch(LANGCHAIN_OPENAI_PATH, new_callable=MagicMock)
@patch(OS_GETENV_PATH, return_value="dummy_openai_api_key")
def test_get_llm_instance_openai_success(mock_getenv, MockChatOpenAI, trading_crew_service_instance_for_llm_test):
    llm_config = LLMConfig(
        id="openai_test",
        model_name="gpt-4-turbo",
        api_key_env_var="OPENAI_API_KEY",
        parameters=LLMParameter(temperature=0.5, max_tokens=100)
    )
    # Simulate ChatOpenAI being available
    if ChatOpenAI is None: # If original import failed, make mock available
        trading_crew_service_instance_for_llm_test.ChatOpenAI = MockChatOpenAI

    llm_instance = trading_crew_service_instance_for_llm_test._get_llm_instance(llm_config)

    mock_getenv.assert_called_once_with("OPENAI_API_KEY")
    MockChatOpenAI.assert_called_once_with(
        model="gpt-4-turbo",
        api_key="dummy_openai_api_key",
        temperature=0.5,
        max_tokens=100
    )
    assert llm_instance == MockChatOpenAI.return_value

@patch(LANGCHAIN_GEMINI_PATH, new_callable=MagicMock)
@patch(OS_GETENV_PATH, return_value="dummy_gemini_api_key")
def test_get_llm_instance_gemini_success(mock_getenv, MockChatGemini, trading_crew_service_instance_for_llm_test):
    llm_config = LLMConfig(
        id="gemini_test",
        model_name="gemini-1.5-pro",
        api_key_env_var="GEMINI_API_KEY",
        parameters=LLMParameter(temperature=0.8, top_k=30)
    )
    if ChatGoogleGenerativeAI is None:
        trading_crew_service_instance_for_llm_test.ChatGoogleGenerativeAI = MockChatGemini

    llm_instance = trading_crew_service_instance_for_llm_test._get_llm_instance(llm_config)

    mock_getenv.assert_called_once_with("GEMINI_API_KEY")
    MockChatGemini.assert_called_once_with(
        model_name="gemini-1.5-pro",
        google_api_key="dummy_gemini_api_key",
        temperature=0.8,
        top_k=30
    )
    assert llm_instance == MockChatGemini.return_value

@patch(OS_GETENV_PATH, return_value=None)
def test_get_llm_instance_missing_api_key(mock_getenv, trading_crew_service_instance_for_llm_test):
    llm_config = LLMConfig(
        id="openai_test_no_key",
        model_name="gpt-4-turbo",
        api_key_env_var="MISSING_OPENAI_KEY",
        parameters=LLMParameter()
    )
    with pytest.raises(ValueError, match="API key for gpt-4-turbo not configured."):
        trading_crew_service_instance_for_llm_test._get_llm_instance(llm_config)
    mock_getenv.assert_called_once_with("MISSING_OPENAI_KEY")

def test_get_llm_instance_unsupported_model(trading_crew_service_instance_for_llm_test):
    llm_config = LLMConfig(
        id="unsupported_test",
        model_name="llama-3-70b", # Assuming not directly supported by name check
        api_key_env_var="ANY_KEY_VAR", # os.getenv will be called if var is set
        parameters=LLMParameter()
    )
    with patch(OS_GETENV_PATH, return_value="dummy_key"): # Mock getenv to proceed to model check
        with pytest.raises(NotImplementedError, match="LLM support for 'llama-3-70b' is not implemented."):
            trading_crew_service_instance_for_llm_test._get_llm_instance(llm_config)

# --- Tests for TradingCrewService.run_analysis ---

from python_ai_services.services.agent_persistence_service import AgentPersistenceService # For mocking
from python_ai_services.models.crew_models import TaskStatus # For status assertion
import uuid # For task_id generation/assertion

@pytest_asyncio.fixture
async def mock_persistence_service_for_crew() -> AgentPersistenceService:
    """Provides a fully mocked AgentPersistenceService for TradingCrewService tests."""
    mock_svc = AsyncMock(spec=AgentPersistenceService)
    # Configure create_agent_task to return a mock task dict
    mock_svc.create_agent_task = AsyncMock(return_value={
        "task_id": str(uuid.uuid4()), "crew_id": "trading_analysis_crew",
        "status": TaskStatus.PENDING.value, "inputs": {}
    })
    mock_svc.update_agent_task_status = AsyncMock(return_value={"status": "updated"}) # Simple success
    mock_svc.update_agent_task_result = AsyncMock(return_value={"status": "result_updated"}) # Simple success
    return mock_svc

@pytest_asyncio.fixture
async def trading_crew_service(mock_persistence_service_for_crew: AgentPersistenceService) -> TradingCrewService:
    """Provides a TradingCrewService instance with mocked persistence and _get_llm_instance."""
    # Pass the mocked persistence service to the constructor
    service = TradingCrewService(persistence_service=mock_persistence_service_for_crew)
    service._get_llm_instance = MagicMock(return_value=MagicMock(spec=["generate", "invoke"]))
    return service

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy_name_to_test, sample_strategy_config",
    [
        ("DarvasBoxStrategy", {"lookback_period_highs": 200, "min_box_duration": 5}),
        ("WilliamsAlligatorStrategy", {"jaw_period": 13, "teeth_period": 8, "lips_period": 5, "price_source_column": "close"}),
        ("HeikinAshiStrategy", {"min_trend_candles": 3, "small_wick_threshold_percent": 10.0}),
        # Add a default/generic one for cases where strategy logic isn't the focus of the test
        ("GenericTestStrategy", {"param1": "value1", "param2": 100})
    ]
)
@patch("python_ai_services.crews.trading_crew_service.Crew", new_callable=MagicMock) # Patch Crew where it's used
async def test_run_analysis_success(
    MockCrewClass: MagicMock,
    trading_crew_service: TradingCrewService,
    strategy_name_to_test: str,
    sample_strategy_config: Dict[str, Any]
):
    mock_llm_instance = MagicMock()
    trading_crew_service._get_llm_instance = MagicMock(return_value=mock_llm_instance)

    # Get the mock persistence service from the fixture
    mock_persistence_service = trading_crew_service.persistence_service
    mock_task_id = mock_persistence_service.create_agent_task.return_value["task_id"] # Get the mocked task_id

    mock_crew_instance = MockCrewClass.return_value
    # Use parameterized strategy_name for symbol to make output slightly distinct if needed for debugging
    mock_crew_output = {
        "symbol": f"{strategy_name_to_test}_SYM", "action": "BUY", "confidence_score": 0.8,
        "reasoning": f"Strong signal for {strategy_name_to_test}",
        "decision_id": str(uuid.uuid4()), "timestamp": datetime.utcnow().isoformat()
    }
    mock_crew_instance.kickoff_async = AsyncMock(return_value=mock_crew_output)

    request = TradingCrewRequest(
        symbol=f"{strategy_name_to_test}_SYM",
        timeframe="1h",
        strategy_name=strategy_name_to_test,
        llm_config_id="openai_gpt4_turbo",
        strategy_config=sample_strategy_config # Added strategy_config
    )

    result = await trading_crew_service.run_analysis(request)

    # Assert Task Logging
    mock_persistence_service.create_agent_task.assert_called_once_with(
        task_id_str=mock.ANY,
        crew_id="trading_analysis_crew",
        inputs=request.model_dump(), # This now includes strategy_config
        status=TaskStatus.PENDING.value
    )
    update_status_calls = [
        mock.call(task_id=mock_task_id, status=TaskStatus.RUNNING.value),
    ]
    # Check if update_agent_task_status was called with RUNNING
    # Note: a second call to FAILED might occur if parsing fails, so we check specific calls
    called_with_running = any(
    call_item == mock.call(task_id=mock_task_id, status=TaskStatus.RUNNING.value)
    for call_item in mock_persistence_service.update_agent_task_status.call_args_list
    )
    assert called_with_running, "update_agent_task_status was not called with RUNNING status"

    mock_persistence_service.update_agent_task_result.assert_called_once()
    args_result, kwargs_result = mock_persistence_service.update_agent_task_result.call_args
    assert kwargs_result['task_id'] == mock_task_id
    # The output passed to update_agent_task_result is after Pydantic parsing by the service
    assert kwargs_result['output'] == TradingDecision(**mock_crew_output).model_dump()
    assert kwargs_result['status'] == TaskStatus.COMPLETED.value
    assert isinstance(kwargs_result['logs_summary'], list)

    # Assertions for crew logic
    trading_crew_service._get_llm_instance.assert_called_once()
    MockCrewClass.assert_called_once()

    # Key Assertion: Verify inputs to kickoff_async
    expected_kickoff_inputs = {
        "symbol": f"{strategy_name_to_test}_SYM",
        "timeframe": "1h",
        "strategy_name": strategy_name_to_test,
        "strategy_config": sample_strategy_config,
        "crew_run_id": mock_task_id # Verify crew_run_id is passed
    }
    mock_crew_instance.kickoff_async.assert_called_once_with(inputs=expected_kickoff_inputs)

    assert isinstance(result, TradingDecision)
    assert result.symbol == f"{strategy_name_to_test}_SYM"
    assert result.action == TradeAction.BUY

@pytest.mark.asyncio
async def test_run_analysis_llm_instantiation_fails(trading_crew_service: TradingCrewService):
    trading_crew_service._get_llm_instance = MagicMock(side_effect=ValueError("LLM init error"))
    mock_persistence_service = trading_crew_service.persistence_service
    mock_task_id = mock_persistence_service.create_agent_task.return_value["task_id"]

    request = TradingCrewRequest(
        symbol="BTC/USD",
        timeframe="1h",
        strategy_name="TestStrategy",
        llm_config_id="some_config",
        strategy_config={"param": "value"} # Added default strategy_config
    )

    result = await trading_crew_service.run_analysis(request)
    assert result is None

    # create_agent_task should be called once
    mock_persistence_service.create_agent_task.assert_called_once()

    # update_agent_task_status should be called once with FAILED status
    mock_persistence_service.update_agent_task_status.assert_called_once_with(
        task_id=mock_task_id, status=TaskStatus.FAILED.value, error_message="LLM init error"
    )

@pytest.mark.asyncio
@patch("python_ai_services.crews.trading_crew_service.Crew", new_callable=MagicMock)
async def test_run_analysis_crew_kickoff_fails(MockCrewClass: MagicMock, trading_crew_service: TradingCrewService):
    trading_crew_service._get_llm_instance = MagicMock(return_value=MagicMock())
    mock_persistence_service = trading_crew_service.persistence_service
    mock_task_id = mock_persistence_service.create_agent_task.return_value["task_id"]

    mock_crew_instance = MockCrewClass.return_value
    mock_crew_instance.kickoff_async = AsyncMock(side_effect=Exception("Crew failed!"))

    request = TradingCrewRequest(
        symbol="BTC/USD",
        timeframe="1h",
        strategy_name="TestStrategy",
        llm_config_id="openai_gpt4_turbo",
        strategy_config={"param": "value"} # Added default strategy_config
    )

    result = await trading_crew_service.run_analysis(request)
    assert result is None

    mock_persistence_service.create_agent_task.assert_called_once()
    update_status_calls = [
        mock.call(task_id=mock_task_id, status=TaskStatus.RUNNING.value),
        mock.call(task_id=mock_task_id, status=TaskStatus.FAILED.value, error_message="Crew failed!")
    ]
    mock_persistence_service.update_agent_task_status.assert_has_calls(update_status_calls, any_order=False)

@pytest.mark.asyncio
@patch("python_ai_services.crews.trading_crew_service.Crew", new_callable=MagicMock)
async def test_run_analysis_invalid_crew_output_dict(MockCrewClass: MagicMock, trading_crew_service: TradingCrewService):
    trading_crew_service._get_llm_instance = MagicMock(return_value=MagicMock())
    mock_persistence_service = trading_crew_service.persistence_service
    mock_task_id = mock_persistence_service.create_agent_task.return_value["task_id"]

    mock_crew_instance = MockCrewClass.return_value
    malformed_output = {"symbol": "BTC/USD", "confidence_score": 0.7} # Missing 'action'
    mock_crew_instance.kickoff_async = AsyncMock(return_value=malformed_output)

    request = TradingCrewRequest(
        symbol="BTC/USD",
        timeframe="1h",
        strategy_name="TestStrategy",
        llm_config_id="openai_gpt4_turbo",
        strategy_config={"param1": "value1"} # Ensure this is present
    )

    result = await trading_crew_service.run_analysis(request)
    assert result is None

    mock_persistence_service.create_agent_task.assert_called_once()
    update_status_calls = mock_persistence_service.update_agent_task_status.call_args_list

    # Ensure RUNNING status was called before FAILED
    assert mock.call(task_id=mock_task_id, status=TaskStatus.RUNNING.value) in update_status_calls

    # Ensure FAILED status was called with the correct error message
    failed_call_found = any(
        call_item == mock.call(task_id=mock_task_id, status=TaskStatus.FAILED.value, error_message="Crew failed!")
        for call_item in update_status_calls
    )
    assert failed_call_found, "update_agent_task_status was not called with FAILED status and correct error message"


@pytest.mark.asyncio
@patch("python_ai_services.crews.trading_crew_service.Crew", new_callable=MagicMock)
async def test_run_analysis_invalid_crew_output_dict(MockCrewClass: MagicMock, trading_crew_service: TradingCrewService):
    trading_crew_service._get_llm_instance = MagicMock(return_value=MagicMock())
    mock_persistence_service = trading_crew_service.persistence_service
    mock_task_id = mock_persistence_service.create_agent_task.return_value["task_id"]

    mock_crew_instance = MockCrewClass.return_value
    malformed_output = {"symbol": "BTC/USD", "confidence_score": 0.7} # Missing 'action'
    mock_crew_instance.kickoff_async = AsyncMock(return_value=malformed_output)

    request = TradingCrewRequest(
        symbol="BTC/USD",
        timeframe="1h",
        strategy_name="TestStrategy",
        llm_config_id="openai_gpt4_turbo",
        strategy_config={"param": "value"} # Added default strategy_config
    )

    result = await trading_crew_service.run_analysis(request)
    assert result is None

    mock_persistence_service.create_agent_task.assert_called_once()
    update_status_calls = mock_persistence_service.update_agent_task_status.call_args_list
    assert mock.call(task_id=mock_task_id, status=TaskStatus.RUNNING.value) in update_status_calls

    failed_call_found = False
    for call_item in update_status_calls:
        if call_item.kwargs.get("status") == TaskStatus.FAILED.value:
            failed_call_found = True
            assert "Error parsing crew result" in call_item.kwargs.get("error_message", "")
            # PydanticValidationError results in a specific string representation
            assert "1 validation error for TradingDecision" in call_item.kwargs.get("error_message", "") # More specific error message
            break
    assert failed_call_found


@pytest.mark.asyncio
@patch("python_ai_services.crews.trading_crew_service.Crew", new_callable=MagicMock)
async def test_run_analysis_crew_output_string_force_info(MockCrewClass: MagicMock, trading_crew_service: TradingCrewService):
    trading_crew_service._get_llm_instance = MagicMock(return_value=MagicMock())
    mock_persistence_service = trading_crew_service.persistence_service
    mock_task_id = mock_persistence_service.create_agent_task.return_value["task_id"]

    mock_crew_instance = MockCrewClass.return_value
    crew_output_string = "The market looks very uncertain, better to wait."
    mock_crew_instance.kickoff_async = AsyncMock(return_value=crew_output_string)

    request = TradingCrewRequest(
        symbol="XYZ/USD",
        timeframe="1h",
        strategy_name="TestStrategy",
        llm_config_id="openai_gpt4_turbo",
        strategy_config={"param": "value"} # Added default strategy_config
    )

    result = await trading_crew_service.run_analysis(request)
    assert result is not None
    assert isinstance(result, TradingDecision)
    assert result.symbol == "XYZ/USD"
    assert result.action == TradeAction.INFO

    mock_persistence_service.update_agent_task_result.assert_called_once()
    args_result, kwargs_result = mock_persistence_service.update_agent_task_result.call_args
    assert kwargs_result['task_id'] == mock_task_id
    assert kwargs_result['output']['action'] == "INFO"
    assert kwargs_result['status'] == TaskStatus.COMPLETED.value

@pytest.mark.asyncio
async def test_run_analysis_task_creation_fails(trading_crew_service: TradingCrewService):
    """Test behavior when initial task creation fails."""
    mock_persistence_service = trading_crew_service.persistence_service
    mock_persistence_service.create_agent_task = AsyncMock(return_value=None) # Simulate DB error

    request = TradingCrewRequest(
        symbol="FAIL/TASK",
        timeframe="1h",
        strategy_name="TestStrategy",
        llm_config_id="openai_gpt4_turbo",
        strategy_config={"param": "value"} # Added default strategy_config
    )

    result = await trading_crew_service.run_analysis(request)
    assert result is None
    mock_persistence_service.create_agent_task.assert_called_once()
    # Ensure no further calls if task creation fails
    trading_crew_service._get_llm_instance.assert_not_called()
    mock_persistence_service.update_agent_task_status.assert_not_called()
    mock_persistence_service.update_agent_task_result.assert_not_called()
