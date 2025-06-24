import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call # Added call
from fastapi.testclient import TestClient
import uuid
from datetime import date, datetime, timezone, timedelta # Added timedelta
from typing import List, Dict, Any, Optional
import json # For serializing/deserializing cache data
import redis.asyncio as aioredis # For RedisError

# Assuming main.app is the FastAPI instance
from python_ai_services.main import app

# Import models for request/response validation and mocking service returns
from python_ai_services.models.visualization_models import StrategyVisualizationRequest, StrategyVisualizationDataResponse, OHLCVBar
from python_ai_services.models.strategy_models import StrategyTimeframe, StrategyConfig, DarvasBoxParams # Added StrategyConfig, DarvasBoxParams
# Assuming StrategyFormMetadataResponse is defined in main.py or easily importable
# For this test, let's assume it's importable from main or a models file
try:
    from python_ai_services.main import StrategyFormMetadataResponse # If defined in main
except ImportError:
    # If you have a dedicated api_models.py or similar, import from there:
    # from python_ai_services.models.api_models import StrategyFormMetadataResponse
    # For this test structure, we'll assume it could be in main or we'll define a fallback if needed.
    # Fallback if not found, to allow tests to run, though ideally this import should be solid.
    class StrategyFormMetadataResponse(MagicMock): # type: ignore
        pass


# Import services to mock their behavior when injected into endpoints
from python_ai_services.services.strategy_visualization_service import StrategyVisualizationService, StrategyVisualizationServiceError
from python_ai_services.services.strategy_config_service import StrategyConfigService

# Import actual dependency injector functions to use as keys for overrides
from python_ai_services.main import get_strategy_visualization_service, get_strategy_config_service
from python_ai_services.main import get_user_preference_service, get_current_active_user # Added for User Preferences

# Import models and services for User Preferences tests
from python_ai_services.services.user_preference_service import UserPreferenceService, UserPreferenceServiceError
from python_ai_services.models.user_models import UserPreferences
from python_ai_services.models.auth_models import AuthenticatedUser


# --- Test Client Fixture ---
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# --- Mock Service Fixtures ---
@pytest_asyncio.fixture
async def mock_viz_service():
    service = MagicMock(spec=StrategyVisualizationService)
    service.get_strategy_visualization_data = AsyncMock()
    return service

# No specific mock for StrategyConfigService needed for form_metadata endpoint as it's simple,
# but could be added if testing more complex scenarios involving it.

# --- Tests for Strategy Visualization Endpoint ---

def test_get_strategy_chart_data_success(client: TestClient, mock_viz_service: MagicMock):
    # Arrange
    strategy_config_id = uuid.uuid4()
    user_id = uuid.uuid4()
    start_date_obj = date(2023, 1, 1)
    end_date_obj = date(2023, 1, 31)
    start_date_str = start_date_obj.isoformat()
    end_date_str = end_date_obj.isoformat()


    mock_response_data = StrategyVisualizationDataResponse(
        strategy_config_id=strategy_config_id,
        symbol_visualized="AAPL",
        period_start_date=start_date_obj,
        period_end_date=end_date_obj,
        ohlcv_data=[OHLCVBar(timestamp=datetime.now(timezone.utc), open=1.0,high=2.0,low=0.0,close=1.5,volume=1000.0)],
        generated_at=datetime.now(timezone.utc)
    )
    mock_viz_service.get_strategy_visualization_data.return_value = mock_response_data

    app.dependency_overrides[get_strategy_visualization_service] = lambda: mock_viz_service

    # Act
    response = client.get(
        "/api/v1/visualizations/strategy",
        params={
            "strategy_config_id": str(strategy_config_id),
            "user_id": str(user_id),
            "start_date": start_date_str,
            "end_date": end_date_str
        }
    )

    app.dependency_overrides.clear()

    # Assert
    assert response.status_code == 200
    response_data_dict = response.json()
    # Re-parse to validate against the model, or compare dict fields carefully
    response_data_model = StrategyVisualizationDataResponse(**response_data_dict)
    assert response_data_model.strategy_config_id == strategy_config_id
    assert response_data_model.symbol_visualized == "AAPL"
    assert len(response_data_model.ohlcv_data) == 1

    mock_viz_service.get_strategy_visualization_data.assert_called_once()
    call_args = mock_viz_service.get_strategy_visualization_data.call_args[1]
    assert isinstance(call_args['request'], StrategyVisualizationRequest)
    assert call_args['request'].strategy_config_id == strategy_config_id
    assert call_args['request'].user_id == user_id
    assert call_args['request'].start_date == start_date_obj
    assert call_args['request'].end_date == end_date_obj


