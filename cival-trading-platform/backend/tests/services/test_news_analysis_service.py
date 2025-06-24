import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from python_ai_services.services.news_analysis_service import NewsAnalysisService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig
from python_ai_services.models.agent_models import AgentStrategyConfig # For NewsAnalysisParams
from python_ai_services.models.event_bus_models import Event, NewsArticleEventPayload

# --- Fixtures ---
@pytest_asyncio.fixture
def mock_event_bus() -> EventBusService:
    service = AsyncMock(spec=EventBusService)
    service.publish = AsyncMock()
    return service

# Helper to create AgentConfigOutput for NewsAnalysisAgent
def create_news_agent_config(
    agent_id: str,
    rss_urls: List[str] = None,
    symbols: List[str] = None,
    pos_kw: List[str] = None,
    neg_kw: List[str] = None,
    limit_per_feed: Optional[int] = 10
) -> AgentConfigOutput:

    params_data = {}
    if rss_urls is not None: params_data["rss_feed_urls"] = rss_urls
    if symbols is not None: params_data["symbols_of_interest"] = symbols
    if pos_kw is not None: params_data["keywords_positive"] = pos_kw
    if neg_kw is not None: params_data["keywords_negative"] = neg_kw
    if limit_per_feed is not None: params_data["fetch_limit_per_feed"] = limit_per_feed

    news_params = AgentStrategyConfig.NewsAnalysisParams(**params_data)

    strategy_config = AgentStrategyConfig(
        strategy_name="NewsAnalysisStrategy",
        news_analysis_params=news_params
    )
    return AgentConfigOutput(
        agent_id=agent_id, name=f"NewsAgent_{agent_id}", agent_type="NewsAnalysisAgent",
        strategy=strategy_config, risk_config=MagicMock(), # RiskConfig not used by this service directly
        is_active=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )

# Mock feedparser.parse
def mock_feedparser_entry(title, link, summary, published_struct=None, updated_struct=None, content_value=None):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.description = summary # Often description is an alias or fallback for summary
    entry.published_parsed = published_struct
    entry.updated_parsed = updated_struct
    if content_value:
        entry.content = [MagicMock(value=content_value)] # feedparser content is a list of content objects
    else:
        entry.content = []
    return entry

# --- Test Cases ---

@pytest.mark.asyncio
async def test_news_service_init_params(mock_event_bus: MagicMock):
    custom_params = {"rss_feed_urls": ["http://custom.feed.com"], "fetch_limit_per_feed": 5}
    agent_config = create_news_agent_config("agent_custom_news", **custom_params) # type: ignore
    service = NewsAnalysisService(agent_config, mock_event_bus)
    assert service.params.rss_feed_urls == ["http://custom.feed.com"]
    assert service.params.fetch_limit_per_feed == 5

    # Test default params usage
    agent_config_default = AgentConfigOutput(
        agent_id="agent_def_news", name="DefNews", agent_type="NewsAnalysisAgent",
        strategy=AgentStrategyConfig(strategy_name="News", news_analysis_params=None), # Params explicitly None
        risk_config=MagicMock()
    )
    service_default = NewsAnalysisService(agent_config_default, mock_event_bus)
    default_model_params = AgentStrategyConfig.NewsAnalysisParams()
    assert service_default.params.rss_feed_urls == default_model_params.rss_feed_urls # Empty list
    assert service_default.params.fetch_limit_per_feed == default_model_params.fetch_limit_per_feed # 10

def test_perform_basic_sentiment():
    # Service instance needed to access _perform_basic_sentiment with its params
    agent_config = create_news_agent_config(
        "sentiment_test_agent",
        pos_kw=["good", "great"],
        neg_kw=["bad", "terrible"]
    )
    service = NewsAnalysisService(agent_config, MagicMock()) # Event bus not needed for this sync method test

    res_pos = service._perform_basic_sentiment("This is good and great news.")
    assert res_pos["score"] == 2.0
    assert res_pos["label"] == "positive"
    assert sorted(res_pos["matched"]) == sorted(["good", "great"])

    res_neg = service._perform_basic_sentiment("What a bad and terrible situation.")
    assert res_neg["score"] == -2.0
    assert res_neg["label"] == "negative"

    res_neutral = service._perform_basic_sentiment("This is standard information.")
    assert res_neutral["score"] == 0.0
    assert res_neutral["label"] == "neutral"

    res_mixed = service._perform_basic_sentiment("This is good but also bad.")
    assert res_mixed["score"] == 0.0 # 1 - 1 = 0
    assert res_mixed["label"] == "neutral"


@pytest.mark.asyncio
async def test_fetch_no_rss_urls(mock_event_bus: MagicMock):
    agent_config = create_news_agent_config("agent_no_urls", rss_urls=[])
    service = NewsAnalysisService(agent_config, mock_event_bus)
    await service.fetch_and_analyze_feeds()
    mock_event_bus.publish.assert_not_called()

@pytest.mark.asyncio
@patch('python_ai_services.services.news_analysis_service.feedparser.parse')
async def test_fetch_and_analyze_feeds_success(mock_feedparser_parse: MagicMock, mock_event_bus: MagicMock):
    agent_id = "agent_feed_success"
    rss_url = "http://test.feed.com/rss"
    symbols = ["BTC", "ETH"]
    agent_config = create_news_agent_config(agent_id, rss_urls=[rss_url], symbols=symbols)
    service = NewsAnalysisService(agent_config, mock_event_bus)

    # Mock feedparser response
    entry1_time_struct = (2023, 10, 26, 12, 0, 0, 0, 0, 0) # struct_time
    mock_feed_data = MagicMock()
    mock_feed_data.entries = [
        mock_feedparser_entry("Great news for BTC!", "http://link1.com", "Summary about BTC rally.", published_struct=entry1_time_struct, content_value="More BTC details here."),
        mock_feedparser_entry("ETH faces downgrade", "http://link2.com", "A weak outlook for ETH.", updated_struct=entry1_time_struct) # Use updated_parsed
    ]
    # feedparser.parse is called inside run_in_executor, so the mock needs to handle that if it were a real async test.
    # For unit test, directly mocking the return of parse is usually fine.
    mock_feedparser_parse.return_value = mock_feed_data

    await service.fetch_and_analyze_feeds()

    assert mock_event_bus.publish.call_count == 2

    # Call 1 (BTC)
    event1_args = mock_event_bus.publish.call_args_list[0][0][0]
    assert isinstance(event1_args, Event)
    assert event1_args.publisher_agent_id == agent_id
    assert event1_args.message_type == "NewsArticleEvent"
    payload1 = NewsArticleEventPayload(**event1_args.payload)
    assert payload1.headline == "Great news for BTC!"
    assert payload1.link == "http://link1.com"
    assert payload1.sentiment_label == "positive" # "great" is a default positive keyword
    assert "BTC" in payload1.mentioned_symbols
    assert payload1.published_date == datetime(*entry1_time_struct[:6], tzinfo=timezone.utc)


    # Call 2 (ETH)
    event2_args = mock_event_bus.publish.call_args_list[1][0][0]
    payload2 = NewsArticleEventPayload(**event2_args.payload)
    assert payload2.headline == "ETH faces downgrade"
    assert payload2.sentiment_label == "negative" # "downgrade", "weak" are default negative keywords
    assert "ETH" in payload2.mentioned_symbols


@pytest.mark.asyncio
@patch('python_ai_services.services.news_analysis_service.feedparser.parse')
async def test_fetch_feed_error(mock_feedparser_parse: MagicMock, mock_event_bus: MagicMock):
    agent_config = create_news_agent_config("agent_feed_err", rss_urls=["http://bad.feed.com"])
    service = NewsAnalysisService(agent_config, mock_event_bus)
    mock_feedparser_parse.side_effect = Exception("Network Error")

    await service.fetch_and_analyze_feeds()
    mock_event_bus.publish.assert_not_called() # Should skip on error and not publish


@pytest.mark.asyncio
@patch('python_ai_services.services.news_analysis_service.feedparser.parse')
async def test_fetch_limit_per_feed(mock_feedparser_parse: MagicMock, mock_event_bus: MagicMock):
    agent_config = create_news_agent_config("agent_limit_feed", rss_urls=["http://many.items.feed"], fetch_limit_per_feed=1)
    service = NewsAnalysisService(agent_config, mock_event_bus)

    mock_feed_data = MagicMock()
    mock_feed_data.entries = [
        mock_feedparser_entry("Title 1", "link1", "Sum1"),
        mock_feedparser_entry("Title 2", "link2", "Sum2")
    ]
    mock_feedparser_parse.return_value = mock_feed_data

    await service.fetch_and_analyze_feeds()
    assert mock_event_bus.publish.call_count == 1 # Only first entry due to limit
    payload = NewsArticleEventPayload(**mock_event_bus.publish.call_args[0][0].payload)
    assert payload.headline == "Title 1"