def test_get_strategy_chart_data_service_error(client: TestClient, mock_viz_service: MagicMock):
    mock_viz_service.get_strategy_visualization_data.side_effect = StrategyVisualizationServiceError("Service failed")
    app.dependency_overrides[get_strategy_visualization_service] = lambda: mock_viz_service

    response = client.get("/api/v1/visualizations/strategy", params={"strategy_config_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "start_date": "2023-01-01", "end_date": "2023-01-10"})
    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "Service failed" in response.json()["detail"]

def test_get_strategy_chart_data_not_found_error(client: TestClient, mock_viz_service: MagicMock):
    mock_viz_service.get_strategy_visualization_data.side_effect = StrategyVisualizationServiceError("Could not fetch price data for SYMBOL")
    app.dependency_overrides[get_strategy_visualization_service] = lambda: mock_viz_service

    response = client.get("/api/v1/visualizations/strategy", params={"strategy_config_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "start_date": "2023-01-01", "end_date": "2023-01-10"})
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "Could not fetch price data for SYMBOL" in response.json()["detail"]


def test_get_strategy_chart_data_bad_request_params(client: TestClient):
    response = client.get(
        "/api/v1/visualizations/strategy",
        params={
            "strategy_config_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "start_date": "invalid-date-format",
            "end_date": "2023-01-31"
        }
    )
    assert response.status_code == 422

# --- Tests for Strategy Form Metadata Endpoint ---

def test_get_strategy_form_metadata_success(client: TestClient):
    expected_types = ["DarvasBox", "WilliamsAlligator", "HeikinAshi", "Renko", "SMACrossover", "ElliottWave"]
    expected_timeframes = list(StrategyTimeframe.__args__)

    response = client.get("/api/v1/strategies/form-metadata")

    assert response.status_code == 200
    data = response.json()
    assert data["available_strategy_types"] == expected_types
    assert data["available_timeframes"] == expected_timeframes


# --- Placeholders for other API endpoint tests (Watchlist, Paper Trading, etc.) ---

# Ensure these are imported if not already at the top:
from python_ai_services.services.simulated_trade_executor import SimulatedTradeExecutor
from python_ai_services.models.watchlist_models import BatchQuotesRequest, BatchQuotesResponse, BatchQuotesResponseItem # BatchQuotesResponseItem needed for mock
from python_ai_services.models.paper_trading_models import PaperTradeOrder, PaperTradeFill, CreatePaperTradeOrderRequest, PaperPosition # Added PaperPosition
from python_ai_services.models.trading_history_models import TradeRecord, TradeSide, OrderType as PaperOrderType, OrderStatus as PaperOrderStatus
from python_ai_services.main import get_simulated_trade_executor # Dependency injector
# import uuid, datetime, timezone, List, Optional, Dict, Any # Standard imports
# from fastapi.testclient import TestClient # Covered by fixture
# from unittest.mock import AsyncMock, MagicMock, call # call already imported at top
# import pytest # Covered

# --- Mock Service Fixture for SimulatedTradeExecutor ---
@pytest_asyncio.fixture
async def mock_simulated_trade_executor():
    service = MagicMock(spec=SimulatedTradeExecutor)
    service.get_open_paper_orders = AsyncMock()
    service.submit_paper_order = AsyncMock()
    service.cancel_paper_order = AsyncMock()
    service.apply_fill_to_position = AsyncMock()
    service._log_paper_trade_to_history = AsyncMock()
    return service

# --- Tests for Batch Quotes Endpoint ---

def test_get_batch_quotes_success(client: TestClient, mock_watchlist_service: MagicMock): # Uses mock_watchlist_service
    request_data = BatchQuotesRequest(symbols=["AAPL", "MSFT"], provider="test_prov")
    mock_response_items = [
        BatchQuotesResponseItem(symbol="AAPL", quote_data={"price": 150.0}),
        BatchQuotesResponseItem(symbol="MSFT", quote_data={"price": 300.0})
    ]
    mock_watchlist_service.get_batch_quotes_for_symbols.return_value = BatchQuotesResponse(results=mock_response_items)
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.post("/api/v1/quotes/batch", json=request_data.model_dump())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = BatchQuotesResponse(**response.json())
    assert len(data.results) == 2
    assert data.results[0].symbol == "AAPL"
    mock_watchlist_service.get_batch_quotes_for_symbols.assert_called_once_with(
        symbols=request_data.symbols, provider=request_data.provider
    )

def test_get_batch_quotes_service_error(client: TestClient, mock_watchlist_service: MagicMock): # Uses mock_watchlist_service
    request_data = BatchQuotesRequest(symbols=["FAIL"])
    mock_watchlist_service.get_batch_quotes_for_symbols.side_effect = Exception("Service error")
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.post("/api/v1/quotes/batch", json=request_data.model_dump())
    app.dependency_overrides.clear()
    assert response.status_code == 500
    assert "Failed to fetch batch quotes" in response.json()["detail"]


# --- Tests for Paper Trading Order Endpoints ---

def test_list_open_paper_orders_success(client: TestClient, mock_simulated_trade_executor: MagicMock):
    user_id = uuid.uuid4()
    # Constructing mock data that can be parsed by TradeRecord
    mock_orders_data = [
        {"trade_id": str(uuid.uuid4()), "user_id": str(user_id), "order_id":str(uuid.uuid4()), "symbol":"AAPL", "side":TradeSide.BUY.value, "order_type":PaperOrderType.MARKET.value, "status":PaperOrderStatus.NEW.value, "quantity_ordered":10.0, "created_at":datetime.now(timezone.utc).isoformat(), "updated_at":datetime.now(timezone.utc).isoformat(), "exchange":"PAPER_BACKTEST", "quantity_filled": 0.0}
    ]
    mock_orders_models = [TradeRecord(**data) for data in mock_orders_data]
    mock_simulated_trade_executor.get_open_paper_orders.return_value = mock_orders_models
    app.dependency_overrides[get_simulated_trade_executor] = lambda: mock_simulated_trade_executor

    response = client.get(f"/api/v1/paper-trading/orders/open/user/{user_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = [TradeRecord(**o) for o in response.json()]
    assert len(response_data) == 1
    assert response_data[0].symbol == "AAPL"
    mock_simulated_trade_executor.get_open_paper_orders.assert_called_once_with(user_id=user_id)

def test_submit_new_paper_order_success(client: TestClient, mock_simulated_trade_executor: MagicMock):
    user_id = uuid.uuid4()
    order_req_data = CreatePaperTradeOrderRequest(user_id=user_id, symbol="MSFT", side=TradeSide.BUY, order_type=PaperOrderType.MARKET, quantity=5)

    mock_order_id = uuid.uuid4()
    mock_updated_order = PaperTradeOrder(
        order_id=mock_order_id, user_id=user_id, symbol="MSFT", side=TradeSide.BUY,
        order_type=PaperOrderType.MARKET, quantity=5,
        status=PaperOrderStatus.FILLED,
        order_request_timestamp=datetime.now(timezone.utc) # Default factory will handle this in actual model
    )
    mock_fills = [PaperTradeFill(
        order_id=mock_order_id, user_id=user_id, symbol="MSFT", side=TradeSide.BUY,
        price=100.0, quantity=5, fill_timestamp=datetime.now(timezone.utc)
    )]
    mock_simulated_trade_executor.submit_paper_order.return_value = (mock_updated_order, mock_fills)

    mock_simulated_trade_executor.apply_fill_to_position = AsyncMock(return_value=MagicMock(spec=PaperPosition))
    mock_simulated_trade_executor._log_paper_trade_to_history = AsyncMock(return_value=MagicMock(spec=TradeRecord))

    app.dependency_overrides[get_simulated_trade_executor] = lambda: mock_simulated_trade_executor

    response = client.post("/api/v1/paper-trading/orders", json=order_req_data.model_dump())
    app.dependency_overrides.clear()

    assert response.status_code == 202
    data = response.json()
    assert data["message"].startswith("Paper order")
    assert data["updated_order"]["symbol"] == "MSFT"
    assert data["updated_order"]["status"] == PaperOrderStatus.FILLED.value
    assert len(data["fills"]) == 1

    mock_simulated_trade_executor.submit_paper_order.assert_called_once()
    passed_paper_order_arg = mock_simulated_trade_executor.submit_paper_order.call_args[0][0]
    assert isinstance(passed_paper_order_arg, PaperTradeOrder)
    assert passed_paper_order_arg.symbol == order_req_data.symbol

    mock_simulated_trade_executor.apply_fill_to_position.assert_called_once_with(mock_fills[0])
    mock_simulated_trade_executor._log_paper_trade_to_history.assert_called_once_with(mock_updated_order, mock_fills[0])


def test_cancel_user_paper_order_success(client: TestClient, mock_simulated_trade_executor: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()

    mock_canceled_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="GOOG", side=TradeSide.BUY,
        order_type=PaperOrderType.LIMIT, quantity=2, limit_price=100.0,
        status=PaperOrderStatus.CANCELED,
        order_request_timestamp=datetime.now(timezone.utc), notes="User Canceled"
    )
    mock_simulated_trade_executor.cancel_paper_order.return_value = mock_canceled_order
    app.dependency_overrides[get_simulated_trade_executor] = lambda: mock_simulated_trade_executor

    response = client.post(f"/api/v1/paper-trading/orders/{order_id}/user/{user_id}/cancel")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = PaperTradeOrder(**response.json())
    assert response_data.order_id == order_id
    assert response_data.status == PaperOrderStatus.CANCELED
    mock_simulated_trade_executor.cancel_paper_order.assert_called_once_with(user_id=user_id, order_id=order_id)


# Ensure these are imported if not already at the top:
# from python_ai_services.services.strategy_config_service import StrategyConfigService, StrategyConfigServiceError (StrategyConfigService is already imported)
from python_ai_services.services.strategy_config_service import StrategyConfigServiceError # Explicitly import the error
from python_ai_services.models.strategy_models import StrategyPerformanceTeaser # StrategyTimeframe already imported at top
# from python_ai_services.main import get_strategy_config_service # Already imported at top
# import uuid # Already imported
# from fastapi.testclient import TestClient # Covered by fixture
# from unittest.mock import AsyncMock, MagicMock # Covered
# import pytest # Covered
# from datetime import datetime, timezone # Already imported

# --- Mock Service Fixture for StrategyConfigService (if not already suitable one exists) ---
@pytest_asyncio.fixture
async def mock_strategy_config_service_for_api(): # Specific name to avoid clashes
    service = MagicMock(spec=StrategyConfigService)
    service.get_all_user_strategies_with_performance_teasers = AsyncMock()
    return service

# --- Tests for Strategy Performance Teasers Endpoint ---

def test_get_user_strategies_performance_teasers_success(
    client: TestClient,
    mock_strategy_config_service_for_api: MagicMock
):
    # Arrange
    user_id = uuid.uuid4()
    mock_teasers = [
        StrategyPerformanceTeaser(
            strategy_id=uuid.uuid4(), strategy_name="Test Strat 1", strategy_type="DarvasBox",
            is_active=True, symbols=["AAPL"], timeframe=StrategyTimeframe.d1,
            latest_performance_record_timestamp=datetime.now(timezone.utc),
            latest_net_profit_percentage=10.5, total_trades_from_latest_metrics=50
        ),
        StrategyPerformanceTeaser(
            strategy_id=uuid.uuid4(), strategy_name="Test Strat 2", strategy_type="SMACrossover",
            is_active=False, symbols=["MSFT"], timeframe=StrategyTimeframe.h4,
            latest_performance_record_timestamp=datetime.now(timezone.utc),
            latest_net_profit_percentage=-2.3, total_trades_from_latest_metrics=25
        )
    ]
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.return_value = mock_teasers

    app.dependency_overrides[get_strategy_config_service] = lambda: mock_strategy_config_service_for_api

    # Act
    response = client.get(f"/api/v1/strategies/user/{user_id}/performance-teasers")
    app.dependency_overrides.clear()

    # Assert
    assert response.status_code == 200
    response_data = [StrategyPerformanceTeaser(**t) for t in response.json()]
    assert len(response_data) == 2
    assert response_data[0].strategy_name == "Test Strat 1"
    assert response_data[1].is_active is False
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.assert_called_once_with(user_id=user_id)

def test_get_user_strategies_performance_teasers_empty(
    client: TestClient,
    mock_strategy_config_service_for_api: MagicMock
):
    # Arrange
    user_id = uuid.uuid4()
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.return_value = []
    app.dependency_overrides[get_strategy_config_service] = lambda: mock_strategy_config_service_for_api

    # Act
    response = client.get(f"/api/v1/strategies/user/{user_id}/performance-teasers")
    app.dependency_overrides.clear()

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.assert_called_once_with(user_id=user_id)

def test_get_user_strategies_performance_teasers_service_error(
    client: TestClient,
    mock_strategy_config_service_for_api: MagicMock
):
    # Arrange
    user_id = uuid.uuid4()
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.side_effect = StrategyConfigServiceError("DB connection lost")
    app.dependency_overrides[get_strategy_config_service] = lambda: mock_strategy_config_service_for_api

    # Act
    response = client.get(f"/api/v1/strategies/user/{user_id}/performance-teasers")
    app.dependency_overrides.clear()

    # Assert
    assert response.status_code == 500
    assert "DB connection lost" in response.json()["detail"]

# Ensure these are imported if not already at the top:
# from python_ai_services.services.watchlist_service import WatchlistService, WatchlistNotFoundError, WatchlistItemNotFoundError, WatchlistOperationForbiddenError # Already imported effectively by direct use or spec
from python_ai_services.models.watchlist_models import Watchlist, WatchlistCreate, WatchlistItem, WatchlistWithItems, AddWatchlistItemsRequest # WatchlistItemCreate also needed for some tests
from python_ai_services.main import get_watchlist_service # Dependency injector
# import uuid, datetime, timezone, List, Optional, Dict, Any # Standard imports, mostly covered
# from fastapi.testclient import TestClient # Covered by fixture
# from unittest.mock import AsyncMock, MagicMock # Covered by imports at top of file
# import pytest # Covered

# --- Mock Service Fixture for WatchlistService ---
@pytest_asyncio.fixture
async def mock_watchlist_service():
    service = MagicMock(spec=WatchlistService)
    service.create_watchlist = AsyncMock()
    service.get_watchlists_by_user = AsyncMock()
    service.get_watchlist = AsyncMock()
    service.update_watchlist = AsyncMock()
    service.delete_watchlist = AsyncMock()
    service.add_multiple_items_to_watchlist = AsyncMock()
    service.remove_item_from_watchlist = AsyncMock()
    return service

# --- Tests for Watchlist CRUD Endpoints ---

def test_create_new_watchlist_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    watchlist_data_in = WatchlistCreate(name="Crypto Majors", description="Track top cryptos")

    mock_created_watchlist = Watchlist(
        watchlist_id=uuid.uuid4(), user_id=user_id, name=watchlist_data_in.name,
        description=watchlist_data_in.description,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_watchlist_service.create_watchlist.return_value = mock_created_watchlist
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.post(f"/api/v1/watchlists/user/{user_id}", json=watchlist_data_in.model_dump())
    app.dependency_overrides.clear()

    assert response.status_code == 201
    response_data = Watchlist(**response.json())
    assert response_data.name == watchlist_data_in.name
    assert response_data.user_id == user_id
    mock_watchlist_service.create_watchlist.assert_called_once_with(user_id=user_id, data=watchlist_data_in)

def test_get_user_watchlists_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    mock_watchlists = [
        Watchlist(watchlist_id=uuid.uuid4(), user_id=user_id, name="WL1", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)),
        Watchlist(watchlist_id=uuid.uuid4(), user_id=user_id, name="WL2", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    mock_watchlist_service.get_watchlists_by_user.return_value = mock_watchlists
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.get(f"/api/v1/watchlists/user/{user_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = [Watchlist(**wl) for wl in response.json()]
    assert len(response_data) == 2
    assert response_data[0].name == "WL1"
    mock_watchlist_service.get_watchlists_by_user.assert_called_once_with(user_id=user_id)

def test_get_user_watchlist_details_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    watchlist_id = uuid.uuid4()
    mock_watchlist_with_items = WatchlistWithItems(
        watchlist_id=watchlist_id, user_id=user_id, name="Detailed WL", items=[],
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_watchlist_service.get_watchlist.return_value = mock_watchlist_with_items
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.get(f"/api/v1/watchlists/{watchlist_id}/user/{user_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = WatchlistWithItems(**response.json())
    assert response_data.watchlist_id == watchlist_id
    mock_watchlist_service.get_watchlist.assert_called_once_with(watchlist_id=watchlist_id, user_id=user_id, include_items=True)

def test_get_user_watchlist_details_not_found(client: TestClient, mock_watchlist_service: MagicMock):
    mock_watchlist_service.get_watchlist.return_value = None
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.get(f"/api/v1/watchlists/{uuid.uuid4()}/user/{uuid.uuid4()}")
    app.dependency_overrides.clear()
    assert response.status_code == 404

def test_update_user_watchlist_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    watchlist_id = uuid.uuid4()
    update_payload = WatchlistCreate(name="Updated WL Name", description="Updated desc.")

    mock_updated_wl = Watchlist(
        watchlist_id=watchlist_id, user_id=user_id, name=update_payload.name, description=update_payload.description,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_watchlist_service.update_watchlist.return_value = mock_updated_wl
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.put(f"/api/v1/watchlists/{watchlist_id}/user/{user_id}", json=update_payload.model_dump())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = Watchlist(**response.json())
    assert response_data.name == update_payload.name
    mock_watchlist_service.update_watchlist.assert_called_once_with(watchlist_id=watchlist_id, user_id=user_id, data=update_payload)

def test_delete_user_watchlist_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    watchlist_id = uuid.uuid4()
    mock_watchlist_service.delete_watchlist.return_value = None
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.delete(f"/api/v1/watchlists/{watchlist_id}/user/{user_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 204
    mock_watchlist_service.delete_watchlist.assert_called_once_with(watchlist_id=watchlist_id, user_id=user_id)

# --- Tests for Watchlist Item CRUD Endpoints ---

def test_add_items_to_watchlist_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    watchlist_id = uuid.uuid4()
    items_req_payload = AddWatchlistItemsRequest(symbols=["AAPL", "TSLA"])

    mock_created_items = [
        WatchlistItem(item_id=uuid.uuid4(), watchlist_id=watchlist_id, user_id=user_id, symbol="AAPL", added_at=datetime.now(timezone.utc)),
        WatchlistItem(item_id=uuid.uuid4(), watchlist_id=watchlist_id, user_id=user_id, symbol="TSLA", added_at=datetime.now(timezone.utc))
    ]
    mock_watchlist_service.add_multiple_items_to_watchlist.return_value = mock_created_items
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.post(f"/api/v1/watchlists/{watchlist_id}/user/{user_id}/items", json=items_req_payload.model_dump())
    app.dependency_overrides.clear()

    assert response.status_code == 201
    response_data = [WatchlistItem(**item) for item in response.json()]
    assert len(response_data) == 2
    assert response_data[0].symbol == "AAPL"
    mock_watchlist_service.add_multiple_items_to_watchlist.assert_called_once_with(watchlist_id=watchlist_id, user_id=user_id, items_request=items_req_payload)

def test_add_items_to_watchlist_not_found(client: TestClient, mock_watchlist_service: MagicMock):
    # Import specific exception for this test
    from python_ai_services.services.watchlist_service import WatchlistNotFoundError
    mock_watchlist_service.add_multiple_items_to_watchlist.side_effect = WatchlistNotFoundError("WL not found")
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    items_req_payload = AddWatchlistItemsRequest(symbols=["FAIL"])
    response = client.post(f"/api/v1/watchlists/{uuid.uuid4()}/user/{uuid.uuid4()}/items", json=items_req_payload.model_dump())
    app.dependency_overrides.clear()
    assert response.status_code == 404

def test_add_items_to_watchlist_conflict_duplicate(client: TestClient, mock_watchlist_service: MagicMock):
    # Import specific exception for this test
    from python_ai_services.services.watchlist_service import WatchlistServiceError
    mock_watchlist_service.add_multiple_items_to_watchlist.side_effect = WatchlistServiceError("Symbol already exists")
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    items_req_payload = AddWatchlistItemsRequest(symbols=["DUPE"])
    response = client.post(f"/api/v1/watchlists/{uuid.uuid4()}/user/{uuid.uuid4()}/items", json=items_req_payload.model_dump())
    app.dependency_overrides.clear()
    assert response.status_code == 409

def test_remove_item_from_watchlist_success(client: TestClient, mock_watchlist_service: MagicMock):
    user_id = uuid.uuid4()
    item_id = uuid.uuid4()
    mock_watchlist_service.remove_item_from_watchlist.return_value = None
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.delete(f"/api/v1/watchlists/items/{item_id}/user/{user_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 204
    mock_watchlist_service.remove_item_from_watchlist.assert_called_once_with(item_id=item_id, user_id=user_id)

def test_remove_item_from_watchlist_not_found(client: TestClient, mock_watchlist_service: MagicMock):
    from python_ai_services.services.watchlist_service import WatchlistItemNotFoundError
    mock_watchlist_service.remove_item_from_watchlist.side_effect = WatchlistItemNotFoundError("Item not found")
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.delete(f"/api/v1/watchlists/items/{uuid.uuid4()}/user/{uuid.uuid4()}")
    app.dependency_overrides.clear()
    assert response.status_code == 404

def test_remove_item_from_watchlist_forbidden(client: TestClient, mock_watchlist_service: MagicMock):
    from python_ai_services.services.watchlist_service import WatchlistOperationForbiddenError
    mock_watchlist_service.remove_item_from_watchlist.side_effect = WatchlistOperationForbiddenError("Forbidden")
    app.dependency_overrides[get_watchlist_service] = lambda: mock_watchlist_service

    response = client.delete(f"/api/v1/watchlists/items/{uuid.uuid4()}/user/{uuid.uuid4()}")
    app.dependency_overrides.clear()
    assert response.status_code == 403

# --- Mock Fixture for UserPreferenceService (if a distinct one is needed for API tests) ---
@pytest_asyncio.fixture
async def mock_user_preference_service_api():
    service = MagicMock(spec=UserPreferenceService)
    service.get_user_preferences = AsyncMock()
    service.update_user_preferences = AsyncMock()
    return service

# --- Tests for User Preferences API Endpoints ---

def test_get_my_user_preferences_success(client: TestClient, mock_user_preference_service_api: MagicMock):
    user_id = uuid.uuid4()
    mock_auth_user = AuthenticatedUser(id=user_id, email="test@example.com", roles=["user"])

    expected_prefs = UserPreferences(user_id=user_id, preferences={"theme": "dark"})
    mock_user_preference_service_api.get_user_preferences.return_value = expected_prefs

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_user_preference_service] = lambda: mock_user_preference_service_api

    response = client.get("/api/v1/users/me/preferences")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    # Assuming UserPreferences model can parse the response directly for validation
    prefs_data = UserPreferences(**response.json())
    assert prefs_data.user_id == user_id
    assert prefs_data.preferences == {"theme": "dark"}
    mock_user_preference_service_api.get_user_preferences.assert_called_once_with(user_id=user_id)

def test_update_my_user_preferences_success(client: TestClient, mock_user_preference_service_api: MagicMock):
    user_id = uuid.uuid4()
    mock_auth_user = AuthenticatedUser(id=user_id, email="test@example.com", roles=["user"])

    request_payload = {"theme": "light", "notifications": True}
    # Ensure the mock service returns a UserPreferences object
    expected_response_prefs = UserPreferences(user_id=user_id, preferences=request_payload, last_updated_at=datetime.now(timezone.utc))
    mock_user_preference_service_api.update_user_preferences.return_value = expected_response_prefs

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_user_preference_service] = lambda: mock_user_preference_service_api

    response = client.put("/api/v1/users/me/preferences", json=request_payload)
    app.dependency_overrides.clear()

    assert response.status_code == 200
    prefs_data = UserPreferences(**response.json())
    assert prefs_data.preferences == request_payload
    assert prefs_data.user_id == user_id
    mock_user_preference_service_api.update_user_preferences.assert_called_once_with(user_id=user_id, preferences_payload=request_payload)

def test_update_my_user_preferences_service_error(client: TestClient, mock_user_preference_service_api: MagicMock):
    user_id = uuid.uuid4()
    mock_auth_user = AuthenticatedUser(id=user_id, email="test@example.com", roles=["user"])

    request_payload = {"theme": "funky"}
    mock_user_preference_service_api.update_user_preferences.side_effect = UserPreferenceServiceError("Update failed in DB")

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_user_preference_service] = lambda: mock_user_preference_service_api

    response = client.put("/api/v1/users/me/preferences", json=request_payload)
    app.dependency_overrides.clear()

    assert response.status_code == 400 # As mapped in main.py for UserPreferenceServiceError on PUT
    assert "Update failed in DB" in response.json()["detail"]

# --- Tests for Caching on GET /api/v1/strategies/performance-teasers ---

@pytest.mark.asyncio
async def test_get_performance_teasers_cache_miss_then_hit(
    client: TestClient,
    mock_strategy_config_service_for_api: MagicMock # Existing fixture
):
    user_id = uuid.uuid4()
    mock_auth_user = AuthenticatedUser(id=user_id, email="cache@example.com", roles=["user"])

    # Mock Redis client on app.state for this test
    mock_redis_client = AsyncMock(spec=aioredis.Redis)
    mock_redis_client.get = AsyncMock(return_value=None) # Cache miss on first call
    mock_redis_client.set = AsyncMock()

    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.redis_cache_client = mock_redis_client

    # Mock service response for cache miss
    # Data as it would be after .model_dump(mode='json') for caching
    mock_teasers_data_as_dicts = [
        StrategyPerformanceTeaser(
            strategy_id=uuid.uuid4(), strategy_name="Cached Strat", strategy_type="DarvasBox",
            is_active=True, symbols=["GOOG"], timeframe=StrategyTimeframe.d1,
            latest_performance_record_timestamp=datetime.now(timezone.utc)
        ).model_dump(mode='json')
    ]
    # Service method returns list of Pydantic models
    mock_service_return_models = [
        StrategyPerformanceTeaser(**data) for data in mock_teasers_data_as_dicts
    ]
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.return_value = mock_service_return_models

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_strategy_config_service] = lambda: mock_strategy_config_service_for_api

    # 1. First call (cache miss)
    response_miss = client.get("/api/v1/strategies/performance-teasers")
    assert response_miss.status_code == 200
    # Service should be called
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.assert_called_once_with(user_id=user_id)
    # Redis get should be called
    mock_redis_client.get.assert_called_once()
    # Redis set should be called to store the result
    mock_redis_client.set.assert_called_once()

    # Ensure the data set to cache is what the service returned, serialized
    # The value passed to redis_client.set should be a JSON string representation of mock_teasers_data_as_dicts
    assert json.loads(mock_redis_client.set.call_args[0][1]) == mock_teasers_data_as_dicts


    # 2. Second call (cache hit)
    # Reset service mock call count to ensure it's not called again
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.reset_mock()
    # Simulate Redis get now returns the cached data
    # The data is stored as a JSON string of a list of dicts
    mock_redis_client.get.return_value = json.dumps(mock_teasers_data_as_dicts)

    response_hit = client.get("/api/v1/strategies/performance-teasers")
    assert response_hit.status_code == 200
    # The endpoint returns a list of Pydantic models, which TestClient serializes to JSON.
    # So, response_hit.json() will be a list of dicts.
    assert response_hit.json() == mock_teasers_data_as_dicts

    # Service should NOT be called again
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.assert_not_called()
    # Redis get was called again (total 2 times)
    assert mock_redis_client.get.call_count == 2
    # Redis set should NOT be called again (total 1 time)
    assert mock_redis_client.set.call_count == 1

    # Cleanup
    app.dependency_overrides.clear()
    if original_redis_client is not None:
        app.state.redis_cache_client = original_redis_client
    elif hasattr(app.state, 'redis_cache_client'): # If it was set to None by this test initially
        delattr(app.state, 'redis_cache_client')


@pytest.mark.asyncio
async def test_get_performance_teasers_redis_get_error(
    client: TestClient,
    mock_strategy_config_service_for_api: MagicMock
):
    user_id = uuid.uuid4()
    mock_auth_user = AuthenticatedUser(id=user_id, email="cache_err@example.com", roles=["user"])

    mock_redis_client = AsyncMock(spec=aioredis.Redis)
    mock_redis_client.get = AsyncMock(side_effect=aioredis.RedisError("Simulated Redis GET error"))
    mock_redis_client.set = AsyncMock() # Mock set as it might be called if get fails then service succeeds

    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.redis_cache_client = mock_redis_client

    # Prepare service return data (list of Pydantic models)
    mock_service_return_models = [StrategyPerformanceTeaser(strategy_id=uuid.uuid4(), strategy_name="NoCache Strat", strategy_type="SMACrossover", is_active=True, symbols=["GE"], timeframe=StrategyTimeframe.h1)]
    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.return_value = mock_service_return_models

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_strategy_config_service] = lambda: mock_strategy_config_service_for_api

    response = client.get("/api/v1/strategies/performance-teasers")

    assert response.status_code == 200 # Should fall back to service call

    # The response.json() will be a list of dicts, so compare fields
    response_json = response.json()
    assert len(response_json) == 1
    assert response_json[0]['strategy_name'] == "NoCache Strat"

    mock_strategy_config_service_for_api.get_all_user_strategies_with_performance_teasers.assert_called_once() # Service was called
    mock_redis_client.set.assert_called_once() # Attempted to cache fresh data

    # Cleanup
    app.dependency_overrides.clear()
    if original_redis_client is not None:
        app.state.redis_cache_client = original_redis_client
    elif hasattr(app.state, 'redis_cache_client'):
        delattr(app.state, 'redis_cache_client')

# TODO: Add test for Redis SET error (data fetched from service, but fails to cache)
# TODO: Add test for JSONDecodeError if cached data is malformed (should fetch fresh)

# --- Tests for Caching on GET /api/v1/visualizations/strategy ---

@pytest.mark.asyncio
async def test_get_strategy_chart_data_cache_miss_then_hit(
    client: TestClient,
    mock_viz_service: MagicMock # Existing fixture from previous tests for this endpoint
):
    user_id = uuid.uuid4()
    strategy_config_id = uuid.uuid4()
    start_date_str = "2023-02-01"
    end_date_str = "2023-02-10"

    mock_auth_user = AuthenticatedUser(id=user_id, email="vizcache@example.com", roles=["user"])

    # Mock Redis client
    mock_redis_client = AsyncMock(spec=aioredis.Redis)
    mock_redis_client.get = AsyncMock(return_value=None) # Cache miss on first call
    mock_redis_client.set = AsyncMock()

    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.redis_cache_client = mock_redis_client

    # Mock service response for cache miss
    mock_viz_response_data = StrategyVisualizationDataResponse(
        strategy_config_id=strategy_config_id,
        symbol_visualized="TSLA",
        period_start_date=date.fromisoformat(start_date_str),
        period_end_date=date.fromisoformat(end_date_str),
        ohlcv_data=[OHLCVBar(timestamp=datetime.now(timezone.utc), open=200,high=202,low=198,close=201,volume=2000)],
        generated_at=datetime.now(timezone.utc)
    )
    # The service method is what's called when cache misses
    mock_viz_service.get_strategy_visualization_data.return_value = mock_viz_response_data

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_strategy_visualization_service] = lambda: mock_viz_service

    query_params = {
        "strategy_config_id": str(strategy_config_id),
        "start_date": start_date_str,
        "end_date": end_date_str
        # user_id is not in query_params as it comes from current_user for service_request construction
    }

    # 1. First call (cache miss)
    response_miss = client.get("/api/v1/visualizations/strategy", params=query_params)
    assert response_miss.status_code == 200

    mock_viz_service.get_strategy_visualization_data.assert_called_once()
    # Check the service_request argument passed to the service
    service_call_args = mock_viz_service.get_strategy_visualization_data.call_args[1]['request']
    assert service_call_args.strategy_config_id == strategy_config_id
    assert service_call_args.user_id == user_id # User ID from token
    assert service_call_args.start_date == date.fromisoformat(start_date_str)

    mock_redis_client.get.assert_called_once() # Check specific key later if needed
    mock_redis_client.set.assert_called_once()
    # Assert data set to cache is the JSON dump of the Pydantic model
    # model_dump_json() is for Pydantic v2
    cached_value_json = mock_redis_client.set.call_args[0][1]
    assert json.loads(cached_value_json) == mock_viz_response_data.model_dump(mode='json')


    # 2. Second call (cache hit)
    mock_viz_service.get_strategy_visualization_data.reset_mock() # Reset call count for service
    # Simulate Redis get now returns the cached data
    mock_redis_client.get.return_value = mock_viz_response_data.model_dump_json()

    response_hit = client.get("/api/v1/visualizations/strategy", params=query_params)
    assert response_hit.status_code == 200
    # Compare dicts after Pydantic parsing by endpoint from cached JSON
    assert response_hit.json() == mock_viz_response_data.model_dump(mode='json')

    mock_viz_service.get_strategy_visualization_data.assert_not_called() # Service not called
    assert mock_redis_client.get.call_count == 2 # Get called again
    assert mock_redis_client.set.call_count == 1 # Set not called again

    # Cleanup
    app.dependency_overrides.clear()
    if original_redis_client is not None:
        app.state.redis_cache_client = original_redis_client
    elif hasattr(app.state, 'redis_cache_client'):
        delattr(app.state, 'redis_cache_client')


@pytest.mark.asyncio
async def test_get_strategy_chart_data_redis_get_error(
    client: TestClient,
    mock_viz_service: MagicMock
):
    user_id = uuid.uuid4()
    strategy_config_id = uuid.uuid4()
    start_date_str="2023-03-01"; end_date_str="2023-03-10"
    mock_auth_user = AuthenticatedUser(id=user_id, email="viz_err@example.com", roles=["user"])

    mock_redis_client = AsyncMock(spec=aioredis.Redis)
    mock_redis_client.get = AsyncMock(side_effect=aioredis.RedisError("Simulated Redis GET error for viz"))
    mock_redis_client.set = AsyncMock()

    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.redis_cache_client = mock_redis_client

    mock_viz_response_data = StrategyVisualizationDataResponse(
        strategy_config_id=strategy_config_id, symbol_visualized="GE",
        period_start_date=date.fromisoformat(start_date_str), period_end_date=date.fromisoformat(end_date_str),
        ohlcv_data=[], generated_at=datetime.now(timezone.utc)
    )
    mock_viz_service.get_strategy_visualization_data.return_value = mock_viz_response_data

    app.dependency_overrides[get_current_active_user] = lambda: mock_auth_user
    app.dependency_overrides[get_strategy_visualization_service] = lambda: mock_viz_service

    query_params = {"strategy_config_id": str(strategy_config_id), "start_date": start_date_str, "end_date": end_date_str}
    response = client.get("/api/v1/visualizations/strategy", params=query_params)

    assert response.status_code == 200 # Falls back to service
    assert response.json()['symbol_visualized'] == "GE" # Check data from service
    mock_viz_service.get_strategy_visualization_data.assert_called_once() # Service was called
    mock_redis_client.set.assert_called_once() # Attempted to cache fresh data

    # Cleanup
    app.dependency_overrides.clear()
    if original_redis_client is not None:
        app.state.redis_cache_client = original_redis_client
    elif hasattr(app.state, 'redis_cache_client'):
        delattr(app.state, 'redis_cache_client')

# TODO: Add tests for Redis SET error and JSONDecodeError for visualization endpoint cache.
